// screen_switch.v
// 斜面"屏幕"钮子开关（经电源板、EL-IF J_PF-2 → SCR_EN_3V3 → Dock J14-7）。
//   scr_en = 1：允许开屏（EL-IF 上 10k 上拉，J_PF 不插时也是 1）
//   scr_en = 0：开关关闭。EL-IF 上 D4 已经硬件拉低 EN_VD；FPGA 这边同时撤掉 VD_ON_N（vd_inhibit=1），
//              否则开关重新打开时二极管一松，VD 会在 FPGA 没准备的情况下直接上电。
// 开关重新打开后再等 RELEASE_CYCLES 才放开 vd_inhibit：扫描一直在走，这段时间保证至少几帧完整黑场/画面后才开 VD。
`timescale 1ns / 1ps
module screen_switch #(
    parameter integer DEBOUNCE_CYCLES = 1080000,    // 20 ms @ 54 MHz（钮子开关抖动）
    parameter integer RELEASE_CYCLES  = 5400000     // 100 ms @ 54 MHz（60 Hz 下约 6 帧）
) (
    input  wire clk,
    input  wire rst,
    input  wire scr_en,         // 引脚原始电平
    output reg  scr_inhibit,    // 1 = 不允许开 VD
    output wire scr_on          // 去抖后的开关状态（1 = 开），给状态显示用
);

    wire s_en;
    input_sync #(.STABLE_CYCLES(DEBOUNCE_CYCLES), .CNT_W(21), .RESET_VALUE(1'b0)) u_sync (
        .clk(clk), .rst(rst), .din(scr_en), .dout(s_en)
    );
    assign scr_on = s_en;

    reg [22:0] hold;
    always @(posedge clk) begin
        if (rst) begin
            scr_inhibit <= 1'b1;
            hold        <= 23'd0;
        end else if (!s_en) begin
            scr_inhibit <= 1'b1;
            hold        <= 23'd0;
        end else if (scr_inhibit) begin
            if (hold == RELEASE_CYCLES - 1) scr_inhibit <= 1'b0;
            else                            hold <= hold + 23'd1;
        end
    end

endmodule
