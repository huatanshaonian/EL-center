// key_press.v
// 低有效按键：去抖后在“按下”瞬间输出一个时钟宽的脉冲。
`timescale 1ns / 1ps
module key_press #(
    parameter integer DEBOUNCE_CYCLES = 540000,   // 54 MHz 下约 10 ms
    parameter integer CNT_W           = 20
) (
    input  wire clk,
    input  wire rst,
    input  wire key_n,     // 按下 = 0
    output reg  pressed    // 按下瞬间为 1，持续一个时钟
);

    wire key_n_clean;
    reg  key_n_last;

    input_sync #(
        .STABLE_CYCLES(DEBOUNCE_CYCLES),
        .CNT_W        (CNT_W),
        .RESET_VALUE  (1'b1)
    ) u_sync (
        .clk (clk),
        .rst (rst),
        .din (key_n),
        .dout(key_n_clean)
    );

    always @(posedge clk) begin
        if (rst) begin
            key_n_last <= 1'b1;
            pressed    <= 1'b0;
        end else begin
            key_n_last <= key_n_clean;
            pressed    <= key_n_last & ~key_n_clean;
        end
    end

endmodule
