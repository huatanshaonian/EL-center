// 辉光钟内容与 595 刷新。亮灭跟随高压（F2）：高压关时发全灭帧。
// 位序（规格 F4）：SPI 模式 0、MSB 先发；字节 0 bit5..0 = 管 1..6 右小数点；
// 字节 1..3 = (十位 << 4) | 个位，半字节为 K155ID1 的 DCBA；0xF = 该位全灭。
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "esp_log.h"
#include "nixie.h"
#include "nixie_fx.h"
#include "anim.h"
#include "spibus.h"
#include "dispmode.h"
#include "hv.h"
#include "rtc.h"
#include "cfg.h"
#include "util.h"

static const char *TAG = "nixie";

#define BLANK_D      0xF
#define CYCLE_STEP_MS 200

static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;
static uint8_t s_host_dig[6];
static uint8_t s_host_dp;          // bit5..0 = 管 1..6
static bool s_cycle_req;
static int s_cycle_step = -1;      // -1 = 不在轮换
static uint32_t s_cycle_step_ms, s_last_cycle_ms;
static uint8_t s_last_frame[4];
static uint32_t s_last_send_ms;
static int s_last_min = -1;

void nixie_init(void)
{
    uint8_t blank[4] = {0, 0xFF, 0xFF, 0xFF};
    spibus_send_595(blank);
    memcpy(s_last_frame, blank, 4);
    s_last_cycle_ms = now_ms();
}

int nixie_show(const char *t, int t_s)
{
    uint8_t dig[6], dp = 0;
    int n = 0;
    for (const char *p = t; *p; p++) {
        if (*p == '.') {
            if (n == 0) return -1;              // 点在最前：前面没有管
            dp |= 1u << (6 - n);                // 前一位（管 n）的右小数点 → bit(6-n)
            continue;
        }
        if (n >= 6) return -1;
        if (*p == ' ') dig[n++] = BLANK_D;
        else if (*p >= '0' && *p <= '9') dig[n++] = (uint8_t)(*p - '0');
        else return -1;
    }
    // 不足 6 位时右对齐（左侧补灭），小数点跟着移
    int pad = 6 - n;
    uint8_t out[6];
    for (int i = 0; i < 6; i++) out[i] = i < pad ? BLANK_D : dig[i - pad];
    dp >>= pad;
    taskENTER_CRITICAL(&s_mux);
    memcpy(s_host_dig, out, 6);
    s_host_dp = dp;
    taskEXIT_CRITICAL(&s_mux);
    dm_set_host(DM_NIX, t_s);
    return 0;
}

void nixie_off(int t_s)
{
    taskENTER_CRITICAL(&s_mux);
    memset(s_host_dig, BLANK_D, 6);
    s_host_dp = 0;
    taskEXIT_CRITICAL(&s_mux);
    dm_set_host(DM_NIX, t_s);
}

void nixie_auto(void) { dm_set_auto(DM_NIX); }
void nixie_cycle_now(void) { s_cycle_req = true; }

static void make_frame(const uint8_t d[6], uint8_t dp, uint8_t f[4])
{
    f[0] = dp & 0x3F;
    f[1] = (uint8_t)((d[0] << 4) | d[1]);
    f[2] = (uint8_t)((d[2] << 4) | d[3]);
    f[3] = (uint8_t)((d[4] << 4) | d[5]);
}

void nixie_tick(void)
{
    uint32_t now = now_ms();
    uint8_t d[6], dp = 0;

    nixfx_acp_tick();
    bool acp = nixfx_acp_active();

    // 开机动画：高压开 300 ms 后（高压板升压完成）滚动停到当前内容
    if (hv_on_ms() >= 300 && anim_take(ANIM_NIX) && !dm_is_host(DM_NIX)) nixfx_roll_start(700, 150);

    // 防阴极中毒：每 NIX_CYCLE_MIN 分钟（高压开着时）6 位一起 0–9 各 200 ms
    if (s_cycle_step < 0 && !acp && !nixfx_roll_active() && hv_is_on()
        && (s_cycle_req || now - s_last_cycle_ms >= (uint32_t)g_cfg.nix_cycle_min * 60000u)) {
        s_cycle_req = false;
        s_cycle_step = 0;
        s_cycle_step_ms = now;
        ESP_LOGI(TAG, "防阴极中毒轮换");
    }
    if (s_cycle_step >= 0) {
        if (now - s_cycle_step_ms >= CYCLE_STEP_MS) { s_cycle_step++; s_cycle_step_ms = now; }
        if (s_cycle_step > 9) { s_cycle_step = -1; s_last_cycle_ms = now; }
    }

    if (!hv_is_on()) {
        memset(d, BLANK_D, 6);
    } else if (acp) {
        nixfx_acp_apply(d, &dp);
    } else if (s_cycle_step >= 0) {
        memset(d, s_cycle_step, 6);
    } else if (dm_is_host(DM_NIX)) {
        taskENTER_CRITICAL(&s_mux);
        memcpy(d, s_host_dig, 6);
        dp = s_host_dp;
        taskEXIT_CRITICAL(&s_mux);
    } else {
        // AUTO：HH:MM:SS，管 2、管 4 右小数点每秒亮 500 ms 作分隔；时间无效时 00:00:00 闪烁
        bool first_half = clk_ms_into_second() < 500;
        if (clk_time_valid()) {
            civil_t c;
            clk_to_civil(clk_now(), &c);
            uint8_t v[6] = {c.hour / 10, c.hour % 10, c.min / 10, c.min % 10, c.sec / 10, c.sec % 10};
            memcpy(d, v, 6);
            if (first_half) dp = (1u << 4) | (1u << 2);   // 管 2 → bit4，管 4 → bit2
            // 换分滚动（防中毒 ①）
            if (c.min != s_last_min) {
                if (s_last_min >= 0 && g_cfg.nix_slot && !nixfx_roll_active()) nixfx_roll_start(250, 60);
                s_last_min = c.min;
            }
        } else if (first_half) {
            memset(d, 0, 6);
            dp = (1u << 4) | (1u << 2);
        } else {
            memset(d, BLANK_D, 6);
        }
    }

    if (hv_is_on() && !acp && s_cycle_step < 0) nixfx_roll_apply(d);

    uint8_t f[4];
    make_frame(d, dp, f);
    // 内容变了立即发；否则每 500 ms 重发一次（防干扰）
    if (memcmp(f, s_last_frame, 4) || now - s_last_send_ms >= 500) {
        if (spibus_send_595(f)) { memcpy(s_last_frame, f, 4); s_last_send_ms = now; }
    }
}

bool nixie_needs_hv(void) { return nixfx_acp_active(); }
void nixie_last_frame(uint8_t f[4]) { memcpy(f, s_last_frame, 4); }
