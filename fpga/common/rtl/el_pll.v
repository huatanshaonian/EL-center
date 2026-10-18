// el_pll.v
// 27 MHz 板载晶振 -> 54 MHz EL 时序时钟（设计笔记 §8.3：CP2 = 54 MHz / 10 = 5.4 MHz）。
// Gowin rPLL：CLKOUT = FCLKIN * (FBDIV_SEL+1) / (IDIV_SEL+1) = 27 * 2 / 1 = 54 MHz
//             PFD = 27 MHz；VCO = CLKOUT * ODIV_SEL = 54 * 16 = 864 MHz（GW2A 允许 500–1250 MHz）
// 只写必要参数：开源工具链（apicula）和高云 EDA 都能用，其余取默认值。
`timescale 1ns / 1ps
module el_pll (
    input  wire clk_in,    // 27 MHz，H11
    output wire clk_out,   // 54 MHz
    output wire lock       // 高 = PLL 已锁定
);

    rPLL #(
        .FCLKIN   ("27"),
        .IDIV_SEL (0),
        .FBDIV_SEL(1),
        .ODIV_SEL (16)
    ) u_rpll (
        .CLKOUT  (clk_out),
        .LOCK    (lock),
        .CLKOUTP (),
        .CLKOUTD (),
        .CLKOUTD3(),
        .RESET   (1'b0),
        .RESET_P (1'b0),
        .CLKIN   (clk_in),
        .CLKFB   (1'b0),
        .FBDSEL  (6'b0),
        .IDSEL   (6'b0),
        .ODSEL   (6'b0),
        .PSDA    (4'b0),
        .DUTYDA  (4'b0),
        .FDLY    (4'b0)
    );

endmodule
