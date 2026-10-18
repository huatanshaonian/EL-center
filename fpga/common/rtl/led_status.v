// led_status.v
// Dock 板 LED 的含义（led[0..5] 依次接约束文件里的 LED0..LED5；测试程序只接 LED0..LED3）：
//   led[0] = OE 已使能（OE_N=0）
//   led[1] = 正在扫描
//   led[2] = VD_ON_N=0（面包板阶段：现在可以手动开 VD）
//   led[3] = 故障快闪（4 Hz）；发生过 PFAIL 慢闪（1 Hz）
//   led[4] = HDMI 已锁定（PLL 锁定且三条通道对齐）
//   led[5] = 正在显示 HDMI 视频；每换一帧新画面翻转一次（有画面更新时闪烁）
//   show_pulse 后 1 秒内，led[3:0] 改为显示 show_value（二进制，led[0] = 最低位），用于提示当前信号源/图案号。
`timescale 1ns / 1ps
module led_status #(
    parameter integer CLK_HZ = 54000000
) (
    input  wire       clk,
    input  wire       rst,
    input  wire       oe_n,
    input  wire       scanning,
    input  wire       vd_on_n,
    input  wire       fault,
    input  wire       pfail_seen,
    input  wire       hdmi_locked,
    input  wire       video_shown,
    input  wire       frame_swap,     // 脉冲：换上了一帧新画面
    input  wire [3:0] show_value,
    input  wire       show_pulse,
    output wire [5:0] led             // 1 = 亮（极性在顶层处理）
);

    localparam integer FAST_HALF = CLK_HZ / 8;   // 4 Hz 闪烁的半周期
    localparam integer SHOW_TIME = CLK_HZ;       // 显示 1 s

    reg [26:0] blink_cnt;
    reg [2:0]  blink_div;     // blink_div[0] = 4 Hz，blink_div[2] = 1 Hz
    reg [26:0] show_cnt;
    reg        swap_tgl;

    always @(posedge clk) begin
        if (rst) begin
            blink_cnt <= 27'd0;
            blink_div <= 3'd0;
            show_cnt  <= 27'd0;
            swap_tgl  <= 1'b0;
        end else begin
            if (blink_cnt == FAST_HALF - 1) begin
                blink_cnt <= 27'd0;
                blink_div <= blink_div + 3'd1;
            end else begin
                blink_cnt <= blink_cnt + 27'd1;
            end

            if (show_pulse)
                show_cnt <= SHOW_TIME;
            else if (show_cnt != 27'd0)
                show_cnt <= show_cnt - 27'd1;

            if (frame_swap)
                swap_tgl <= ~swap_tgl;
        end
    end

    wire showing = (show_cnt != 27'd0);
    wire alarm   = fault ? blink_div[0] : (pfail_seen ? blink_div[2] : 1'b0);

    assign led[3:0] = showing ? show_value : {alarm, ~vd_on_n, scanning, ~oe_n};
    assign led[4]   = hdmi_locked;
    assign led[5]   = video_shown & ~swap_tgl;

endmodule
