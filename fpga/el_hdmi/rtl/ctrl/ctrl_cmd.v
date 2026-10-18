// ctrl_cmd.v（54 MHz 域）
// UART 文本命令解析与设置寄存器。一行一条命令，以 CR 或 LF 结束，字母不分大小写，空格忽略。
//   R1 / R0      开机 / 关机（R1 也用于清除故障）
//   S0..S9       信号源：0 = HDMI 视频，1..8 = 测试图案 0..7，9 = 帧缓存自检画面
//   T0..T255     黑白阈值（抖动模式下为亮度偏移，128 = 不偏移）
//   I1 / I0      反色开 / 关
//   D1 / D0      Bayer 抖动开 / 关
//   F60 / F120   EL 刷新率
//   O0..O255     无 HDMI 信号多少秒后关 VD（0 = 不关）
//   P            拉低 HPD 约 150 ms，让信号源重新读 EDID
//   ?            回一行状态（十六进制字段，见 status_char）
// 回应：成功 "OK\r\n"，参数错误 "ERR\r\n"；空行不回应。回应发送中又来新命令时，新命令照常执行但不回应。
`timescale 1ns / 1ps
module ctrl_cmd #(
    parameter [7:0] THR_DEFAULT = 8'd128
) (
    input  wire        clk,
    input  wire        rst,

    input  wire [7:0]  rx_byte,
    input  wire        rx_valid,
    output reg  [7:0]  tx_byte,
    output reg         tx_valid,
    input  wire        tx_ready,

    input  wire        key_src_next,    // 按键：切到下一个信号源

    // 设置
    output reg  [3:0]  src_sel,
    output reg  [7:0]  cfg_threshold,
    output reg         cfg_invert,
    output reg         cfg_dither,
    output reg         cfg_120hz,
    output reg  [7:0]  cfg_timeout_s,
    output reg         cmd_start,
    output reg         cmd_stop,
    output reg         hpd_pulse,
    output reg         src_changed,     // 信号源变了（给 LED 显示用）

    // 状态（用于 '?'）
    input  wire [2:0]  st_state,
    input  wire        st_hdmi_lock,
    input  wire        st_video_ok,
    input  wire [15:0] st_shown,
    input  wire [15:0] st_dropped,
    input  wire [11:0] st_h,
    input  wire [10:0] st_v,
    input  wire        st_fault,
    input  wire        st_pfail,
    input  wire        st_overflow
);

    // ---------------- 行缓冲与数字解析 ----------------
    reg [7:0]  cmd;          // 命令字母（大写），0 = 还没收到
    reg [9:0]  num;          // 十进制参数
    reg [1:0]  ndig;         // 参数位数（最多 3 位）
    reg        bad;          // 本行格式错误

    wire [7:0] up = (rx_byte >= "a" && rx_byte <= "z") ? rx_byte - 8'd32 : rx_byte;
    wire       is_digit = (rx_byte >= "0" && rx_byte <= "9");
    wire       is_eol   = (rx_byte == 8'h0D) || (rx_byte == 8'h0A);

    // ---------------- 回应发送 ----------------
    localparam [1:0] RESP_NONE = 2'd0, RESP_OK = 2'd1, RESP_ERR = 2'd2, RESP_STAT = 2'd3;
    reg [1:0] resp;
    reg [6:0] pos;           // 当前发到第几个字符
    reg       sending;

    localparam integer STAT_LEN = 84;

    function [7:0] hex;
        input [3:0] v;
        hex = (v < 4'd10) ? (8'd48 + v) : (8'd55 + v);
    endfunction

    // 状态行：ST=s SRC=s HDMI=l VID=v SHOWN=hhhh DROP=hhhh H=hhh V=hhh T=hh I=i D=d F=nnn O=hh FLT=f PF=p OVF=o\r\n
    reg [7:0] stat_char;
    always @(*) begin
        case (pos)
            7'd0:  stat_char = "S";  7'd1:  stat_char = "T";  7'd2:  stat_char = "=";  7'd3:  stat_char = hex({1'b0, st_state});
            7'd4:  stat_char = " ";  7'd5:  stat_char = "S";  7'd6:  stat_char = "R";  7'd7:  stat_char = "C";
            7'd8:  stat_char = "=";  7'd9:  stat_char = hex(src_sel);
            7'd10: stat_char = " ";  7'd11: stat_char = "H";  7'd12: stat_char = "D";  7'd13: stat_char = "M";
            7'd14: stat_char = "I";  7'd15: stat_char = "=";  7'd16: stat_char = hex({3'b0, st_hdmi_lock});
            7'd17: stat_char = " ";  7'd18: stat_char = "V";  7'd19: stat_char = "I";  7'd20: stat_char = "D";
            7'd21: stat_char = "=";  7'd22: stat_char = hex({3'b0, st_video_ok});
            7'd23: stat_char = " ";  7'd24: stat_char = "S";  7'd25: stat_char = "H";  7'd26: stat_char = "O";
            7'd27: stat_char = "W";  7'd28: stat_char = "N";  7'd29: stat_char = "=";
            7'd30: stat_char = hex(st_shown[15:12]);  7'd31: stat_char = hex(st_shown[11:8]);
            7'd32: stat_char = hex(st_shown[7:4]);    7'd33: stat_char = hex(st_shown[3:0]);
            7'd34: stat_char = " ";  7'd35: stat_char = "D";  7'd36: stat_char = "R";  7'd37: stat_char = "O";
            7'd38: stat_char = "P";  7'd39: stat_char = "=";
            7'd40: stat_char = hex(st_dropped[15:12]); 7'd41: stat_char = hex(st_dropped[11:8]);
            7'd42: stat_char = hex(st_dropped[7:4]);   7'd43: stat_char = hex(st_dropped[3:0]);
            7'd44: stat_char = " ";  7'd45: stat_char = "H";  7'd46: stat_char = "=";
            7'd47: stat_char = hex(st_h[11:8]);  7'd48: stat_char = hex(st_h[7:4]);  7'd49: stat_char = hex(st_h[3:0]);
            7'd50: stat_char = " ";  7'd51: stat_char = "V";  7'd52: stat_char = "=";
            7'd53: stat_char = hex({1'b0, st_v[10:8]});  7'd54: stat_char = hex(st_v[7:4]);  7'd55: stat_char = hex(st_v[3:0]);
            7'd56: stat_char = " ";  7'd57: stat_char = "T";  7'd58: stat_char = "=";
            7'd59: stat_char = hex(cfg_threshold[7:4]);  7'd60: stat_char = hex(cfg_threshold[3:0]);
            7'd61: stat_char = " ";  7'd62: stat_char = "I";  7'd63: stat_char = "=";  7'd64: stat_char = hex({3'b0, cfg_invert});
            7'd65: stat_char = " ";  7'd66: stat_char = "D";  7'd67: stat_char = "=";  7'd68: stat_char = hex({3'b0, cfg_dither});
            7'd69: stat_char = " ";  7'd70: stat_char = "F";  7'd71: stat_char = "=";
            7'd72: stat_char = cfg_120hz ? "1" : "0";  7'd73: stat_char = cfg_120hz ? "2" : "6";  7'd74: stat_char = "0";
            7'd75: stat_char = " ";  7'd76: stat_char = "O";  7'd77: stat_char = "=";
            7'd78: stat_char = hex(cfg_timeout_s[7:4]);  7'd79: stat_char = hex(cfg_timeout_s[3:0]);
            7'd80: stat_char = " ";  7'd81: stat_char = st_fault ? "F" : (st_pfail ? "P" : (st_overflow ? "X" : "-"));
            7'd82: stat_char = 8'h0D; 7'd83: stat_char = 8'h0A;
            default: stat_char = 8'h0A;
        endcase
    end

    reg [7:0] resp_char;
    reg       resp_last;
    always @(*) begin
        resp_char = 8'h0A;
        resp_last = 1'b0;
        case (resp)
            RESP_OK: begin
                case (pos)
                    7'd0: resp_char = "O";  7'd1: resp_char = "K";  7'd2: resp_char = 8'h0D;
                    default: begin resp_char = 8'h0A; resp_last = 1'b1; end
                endcase
            end
            RESP_ERR: begin
                case (pos)
                    7'd0: resp_char = "E";  7'd1: resp_char = "R";  7'd2: resp_char = "R";  7'd3: resp_char = 8'h0D;
                    default: begin resp_char = 8'h0A; resp_last = 1'b1; end
                endcase
            end
            RESP_STAT: begin
                resp_char = stat_char;
                resp_last = (pos == STAT_LEN - 1);
            end
            default: ;
        endcase
    end

    // ---------------- 主状态机 ----------------
    reg [1:0] exec_resp;      // 本次执行要发的回应
    reg       exec_now;

    always @(posedge clk) begin
        if (rst) begin
            cmd           <= 8'd0;
            num           <= 10'd0;
            ndig          <= 2'd0;
            bad           <= 1'b0;
            src_sel       <= 4'd0;
            cfg_threshold <= THR_DEFAULT;
            cfg_invert    <= 1'b0;
            cfg_dither    <= 1'b0;
            cfg_120hz     <= 1'b0;
            cfg_timeout_s <= 8'd60;
            cmd_start     <= 1'b0;
            cmd_stop      <= 1'b0;
            hpd_pulse     <= 1'b0;
            src_changed   <= 1'b0;
            resp          <= RESP_NONE;
            pos           <= 7'd0;
            sending       <= 1'b0;
            tx_valid      <= 1'b0;
            tx_byte       <= 8'd0;
        end else begin
            cmd_start   <= 1'b0;
            cmd_stop    <= 1'b0;
            hpd_pulse   <= 1'b0;
            src_changed <= 1'b0;
            tx_valid    <= 1'b0;

            // ---- 按键切信号源 ----
            if (key_src_next) begin
                src_sel     <= (src_sel == 4'd9) ? 4'd0 : src_sel + 4'd1;
                src_changed <= 1'b1;
            end

            // ---- 收字符 ----
            if (rx_valid) begin
                if (is_eol) begin
                    if (cmd != 8'd0) begin
                        // 执行
                        exec_resp = RESP_OK;
                        if (bad) exec_resp = RESP_ERR;
                        else case (cmd)
                            "R": if (ndig != 0 && num == 10'd1) cmd_start <= 1'b1;
                                 else if (ndig != 0 && num == 10'd0) cmd_stop <= 1'b1;
                                 else exec_resp = RESP_ERR;
                            "S": if (ndig != 0 && num <= 10'd9) begin src_sel <= num[3:0]; src_changed <= 1'b1; end
                                 else exec_resp = RESP_ERR;
                            "T": if (ndig != 0 && num <= 10'd255) cfg_threshold <= num[7:0];
                                 else exec_resp = RESP_ERR;
                            "I": if (ndig != 0 && num <= 10'd1) cfg_invert <= num[0];
                                 else exec_resp = RESP_ERR;
                            "D": if (ndig != 0 && num <= 10'd1) cfg_dither <= num[0];
                                 else exec_resp = RESP_ERR;
                            "F": if (ndig != 0 && num == 10'd60) cfg_120hz <= 1'b0;
                                 else if (ndig != 0 && num == 10'd120) cfg_120hz <= 1'b1;
                                 else exec_resp = RESP_ERR;
                            "O": if (ndig != 0 && num <= 10'd255) cfg_timeout_s <= num[7:0];
                                 else exec_resp = RESP_ERR;
                            "P": if (ndig == 0) hpd_pulse <= 1'b1;
                                 else exec_resp = RESP_ERR;
                            "?": if (ndig == 0) exec_resp = RESP_STAT;
                                 else exec_resp = RESP_ERR;
                            default: exec_resp = RESP_ERR;
                        endcase
                        if (!sending) begin
                            resp    <= exec_resp;
                            pos     <= 7'd0;
                            sending <= 1'b1;
                        end
                    end
                    cmd  <= 8'd0;
                    num  <= 10'd0;
                    ndig <= 2'd0;
                    bad  <= 1'b0;
                end else if (rx_byte == " ") begin
                    // 忽略空格
                end else if (cmd == 8'd0) begin
                    cmd <= up;
                end else if (is_digit) begin
                    if (ndig == 2'd3) bad <= 1'b1;
                    else begin
                        num  <= num * 10'd10 + (rx_byte - "0");
                        ndig <= ndig + 2'd1;
                    end
                end else begin
                    bad <= 1'b1;
                end
            end

            // ---- 发回应 ----
            if (sending && tx_ready && !tx_valid) begin
                tx_byte  <= resp_char;
                tx_valid <= 1'b1;
                if (resp_last) begin
                    sending <= 1'b0;
                    resp    <= RESP_NONE;
                end else begin
                    pos <= pos + 7'd1;
                end
            end
        end
    end

endmodule
