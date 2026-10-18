// signal_watch.v（54 MHz 域）
// 判断 HDMI 视频是否“正在来”，以及无信号是否已超时（设计笔记 §15.7：无信号超过 N 秒显示黑场并关 VD）。
//   video_ok    ：最近 OK_WINDOW 个时钟内收到过合格整帧（默认 100 ms，正常 60 Hz 输入每 16.7 ms 一帧）
//   timed_out   ：timeout_s != 0 且已连续 timeout_s 秒没有合格整帧
// frame_good_tgl 来自像素时钟域（每合格一帧翻转一次），这里同步后检测翻转。
`timescale 1ns / 1ps
module signal_watch #(
    parameter integer CLK_HZ    = 54000000,
    parameter integer OK_WINDOW = 5400000     // 100 ms
) (
    input  wire       clk,
    input  wire       rst,
    input  wire       frame_good_tgl,
    input  wire [7:0] timeout_s,
    output reg        video_ok,
    output reg        timed_out,
    output reg        frame_seen      // 脉冲：收到一帧合格画面
);

    reg [2:0]  sync;
    reg [22:0] ok_cnt;
    reg [25:0] sec_cnt;
    reg [7:0]  age_s;      // 距上次合格帧的整秒数（饱和在 255）

    always @(posedge clk) begin
        if (rst) begin
            sync       <= 3'b000;
            ok_cnt     <= 23'd0;
            sec_cnt    <= 26'd0;
            age_s      <= 8'd255;
            video_ok   <= 1'b0;
            timed_out  <= 1'b0;
            frame_seen <= 1'b0;
        end else begin
            sync       <= {sync[1:0], frame_good_tgl};
            frame_seen <= sync[2] ^ sync[1];

            if (sync[2] ^ sync[1]) begin
                ok_cnt   <= OK_WINDOW;
                sec_cnt  <= 26'd0;
                age_s    <= 8'd0;
                video_ok <= 1'b1;
            end else begin
                if (ok_cnt != 23'd0) ok_cnt <= ok_cnt - 23'd1;
                else                 video_ok <= 1'b0;

                if (sec_cnt == CLK_HZ - 1) begin
                    sec_cnt <= 26'd0;
                    if (age_s != 8'd255) age_s <= age_s + 8'd1;
                end else begin
                    sec_cnt <= sec_cnt + 26'd1;
                end
            end

            timed_out <= (timeout_s != 8'd0) && (age_s >= timeout_s);
        end
    end

endmodule
