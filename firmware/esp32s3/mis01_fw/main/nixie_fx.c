#include <string.h>
#include "esp_log.h"
#include "nixie_fx.h"
#include "hv.h"
#include "power.h"
#include "rtc.h"
#include "cfg.h"
#include "util.h"

static const char *TAG = "nixie_fx";

#define ROLL_STEP_MS  40     // 滚动时每 40 ms 换一个数字
#define ACP_DIGIT_MS  1000   // 修复时每个数字 1 s

static bool s_roll;
static uint32_t s_roll_t0;
static int s_first_stop, s_step;

void nixfx_roll_start(int first_stop_ms, int step_ms)
{
    s_roll = true;
    s_roll_t0 = now_ms();
    s_first_stop = first_stop_ms;
    s_step = step_ms;
}

bool nixfx_roll_active(void)
{
    if (s_roll && now_ms() - s_roll_t0 >= (uint32_t)(s_first_stop + 5 * s_step)) s_roll = false;
    return s_roll;
}

void nixfx_roll_apply(uint8_t d[6])
{
    if (!nixfx_roll_active()) return;
    uint32_t el = now_ms() - s_roll_t0;
    for (int i = 0; i < 6; i++)
        if (el < (uint32_t)(s_first_stop + i * s_step))
            d[i] = (uint8_t)((el / ROLL_STEP_MS + i * 3) % 10);   // 各位错开起点，看着更像老虎机
}

// ---------------- 每日修复 ----------------
static bool s_acp;
static uint32_t s_acp_t0, s_acp_len_ms;
static int s_done_day = -1;

static bool acp_allowed(void)
{
    return power_sw_hv() && !power_pfail() && hv_get_mode() != HV_MODE_OFF;
}

void nixfx_acp_tick(void)
{
    if (s_acp) {
        if (!acp_allowed()) { s_acp = false; ESP_LOGI(TAG, "每日修复中止"); }
        else if (now_ms() - s_acp_t0 >= s_acp_len_ms) { s_acp = false; ESP_LOGI(TAG, "每日修复完成"); }
        return;
    }
    if (g_cfg.nix_acp_min <= 0 || !clk_time_valid()) return;
    uint32_t t = clk_now();
    int day = (int)(t / 86400);
    int mod = (int)(t % 86400) / 60;
    int trigger = g_cfg.night_start_min != g_cfg.night_end_min ? g_cfg.night_start_min : 0;
    if (mod != trigger || day == s_done_day) return;
    s_done_day = day;                 // 不管做没做成，今天都算过了
    if (!acp_allowed()) { ESP_LOGI(TAG, "每日修复跳过（高压不允许）"); return; }
    s_acp = true;
    s_acp_t0 = now_ms();
    s_acp_len_ms = (uint32_t)g_cfg.nix_acp_min * 60000u;
    ESP_LOGI(TAG, "每日防中毒修复开始，%d 分钟", g_cfg.nix_acp_min);
}

bool nixfx_acp_active(void) { return s_acp; }

void nixfx_acp_apply(uint8_t d[6], uint8_t *dp)
{
    uint8_t v = (uint8_t)(((now_ms() - s_acp_t0) / ACP_DIGIT_MS) % 10);
    memset(d, v, 6);
    *dp = 0x3F;
}
