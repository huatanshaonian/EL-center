// el_test.sdc —— 输入时钟约束；PLL 输出（54 MHz）由时序分析自动推导
create_clock -name clk27 -period 37.037 -waveform {0 18.518} [get_ports {clk27}]
