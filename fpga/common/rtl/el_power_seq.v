// el_power_seq.v
// EL 上/下电顺序控制（设计笔记 §16.4 与面包板文档“E. 提供给 RTL 的时序约定”）。
//
// 正常开机（按一次 RUN）：
//   OFF → OE_ON（OE_N=0，信号全低，等 OE_LEAD_CYCLES）
//       → SCAN（开始有效扫描，等满 SCAN_FRAMES 整帧）
//       → RUN（VD_ON_N=0；面包板阶段 VD 由人工开，此时 LED 提示“可以开 VD”）
// 正常关机（RUN 状态再按一次 RUN）：
//   RUN → VD_OFF（VD_ON_N=1，继续扫描；等 VD_HI_N=1 后再等 VD_WAIT_CYCLES）
//       → STOP（scan_en=0，扫完当前整帧）→ OE_OFF（OE_N=1）→ OFF
//
// 保护（任何非 OFF/FAULT 状态都检查，输入须已同步）：
//   VL_OK=0      ：VL 掉电。立即 VD_ON_N=1、中止扫描、OE_N=1，回 OFF（不再假定 5V 逻辑有效）。
//   PFAIL_N=0    ：24V 掉电预警。立即 VD_ON_N=1，VL 仍在就继续扫描，按关机流程走完，回 OFF；记下 pfail_seen。
//   VD/VL_FLT_N=0：eFuse 故障。立即 VD_ON_N=1，锁存故障，按关机流程走完后停在 FAULT，不自动重试。
//                  故障线恢复为高后，按 RUN 清除故障回到 OFF；再按 RUN 才重新开机。
// PFAIL 低、故障未清时不允许开机。
//
// 面包板阶段这些状态输入悬空，由 FPGA 内部上拉读作 1（= 正常），见约束文件。
//
// 其他控制：
//   cmd_start / cmd_stop：UART 命令开机 / 关机（与按 RUN 等效，但不是翻转）；cmd_start 也用于清除故障。
//   vd_inhibit：1 时 RUN 状态下暂时关 VD、继续扫描（无 HDMI 信号超时防烧屏）；变回 0 后立即重新开 VD。
`timescale 1ns / 1ps
module el_power_seq #(
    parameter integer OE_LEAD_CYCLES = 54000,       // OE 使能到开始扫描，约 1 ms
    parameter integer SCAN_FRAMES    = 2,           // VD 开之前至少稳定扫描的整帧数（≥ 1）
    parameter integer VD_WAIT_CYCLES = 54000000,    // VD_HI_N 变高后再等多久停扫描，约 1 s（T_VD_WAIT，待实测）
    parameter integer TIMER_W        = 27
) (
    input  wire       clk,
    input  wire       rst,

    input  wire       btn_run,      // 按键脉冲（开/关翻转）
    input  wire       cmd_start,    // 命令脉冲：开机 / 清除故障
    input  wire       cmd_stop,     // 命令脉冲：关机
    input  wire       vd_inhibit,   // 1 = 暂时不允许开 VD
    input  wire       vl_ok,        // 1 = +5V_EL 正常
    input  wire       pfail_n,      // 0 = 24V 掉电
    input  wire       vd_flt_n,     // 0 = VD eFuse 故障
    input  wire       vl_flt_n,     // 0 = VL eFuse 故障
    input  wire       vd_hi_n,      // 0 = VD 仍高于检测门限

    input  wire       frame_tick,   // 来自 el_scan_timing
    input  wire       scan_running,

    output reg        scan_en,
    output reg        scan_abort,
    output reg        oe_n,
    output reg        vd_on_n,

    output reg  [2:0] state,
    output reg        fault,        // 锁存：eFuse 故障
    output reg        pfail_seen    // 锁存：发生过 PFAIL，下次开机时清除
);

    localparam [2:0] ST_OFF    = 3'd0,
                     ST_OE_ON  = 3'd1,
                     ST_SCAN   = 3'd2,
                     ST_RUN    = 3'd3,
                     ST_VD_OFF = 3'd4,
                     ST_STOP   = 3'd5,
                     ST_OE_OFF = 3'd6,
                     ST_FAULT  = 3'd7;

    reg [TIMER_W-1:0] timer;
    reg [7:0]         frames;

    wire flt_now = ~vd_flt_n | ~vl_flt_n;
    wire active  = (state != ST_OFF) && (state != ST_FAULT);

    always @(posedge clk) begin
        if (rst) begin
            state      <= ST_OFF;
            timer      <= {TIMER_W{1'b0}};
            frames     <= 8'd0;
            scan_en    <= 1'b0;
            scan_abort <= 1'b0;
            oe_n       <= 1'b1;
            vd_on_n    <= 1'b1;
            fault      <= 1'b0;
            pfail_seen <= 1'b0;
        end else begin
            scan_abort <= 1'b0;

            if (active && !vl_ok) begin
                // VL 掉电：全部立刻关
                vd_on_n    <= 1'b1;
                scan_en    <= 1'b0;
                scan_abort <= 1'b1;
                oe_n       <= 1'b1;
                state      <= ST_OFF;
            end else if (active && (flt_now || !pfail_n) &&
                         (state == ST_OE_ON || state == ST_SCAN || state == ST_RUN)) begin
                // 故障或 PFAIL：立刻关 VD，转入关机流程（继续扫描）
                vd_on_n <= 1'b1;
                if (flt_now)  fault      <= 1'b1;
                if (!pfail_n) pfail_seen <= 1'b1;
                if (state == ST_OE_ON) begin
                    // 还没开始扫描：直接收 OE
                    state <= ST_OE_OFF;
                end else begin
                    timer <= {TIMER_W{1'b0}};
                    state <= ST_VD_OFF;
                end
            end else begin
                if (active && flt_now)  fault      <= 1'b1;
                if (active && !pfail_n) pfail_seen <= 1'b1;

                case (state)
                    ST_OFF: begin
                        scan_en <= 1'b0;
                        oe_n    <= 1'b1;
                        vd_on_n <= 1'b1;
                        if ((btn_run || cmd_start) && vl_ok && pfail_n && !flt_now && !fault) begin
                            pfail_seen <= 1'b0;
                            timer      <= {TIMER_W{1'b0}};
                            oe_n       <= 1'b0;
                            state      <= ST_OE_ON;
                        end
                    end

                    ST_OE_ON: begin
                        if (timer == OE_LEAD_CYCLES - 1) begin
                            frames  <= 8'd0;
                            scan_en <= 1'b1;
                            state   <= ST_SCAN;
                        end else begin
                            timer <= timer + 1'b1;
                        end
                    end

                    ST_SCAN: begin
                        if (frame_tick)
                            frames <= frames + 8'd1;
                        if (frames >= SCAN_FRAMES) begin
                            vd_on_n <= vd_inhibit;
                            state   <= ST_RUN;
                        end else if (btn_run || cmd_stop) begin
                            // 还没开 VD 就要求关机：直接停扫描
                            state <= ST_STOP;
                        end
                    end

                    ST_RUN: begin
                        if (btn_run || cmd_stop) begin
                            vd_on_n <= 1'b1;
                            timer   <= {TIMER_W{1'b0}};
                            state   <= ST_VD_OFF;
                        end else begin
                            vd_on_n <= vd_inhibit;
                        end
                    end

                    ST_VD_OFF: begin
                        vd_on_n <= 1'b1;
                        if (!vd_hi_n) begin
                            timer <= {TIMER_W{1'b0}};        // VD 还高，从头计时
                        end else if (timer == VD_WAIT_CYCLES - 1) begin
                            state <= ST_STOP;
                        end else begin
                            timer <= timer + 1'b1;
                        end
                    end

                    ST_STOP: begin
                        scan_en <= 1'b0;
                        if (!scan_en && !scan_running)
                            state <= ST_OE_OFF;
                    end

                    ST_OE_OFF: begin
                        scan_en <= 1'b0;
                        oe_n    <= 1'b1;
                        state   <= fault ? ST_FAULT : ST_OFF;
                    end

                    ST_FAULT: begin
                        scan_en <= 1'b0;
                        oe_n    <= 1'b1;
                        vd_on_n <= 1'b1;
                        if ((btn_run || cmd_start) && !flt_now) begin
                            fault <= 1'b0;
                            state <= ST_OFF;
                        end
                    end

                    default: state <= ST_OFF;
                endcase
            end
        end
    end

endmodule
