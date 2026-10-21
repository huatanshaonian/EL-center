// PCNT 上限设为 1：每计到 1 个下降沿就触发一次中断并自动清零，在中断里做 50 µs 软件死区再计数。
// 盖革板高压来自 HV-C：HV_EN 关时不计数、GMV=0；HV_EN 开后 2 s 才开始计数。
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "driver/pulse_cnt.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "geiger.h"
#include "hv.h"
#include "cfg.h"
#include "proto.h"
#include "pins.h"
#include "util.h"

static const char *TAG = "geiger";

#define DEAD_US     50
#define WINDOW_S    60
#define HV_SETTLE_MS 2000

static pcnt_unit_handle_t s_unit;
static volatile bool s_counting;
static volatile uint32_t s_isr_count;
static int64_t s_last_pulse_us;

static uint16_t s_bins[WINDOW_S];
static int s_bin_idx, s_bins_filled;
static uint32_t s_taken;            // 已转入窗口的 ISR 计数
static uint32_t s_total;
static int s_cpm;
static bool s_valid;
static uint32_t s_sec_ms, s_report_ms;

static bool IRAM_ATTR on_reach(pcnt_unit_handle_t u, const pcnt_watch_event_data_t *ed, void *ctx)
{
    int64_t t = esp_timer_get_time();
    if (s_counting && t - s_last_pulse_us >= DEAD_US) s_isr_count++;
    s_last_pulse_us = t;    // 死区内的毛刺也顺延死区
    return false;
}

void geiger_init(void)
{
    pcnt_unit_config_t uc = { .low_limit = -1, .high_limit = 1 };
    ESP_ERROR_CHECK(pcnt_new_unit(&uc, &s_unit));
    pcnt_glitch_filter_config_t fc = { .max_glitch_ns = 1000 };
    ESP_ERROR_CHECK(pcnt_unit_set_glitch_filter(s_unit, &fc));
    pcnt_chan_config_t cc = { .edge_gpio_num = PIN_GEIGER_IN, .level_gpio_num = -1 };
    pcnt_channel_handle_t ch;
    ESP_ERROR_CHECK(pcnt_new_channel(s_unit, &cc, &ch));
    // 上升沿不动，下降沿 +1
    ESP_ERROR_CHECK(pcnt_channel_set_edge_action(ch, PCNT_CHANNEL_EDGE_ACTION_HOLD, PCNT_CHANNEL_EDGE_ACTION_INCREASE));
    ESP_ERROR_CHECK(pcnt_unit_add_watch_point(s_unit, 1));
    pcnt_event_callbacks_t cbs = { .on_reach = on_reach };
    ESP_ERROR_CHECK(pcnt_unit_register_event_callbacks(s_unit, &cbs, NULL));
    gpio_pullup_en(PIN_GEIGER_IN);       // 与底板 10 k 上拉同向，裸板调试时不悬空
    ESP_ERROR_CHECK(pcnt_unit_enable(s_unit));
    ESP_ERROR_CHECK(pcnt_unit_clear_count(s_unit));
    ESP_ERROR_CHECK(pcnt_unit_start(s_unit));
    s_sec_ms = s_report_ms = now_ms();
}

static void clear_window(void)
{
    memset(s_bins, 0, sizeof(s_bins));
    s_bins_filled = 0;
    s_cpm = 0;
}

void geiger_tick(void)
{
    uint32_t now = now_ms();
    bool run = hv_on_ms() >= HV_SETTLE_MS;
    if (run != s_counting) {
        s_counting = run;
        s_taken = s_isr_count;
        clear_window();
        s_valid = run;
        s_sec_ms = now;
        ESP_LOGI(TAG, "%s", run ? "开始计数" : "停止计数（高压关）");
    }
    if (now - s_sec_ms >= 1000) {
        s_sec_ms += 1000;
        if (now - s_sec_ms > 3000) s_sec_ms = now;     // 长时间没调到：不补格
        if (s_counting) {
            uint32_t c = s_isr_count;
            uint32_t n = c - s_taken;
            s_taken = c;
            s_total += n;
            s_bins[s_bin_idx] = (uint16_t)(n > 65535 ? 65535 : n);
            s_bin_idx = (s_bin_idx + 1) % WINDOW_S;
            if (s_bins_filled < WINDOW_S) s_bins_filled++;
            uint32_t sum = 0;
            for (int i = 0; i < WINDOW_S; i++) sum += s_bins[i];
            // 窗口未满时按已有秒数折算到每分钟
            s_cpm = (int)(sum * 60u / (uint32_t)s_bins_filled);
        }
    }
    if (now - s_report_ms >= (uint32_t)g_cfg.gm_period_s * 1000u) {
        s_report_ms = now;
        proto_report("!GM CPM=%d TOTAL=%lu USV=%.3f VALID=%d", s_cpm, (unsigned long)s_total, gm_usv(), s_valid);
    }
}

int gm_cpm(void) { return s_cpm; }
uint32_t gm_total(void) { return s_total; }
float gm_usv(void) { return (float)s_cpm * g_cfg.gm_k; }
bool gm_valid(void) { return s_valid; }
void gm_reset(void) { s_total = 0; }
