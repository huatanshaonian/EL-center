// 来源：tang-monitor（https://github.com/kami4ka/tang-monitor，commit 1239ace），MIT 许可，
// Copyright (c) 2026 Oleg Kulyk，许可全文见同目录 LICENSE_tang-monitor.txt。
// Hot-plug detect driver: assert HPD ~200ms after reset (lets DDC settle),
// pulse low ~150ms on request to force the source to re-read EDID.
module hpd_ctrl #(
    parameter CLK_HZ = 27_000_000
) (
    input  wire clk,
    input  wire rst_n,
    input  wire pulse_req,   // 1-cycle strobe
    output reg  hpd
);
    localparam integer T_ASSERT = CLK_HZ / 5;       // 200 ms
    localparam integer T_PULSE  = (CLK_HZ / 20) * 3; // 150 ms

    reg [24:0] cnt;
    reg        pulsing;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cnt <= 0; hpd <= 1'b0; pulsing <= 1'b0;
        end else if (pulsing) begin
            if (cnt == T_PULSE) begin
                pulsing <= 1'b0; hpd <= 1'b1; cnt <= 0;
            end else cnt <= cnt + 1'b1;
        end else if (pulse_req) begin
            pulsing <= 1'b1; hpd <= 1'b0; cnt <= 0;
        end else if (!hpd) begin
            if (cnt == T_ASSERT) hpd <= 1'b1;
            else cnt <= cnt + 1'b1;
        end
    end
endmodule
