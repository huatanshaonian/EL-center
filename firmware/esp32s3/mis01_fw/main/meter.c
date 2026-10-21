#include "meter.h"
#include "anim.h"
#include "ledc_map.h"
#include "dispmode.h"
#include "cfg.h"
#include "pins.h"
#include "util.h"

static volatile int s_val;
static volatile bool s_raw;
static int s_duty_applied = -1;

void meter_init(void)
{
    ledc_timer_config_t t = {
        .speed_mode = LEDC_MODE, .duty_resolution = LEDC_TIMER_12_BIT, .timer_num = LEDC_TMR_METER,
        .freq_hz = 19531, .clk_cfg = LEDC_USE_APB_CLK,
    };
    ledc_timer_config(&t);
    ledc_channel_config_t c = {
        .gpio_num = PIN_METER_PWM, .speed_mode = LEDC_MODE, .channel = LEDC_CH_METER,
        .timer_sel = LEDC_TMR_METER, .duty = 0, .hpoint = 0,
    };
    ledc_channel_config(&c);
}

void meter_set(int v, int t_s) { s_raw = false; s_val = v; dm_set_host(DM_MTR, t_s); }
void meter_raw(int raw, int t_s) { s_raw = true; s_val = raw; dm_set_host(DM_MTR, t_s); }
void meter_auto(void) { dm_set_auto(DM_MTR); }
void meter_set_fs(int fs) { g_cfg.mtr_fs = (uint16_t)fs; cfg_save_mtr_fs(); }

// 开机扫一次：2 s 内 0 → 1000 → 0，扫完返回 -1
static int sweep_value(bool *active, uint32_t t0)
{
    if (!*active) return -1;
    uint32_t el = now_ms() - t0;
    if (el >= 2000) { *active = false; return -1; }
    return el < 1000 ? (int)el : (int)(2000 - el);
}

static bool s_sweep;
static uint32_t s_sweep_t0;

void meter_tick(void)
{
    if (anim_take(ANIM_MTR)) { s_sweep = true; s_sweep_t0 = now_ms(); }
    int sw = sweep_value(&s_sweep, s_sweep_t0);
    int duty = sw >= 0 ? sw * g_cfg.mtr_fs / 1000 : 0;
    if (dm_is_host(DM_MTR))
        duty = s_raw ? clampi(s_val, 0, 4095) : clampi(s_val, 0, 1000) * g_cfg.mtr_fs / 1000;
    if (duty != s_duty_applied) {
        ledc_set_duty(LEDC_MODE, LEDC_CH_METER, duty);
        ledc_update_duty(LEDC_MODE, LEDC_CH_METER);
        s_duty_applied = duty;
    }
}
