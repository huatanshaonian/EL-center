// IV-18 扫描引擎。
// 每位一个时间片（SLOT_US）。GPTimer 中断在一片里走三步：
//   ① 片头：BLANK=高，换到下一位，通知扫描任务去装这一位的数据；
//   ② 片头 + LOAD_US：扫描任务已装好本片数据才放开 BLANK（否则整片保持全灭）；
//   ③ 再过亮度对应的时间：BLANK=高。
// 所以扫描任务卡住、SPI 抢不到、数据没装好时都只会"这位不亮"，不会某一位常亮（S1）。
// 中断本身停了（死机）由中断看门狗复位，复位后 BLANK 板上上拉 = 全灭；另有 panic 钩子先关显示（safety.c）。
// 控制任务每轮检查片计数，20 ms 不走即判扫描故障并按关显示顺序全关。
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "driver/gpio.h"
#include "driver/gptimer.h"
#include "hal/gpio_ll.h"
#include "esp_attr.h"
#include "esp_log.h"
#include "esp_task_wdt.h"
#include "vfd_scan.h"
#include "spibus.h"
#include "ledc_map.h"
#include "cfg.h"
#include "evlog.h"
#include "proto.h"
#include "pins.h"
#include "util.h"

static const char *TAG = "vfd_scan";

#define SLOT_US      1000   // 每位 1 ms，9 位帧率 111 Hz（规格 F5）；G1 不显示内容也保留时隙，每位 ≤ 1/9（S1）
#define LOAD_US      100    // 片头到放开 BLANK：这段时间内 BLANK 为高，期间装数据（规格要求先 BLANK 2–5 µs；60 µs 实测偶有来不及）
#define GUARD_US     10     // 片尾留的全灭时间
#define MAX_ON_US    (SLOT_US - LOAD_US - GUARD_US)
#define PREHEAT_MS   200    // 灯丝预热 [默认 200 ms，实测后定]
#define FIL_LEAD_MS  20     // FIL 先跑多久再开 IV18_PWR_EN：板上约 5 ms 才判定 FIL 正常，规格要求 ≥ 10 ms（S6）
#define FIL_RES      LEDC_TIMER_8_BIT

typedef enum { VS_OFF = 0, VS_FIL_LEAD, VS_PREHEAT, VS_ON } vs_state_t;

static gptimer_handle_t s_tmr;
static TaskHandle_t s_task;
static SemaphoreHandle_t s_ready_sem;

// ISR 与扫描任务同在核 1
static volatile bool     s_enable;       // 允许放开 BLANK
static volatile uint32_t s_slot_seq;     // 片计数
static volatile uint32_t s_ready_seq;    // 已装好数据的片号
static volatile uint8_t  s_slot_idx;
static volatile uint16_t s_cur_on_us;
static volatile uint32_t s_loaded_cnt, s_lit_cnt;   // 统计：装好数据的片数、真正放开 BLANK 的片数
static uint64_t s_t0;
static uint8_t  s_phase;

static uint32_t s_frames[2][VFD_GRIDS];
static volatile int s_active;
static volatile int s_brt = 700;
static vs_state_t s_state = VS_OFF;
static uint32_t s_state_ms;
static uint32_t s_last_seq_seen, s_last_seq_ms;
static bool s_fault, s_running;
static volatile bool s_isr_off;
static int s_fil_hz_applied;

static inline void IRAM_ATTR blank(bool on) { gpio_ll_set_level(&GPIO, PIN_BLANK_6921, on ? 1 : 0); }

static bool IRAM_ATTR on_alarm(gptimer_handle_t t, const gptimer_alarm_event_data_t *ed, void *ctx)
{
    BaseType_t hp = pdFALSE;
    uint64_t next;
    switch (s_phase) {
    case 0:
        blank(true);
        s_t0 = ed->alarm_value;
        s_slot_idx = (s_slot_idx + 1) % VFD_GRIDS;
        s_slot_seq++;
        vTaskNotifyGiveFromISR(s_task, &hp);
        s_phase = 1;
        next = s_t0 + LOAD_US;
        break;
    case 1:
        if (s_enable && s_ready_seq == s_slot_seq && s_cur_on_us > 0) {
            blank(false);
            s_lit_cnt++;
            s_phase = 2;
            next = s_t0 + LOAD_US + s_cur_on_us;
        } else {
            s_phase = 0;
            next = s_t0 + SLOT_US;
        }
        break;
    default:
        blank(true);
        s_phase = 0;
        next = s_t0 + SLOT_US;
        break;
    }
    gptimer_alarm_config_t a = { .alarm_count = next };
    gptimer_set_alarm_action(t, &a);
    return hp == pdTRUE;
}

static void scan_task(void *arg)
{
    gptimer_config_t tc = {
        .clk_src = GPTIMER_CLK_SRC_DEFAULT,
        .direction = GPTIMER_COUNT_UP,
        .resolution_hz = 1000000,
        .intr_priority = 3,
    };
    ESP_ERROR_CHECK(gptimer_new_timer(&tc, &s_tmr));
    gptimer_event_callbacks_t cb = { .on_alarm = on_alarm };
    ESP_ERROR_CHECK(gptimer_register_event_callbacks(s_tmr, &cb, NULL));   // 中断分配在本核（核 1）
    ESP_ERROR_CHECK(gptimer_enable(s_tmr));
    xSemaphoreGive(s_ready_sem);
    esp_task_wdt_add(NULL);

    for (;;) {
        uint32_t n = ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(100));
        esp_task_wdt_reset();
        if (!n || !s_enable) continue;
        uint32_t seq = s_slot_seq;
        int idx = s_slot_idx;
        uint32_t frame = s_frames[s_active][idx];
        uint32_t on = (uint32_t)MAX_ON_US * (uint32_t)s_brt / 1000u;
        if (!spibus_try_lock_us(30)) continue;     // 抢不到总线：本片不亮
        spibus_send_6921_locked(frame);
        spibus_unlock();
        if (seq == s_slot_seq) {                   // 没被下一片超过才算装好
            s_cur_on_us = (uint16_t)on;
            s_ready_seq = seq;
            s_loaded_cnt++;
        }
    }
}

static void fil_start(void)
{
    ledc_set_duty(LEDC_MODE, LEDC_CH_FIL, 128);    // 50% 方波，硬件持续翻转（S6）
    ledc_update_duty(LEDC_MODE, LEDC_CH_FIL);
}

static void fil_stop(void) { ledc_stop(LEDC_MODE, LEDC_CH_FIL, 0); }

void vfd_scan_init(void)
{
    // 安全默认：BLANK 高、IV-18 电源关
    gpio_set_level(PIN_BLANK_6921, 1);
    gpio_set_level(PIN_IV18_PWR_EN, 0);
    gpio_config_t io = { .pin_bit_mask = (1ULL << PIN_BLANK_6921) | (1ULL << PIN_IV18_PWR_EN), .mode = GPIO_MODE_OUTPUT };
    gpio_config(&io);

    ledc_timer_config_t lt = {
        .speed_mode = LEDC_MODE, .duty_resolution = FIL_RES, .timer_num = LEDC_TMR_FIL,
        .freq_hz = g_cfg.fil_hz, .clk_cfg = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&lt);
    ledc_channel_config_t lc = {
        .gpio_num = PIN_IV18_FIL, .speed_mode = LEDC_MODE, .channel = LEDC_CH_FIL,
        .timer_sel = LEDC_TMR_FIL, .duty = 0, .hpoint = 0,
    };
    ledc_channel_config(&lc);
    fil_stop();
    s_fil_hz_applied = g_cfg.fil_hz;

    s_ready_sem = xSemaphoreCreateBinary();
    xTaskCreatePinnedToCore(scan_task, "vfd_scan", 3072, NULL, configMAX_PRIORITIES - 2, &s_task, 1);
    xSemaphoreTake(s_ready_sem, portMAX_DELAY);
}

void vfd_scan_set_frames(const uint32_t f[VFD_GRIDS])
{
    int nxt = s_active ^ 1;
    memcpy(s_frames[nxt], f, sizeof(s_frames[nxt]));
    s_active = nxt;
}

void vfd_scan_set_brightness(int p) { s_brt = clampi(p, 0, 1000); }

static void start_scan(void)
{
    s_phase = 0;
    s_ready_seq = s_slot_seq - 1;
    gptimer_set_raw_count(s_tmr, 0);
    gptimer_alarm_config_t a = { .alarm_count = 100 };
    gptimer_set_alarm_action(s_tmr, &a);
    s_enable = true;
    gptimer_start(s_tmr);
    s_running = true;
    s_last_seq_seen = s_slot_seq;
    s_last_seq_ms = now_ms();
}

// 关显示顺序：BLANK=高 → 停扫描 → IV18_PWR_EN=低（灯丝与 XL6009 一起断）→ 停灯丝方波
static void power_down(const char *why)
{
    s_enable = false;
    blank(true);
    if (s_running) { gptimer_stop(s_tmr); s_running = false; }
    blank(true);
    gpio_set_level(PIN_IV18_PWR_EN, 0);
    fil_stop();
    if (s_state != VS_OFF) ESP_LOGI(TAG, "IV-18 关（%s）", why);
    s_state = VS_OFF;
    s_state_ms = now_ms();
}

void IRAM_ATTR vfd_scan_emergency_off_isr(void)
{
    s_enable = false;
    blank(true);
    gpio_ll_set_level(&GPIO, PIN_IV18_PWR_EN, 0);
    s_isr_off = true;
}

void vfd_scan_power(bool want)
{
    if (s_isr_off) { s_isr_off = false; power_down("紧急关断"); }
    if (g_cfg.fil_hz != s_fil_hz_applied) {
        ledc_set_freq(LEDC_MODE, LEDC_TMR_FIL, g_cfg.fil_hz);
        s_fil_hz_applied = g_cfg.fil_hz;
    }
    want = want && !s_fault;
    switch (s_state) {
    case VS_OFF:
        if (want && now_ms() - s_state_ms >= 100) {
            // 开显示顺序：先让灯丝方波跑 FIL_LEAD_MS，再开 IV18_PWR_EN，预热后开始扫描
            fil_start();
            s_state = VS_FIL_LEAD;
            s_state_ms = now_ms();
        }
        break;
    case VS_FIL_LEAD:
        if (!want) { power_down("灯丝先行中取消"); break; }
        if (now_ms() - s_state_ms >= FIL_LEAD_MS) {
            gpio_set_level(PIN_IV18_PWR_EN, 1);
            s_state = VS_PREHEAT;
            s_state_ms = now_ms();
            ESP_LOGI(TAG, "IV-18 上电，预热 %d ms", PREHEAT_MS);
        }
        break;
    case VS_PREHEAT:
        if (!want) { power_down("预热中取消"); break; }
        if (now_ms() - s_state_ms >= PREHEAT_MS) { start_scan(); s_state = VS_ON; }
        break;
    case VS_ON:
        if (!want) power_down("不需要显示");
        break;
    }
}

void vfd_scan_check(void)
{
    if (s_state != VS_ON) return;
    uint32_t seq = s_slot_seq;
    if (seq != s_last_seq_seen) {
        s_last_seq_seen = seq;
        s_last_seq_ms = now_ms();
    } else if (now_ms() - s_last_seq_ms >= 20) {   // 20 ms（25 片）片计数不动：扫描停了
        s_fault = true;
        power_down("扫描心跳丢失");
        evlog_add(EV_SCAN_FAULT, 0);
        proto_report("!ERR VFD scan stalled");
    }
}

bool vfd_scan_is_on(void) { return s_state == VS_ON; }
bool vfd_scan_fault(void) { return s_fault; }
void vfd_scan_clear_fault(void) { s_fault = false; }

void vfd_scan_stats(uint32_t *slots, uint32_t *loaded, uint32_t *lit)
{
    *slots = s_slot_seq;
    *loaded = s_loaded_cnt;
    *lit = s_lit_cnt;
}

uint32_t vfd_scan_frame(int i) { return s_frames[s_active][i % VFD_GRIDS]; }
