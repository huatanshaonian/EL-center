// pixel_mono.v
// RGB888 → 1 位黑白（组合逻辑），设计笔记 §7.4。
//   亮度 Y = (77·R + 150·G + 29·B) >> 8
//   阈值模式（dither=0）：亮 = Y >= threshold
//   抖动模式（dither=1）：4×4 Bayer 有序抖动，threshold 作亮度偏移（128 = 不偏移）：
//                         亮 = (Y + 128 - threshold，限制在 0..255) > Bayer[ym][xm]*16 + 8
//   invert=1 时输出取反。1 = 屏上该像素亮。
`timescale 1ns / 1ps
module pixel_mono (
    input  wire [23:0] rgb,        // {R, G, B}
    input  wire [1:0]  xm,         // x mod 4
    input  wire [1:0]  ym,         // 行号 mod 4
    input  wire [7:0]  threshold,
    input  wire        invert,
    input  wire        dither,
    output wire        lit
);

    wire [7:0] r = rgb[23:16];
    wire [7:0] g = rgb[15:8];
    wire [7:0] b = rgb[7:0];

    wire [15:0] y_sum = r * 8'd77 + g * 8'd150 + b * 8'd29;   // 最大 255*256 = 65280
    wire [7:0]  luma  = y_sum[15:8];

    // 抖动：亮度偏移后与 Bayer 门限比较
    wire [9:0] adj_raw = {2'b00, luma} + 10'd128 - {2'b00, threshold};   // 范围 -127..383（10 位补码）
    wire [7:0] adj     = adj_raw[9] ? 8'd0 : (adj_raw[8] ? 8'd255 : adj_raw[7:0]);

    reg [3:0] bayer;
    always @(*) begin
        case ({ym, xm})
            4'h0: bayer = 4'd0;   4'h1: bayer = 4'd8;   4'h2: bayer = 4'd2;   4'h3: bayer = 4'd10;
            4'h4: bayer = 4'd12;  4'h5: bayer = 4'd4;   4'h6: bayer = 4'd14;  4'h7: bayer = 4'd6;
            4'h8: bayer = 4'd3;   4'h9: bayer = 4'd11;  4'hA: bayer = 4'd1;   4'hB: bayer = 4'd9;
            4'hC: bayer = 4'd15;  4'hD: bayer = 4'd7;   4'hE: bayer = 4'd13;  default: bayer = 4'd5;
        endcase
    end
    wire [7:0] bayer_thr = {bayer, 4'b1000};   // bayer*16 + 8

    wire on_thr    = (luma >= threshold);
    wire on_dither = (adj > bayer_thr);

    assign lit = (dither ? on_dither : on_thr) ^ invert;

endmodule
