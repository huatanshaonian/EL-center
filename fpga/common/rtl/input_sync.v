// input_sync.v
// 外部输入的同步与滤波：两级触发器同步到本时钟域，输入必须连续 STABLE_CYCLES 个时钟保持新值，输出才跟着变。
// 用途：按键去抖（约 10 ms）、状态线（PFAIL_N / VL_OK / FLT_N / VD_HI_N）滤掉短毛刺（约 1 µs）。
`timescale 1ns / 1ps
module input_sync #(
    parameter integer STABLE_CYCLES = 54,     // 需 >= 1，且 < 2^CNT_W
    parameter integer CNT_W         = 8,
    parameter         RESET_VALUE   = 1'b1    // 复位期间输出值（低有效信号取 1 = 不动作）
) (
    input  wire clk,
    input  wire rst,
    input  wire din,
    output reg  dout
);

    reg             s1, s2;
    reg [CNT_W-1:0] cnt;

    always @(posedge clk) begin
        if (rst) begin
            s1   <= RESET_VALUE;
            s2   <= RESET_VALUE;
            cnt  <= {CNT_W{1'b0}};
            dout <= RESET_VALUE;
        end else begin
            s1 <= din;
            s2 <= s1;
            if (s2 == dout) begin
                cnt <= {CNT_W{1'b0}};
            end else if (cnt == STABLE_CYCLES - 1) begin
                cnt  <= {CNT_W{1'b0}};
                dout <= s2;
            end else begin
                cnt <= cnt + 1'b1;
            end
        end
    end

endmodule
