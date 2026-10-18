// 来源：tang-monitor（https://github.com/kami4ka/tang-monitor，commit 1239ace），MIT 许可，
// Copyright (c) 2026 Oleg Kulyk，许可全文见同目录 LICENSE_tang-monitor.txt。
// One TMDS data lane: LVDS input -> IDES10 -> self-aligning barrel select.
// Alignment hunts the word boundary by requiring runs of control tokens
// (which appear every blanking interval); hops offset after a long drought.
module tmds_lane_rx (
    input  wire       d_p,
    input  wire       d_n,
    input  wire       fclk,
    input  wire       pclk,
    input  wire       rst_n,
    output reg  [9:0] word,     // aligned 10-bit character
    output reg        aligned,
    output reg  [3:0] offset
);
    wire d_se;
    TLVDS_IBUF u_ibuf (.I(d_p), .IB(d_n), .O(d_se));

    wire [9:0] q;
    IDES10 u_des (
        .D(d_se), .FCLK(fclk), .PCLK(pclk), .CALIB(1'b0), .RESET(!rst_n),
        .Q0(q[0]), .Q1(q[1]), .Q2(q[2]), .Q3(q[3]), .Q4(q[4]),
        .Q5(q[5]), .Q6(q[6]), .Q7(q[7]), .Q8(q[8]), .Q9(q[9])
    );
    defparam u_des.GSREN = "false";
    defparam u_des.LSREN = "true";

    reg [9:0] w0, w1;
    always @(posedge pclk) begin
        w1 <= w0;
        w0 <= q;
    end
    wire [19:0] win = {w0, w1}; // [k+:10] = 10 consecutive stream bits

    wire [9:0] cand = win[offset +: 10];
    wire is_tok = (cand == 10'b1101010100) || (cand == 10'b0010101011) ||
                  (cand == 10'b0101010100) || (cand == 10'b1010101011);

    reg [6:0]  run;
    reg [12:0] gap;
    always @(posedge pclk or negedge rst_n) begin
        if (!rst_n) begin
            offset <= 0; aligned <= 0; run <= 0; gap <= 0; word <= 0;
        end else begin
            word <= cand;
            if (is_tok) begin
                gap <= 0;
                if (!(&run)) run <= run + 1'b1;
                if (run >= 7'd16) aligned <= 1'b1;
            end else begin
                run <= 0;
                if (&gap) begin // ~8k words with no token: wrong offset, hop
                    offset  <= (offset == 4'd9) ? 4'd0 : offset + 1'b1;
                    aligned <= 1'b0;
                    gap     <= 0;
                end else gap <= gap + 1'b1;
            end
        end
    end
endmodule
