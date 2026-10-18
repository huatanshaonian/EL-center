// 来源：tang-monitor（https://github.com/kami4ka/tang-monitor，commit 1239ace），MIT 许可，
// Copyright (c) 2026 Oleg Kulyk，许可全文见同目录 LICENSE_tang-monitor.txt。
// HDMI TMDS clock recovery: TLVDS input -> rPLL x5 -> CLKDIV /5.
// Input pair G16/H15 is NOT a dedicated clock pin — the PLL reference arrives
// via fabric routing (plan risk #1; this module exists to prove it works).
// MIS-01 修改：删除原工程给 LCD 用的第二个 rPLL（x2/5 genlock 时钟）及其端口；监督逻辑只看主 PLL 的 lock。
module hdmi_clk_rx (
    input  wire tmds_clk_p,
    input  wire tmds_clk_n,
    input  wire clk27,         // supervisor timebase
    input  wire rst_n,
    output wire clk_hdmi_raw,  // 25.175 MHz as received (pre-PLL)
    output wire fclk,          // x5 = 125.875 MHz (IDES10 serial clock)
    output wire pclk,          // /5 = 25.175 MHz (pixel/word clock)
    output wire lock,
    output reg  [7:0] rst_cnt, // PLL re-acquire attempts (telemetry)
    input  wire [3:0] psda     // dynamic phase of fclk (sampling eye search)
);
    TLVDS_IBUF u_ibuf (
        .I (tmds_clk_p),
        .IB(tmds_clk_n),
        .O (clk_hdmi_raw)
    );

    // --- input-alive detector + PLL re-acquire supervisor (clk27 domain).
    // The PLL configures with no input clock (source off) and wedges; pulse
    // RESET whenever the input is alive but lock is absent, with backoff.
    reg [3:0] tgl_sync;
    reg       raw_tgl;
    always @(posedge clk_hdmi_raw or negedge rst_n)
        if (!rst_n) raw_tgl <= 0;
        else        raw_tgl <= ~raw_tgl;
    always @(posedge clk27) tgl_sync <= {tgl_sync[2:0], raw_tgl};

    reg [21:0] alive_win;   // ~150 ms window
    reg [15:0] tgl_cnt;
    reg        input_alive;
    reg [21:0] acq_timer;
    reg        pll_reset;

    always @(posedge clk27 or negedge rst_n) begin
        if (!rst_n) begin
            alive_win <= 0; tgl_cnt <= 0; input_alive <= 0;
            acq_timer <= 0; pll_reset <= 0; rst_cnt <= 0;
        end else begin
            alive_win <= alive_win + 1'b1;
            if (tgl_sync[3] ^ tgl_sync[2]) tgl_cnt <= tgl_cnt + 1'b1;
            if (&alive_win) begin
                input_alive <= (tgl_cnt > 16'd1000);
                tgl_cnt <= 0;
            end
            // re-acquire: alive && any PLL unlocked -> reset pulse, backoff
            if (input_alive && !lock) begin
                acq_timer <= acq_timer + 1'b1;
                if (acq_timer == 0) begin
                    pll_reset <= 1'b1;
                    rst_cnt <= rst_cnt + 1'b1;
                end else if (acq_timer == 22'd64) begin
                    pll_reset <= 1'b0;
                end
            end else begin
                acq_timer <= 0;
                pll_reset <= 1'b0;
            end
        end
    end

    // CLKOUTP carries the deserializer clock: its phase is PSDA-adjustable
    // (eye search — our substitute for IODELAY/CDR). CLKDIV follows it.
    wire fclk_fixed;
    rPLL #(
        .FCLKIN("25.175"),
        .IDIV_SEL(0),   // PFD = 25.175 MHz
        .FBDIV_SEL(4),  // CLKOUT = 125.875 MHz
        .ODIV_SEL(8),   // VCO = 1007 MHz — comfortable margin in 500-1250
        .DYN_DA_EN("true"),
        .PSDA_SEL("0000")
    ) u_pll (
        .CLKOUTP(fclk), .CLKOUTD(), .CLKOUTD3(),
        .RESET(pll_reset), .RESET_P(1'b0), .CLKFB(1'b0),
        .FBDSEL(6'b0), .IDSEL(6'b0), .ODSEL(6'b0),
        .PSDA(psda), .DUTYDA(4'b1000), .FDLY(4'b0),
        .CLKIN(clk_hdmi_raw),
        .CLKOUT(fclk_fixed),
        .LOCK(lock)
    );

    CLKDIV #(
        .DIV_MODE("5"),
        .GSREN("false")
    ) u_div (
        .HCLKIN(fclk),
        .RESETN(rst_n & lock),
        .CALIB(1'b0),
        .CLKOUT(pclk)
    );
endmodule
