// local_frame_gen.v（54 MHz 域）
// 帧缓存自检画面（设计笔记 §12 阶段 E：先用本地图案写缓存，核对地址、上下半屏边界和换帧）。
// 每 PERIOD 个时钟生成一整帧写请求（格式同 fb_writer），第 n 帧的画面：
//   - 1 像素边框
//   - 竖线 x = (4n) mod 640，横线 y = (2n) mod 480（两条线一直在移动：换帧正常时平滑移动，不撕裂）
//   - 左上角 8 个 12×16 方块显示帧号 n 的低 8 位（左边是最高位，亮 = 1）
// 上下半屏交界附近不做特殊处理：横线跨过第 239/240 行时应连续，可借此检查两半屏是否同一帧。
`timescale 1ns / 1ps
module local_frame_gen #(
    parameter integer PERIOD = 2700000      // 54 MHz / 2.7M = 20 帧/秒
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        enable,
    output reg         req_valid,
    output reg  [25:0] req
);

    localparam [1:0] T_WR = 2'd0, T_SOF = 2'd1, T_EOF = 2'd2;

    reg [21:0] timer;
    reg [7:0]  n;           // 帧号
    reg        busy;
    reg [8:0]  r;           // 当前行 0..479
    reg [6:0]  col;         // 当前字节列 0..79

    wire [9:0] n4 = {n, 2'b00};                                   // 0..1020
    wire [8:0] n2 = {n, 1'b0};                                    // 0..510
    wire [9:0] vx = (n4 >= 10'd640) ? n4 - 10'd640 : n4;          // 竖线位置 (4n) mod 640
    wire [8:0] hy = (n2 >= 9'd480)  ? n2 - 9'd480  : n2;          // 横线位置 (2n) mod 480

    function pix;
        input [9:0] x;
        input [8:0] y;
        input [7:0] fn;
        input [9:0] vline;
        input [8:0] hline;
        reg   [9:0] bx;
        reg   [3:0] k;
        begin
            pix = (x == 10'd0) || (x == 10'd639) || (y == 9'd0) || (y == 9'd479) ||
                  (x == vline) || (y == hline);
            if (y >= 9'd16 && y < 9'd32 && x >= 10'd16 && x < 10'd144) begin
                bx = x - 10'd16;
                k  = bx[7:4];                       // 第几个方块 0..7
                if (bx[3:0] < 4'd12 && fn[3'd7 - k[2:0]])
                    pix = 1'b1;
            end
        end
    endfunction

    wire [9:0] x0 = {col, 3'b000};
    wire [7:0] byte_now = {
        pix(x0 + 10'd0, r, n, vx, hy), pix(x0 + 10'd1, r, n, vx, hy),
        pix(x0 + 10'd2, r, n, vx, hy), pix(x0 + 10'd3, r, n, vx, hy),
        pix(x0 + 10'd4, r, n, vx, hy), pix(x0 + 10'd5, r, n, vx, hy),
        pix(x0 + 10'd6, r, n, vx, hy), pix(x0 + 10'd7, r, n, vx, hy)
    };

    wire        half = (r >= 9'd240);
    wire [7:0]  rr   = half ? (r - 9'd240) : r[7:0];
    wire [14:0] addr = {rr, 6'b0} + {rr, 4'b0} + col;

    always @(posedge clk) begin
        if (rst || !enable) begin
            timer     <= 22'd0;
            n         <= 8'd0;
            busy      <= 1'b0;
            r         <= 9'd0;
            col       <= 7'd0;
            req_valid <= 1'b0;
            req       <= 26'd0;
        end else begin
            req_valid <= 1'b0;
            timer     <= (timer == PERIOD - 1) ? 22'd0 : timer + 22'd1;

            if (!busy) begin
                if (timer == 22'd0) begin
                    busy      <= 1'b1;
                    r         <= 9'd0;
                    col       <= 7'd0;
                    req_valid <= 1'b1;
                    req       <= {T_SOF, 24'd0};
                end
            end else begin
                req_valid <= 1'b1;
                req       <= {T_WR, half, addr, byte_now};
                if (col == 7'd79) begin
                    col <= 7'd0;
                    if (r == 9'd479) begin
                        busy <= 1'b0;
                        n    <= n + 8'd1;
                    end else begin
                        r <= r + 9'd1;
                    end
                end else begin
                    col <= col + 7'd1;
                end
            end

            // 最后一个字节之后发 EOF
            if (!busy && req_valid && req[25:24] == T_WR) begin
                req_valid <= 1'b1;
                req       <= {T_EOF, 24'd0};
            end
        end
    end

endmodule
