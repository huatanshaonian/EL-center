// el_source_mux.v（54 MHz 域，组合逻辑）
// 选择送给扫描时序的数据：
//   src 0   ：HDMI 视频——有合格画面（已换上过一帧且最近 100 ms 内还在来）时显示帧缓存，否则全黑
//   src 1..8：测试图案 0..7（el_pattern）
//   src 9   ：帧缓存自检画面（显示帧缓存，内容由 local_frame_gen 写入）
// 两路数据对同一预取地址都在装载时刻之前有效（图案 0 拍、帧缓存 4 拍，均 ≤ 6 拍）。
`timescale 1ns / 1ps
module el_source_mux (
    input  wire [3:0] src_sel,
    input  wire [7:0] fb_data,
    input  wire       fb_have_frame,
    input  wire       video_ok,
    input  wire [7:0] pat_group,
    input  wire [7:0] pat_line,
    output reg  [7:0] data,
    output wire       video_shown,
    output wire       local_test
);

    wire [2:0] pat_sel = (src_sel == 4'd0 || src_sel > 4'd8) ? 3'd0 : (src_sel[2:0] - 3'd1);
    wire [7:0] pat_data;

    el_pattern u_pat (.sel(pat_sel), .group(pat_group), .line(pat_line), .data(pat_data));

    assign video_shown = (src_sel == 4'd0) && fb_have_frame && video_ok;
    assign local_test  = (src_sel == 4'd9);

    always @(*) begin
        if (src_sel == 4'd0)
            data = video_shown ? fb_data : 8'd0;
        else if (src_sel == 4'd9)
            data = fb_have_frame ? fb_data : 8'd0;
        else
            data = pat_data;
    end

endmodule
