// BZ 一直由 LEDC 通道驱动：静止电平用 ledc_stop(idle) 输出，报警时放 50% 方波，两声之间回到静止电平。
#include "freertos/FreeRTOS.h"
#include "buzzer.h"
#include "ledc_map.h"
#include "cfg.h"
#include "pins.h"
#include "util.h"

#define BEEP_ON_MS  150
#define BEEP_OFF_MS 150
#define BZ_RES      LEDC_TIMER_10_BIT

static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;
static int s_req_count, s_req_hz;     // 待执行的报警请求
static int s_left;                    // 剩余声数（含正在响的）
static bool s_sounding;
static uint32_t s_phase_ms;
static int s_hz_applied;

static void idle_level(void) { ledc_stop(LEDC_MODE, LEDC_CH_BZ, g_cfg.bz_click ? 1 : 0); }

void buzzer_init(void)
{
    ledc_timer_config_t t = {
        .speed_mode = LEDC_MODE, .duty_resolution = BZ_RES, .timer_num = LEDC_TMR_BZ,
        .freq_hz = g_cfg.bz_hz, .clk_cfg = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&t);
    s_hz_applied = g_cfg.bz_hz;
    ledc_channel_config_t c = {
        .gpio_num = PIN_BZ, .speed_mode = LEDC_MODE, .channel = LEDC_CH_BZ,
        .timer_sel = LEDC_TMR_BZ, .duty = 0, .hpoint = 0,
    };
    ledc_channel_config(&c);
    idle_level();   // 按 NVS 静音设置给出静止电平
}

void bz_set_click(bool on)
{
    g_cfg.bz_click = on;
    cfg_save_bz_click();
}

void bz_alarm(int count, int hz)
{
    taskENTER_CRITICAL(&s_mux);
    s_req_count = count;
    s_req_hz = hz > 0 ? hz : g_cfg.bz_hz;
    taskEXIT_CRITICAL(&s_mux);
}

static void beep(bool on)
{
    s_sounding = on;
    s_phase_ms = now_ms();
    if (on) {
        ledc_set_duty(LEDC_MODE, LEDC_CH_BZ, 1u << (BZ_RES - 1));
        ledc_update_duty(LEDC_MODE, LEDC_CH_BZ);
    } else {
        idle_level();
    }
}

void buzzer_tick(void)
{
    int req, hz;
    taskENTER_CRITICAL(&s_mux);
    req = s_req_count; hz = s_req_hz; s_req_count = 0;
    taskEXIT_CRITICAL(&s_mux);

    if (req > 0) {
        if (hz != s_hz_applied) { ledc_set_freq(LEDC_MODE, LEDC_TMR_BZ, hz); s_hz_applied = hz; }
        s_left = req;
        beep(true);
        return;
    }
    if (s_left > 0) {
        uint32_t el = now_ms() - s_phase_ms;
        if (s_sounding && el >= BEEP_ON_MS) {
            s_left--;
            beep(false);
        } else if (!s_sounding && el >= BEEP_OFF_MS) {
            beep(true);
        }
        return;
    }
    // 空闲：静音设置可能被改了，静止电平跟上
    static bool last_click = true;
    static bool first = true;
    if (first || last_click != g_cfg.bz_click) { idle_level(); last_click = g_cfg.bz_click; first = false; }
}
