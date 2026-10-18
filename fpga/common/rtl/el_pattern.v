// el_pattern.v
// 测试图案（组合逻辑）。输入组号 g (0..159) 和行号 y (0..239)，输出该组上、下半屏各 4 个像素。
// 像素坐标：x = 4g + k（k = 0 最左），上半屏行 r = y，下半屏行 r = y + 240。
// 位序（设计笔记 §8.1）：UD3 = x=4g+0（最左），UD2 = 4g+1，UD1 = 4g+2，UD0 = 4g+3；LD 同理。
// data = {UD3, UD2, UD1, UD0, LD3, LD2, LD1, LD0}；1 = 亮。
//
// 图案按点亮面积从小到大排列，首次点屏先用 0、1：
//   0 全黑
//   1 稀疏点：每 16×16 一个亮点
//   2 边框 + 左上角 32×32 实心方块 + 第 240/241 行（上下半屏交界）横线 —— 查方向、镜像、上下半屏
//   3 8×8 棋盘格
//   4 竖线：每 8 列一条 1 像素竖线
//   5 横线：每 8 行一条 1 像素横线
//   6 4 像素宽竖条、逐行反相 —— 每根数据线每个 CP2 都翻转，用于看信号完整性
//   7 全亮（电流最大）
`timescale 1ns / 1ps
module el_pattern (
    input  wire [2:0] sel,
    input  wire [7:0] group,
    input  wire [7:0] line,
    output wire [7:0] data
);

    function pix;
        input [2:0] f_sel;
        input [9:0] x;     // 0..639
        input [8:0] r;     // 0..479
        begin
            case (f_sel)
                3'd0: pix = 1'b0;
                3'd1: pix = (x[3:0] == 4'd0) && (r[3:0] == 4'd0);
                3'd2: pix = (x == 10'd0) || (x == 10'd639) || (r == 9'd0) || (r == 9'd479) ||
                            ((x < 10'd32) && (r < 9'd32)) ||
                            (r == 9'd239) || (r == 9'd240);
                3'd3: pix = x[3] ^ r[3];
                3'd4: pix = (x[2:0] == 3'd0);
                3'd5: pix = (r[2:0] == 3'd0);
                3'd6: pix = x[2] ^ r[0];
                default: pix = 1'b1;
            endcase
        end
    endfunction

    wire [9:0] x0 = {group, 2'b00};
    wire [8:0] ru = {1'b0, line};
    wire [8:0] rl = {1'b0, line} + 9'd240;

    assign data = {
        pix(sel, x0 + 10'd0, ru), pix(sel, x0 + 10'd1, ru), pix(sel, x0 + 10'd2, ru), pix(sel, x0 + 10'd3, ru),
        pix(sel, x0 + 10'd0, rl), pix(sel, x0 + 10'd1, rl), pix(sel, x0 + 10'd2, rl), pix(sel, x0 + 10'd3, rl)
    };

endmodule
