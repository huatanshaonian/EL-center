// 来源：tang-monitor（https://github.com/kami4ka/tang-monitor，commit 1239ace），MIT 许可，
// Copyright (c) 2026 Oleg Kulyk，许可全文见同目录 LICENSE_tang-monitor.txt。
// Minimal UART transmitter, 8N1.
module uart_tx #(
    parameter CLK_HZ = 27_000_000,
    parameter BAUD   = 115_200
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] data,
    input  wire       valid,
    output reg        ready,
    output reg        txd
);
    localparam integer DIV = CLK_HZ / BAUD;

    reg [15:0] baud_cnt;
    reg [3:0]  bit_idx;   // 0=start, 1..8=data, 9=stop
    reg [9:0]  shifter;
    reg        busy;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            txd      <= 1'b1;
            busy     <= 1'b0;
            ready    <= 1'b1;
            baud_cnt <= 0;
            bit_idx  <= 0;
            shifter  <= 10'h3FF;
        end else begin
            if (!busy) begin
                if (valid) begin
                    shifter  <= {1'b1, data, 1'b0}; // stop, data LSB-first, start
                    busy     <= 1'b1;
                    ready    <= 1'b0;
                    baud_cnt <= 0;
                    bit_idx  <= 0;
                end
            end else begin
                if (baud_cnt == DIV - 1) begin
                    baud_cnt <= 0;
                    txd      <= shifter[0];
                    shifter  <= {1'b1, shifter[9:1]};
                    if (bit_idx == 4'd9) begin
                        busy  <= 1'b0;
                        ready <= 1'b1;
                    end else begin
                        bit_idx <= bit_idx + 1'b1;
                    end
                end else begin
                    baud_cnt <= baud_cnt + 1'b1;
                end
            end
        end
    end
endmodule
