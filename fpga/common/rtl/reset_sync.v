// reset_sync.v
// 复位同步器：rst_in 为高时立即（异步）置位 rst_out，rst_in 撤销后在 clk 下经 STAGES 级同步才释放。
// 用于把同一个复位源分别送到多个时钟域（时钟停着也能复位）。
`timescale 1ns / 1ps
module reset_sync #(
    parameter integer STAGES = 3
) (
    input  wire clk,
    input  wire rst_in,
    output wire rst_out
);

    reg [STAGES-1:0] sr;

    always @(posedge clk or posedge rst_in) begin
        if (rst_in) sr <= {STAGES{1'b1}};
        else        sr <= {sr[STAGES-2:0], 1'b0};
    end

    assign rst_out = sr[STAGES-1];

endmodule
