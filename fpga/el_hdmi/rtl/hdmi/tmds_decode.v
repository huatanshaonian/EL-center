// 来源：tang-monitor（https://github.com/kami4ka/tang-monitor，commit 1239ace），MIT 许可，
// Copyright (c) 2026 Oleg Kulyk，许可全文见同目录 LICENSE_tang-monitor.txt。
// TMDS 3-lane decoder: control tokens -> DE/HS/VS (lane 0), data -> RGB888.
// Per DVI 1.0 spec: if w[9] invert w[7:0]; then w[8] selects XOR/XNOR undo.
module tmds_decode (
    input  wire        pclk,
    input  wire        rst_n,
    input  wire [9:0]  c0,   // blue + syncs
    input  wire [9:0]  c1,   // green
    input  wire [9:0]  c2,   // red
    output reg  [23:0] rgb,  // {r,g,b}
    output reg         de,
    output reg         hs,
    output reg         vs
);
    function [7:0] dec8(input [9:0] w);
        reg [7:0] d;
        integer i;
        begin
            d = w[9] ? ~w[7:0] : w[7:0];
            dec8[0] = d[0];
            for (i = 1; i < 8; i = i + 1)
                dec8[i] = w[8] ? (d[i] ^ d[i-1]) : ~(d[i] ^ d[i-1]);
        end
    endfunction

    function is_tok(input [9:0] w);
        begin
            is_tok = (w == 10'b1101010100) || (w == 10'b0010101011) ||
                     (w == 10'b0101010100) || (w == 10'b1010101011);
        end
    endfunction

    function [1:0] tok_c(input [9:0] w); // {C1,C0}
        begin
            case (w)
            10'b1101010100: tok_c = 2'b00;
            10'b0010101011: tok_c = 2'b01;
            10'b0101010100: tok_c = 2'b10;
            default:        tok_c = 2'b11; // 1010101011
            endcase
        end
    endfunction

    wire [1:0] c0_ctl = tok_c(c0);

    always @(posedge pclk or negedge rst_n) begin
        if (!rst_n) begin
            rgb <= 0; de <= 0; hs <= 0; vs <= 0;
        end else begin
            if (is_tok(c0)) begin
                de <= 1'b0;
                hs <= c0_ctl[0];
                vs <= c0_ctl[1];
            end else begin
                de  <= 1'b1;
                rgb <= {dec8(c2), dec8(c1), dec8(c0)};
            end
        end
    end
endmodule
