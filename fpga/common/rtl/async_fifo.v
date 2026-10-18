// async_fifo.v
// 异步 FIFO（Gray 码指针 + 两级同步）。写端不反压：满时丢弃并置 overflow（本工程里写入速率远低于读出速率，不应发生）。
// 读端为“先行输出”：empty=0 时 rd_data 即为队头，拉 rd_en 一拍弹出。
// 复位：rst_w / rst_r 为异步置位、同步释放（顶层用 reset_sync 从同一个复位源分别产生）。
//       写端时钟（HDMI 像素时钟）失锁时会停，异步置位保证没有时钟也能把写指针清零。
`timescale 1ns / 1ps
module async_fifo #(
    parameter integer DW = 26,
    parameter integer AW = 4            // 深度 2^AW
) (
    input  wire          wclk,
    input  wire          rst_w,
    input  wire          wr_en,
    input  wire [DW-1:0] wr_data,
    output reg           overflow,      // 锁存，直到复位

    input  wire          rclk,
    input  wire          rst_r,
    input  wire          rd_en,
    output wire [DW-1:0] rd_data,
    output wire          empty
);

    reg [DW-1:0] mem [0:(1<<AW)-1];

    reg  [AW:0] wbin, wgray, rbin, rgray;
    reg  [AW:0] rgray_w1, rgray_w2;     // 读指针同步到写域
    reg  [AW:0] wgray_r1, wgray_r2;     // 写指针同步到读域

    function [AW:0] bin2gray;
        input [AW:0] b;
        bin2gray = b ^ (b >> 1);
    endfunction

    // ---------------- 写域 ----------------
    wire [AW:0] wbin_next  = wbin + 1'b1;
    wire [AW:0] wgray_next = bin2gray(wbin_next);
    wire        full = (wgray_next == {~rgray_w2[AW:AW-1], rgray_w2[AW-2:0]});

    always @(posedge wclk or posedge rst_w) begin
        if (rst_w) begin
            wbin     <= {(AW+1){1'b0}};
            wgray    <= {(AW+1){1'b0}};
            rgray_w1 <= {(AW+1){1'b0}};
            rgray_w2 <= {(AW+1){1'b0}};
            overflow <= 1'b0;
        end else begin
            rgray_w1 <= rgray;
            rgray_w2 <= rgray_w1;
            if (wr_en) begin
                if (full) begin
                    overflow <= 1'b1;
                end else begin
                    wbin  <= wbin_next;
                    wgray <= wgray_next;
                end
            end
        end
    end

    always @(posedge wclk)
        if (wr_en && !full && !rst_w)
            mem[wbin[AW-1:0]] <= wr_data;

    // ---------------- 读域 ----------------
    assign empty   = (rgray == wgray_r2);
    assign rd_data = mem[rbin[AW-1:0]];

    always @(posedge rclk or posedge rst_r) begin
        if (rst_r) begin
            rbin     <= {(AW+1){1'b0}};
            rgray    <= {(AW+1){1'b0}};
            wgray_r1 <= {(AW+1){1'b0}};
            wgray_r2 <= {(AW+1){1'b0}};
        end else begin
            wgray_r1 <= wgray;
            wgray_r2 <= wgray_r1;
            if (rd_en && !empty) begin
                rbin  <= rbin + 1'b1;
                rgray <= bin2gray(rbin + 1'b1);
            end
        end
    end

endmodule
