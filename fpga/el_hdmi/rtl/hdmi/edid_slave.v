// 来源：tang-monitor（https://github.com/kami4ka/tang-monitor，commit 1239ace），MIT 许可，
// Copyright (c) 2026 Oleg Kulyk，许可全文见同目录 LICENSE_tang-monitor.txt。
// I2C slave serving a 128-byte EDID ROM at address 0x50 (DDC).
// Also ACKs the E-DDC segment pointer at 0x30 (segment 0 only is served).
// clk domain: clk27. SCL is never stretched. SDA is open-drain via sda_oe.
//
// Event log interface: one-cycle strobes with a tag byte for the DDC monitor.
module edid_slave #(
    parameter ROM_INIT = "edid/edid_640x480.hex"
) (
    input  wire clk,
    input  wire rst_n,
    input  wire scl_i,
    input  wire sda_i,
    output reg  sda_oe,       // 1 = pull SDA low
    // debug event stream
    output reg        ev_valid,
    output reg  [7:0] ev_tag,   // 'S' start, 'P' stop, 'A' addr, 'W' wr, 'R' rd, 'N' nak-addr
    output reg  [7:0] ev_data
);
    reg [7:0] rom [0:127];
    initial $readmemh(ROM_INIT, rom);

    // --- input conditioning: 2FF sync + 4-sample majority filter ---
    reg [1:0] scl_s, sda_s;
    always @(posedge clk) begin
        scl_s <= {scl_s[0], scl_i};
        sda_s <= {sda_s[0], sda_i};
    end
    reg [3:0] scl_f, sda_f;
    reg scl_q, sda_q;
    always @(posedge clk) begin
        scl_f <= {scl_f[2:0], scl_s[1]};
        sda_f <= {sda_f[2:0], sda_s[1]};
        if (scl_f == 4'b1111) scl_q <= 1'b1;
        else if (scl_f == 4'b0000) scl_q <= 1'b0;
        if (sda_f == 4'b1111) sda_q <= 1'b1;
        else if (sda_f == 4'b0000) sda_q <= 1'b0;
    end

    reg scl_d, sda_d;
    always @(posedge clk) begin
        scl_d <= scl_q;
        sda_d <= sda_q;
    end
    wire scl_rise = scl_q & ~scl_d;
    wire scl_fall = ~scl_q & scl_d;
    wire start_cond = scl_q & scl_d & sda_d & ~sda_q; // SDA falls while SCL high
    wire stop_cond  = scl_q & scl_d & ~sda_d & sda_q; // SDA rises while SCL high

    // --- FSM ---
    localparam ST_IDLE  = 3'd0;
    localparam ST_ADDR  = 3'd1;
    localparam ST_AACK  = 3'd2;
    localparam ST_WBYTE = 3'd3;
    localparam ST_WACK  = 3'd4;
    localparam ST_RBYTE = 3'd5;
    localparam ST_RACK  = 3'd6;

    reg [2:0] state;
    reg [7:0] shifter;
    reg [3:0] bitcnt;
    reg [7:0] offset;      // EDID word offset (auto-increment)
    reg       tgt_edid;    // transaction targets 0x50
    reg       tgt_seg;     // transaction targets 0x30
    reg       seg_byte;    // next written byte is the segment pointer

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= ST_IDLE; sda_oe <= 0; bitcnt <= 0; shifter <= 0;
            offset <= 0; tgt_edid <= 0; tgt_seg <= 0; seg_byte <= 0;
            ev_valid <= 0; ev_tag <= 0; ev_data <= 0;
        end else begin
            ev_valid <= 1'b0;
            if (start_cond) begin
                state  <= ST_ADDR;
                bitcnt <= 0;
                sda_oe <= 0;
                ev_valid <= 1'b1; ev_tag <= "S"; ev_data <= 0;
            end else if (stop_cond) begin
                state  <= ST_IDLE;
                sda_oe <= 0;
                tgt_edid <= 0; tgt_seg <= 0; seg_byte <= 0;
                ev_valid <= 1'b1; ev_tag <= "P"; ev_data <= 0;
            end else begin
                case (state)
                ST_ADDR: begin
                    if (scl_rise) begin
                        shifter <= {shifter[6:0], sda_q};
                        bitcnt  <= bitcnt + 1'b1;
                    end
                    if (bitcnt == 8 && scl_fall) begin
                        bitcnt <= 0;
                        ev_valid <= 1'b1; ev_tag <= "A"; ev_data <= shifter;
                        if (shifter[7:1] == 7'h50) begin
                            tgt_edid <= 1'b1; tgt_seg <= 1'b0;
                            sda_oe <= 1'b1; // ACK
                            state  <= ST_AACK;
                        end else if (shifter[7:1] == 7'h30 && !shifter[0]) begin
                            tgt_seg <= 1'b1; tgt_edid <= 1'b0; seg_byte <= 1'b1;
                            sda_oe <= 1'b1; // ACK
                            state  <= ST_AACK;
                        end else begin
                            state <= ST_IDLE; // not ours, stay quiet
                            ev_tag <= "N";
                        end
                    end
                end
                ST_AACK: begin
                    if (scl_fall) begin
                        sda_oe <= 1'b0;
                        if (tgt_edid && shifter[0]) begin
                            // read: preload first data bit
                            state   <= ST_RBYTE;
                            shifter <= rom[offset[6:0]];
                            sda_oe  <= ~rom[offset[6:0]][7]; // drive MSB
                            bitcnt  <= 1;
                        end else begin
                            state  <= ST_WBYTE;
                            bitcnt <= 0;
                        end
                    end
                end
                ST_WBYTE: begin
                    if (scl_rise) begin
                        shifter <= {shifter[6:0], sda_q};
                        bitcnt  <= bitcnt + 1'b1;
                    end
                    if (bitcnt == 8 && scl_fall) begin
                        bitcnt <= 0;
                        sda_oe <= 1'b1; // ACK the byte
                        state  <= ST_WACK;
                        if (seg_byte) seg_byte <= 1'b0; // segment value: ignored (only seg 0)
                        else if (tgt_edid) offset <= shifter;
                        ev_valid <= 1'b1; ev_tag <= "W"; ev_data <= shifter;
                    end
                end
                ST_WACK: begin
                    if (scl_fall) begin
                        sda_oe <= 1'b0;
                        state  <= ST_WBYTE;
                    end
                end
                ST_RBYTE: begin
                    if (scl_fall) begin
                        if (bitcnt == 8) begin
                            // release for master ACK
                            sda_oe <= 1'b0;
                            state  <= ST_RACK;
                            ev_valid <= 1'b1; ev_tag <= "R"; ev_data <= rom[offset[6:0]];
                            offset <= offset + 1'b1;
                        end else begin
                            sda_oe <= ~shifter[6];
                            shifter <= {shifter[6:0], 1'b0};
                            bitcnt  <= bitcnt + 1'b1;
                        end
                    end
                end
                ST_RACK: begin
                    if (scl_rise) shifter[7] <= sda_q; // master ACK=0 / NAK=1
                    if (scl_fall) begin
                        if (shifter[7]) begin
                            state <= ST_IDLE; // NAK: master is done
                        end else begin
                            state   <= ST_RBYTE;
                            sda_oe  <= ~rom[offset[6:0]][7];
                            shifter <= rom[offset[6:0]]; // unshifted, as in AACK path
                            bitcnt  <= 1;
                        end
                    end
                end
                default: state <= ST_IDLE;
                endcase
            end
        end
    end
endmodule
