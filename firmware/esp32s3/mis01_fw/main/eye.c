// 6E2 栅压 PWM。占空比 D = 三极管导通比例：D 越大栅极越负、光条越长（两段合拢）。
// 引脚高阻（复位）时三极管截止 = 光条最短，安全。
// AUTO 本地内容：A = 盖革 CPM（对数，10–10000 CPM → 0–1000）；B = 环境光（对数，1–1000 lux → 0–1000，暂定）。
#include <math.h>
#include <string.h>
#include "eye.h"
#include "anim.h"
#include "hv.h"
#include "ledc_map.h"
#include "dispmode.h"
#include "geiger.h"
#include "sensors.h"
#include "cfg.h"
#include "pins.h"
#include "util.h"

static const int PIN[2] = {PIN_E2_A, PIN_E2_B};
static const ledc_channel_t CH[2] = {LEDC_CH_EYE_A, LEDC_CH_EYE_B};
static const dm_item_t DM[2] = {DM_EYE_A, DM_EYE_B};

static volatile int s_host_val[2];
static volatile bool s_host_raw[2];
static int s_duty_applied[2] = {-1, -1};

void eye_init(void)
{
    ledc_timer_config_t t = {
        .speed_mode = LEDC_MODE, .duty_resolution = LEDC_TIMER_12_BIT, .timer_num = LEDC_TMR_EYE,
        .freq_hz = 10000, .clk_cfg = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&t);
    for (int i = 0; i < 2; i++) {
        ledc_channel_config_t c = {
            .gpio_num = PIN[i], .speed_mode = LEDC_MODE, .channel = CH[i],
            .timer_sel = LEDC_TMR_EYE, .duty = 0, .hpoint = 0,
        };
        ledc_channel_config(&c);
    }
}

static int cal_lookup(int ch, int v)
{
    v = clampi(v, 0, 1000);
    int i = v / 100;
    if (i >= 10) return g_cfg.eye_cal[ch][10];
    int a = g_cfg.eye_cal[ch][i], b = g_cfg.eye_cal[ch][i + 1];
    return a + (b - a) * (v - i * 100) / 100;
}

void eye_set(int ch, int v, int t_s) { s_host_raw[ch] = false; s_host_val[ch] = v; dm_set_host(DM[ch], t_s); }
void eye_raw(int ch, int raw, int t_s) { s_host_raw[ch] = true; s_host_val[ch] = raw; dm_set_host(DM[ch], t_s); }
void eye_auto(int ch) { dm_set_auto(DM[ch]); }

void eye_set_cal(int ch, const uint16_t cal[11])
{
    memcpy(g_cfg.eye_cal[ch], cal, sizeof(g_cfg.eye_cal[ch]));
    cfg_save_eye_cal(ch);
}

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

static int log_map(float x, float lo, float hi)
{
    if (x <= lo) return 0;
    return clampi((int)(1000.0f * log10f(x / lo) / log10f(hi / lo)), 0, 1000);
}

void eye_tick(void)
{
    // 开机动画：高压开满 15 s（6E2 灯丝预热）后张合一次
    if (hv_on_ms() >= 15000 && anim_take(ANIM_EYE)) { s_sweep = true; s_sweep_t0 = now_ms(); }
    int sw = sweep_value(&s_sweep, s_sweep_t0);
    for (int ch = 0; ch < 2; ch++) {
        int duty;
        if (dm_is_host(DM[ch])) {
            duty = s_host_raw[ch] ? clampi(s_host_val[ch], 0, 4095) : cal_lookup(ch, s_host_val[ch]);
        } else {
            int v;
            if (ch == 0) v = gm_valid() ? log_map((float)gm_cpm(), 10.0f, 10000.0f) : 0;
            else { int lux = sens_lux(); v = lux < 0 ? 0 : log_map((float)lux + 1.0f, 1.0f, 1000.0f); }
            duty = cal_lookup(ch, sw >= 0 ? sw : v);
        }
        if (duty != s_duty_applied[ch]) {
            ledc_set_duty(LEDC_MODE, CH[ch], duty);
            ledc_update_duty(LEDC_MODE, CH[ch]);
            s_duty_applied[ch] = duty;
        }
    }
}
