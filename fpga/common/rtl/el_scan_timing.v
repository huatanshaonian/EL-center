// el_scan_timing.v
// LJ64K052 双扫描时序发生器（设计笔记 §8.2/§8.3）。默认 54 MHz 时钟，1 tick = 18.52 ns。
//
// 一个“行周期”= line_ticks 个 tick，从上一行的 CP1↓ 开始：
//   t = CP2_START + 10n      CP2↑（n = 0..159）
//   t = CP2_START + 10n + 5  CP2↓，屏在此沿采样数据
//   t = 行周期 - CP1_HIGH     CP1↑；行周期结束（下一行 t=0）CP1↓，锁存本行
//   刚传完的是第 0 行时，S 跨这一次 CP1↓ 为高（帧起始）。
// 数据在每个 CP2↑ 之前 1 tick 更换：对 CP2↓ 建立 6 tick（111 ns）、保持 4 tick（74 ns）。
// line_ticks = 3750 → 69.44 µs/行、60.0 Hz；1875 → 34.72 µs/行、120 Hz。每帧开始时采样一次。
//
// 取数接口（预取，适配有读延迟的 RAM）：
//   pat_group/pat_line 给出“下一组要用的”组号和行号，pat_data 须在地址变化后 PREFETCH_MIN 个时钟内稳定。
//   本模块在以下时刻装载 pat_data：
//     第 0 组：t = CP2_START-1（地址 g=0 从 t=0 起有效，可用 7 个时钟）
//     第 n 组：第 n-1 组的最后一个 tick（地址 g=n 从第 n-1 组开始起有效，可用 9 个时钟）
//   所以数据源（含 RAM）从地址到数据的延迟必须 ≤ 6 个时钟。
//
// 起停：
//   scan_en 1 → 从第 0 行开始扫描；scan_en 0 → 扫完当前整帧后停止。abort 1 → 立即停止。停止期间全部输出为低。
// 状态输出：
//   frame_tick 每扫完一整帧（锁存第 239 行）脉冲一次
//   swap_ok    最后一行的数据全部取完时脉冲一次：帧缓存可以在此刻换帧，下一帧从第 0 行起读新缓冲
`timescale 1ns / 1ps
module el_scan_timing #(
    parameter integer CP2_HALF  = 5,     // CP2 高、低各几个 tick
    parameter integer GROUPS    = 160,   // 每行 CP2 个数
    parameter integer LINES     = 240,   // 每帧行对数
    parameter integer CP2_START = 8,     // CP1↓ 到首个 CP2↑（tS13 ≥ 100 ns；再加 CP2_HALF 满足 tS12 ≥ 200 ns）
    parameter integer CP1_HIGH  = 8,     // CP1 高电平宽度（≥ 60 ns）
    parameter integer S_LEAD    = 16,    // S 在 CP1↑ 之前多少 tick 变高（S 建立 ≥ 50 ns）
    parameter integer S_HOLD    = 4,     // S 在 CP1↓ 之后保持多少 tick（≥ 40 ns，且 < CP2_START）
    parameter integer MIN_LINE  = 1700   // 行周期下限（tick）；也满足 CP1 周期 ≥ 31 µs（1674）
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        scan_en,
    input  wire        abort,
    input  wire [11:0] line_ticks,

    output wire [7:0]  pat_group,
    output wire [7:0]  pat_line,
    input  wire [7:0]  pat_data,     // {UD3,UD2,UD1,UD0, LD3,LD2,LD1,LD0}

    output reg         cp2,
    output reg         cp1,
    output reg         s,
    output reg  [3:0]  ud,           // ud[3] = UD3 = 每组最左像素
    output reg  [3:0]  ld,

    output reg         running,
    output reg         frame_tick,
    output reg         swap_ok
);

    localparam integer SHIFT_END = CP2_START + GROUPS * 2 * CP2_HALF;   // 移位窗口结束（不含）
    localparam integer PH_LAST   = 2 * CP2_HALF - 1;

    reg [11:0] t;       // 行内 tick
    reg [11:0] lt;      // 本帧使用的行周期
    reg [3:0]  ph;      // CP2 周期内相位 0..PH_LAST
    reg [7:0]  g;       // 当前组号
    reg [7:0]  y;       // 行号 0..LINES-1

    wire [11:0] lt_req   = (line_ticks < MIN_LINE) ? MIN_LINE[11:0] : line_ticks;
    wire in_shift  = (t >= CP2_START) && (t < SHIFT_END);
    wire line_end  = (t == lt - 12'd1);
    wire last_line = (y == LINES - 1);
    wire load_first = (t == CP2_START - 1);
    wire load_next  = in_shift && (ph == PH_LAST);
    wire last_group = (g == GROUPS - 1);

    // 预取地址：移位窗口之前给第 0 组，窗口内给“下一组”（最后一组之后给 0，保持地址在范围内）
    assign pat_group = !in_shift ? 8'd0 : (last_group ? 8'd0 : g + 8'd1);
    assign pat_line  = y;

    always @(posedge clk) begin
        if (rst) begin
            t          <= 12'd0;
            lt         <= 12'd3750;
            ph         <= 4'd0;
            g          <= 8'd0;
            y          <= 8'd0;
            running    <= 1'b0;
            frame_tick <= 1'b0;
            swap_ok    <= 1'b0;
            cp2        <= 1'b0;
            cp1        <= 1'b0;
            s          <= 1'b0;
            ud         <= 4'd0;
            ld         <= 4'd0;
        end else begin
            frame_tick <= 1'b0;
            swap_ok    <= 1'b0;

            if (!running || abort) begin
                t   <= 12'd0;
                ph  <= 4'd0;
                g   <= 8'd0;
                y   <= 8'd0;
                lt  <= lt_req;
                cp2 <= 1'b0;
                cp1 <= 1'b0;
                s   <= 1'b0;
                ud  <= 4'd0;
                ld  <= 4'd0;
                if (abort)
                    running <= 1'b0;
                else if (scan_en)
                    running <= 1'b1;
            end else begin
                // ---- 本 tick 的输出 ----
                cp2 <= in_shift && (ph < CP2_HALF);
                if (load_first || (load_next && !last_group)) begin
                    ud <= pat_data[7:4];
                    ld <= pat_data[3:0];
                end else if (load_next && last_group) begin
                    ud <= 4'd0;
                    ld <= 4'd0;
                end
                cp1 <= (t >= lt - CP1_HIGH);
                s   <= ((y == 8'd0) && (t >= lt - CP1_HIGH - S_LEAD)) ||
                       ((y == 8'd1) && (t < S_HOLD));
                if (last_line && (t == SHIFT_END + 1))
                    swap_ok <= 1'b1;

                // ---- 计数器推进 ----
                if (in_shift) begin
                    if (ph == PH_LAST) begin
                        ph <= 4'd0;
                        g  <= g + 8'd1;
                    end else begin
                        ph <= ph + 4'd1;
                    end
                end

                if (line_end) begin
                    t  <= 12'd0;
                    ph <= 4'd0;
                    g  <= 8'd0;
                    if (last_line) begin
                        y          <= 8'd0;
                        lt         <= lt_req;       // 帧率只在帧边界切换
                        frame_tick <= 1'b1;
                        if (!scan_en)
                            running <= 1'b0;        // 整帧结束后才停
                    end else begin
                        y <= y + 8'd1;
                    end
                end else begin
                    t <= t + 12'd1;
                end
            end
        end
    end

endmodule
