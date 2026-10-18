// el_test_top.v
// MIS-01 EL 屏测试时序（Tang Primer 20K + Dock）。只负责把各模块连起来，不放功能逻辑。
//
// 按键（低有效）：
//   btn_run_n（T10）：开机 / 关机 / 清除故障，见 el_power_seq.v
//   btn_pat_n（T3） ：切换下一个测试图案（0→7 循环），见 el_pattern.v
// 引脚分配见 el_test.cst（与 D1.1 网表 P1/P2/P3 及设计笔记 §11.2.1 一致）。
`timescale 1ns / 1ps
module el_test_top #(
    parameter integer LED_ACTIVE_LOW  = 1,        // Dock LED 低电平点亮；若实测相反改为 0
    parameter integer DEBOUNCE_CYCLES = 540000,   // 按键去抖约 10 ms
    parameter integer STATUS_FILTER   = 54,       // 状态线滤波约 1 µs
    parameter integer RESET_HOLD      = 54000,    // PLL 锁定后复位保持约 1 ms
    parameter integer OE_LEAD_CYCLES  = 54000,
    parameter integer SCAN_FRAMES     = 2,
    parameter integer VD_WAIT_CYCLES  = 54000000
) (
    input  wire       clk27,

    input  wire       btn_run_n,
    input  wire       btn_pat_n,
    output wire [3:0] led_n,

    // 到 EL-IF（3.3V，经 245 转 5V）
    output wire [3:0] el_ud,       // el_ud[0] = UD0 … el_ud[3] = UD3
    output wire [3:0] el_ld,
    output wire       el_cp2,
    output wire       el_cp1,
    output wire       el_s,
    output wire       oe_n,
    output wire       vd_on_n,

    // 来自 EL-IF / PFAIL（面包板阶段悬空，内部上拉 = 正常）
    input  wire       vd_hi_n,
    input  wire       vl_flt_n,
    input  wire       pfail_n,
    input  wire       vl_ok,
    input  wire       vd_flt_n
);

    // ---------------- 时钟与复位 ----------------
    wire clk, pll_lock, rst;

    el_pll u_pll (.clk_in(clk27), .clk_out(clk), .lock(pll_lock));
    reset_gen #(.HOLD_CYCLES(RESET_HOLD)) u_rst (.clk(clk), .lock(pll_lock), .rst(rst));

    // ---------------- 按键 ----------------
    wire run_press, pat_press;

    key_press #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES)) u_key_run (.clk(clk), .rst(rst), .key_n(btn_run_n), .pressed(run_press));
    key_press #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES)) u_key_pat (.clk(clk), .rst(rst), .key_n(btn_pat_n), .pressed(pat_press));

    // ---------------- 状态输入同步 ----------------
    // 复位值取“不安全”方向：复位期间视为 VL 不正常、PFAIL、VD 仍高，避免刚上电误开机
    wire s_vd_hi_n, s_vl_flt_n, s_pfail_n, s_vl_ok, s_vd_flt_n;

    input_sync #(.STABLE_CYCLES(STATUS_FILTER), .RESET_VALUE(1'b0)) u_in_vdhi (.clk(clk), .rst(rst), .din(vd_hi_n),  .dout(s_vd_hi_n));
    input_sync #(.STABLE_CYCLES(STATUS_FILTER), .RESET_VALUE(1'b1)) u_in_vlf  (.clk(clk), .rst(rst), .din(vl_flt_n), .dout(s_vl_flt_n));
    input_sync #(.STABLE_CYCLES(STATUS_FILTER), .RESET_VALUE(1'b0)) u_in_pf   (.clk(clk), .rst(rst), .din(pfail_n),  .dout(s_pfail_n));
    input_sync #(.STABLE_CYCLES(STATUS_FILTER), .RESET_VALUE(1'b0)) u_in_vlok (.clk(clk), .rst(rst), .din(vl_ok),    .dout(s_vl_ok));
    input_sync #(.STABLE_CYCLES(STATUS_FILTER), .RESET_VALUE(1'b1)) u_in_vdf  (.clk(clk), .rst(rst), .din(vd_flt_n), .dout(s_vd_flt_n));

    // ---------------- 图案选择 ----------------
    reg [2:0] pattern;
    reg       pattern_changed;

    always @(posedge clk) begin
        if (rst) begin
            pattern         <= 3'd0;      // 上电默认全黑
            pattern_changed <= 1'b0;
        end else begin
            pattern_changed <= pat_press;
            if (pat_press)
                pattern <= pattern + 3'd1;
        end
    end

    // ---------------- 上/下电顺序 ----------------
    wire       scan_en, scan_abort, scan_running, frame_tick;
    wire       fault, pfail_seen;
    wire [2:0] seq_state;

    el_power_seq #(
        .OE_LEAD_CYCLES(OE_LEAD_CYCLES),
        .SCAN_FRAMES   (SCAN_FRAMES),
        .VD_WAIT_CYCLES(VD_WAIT_CYCLES)
    ) u_seq (
        .clk         (clk),
        .rst         (rst),
        .btn_run     (run_press),
        .cmd_start   (1'b0),
        .cmd_stop    (1'b0),
        .vd_inhibit  (1'b0),
        .vl_ok       (s_vl_ok),
        .pfail_n     (s_pfail_n),
        .vd_flt_n    (s_vd_flt_n),
        .vl_flt_n    (s_vl_flt_n),
        .vd_hi_n     (s_vd_hi_n),
        .frame_tick  (frame_tick),
        .scan_running(scan_running),
        .scan_en     (scan_en),
        .scan_abort  (scan_abort),
        .oe_n        (oe_n),
        .vd_on_n     (vd_on_n),
        .state       (seq_state),
        .fault       (fault),
        .pfail_seen  (pfail_seen)
    );

    // ---------------- 扫描时序与图案 ----------------
    wire [7:0] pat_group, pat_line, pat_data;

    el_pattern u_pat (.sel(pattern), .group(pat_group), .line(pat_line), .data(pat_data));

    el_scan_timing u_scan (
        .clk       (clk),
        .rst       (rst),
        .scan_en   (scan_en),
        .abort     (scan_abort),
        .line_ticks(12'd3750),
        .pat_group (pat_group),
        .pat_line  (pat_line),
        .pat_data  (pat_data),
        .cp2       (el_cp2),
        .cp1       (el_cp1),
        .s         (el_s),
        .ud        (el_ud),          // [3:0] = {UD3,UD2,UD1,UD0}，与引脚向量位号一致
        .ld        (el_ld),
        .running   (scan_running),
        .frame_tick(frame_tick),
        .swap_ok   ()
    );

    // ---------------- LED ----------------
    wire [5:0] led_on;

    led_status u_led (
        .clk            (clk),
        .rst            (rst),
        .oe_n           (oe_n),
        .scanning       (scan_running),
        .vd_on_n        (vd_on_n),
        .fault          (fault),
        .pfail_seen     (pfail_seen),
        .hdmi_locked    (1'b0),
        .video_shown    (1'b0),
        .frame_swap     (1'b0),
        .show_value     ({1'b0, pattern}),
        .show_pulse     (pattern_changed),
        .led            (led_on)
    );

    assign led_n = LED_ACTIVE_LOW ? ~led_on[3:0] : led_on[3:0];

endmodule
