// fb_ram.v
// EL 双帧缓存：上半屏、下半屏各一块存储区，同时读出（屏需要第 y 行和第 y+240 行同时送）。
// 每个半屏存两帧：字节地址 = 帧号 × 19200 + 80 × 行 + 列/8，范围 0..38399。
// 每个半屏用 19 块 BSRAM（SDPB，x8 = 2048 字节/块）：块号 = 地址[15:11]，块内地址 = 地址[10:0]。
// 共 38 块（GW2A-18 共 46 块）。
// 写、读同一时钟（54 MHz 域）。读延迟 2 拍（SDPB READ_MODE=1，与 tang-monitor 硬件实测一致）。
// 帧缓存控制保证写的永远不是正在显示的那一帧，不会出现同址读写冲突。
// 仿真（定义 SIM）用行为模型，延迟同样是 2 拍。
`timescale 1ns / 1ps
module fb_ram (
    input  wire        clk,
    input  wire        we,
    input  wire        w_half,        // 0 = 上半屏，1 = 下半屏
    input  wire [15:0] w_addr,
    input  wire [7:0]  w_data,
    input  wire [15:0] r_addr,
    output wire [7:0]  r_upper,
    output wire [7:0]  r_lower
);

    localparam integer NBLK = 19;

`ifdef SIM
    reg [7:0] mem_u [0:NBLK*2048-1];
    reg [7:0] mem_l [0:NBLK*2048-1];
    reg [7:0] u_q1, u_q2, l_q1, l_q2;
    always @(posedge clk) begin
        if (we && !w_half) mem_u[w_addr] <= w_data;
        if (we &&  w_half) mem_l[w_addr] <= w_data;
        u_q1 <= mem_u[r_addr];  u_q2 <= u_q1;
        l_q1 <= mem_l[r_addr];  l_q2 <= l_q1;
    end
    assign r_upper = u_q2;
    assign r_lower = l_q2;
`else
    wire [4:0] w_blk = w_addr[15:11];
    wire [4:0] r_blk = r_addr[15:11];

    // 读出数据按 2 拍前的块号选择
    reg [4:0] r_blk_q1, r_blk_q2;
    always @(posedge clk) begin
        r_blk_q1 <= r_blk;
        r_blk_q2 <= r_blk_q1;
    end

    wire [7:0] do_u [0:NBLK-1];
    wire [7:0] do_l [0:NBLK-1];

    genvar i;
    generate
        for (i = 0; i < NBLK; i = i + 1) begin : blk
            wire [23:0] dummy_u, dummy_l;
            SDPB mem_u (
                .DO({dummy_u, do_u[i]}),
                .DI({24'd0, w_data}),
                .ADA({w_addr[10:0], 3'b000}),
                .ADB({r_addr[10:0], 3'b000}),
                .CLKA(clk), .CLKB(clk),
                .OCE(1'b1),
                .CEA(we && !w_half && (w_blk == i)),
                .CEB(1'b1),
                .BLKSELA(3'b000), .BLKSELB(3'b000),
                .RESETA(1'b0), .RESETB(1'b0)
            );
            defparam mem_u.READ_MODE   = 1'b1;
            defparam mem_u.BIT_WIDTH_0 = 8;
            defparam mem_u.BIT_WIDTH_1 = 8;
            defparam mem_u.BLK_SEL_0   = 3'b000;
            defparam mem_u.BLK_SEL_1   = 3'b000;
            defparam mem_u.RESET_MODE  = "SYNC";

            SDPB mem_l (
                .DO({dummy_l, do_l[i]}),
                .DI({24'd0, w_data}),
                .ADA({w_addr[10:0], 3'b000}),
                .ADB({r_addr[10:0], 3'b000}),
                .CLKA(clk), .CLKB(clk),
                .OCE(1'b1),
                .CEA(we && w_half && (w_blk == i)),
                .CEB(1'b1),
                .BLKSELA(3'b000), .BLKSELB(3'b000),
                .RESETA(1'b0), .RESETB(1'b0)
            );
            defparam mem_l.READ_MODE   = 1'b1;
            defparam mem_l.BIT_WIDTH_0 = 8;
            defparam mem_l.BIT_WIDTH_1 = 8;
            defparam mem_l.BLK_SEL_0   = 3'b000;
            defparam mem_l.BLK_SEL_1   = 3'b000;
            defparam mem_l.RESET_MODE  = "SYNC";
        end
    endgenerate

    assign r_upper = do_u[r_blk_q2];
    assign r_lower = do_l[r_blk_q2];
`endif

endmodule
