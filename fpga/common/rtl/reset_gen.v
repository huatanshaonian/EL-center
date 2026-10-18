// reset_gen.v
// 上电复位：PLL 未锁定时立即复位（异步置位），锁定后再保持 HOLD_CYCLES 个时钟才释放（同步释放）。
// 复位期间所有 EL 输出为低、OE_N 为高、VD_ON_N 为高（由各模块的复位值保证）。
`timescale 1ns / 1ps
module reset_gen #(
    parameter integer HOLD_CYCLES = 54000   // 54 MHz 下约 1 ms，须 < 65536
) (
    input  wire clk,
    input  wire lock,
    output reg  rst
);

    reg [15:0] cnt;

    always @(posedge clk or negedge lock) begin
        if (!lock) begin
            cnt <= 16'd0;
            rst <= 1'b1;
        end else if (cnt != HOLD_CYCLES) begin
            cnt <= cnt + 16'd1;
            rst <= 1'b1;
        end else begin
            rst <= 1'b0;
        end
    end

endmodule
