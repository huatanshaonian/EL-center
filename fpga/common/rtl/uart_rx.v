// 来源：tang-monitor（https://github.com/kami4ka/tang-monitor，commit 1239ace），MIT 许可，
// Copyright (c) 2026 Oleg Kulyk，许可全文见同目录 LICENSE_tang-monitor.txt。
// Minimal UART receiver, 8N1, 2-FF input sync, mid-bit sampling.
module uart_rx #(
    parameter CLK_HZ = 27_000_000,
    parameter BAUD   = 115_200
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       rxd,
    output reg  [7:0] data,
    output reg        valid   // 1-cycle strobe
);
    localparam integer DIV = CLK_HZ / BAUD;

    reg [1:0]  sync;
    wire       rx = sync[1];
    reg [15:0] baud_cnt;
    reg [3:0]  bit_idx;
    reg [7:0]  shifter;
    reg        busy;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sync     <= 2'b11;
            busy     <= 1'b0;
            valid    <= 1'b0;
            baud_cnt <= 0;
            bit_idx  <= 0;
            data     <= 0;
            shifter  <= 0;
        end else begin
            sync  <= {sync[0], rxd};
            valid <= 1'b0;
            if (!busy) begin
                if (!rx) begin // start edge
                    busy     <= 1'b1;
                    baud_cnt <= DIV / 2; // sample mid-bit
                    bit_idx  <= 0;
                end
            end else begin
                if (baud_cnt == DIV - 1) begin
                    baud_cnt <= 0;
                    if (bit_idx == 0) begin
                        if (rx) busy <= 1'b0; // false start
                        bit_idx <= 1;
                    end else if (bit_idx <= 4'd8) begin
                        shifter <= {rx, shifter[7:1]};
                        bit_idx <= bit_idx + 1'b1;
                    end else begin // stop bit
                        busy <= 1'b0;
                        if (rx) begin
                            data  <= shifter;
                            valid <= 1'b1;
                        end
                    end
                end else begin
                    baud_cnt <= baud_cnt + 1'b1;
                end
            end
        end
    end
endmodule
