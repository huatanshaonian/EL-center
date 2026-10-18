// fb_writer.v（像素时钟域）
// 把 HDMI 解码后的有效像素转成黑白、8 像素打包成 1 字节，生成帧缓存写请求，经 FIFO 交给 54 MHz 域。
//
// 帧边界：不依赖 VSYNC 极性。DE 连续为低超过 VBLANK_GAP 个像素时钟 = 进入垂直消隐；
//         消隐后的第一个 DE 行 = 新一帧的第 0 行。
// 帧校验：每行必须正好 640 个有效像素，整帧必须正好 480 行；进入消隐时才判定，
//         合格发 EOF，否则不发（帧缓存控制会丢弃这帧）。
//
// 写请求（26 位）：{type[1:0], half, addr[14:0], data[7:0]}
//   type 0 = 写字节：half 0 = 上半屏（第 0..239 行），1 = 下半屏（第 240..479 行）；
//                    addr = 80 × (行号 mod 240) + 列号/8；data[7] = 这 8 个像素里最左的一个
//   type 1 = SOF（一帧开始） type 2 = EOF（一帧完整且合格）
// 这样每字节的高 4 位 = 偶数组（UD3..UD0 顺序），低 4 位 = 奇数组，与 el_scan_timing 的 nibble 位序一致。
`timescale 1ns / 1ps
module fb_writer #(
    parameter integer H_ACTIVE   = 640,
    parameter integer V_ACTIVE   = 480,
    parameter integer VBLANK_GAP = 1500    // > 1 行总长（800），< 垂直消隐（45 行 ≈ 36000）
) (
    input  wire        pclk,
    input  wire        rst,
    input  wire        de,
    input  wire [23:0] rgb,
    input  wire [7:0]  threshold,
    input  wire        invert,
    input  wire        dither,

    output reg         req_valid,
    output reg  [25:0] req,

    output reg  [11:0] last_h,         // 上一行有效像素数（状态显示用）
    output reg  [10:0] last_v,         // 上一帧行数
    output reg         frame_good_tgl  // 每收到一帧合格画面翻转一次
);

    localparam [1:0] T_WR = 2'd0, T_SOF = 2'd1, T_EOF = 2'd2;

    reg        de_d;
    reg [11:0] x;              // 本行已收像素数
    reg [10:0] row;            // 当前行号
    reg [11:0] gap;            // DE 连续为低的时钟数
    reg        in_vblank;
    reg        bad;            // 本帧已发现不合格
    reg        frame_open;     // 已发 SOF、尚未判定
    reg [7:0]  shreg;

    // 行开始那一拍，x/row 寄存器还是旧值：用 cur_x/cur_row 直接给出本像素的坐标
    wire        line_start = de && !de_d;
    wire [11:0] cur_x      = line_start ? 12'd0 : x;
    wire [10:0] cur_row    = line_start ? (in_vblank ? 11'd0 : row + 11'd1) : row;

    wire lit;
    pixel_mono u_mono (
        .rgb(rgb), .xm(cur_x[1:0]), .ym(cur_row[1:0]),
        .threshold(threshold), .invert(invert), .dither(dither),
        .lit(lit)
    );

    wire        half    = (cur_row >= 11'd240);
    wire [7:0]  rr      = half ? (cur_row - 11'd240) : cur_row[7:0];   // 行号 mod 240
    wire [14:0] addr    = {rr, 6'b0} + {rr, 4'b0} + cur_x[9:3];       // 80*rr + x/8
    wire [7:0]  byte_nx = {shreg[6:0], lit};                          // byte_nx[7] = 8 个里最左的像素

    always @(posedge pclk) begin
        if (rst) begin
            de_d           <= 1'b0;
            x              <= 12'd0;
            row            <= 11'd0;
            gap            <= 12'd0;
            in_vblank      <= 1'b0;
            bad            <= 1'b1;
            frame_open     <= 1'b0;
            shreg          <= 8'd0;
            req_valid      <= 1'b0;
            req            <= 26'd0;
            last_h         <= 12'd0;
            last_v         <= 11'd0;
            frame_good_tgl <= 1'b0;
        end else begin
            de_d      <= de;
            req_valid <= 1'b0;

            // ---- 垂直消隐检测与整帧判定 ----
            if (de) begin
                gap <= 12'd0;
            end else if (gap != 12'hFFF) begin
                gap <= gap + 12'd1;
                if (gap == VBLANK_GAP) begin
                    in_vblank <= 1'b1;
                    if (frame_open) begin
                        last_v     <= row + 11'd1;
                        frame_open <= 1'b0;
                        if (!bad && row == V_ACTIVE - 1) begin
                            req_valid      <= 1'b1;
                            req            <= {T_EOF, 24'd0};
                            frame_good_tgl <= ~frame_good_tgl;
                        end
                    end
                end
            end

            // ---- 行开始：新帧（消隐之后）或下一行 ----
            if (line_start) begin
                row <= cur_row;
                if (in_vblank) begin
                    in_vblank  <= 1'b0;
                    bad        <= 1'b0;
                    frame_open <= 1'b1;
                    req_valid  <= 1'b1;
                    req        <= {T_SOF, 24'd0};
                end else if (cur_row >= V_ACTIVE) begin
                    bad <= 1'b1;                       // 行数超出
                end
            end

            // ---- 有效像素：打包，每 8 个写一次 ----
            if (de) begin
                x     <= cur_x + 12'd1;
                shreg <= byte_nx;
                if (cur_x[2:0] == 3'd7 && cur_x < H_ACTIVE && !bad && frame_open) begin
                    req_valid <= 1'b1;
                    req       <= {T_WR, half, addr, byte_nx};
                end
            end

            // ---- 行结束：检查行长 ----
            if (!de && de_d) begin
                last_h <= x;
                if (x != H_ACTIVE) bad <= 1'b1;
            end
        end
    end

endmodule
