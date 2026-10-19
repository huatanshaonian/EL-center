// el_hdmi_top.v
// MIS-01：Orange Pi HDMI（640×480）→ Tang Primer 20K → Sharp LJ64K052 EL 屏。只负责连线，不放功能逻辑。
//
// 时钟域：
//   clk27 ：板载晶振。EDID（DDC I2C 从机）、HPD、HDMI 时钟恢复的监督逻辑
//   clk    ：54 MHz（PLL）。屏扫描、帧缓存、上下电顺序、UART 命令、按键、LED
//   pclk   ：HDMI 恢复出的像素时钟 25.175 MHz。TMDS 解码、转黑白、打包
// 跨域：像素数据经 async_fifo（pclk → clk）；设置（阈值等，变化很慢）两级同步进 pclk；状态位两级同步进 clk。
//
// 按键（低有效）：RUN（T10）开/关机；SRC（T3）切信号源；HPD（T2）让信号源重读 EDID。
// UART：Orange Pi（J14-10/11）和 Dock USB 调试口共用一套命令，见 ctrl/ctrl_cmd.v。
`timescale 1ns / 1ps
module el_hdmi_top #(
    parameter         EDID_FILE       = "edid/edid_640x480.hex",
    parameter integer LED_ACTIVE_LOW  = 1,
    parameter integer AUTO_START      = 0,          // 1 = 上电 2 s 后自动开机（整机用；面包板阶段保持 0）
    parameter integer DEBOUNCE_CYCLES = 540000,     // 按键去抖约 10 ms
    parameter integer STATUS_FILTER   = 54,         // 状态线滤波约 1 µs
    parameter integer RESET_HOLD      = 54000,      // PLL 锁定后复位保持约 1 ms
    parameter integer OE_LEAD_CYCLES  = 54000,
    parameter integer SCAN_FRAMES     = 2,
    parameter integer VD_WAIT_CYCLES  = 54000000,
    parameter integer LOCAL_PERIOD    = 2700000     // 自检画面 20 帧/秒
) (
    input  wire       clk27,

    input  wire       btn_run_n,
    input  wire       btn_src_n,
    input  wire       btn_hpd_n,
    output wire [5:0] led_n,

    // 到 EL-IF（与测试程序相同）
    output wire [3:0] el_ud,
    output wire [3:0] el_ld,
    output wire       el_cp2,
    output wire       el_cp1,
    output wire       el_s,
    output wire       oe_n,
    output wire       vd_on_n,
    input  wire       vd_hi_n,
    input  wire       vl_flt_n,
    input  wire       pfail_n,
    input  wire       vl_ok,
    input  wire       vd_flt_n,
    input  wire       scr_en,       // J14-12：斜面"屏幕"开关，1 = 允许开屏（EL-IF D1.2 起）

    // UART
    output wire       opi_tx,       // J14-10 → Orange Pi RX
    input  wire       opi_rx,       // J14-11 ← Orange Pi TX
    output wire       dbg_tx,       // Dock USB 调试串口（BL702）
    input  wire       dbg_rx,

    // HDMI 接收
    inout  wire       hdmi_sda,
    input  wire       hdmi_scl,
    output wire       hdmi_hpd,
    input  wire       tmds_clk_p,
    input  wire       tmds_clk_n,
    input  wire       tmds_d0_p,
    input  wire       tmds_d0_n,
    input  wire       tmds_d1_p,
    input  wire       tmds_d1_n,
    input  wire       tmds_d2_p,
    input  wire       tmds_d2_n
);

    // ======================= clk27 域：上电复位、EDID、HPD =======================
    reg [15:0] por27 = 16'd0;
    always @(posedge clk27) if (!(&por27)) por27 <= por27 + 16'd1;
    wire rst27_n = &por27;

    wire sda_oe;
    edid_slave #(.ROM_INIT(EDID_FILE)) u_edid (
        .clk(clk27), .rst_n(rst27_n),
        .scl_i(hdmi_scl), .sda_i(hdmi_sda), .sda_oe(sda_oe),
        .ev_valid(), .ev_tag(), .ev_data()
    );
    assign hdmi_sda = sda_oe ? 1'b0 : 1'bz;

    reg        hpd_tgl;                 // clk 域翻转 → clk27 域脉冲
    reg  [2:0] hpd_sync;
    always @(posedge clk27) hpd_sync <= {hpd_sync[1:0], hpd_tgl};
    hpd_ctrl u_hpd (
        .clk(clk27), .rst_n(rst27_n),
        .pulse_req(hpd_sync[2] ^ hpd_sync[1]),
        .hpd(hdmi_hpd)
    );

    // ======================= HDMI 接收（pclk 域） =======================
    wire fclk, pclk, hdmi_pll_lock;
    hdmi_clk_rx u_hclk (
        .tmds_clk_p(tmds_clk_p), .tmds_clk_n(tmds_clk_n),
        .clk27(clk27), .rst_n(rst27_n),
        .clk_hdmi_raw(), .fclk(fclk), .pclk(pclk), .lock(hdmi_pll_lock),
        .rst_cnt(), .psda(4'b0)
    );

    wire       rx_rst_n = rst27_n & hdmi_pll_lock;
    wire [9:0] w0, w1, w2;
    wire [2:0] lane_ok;
    tmds_lane_rx u_l0 (.d_p(tmds_d0_p), .d_n(tmds_d0_n), .fclk(fclk), .pclk(pclk), .rst_n(rx_rst_n), .word(w0), .aligned(lane_ok[0]), .offset());
    tmds_lane_rx u_l1 (.d_p(tmds_d1_p), .d_n(tmds_d1_n), .fclk(fclk), .pclk(pclk), .rst_n(rx_rst_n), .word(w1), .aligned(lane_ok[1]), .offset());
    tmds_lane_rx u_l2 (.d_p(tmds_d2_p), .d_n(tmds_d2_n), .fclk(fclk), .pclk(pclk), .rst_n(rx_rst_n), .word(w2), .aligned(lane_ok[2]), .offset());

    wire [23:0] rgb;
    wire        de_v;
    tmds_decode u_dec (
        .pclk(pclk), .rst_n(rx_rst_n),
        .c0(w0), .c1(w1), .c2(w2),
        .rgb(rgb), .de(de_v), .hs(), .vs()
    );

    // 视频链路复位：PLL 失锁或任一通道未对齐时，同时复位 FIFO 两端和打包器
    wire link_rst = ~(rx_rst_n & (&lane_ok));
    wire rst_p, rst_fifo_r;
    reset_sync u_rs_p (.clk(pclk), .rst_in(link_rst), .rst_out(rst_p));

    // 设置同步进 pclk 域（变化很慢，逐位两级同步即可）
    wire [7:0] cfg_threshold;
    wire       cfg_invert, cfg_dither;
    reg  [9:0] cfg_p1, cfg_p2;
    always @(posedge pclk) begin
        cfg_p1 <= {cfg_threshold, cfg_invert, cfg_dither};
        cfg_p2 <= cfg_p1;
    end

    wire        wr_valid;
    wire [25:0] wr_req;
    wire [11:0] last_h;
    wire [10:0] last_v;
    wire        frame_good_tgl;
    fb_writer u_wr (
        .pclk(pclk), .rst(rst_p), .de(de_v), .rgb(rgb),
        .threshold(cfg_p2[9:2]), .invert(cfg_p2[1]), .dither(cfg_p2[0]),
        .req_valid(wr_valid), .req(wr_req),
        .last_h(last_h), .last_v(last_v), .frame_good_tgl(frame_good_tgl)
    );

    // ======================= clk 域（54 MHz） =======================
    wire clk, pll_lock, rst;
    el_pll    u_pll (.clk_in(clk27), .clk_out(clk), .lock(pll_lock));
    reset_gen #(.HOLD_CYCLES(RESET_HOLD)) u_rst (.clk(clk), .lock(pll_lock), .rst(rst));
    reset_sync u_rs_r (.clk(clk), .rst_in(link_rst | rst), .rst_out(rst_fifo_r));

    wire        fifo_empty, fifo_rd, fifo_ovf;
    wire [25:0] fifo_q;
    async_fifo #(.DW(26), .AW(4)) u_fifo (
        .wclk(pclk), .rst_w(rst_p), .wr_en(wr_valid), .wr_data(wr_req), .overflow(fifo_ovf),
        .rclk(clk), .rst_r(rst_fifo_r), .rd_en(fifo_rd), .rd_data(fifo_q), .empty(fifo_empty)
    );

    // ---- 状态位同步进 clk 域 ----
    reg [1:0] lock_s;
    reg [1:0] ovf_s;
    reg [11:0] last_h_s1, last_h_s2;
    reg [10:0] last_v_s1, last_v_s2;
    always @(posedge clk) begin
        lock_s    <= {lock_s[0], ~link_rst};
        ovf_s     <= {ovf_s[0], fifo_ovf};
        last_h_s1 <= last_h;  last_h_s2 <= last_h_s1;
        last_v_s1 <= last_v;  last_v_s2 <= last_v_s1;
    end
    wire hdmi_locked = lock_s[1];

    // ---- 按键 ----
    wire run_press, src_press, hpd_press;
    key_press #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES)) u_k_run (.clk(clk), .rst(rst), .key_n(btn_run_n), .pressed(run_press));
    key_press #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES)) u_k_src (.clk(clk), .rst(rst), .key_n(btn_src_n), .pressed(src_press));
    key_press #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES)) u_k_hpd (.clk(clk), .rst(rst), .key_n(btn_hpd_n), .pressed(hpd_press));

    // ---- 状态输入同步（复位值取“不安全”方向，防止刚上电误开机） ----
    wire s_vd_hi_n, s_vl_flt_n, s_pfail_n, s_vl_ok, s_vd_flt_n;
    input_sync #(.STABLE_CYCLES(STATUS_FILTER), .RESET_VALUE(1'b0)) u_in_vdhi (.clk(clk), .rst(rst), .din(vd_hi_n),  .dout(s_vd_hi_n));
    input_sync #(.STABLE_CYCLES(STATUS_FILTER), .RESET_VALUE(1'b1)) u_in_vlf  (.clk(clk), .rst(rst), .din(vl_flt_n), .dout(s_vl_flt_n));
    input_sync #(.STABLE_CYCLES(STATUS_FILTER), .RESET_VALUE(1'b0)) u_in_pf   (.clk(clk), .rst(rst), .din(pfail_n),  .dout(s_pfail_n));
    input_sync #(.STABLE_CYCLES(STATUS_FILTER), .RESET_VALUE(1'b0)) u_in_vlok (.clk(clk), .rst(rst), .din(vl_ok),    .dout(s_vl_ok));
    input_sync #(.STABLE_CYCLES(STATUS_FILTER), .RESET_VALUE(1'b1)) u_in_vdf  (.clk(clk), .rst(rst), .din(vd_flt_n), .dout(s_vd_flt_n));

    // ---- UART 与命令 ----
    wire [7:0] rx_byte, tx_byte;
    wire       rx_valid, tx_valid, tx_ready, uart_txd;
    uart_rx #(.CLK_HZ(54_000_000)) u_urx (.clk(clk), .rst_n(~rst), .rxd(opi_rx & dbg_rx), .data(rx_byte), .valid(rx_valid));
    uart_tx #(.CLK_HZ(54_000_000)) u_utx (.clk(clk), .rst_n(~rst), .data(tx_byte), .valid(tx_valid), .ready(tx_ready), .txd(uart_txd));
    assign opi_tx = uart_txd;
    assign dbg_tx = uart_txd;

    wire [3:0]  src_sel;
    wire        cfg_120hz, cmd_start_u, cmd_stop, hpd_cmd, src_changed;
    wire [7:0]  cfg_timeout_s;
    wire [2:0]  seq_state;
    wire        fault, pfail_seen, video_ok, timed_out, frame_seen;
    wire [15:0] frames_shown, frames_dropped;

    ctrl_cmd u_cmd (
        .clk(clk), .rst(rst),
        .rx_byte(rx_byte), .rx_valid(rx_valid),
        .tx_byte(tx_byte), .tx_valid(tx_valid), .tx_ready(tx_ready),
        .key_src_next(src_press),
        .src_sel(src_sel), .cfg_threshold(cfg_threshold), .cfg_invert(cfg_invert), .cfg_dither(cfg_dither),
        .cfg_120hz(cfg_120hz), .cfg_timeout_s(cfg_timeout_s),
        .cmd_start(cmd_start_u), .cmd_stop(cmd_stop), .hpd_pulse(hpd_cmd), .src_changed(src_changed),
        .st_state(seq_state), .st_hdmi_lock(hdmi_locked), .st_video_ok(video_ok),
        .st_shown(frames_shown), .st_dropped(frames_dropped),
        .st_h(last_h_s2), .st_v(last_v_s2),
        .st_fault(fault), .st_pfail(pfail_seen), .st_overflow(ovf_s[1])
    );

    always @(posedge clk) begin
        if (rst)                       hpd_tgl <= 1'b0;
        else if (hpd_cmd || hpd_press) hpd_tgl <= ~hpd_tgl;
    end

    // ---- 上电 2 s 后自动开机（可选） ----
    reg [27:0] auto_cnt;
    reg        auto_done, auto_pulse;
    always @(posedge clk) begin
        if (rst) begin
            auto_cnt <= 28'd0; auto_done <= 1'b0; auto_pulse <= 1'b0;
        end else begin
            auto_pulse <= 1'b0;
            if (AUTO_START != 0 && !auto_done) begin
                if (auto_cnt == 28'd108_000_000) begin auto_done <= 1'b1; auto_pulse <= 1'b1; end
                else auto_cnt <= auto_cnt + 28'd1;
            end
        end
    end

    signal_watch u_watch (
        .clk(clk), .rst(rst), .frame_good_tgl(frame_good_tgl), .timeout_s(cfg_timeout_s),
        .video_ok(video_ok), .timed_out(timed_out), .frame_seen(frame_seen)
    );

    // ---- 屏幕开关：关 = 撤掉 VD_ON_N（EL-IF 上 D4 同时硬件关 VD），开 = 等约 100 ms 再放开 ----
    wire scr_inhibit, scr_on;
    screen_switch u_scr (.clk(clk), .rst(rst), .scr_en(scr_en), .scr_inhibit(scr_inhibit), .scr_on(scr_on));

    // ---- 上/下电顺序 ----
    wire scan_en, scan_abort, scan_running, frame_tick, swap_ok;
    el_power_seq #(
        .OE_LEAD_CYCLES(OE_LEAD_CYCLES), .SCAN_FRAMES(SCAN_FRAMES), .VD_WAIT_CYCLES(VD_WAIT_CYCLES)
    ) u_seq (
        .clk(clk), .rst(rst),
        .btn_run(run_press), .cmd_start(cmd_start_u | auto_pulse), .cmd_stop(cmd_stop),
        .vd_inhibit(((src_sel == 4'd0) && timed_out) || scr_inhibit),
        .vl_ok(s_vl_ok), .pfail_n(s_pfail_n), .vd_flt_n(s_vd_flt_n), .vl_flt_n(s_vl_flt_n), .vd_hi_n(s_vd_hi_n),
        .frame_tick(frame_tick), .scan_running(scan_running),
        .scan_en(scan_en), .scan_abort(scan_abort), .oe_n(oe_n), .vd_on_n(vd_on_n),
        .state(seq_state), .fault(fault), .pfail_seen(pfail_seen)
    );

    // ---- 帧缓存、信号源、扫描 ----
    wire        loc_valid;
    wire [25:0] loc_req;
    wire        local_test, video_shown, have_frame, swap_pulse;
    wire [7:0]  pat_group, pat_line, fb_data, scan_data;

    local_frame_gen #(.PERIOD(LOCAL_PERIOD)) u_loc (
        .clk(clk), .rst(rst), .enable(local_test), .req_valid(loc_valid), .req(loc_req)
    );

    fb_ctrl u_fb (
        .clk(clk), .rst(rst),
        .fifo_empty(fifo_empty), .fifo_data(fifo_q), .fifo_rd(fifo_rd), .fifo_flush(rst_fifo_r),
        .src_local(local_test), .loc_valid(loc_valid), .loc_req(loc_req),
        .swap_ok(swap_ok), .scan_running(scan_running),
        .rd_group(pat_group), .rd_line(pat_line), .rd_data(fb_data),
        .have_frame(have_frame), .swap_pulse(swap_pulse),
        .frames_shown(frames_shown), .frames_dropped(frames_dropped)
    );

    el_source_mux u_mux (
        .src_sel(src_sel), .fb_data(fb_data), .fb_have_frame(have_frame), .video_ok(video_ok),
        .pat_group(pat_group), .pat_line(pat_line),
        .data(scan_data), .video_shown(video_shown), .local_test(local_test)
    );

    el_scan_timing u_scan (
        .clk(clk), .rst(rst), .scan_en(scan_en), .abort(scan_abort),
        .line_ticks(cfg_120hz ? 12'd1875 : 12'd3750),
        .pat_group(pat_group), .pat_line(pat_line), .pat_data(scan_data),
        .cp2(el_cp2), .cp1(el_cp1), .s(el_s), .ud(el_ud), .ld(el_ld),
        .running(scan_running), .frame_tick(frame_tick), .swap_ok(swap_ok)
    );

    // ---- LED ----
    wire [5:0] led_on;
    led_status u_led (
        .clk(clk), .rst(rst),
        .oe_n(oe_n), .scanning(scan_running), .vd_on_n(vd_on_n),
        .fault(fault), .pfail_seen(pfail_seen),
        .hdmi_locked(hdmi_locked), .video_shown(video_shown), .frame_swap(swap_pulse),
        .show_value(src_sel), .show_pulse(src_changed),
        .led(led_on)
    );
    assign led_n = LED_ACTIVE_LOW ? ~led_on : led_on;

endmodule
