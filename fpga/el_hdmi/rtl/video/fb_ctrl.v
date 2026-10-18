// fb_ctrl.v（54 MHz 域）
// 双帧缓存的所有权管理（设计笔记 §7.3）：
//   front   = 正在显示的帧（0/1）；写端只写另一帧（back）。
//   SOF     ：若 back 空闲（没有待换上的完整帧）→ 开始写 back；否则整帧丢弃（计入 dropped）。
//   EOF     ：写完的 back 标记为 pending（待换上）。
//   换帧    ：只在 swap_ok（屏最后一行数据已取完）或屏未在扫描时进行：pending → front 翻转。
//   写端在 pending 期间不碰任何一帧，所以显示中的帧永远不会被覆盖，上下半屏总是同一帧。
//
// 写请求来源（src_local=1 时用本地测试画面发生器，忽略 HDMI FIFO）：
//   {type[1:0], half, addr[14:0], data[7:0]}，type 0 写 / 1 SOF / 2 EOF（见 fb_writer.v）
//
// 读出：rd_group/rd_line 来自 el_scan_timing 的预取地址；rd_data 在 4 拍后有效（≤ 6 拍要求）。
//   字节地址 = front*19200 + 80*line + group/2；高 4 位 = 偶数组，低 4 位 = 奇数组。
`timescale 1ns / 1ps
module fb_ctrl (
    input  wire        clk,
    input  wire        rst,

    // HDMI 写请求（异步 FIFO 读端）
    input  wire        fifo_empty,
    input  wire [25:0] fifo_data,
    output wire        fifo_rd,
    input  wire        fifo_flush,     // HDMI 侧复位：中止正在写的帧

    // 本地测试画面写请求（单周期有效）
    input  wire        src_local,
    input  wire        loc_valid,
    input  wire [25:0] loc_req,

    // 与扫描时序的接口
    input  wire        swap_ok,
    input  wire        scan_running,
    input  wire [7:0]  rd_group,
    input  wire [7:0]  rd_line,
    output reg  [7:0]  rd_data,        // {UD3..UD0, LD3..LD0}

    // 状态
    output reg         have_frame,     // 至少换上过一帧
    output reg         swap_pulse,     // 刚换上一帧新画面
    output reg  [15:0] frames_shown,
    output reg  [15:0] frames_dropped
);

    localparam [1:0] T_WR = 2'd0, T_SOF = 2'd1, T_EOF = 2'd2;
    localparam [15:0] FRAME_BYTES = 16'd19200;

    reg front, pending, writing;

    // ---------------- 写请求选择 ----------------
    assign fifo_rd = !src_local && !fifo_empty;          // HDMI 模式下每拍弹出一个
    wire        rq_valid = src_local ? loc_valid : (!fifo_empty);
    wire [25:0] rq       = src_local ? loc_req   : fifo_data;
    wire [1:0]  rq_type  = rq[25:24];
    wire        rq_half  = rq[23];
    wire [14:0] rq_addr  = rq[22:8];
    wire [7:0]  rq_data  = rq[7:0];

    // ---------------- RAM ----------------
    reg         ram_we;
    reg         ram_half;
    reg  [15:0] ram_waddr;
    reg  [7:0]  ram_wdata;
    reg  [15:0] ram_raddr;
    wire [7:0]  ram_u, ram_l;

    fb_ram u_ram (
        .clk(clk), .we(ram_we), .w_half(ram_half), .w_addr(ram_waddr), .w_data(ram_wdata),
        .r_addr(ram_raddr), .r_upper(ram_u), .r_lower(ram_l)
    );

    // ---------------- 所有权与写入 ----------------
    always @(posedge clk) begin
        if (rst) begin
            front          <= 1'b0;
            pending        <= 1'b0;
            writing        <= 1'b0;
            have_frame     <= 1'b0;
            swap_pulse     <= 1'b0;
            frames_shown   <= 16'd0;
            frames_dropped <= 16'd0;
            ram_we         <= 1'b0;
            ram_half       <= 1'b0;
            ram_waddr      <= 16'd0;
            ram_wdata      <= 8'd0;
        end else begin
            ram_we     <= 1'b0;
            swap_pulse <= 1'b0;

            if (fifo_flush && !src_local) begin
                writing <= 1'b0;
            end else if (rq_valid) begin
                case (rq_type)
                    T_SOF: begin
                        if (!pending) begin
                            writing <= 1'b1;
                        end else begin
                            writing        <= 1'b0;
                            frames_dropped <= frames_dropped + 16'd1;
                        end
                    end
                    T_EOF: begin
                        if (writing) begin
                            writing <= 1'b0;
                            pending <= 1'b1;
                        end
                    end
                    T_WR: begin
                        if (writing) begin
                            ram_we    <= 1'b1;
                            ram_half  <= rq_half;
                            ram_waddr <= (front ? 16'd0 : FRAME_BYTES) + {1'b0, rq_addr};   // 写 back = ~front
                            ram_wdata <= rq_data;
                        end
                    end
                    default: ;
                endcase
            end

            // 换帧：屏最后一行取完之后，或屏没在扫描时（pending 期间 writing 一定为 0）
            if (pending && (swap_ok || !scan_running) && !(rq_valid && rq_type == T_EOF)) begin
                front        <= ~front;
                pending      <= 1'b0;
                have_frame   <= 1'b1;
                swap_pulse   <= 1'b1;
                frames_shown <= frames_shown + 16'd1;
            end
        end
    end

    // ---------------- 读出（4 拍：地址寄存 1 + RAM 2 + 选半字节 1）----------------
    reg       nib_sel_q1, nib_sel_q2, nib_sel_q3;
    always @(posedge clk) begin
        ram_raddr  <= (front ? FRAME_BYTES : 16'd0) + {rd_line, 6'b0} + {rd_line, 4'b0} + {9'd0, rd_group[7:1]};
        nib_sel_q1 <= rd_group[0];
        nib_sel_q2 <= nib_sel_q1;
        nib_sel_q3 <= nib_sel_q2;
        rd_data    <= nib_sel_q3 ? {ram_u[3:0], ram_l[3:0]} : {ram_u[7:4], ram_l[7:4]};
    end

endmodule
