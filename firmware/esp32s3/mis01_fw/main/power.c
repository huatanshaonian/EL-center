// 主机电源状态机：
//   OFF → WAIT（钮子开，Pi 由硬件上电，等 PI_RUN）→ RUN（PI_RUN 高，HOLD 高）
//   → SHUT（钮子关：HOLD 仍高、PI_SHDN_REQ 拉低、发 !SHUTDOWN；或 Pi 发 SHUTDOWN：不拉 PI_SHDN_REQ）
//   → PI_RUN 持续低 5 s（或超时 60 s）→ 松开 HOLD → OFF（钮子仍开则 WAIT）
// S4：HOLD 只在看到 PI_RUN 为高后拉高；SHUT 兜底 60 s 必须松开。
// S5：PI_SHDN_REQ 只用开漏拉低，从不推挽输出高电平。
#include "driver/gpio.h"
#include "esp_log.h"
#include "power.h"
#include "hv.h"
#include "vfd.h"
#include "dispmode.h"
#include "proto.h"
#include "evlog.h"
#include "buzzer.h"
#include "pins.h"
#include "util.h"

static const char *TAG = "power";

#define DEBOUNCE_N        3        // 3 次 × 10 ms
#define PI_OFF_CONFIRM_MS 5000     // PI_RUN 低持续 ≥ 5 s 才算关机完成
#define SHUT_TIMEOUT_MS   60000

typedef struct { bool stable; bool last_raw; uint8_t cnt; } deb_t;

static deb_t s_host, s_hv, s_scr, s_pirun;
static pwr_state_t s_state = PWR_OFF;
static uint32_t s_shut_start_ms, s_pirun_low_ms;
static bool s_shut_by_cmd, s_shdn_req_active;
static bool s_wait_pirun_low;   // 关机流程结束后：要先看到 PI_RUN 变低，才允许再拉 HOLD（防止超时松开后又被接住）
static volatile bool s_pfail_latched;
static TaskHandle_t s_ctrl_task;
static uint32_t s_pfail_bit;

static bool sw_on(int level) { return level == SW_ACTIVE_LEVEL; }
static bool scr_on(int level) { return level == SCR_ON_LEVEL; }

static bool deb_update(deb_t *d, bool raw)
{
    if (raw != d->last_raw) { d->last_raw = raw; d->cnt = 0; return false; }
    if (raw == d->stable) { d->cnt = 0; return false; }
    if (++d->cnt >= DEBOUNCE_N) { d->stable = raw; d->cnt = 0; return true; }
    return false;
}

static void deb_init(deb_t *d, bool raw) { d->stable = d->last_raw = raw; d->cnt = 0; }

static void set_hold(bool on) { gpio_set_level(PIN_HOLD, on); }

static void set_shdn_req(bool active)
{
    // 开漏：写 0 = 拉低，写 1 = 释放（高阻，由 Pi 侧上拉到 3.0 V）
    gpio_set_level(PIN_PI_SHDN_REQ, active ? 0 : 1);
    s_shdn_req_active = active;
}

static void IRAM_ATTR pfail_isr(void *arg)
{
    // F3：立即关高压、BLANK、IV-18 电源（直接写寄存器），其余交给控制任务
    hv_emergency_off_isr();
    vfd_emergency_off_isr();
    s_pfail_latched = true;
    BaseType_t hp = pdFALSE;
    if (s_ctrl_task) xTaskNotifyFromISR(s_ctrl_task, s_pfail_bit, eSetBits, &hp);
    if (hp) portYIELD_FROM_ISR();
}

void power_init(TaskHandle_t ctrl_task, uint32_t pfail_bit)
{
    s_ctrl_task = ctrl_task;
    s_pfail_bit = pfail_bit;

    // 输出：先定电平再改方向，避免毛刺
    gpio_set_level(PIN_HOLD, 0);
    gpio_config_t out = { .pin_bit_mask = 1ULL << PIN_HOLD, .mode = GPIO_MODE_OUTPUT };
    gpio_config(&out);
    gpio_set_level(PIN_PI_SHDN_REQ, 1);
    gpio_config_t od = { .pin_bit_mask = 1ULL << PIN_PI_SHDN_REQ, .mode = GPIO_MODE_OUTPUT_OD };
    gpio_config(&od);

    // 内部弱上下拉与板上外部电阻同方向（并联无害），只为裸开发板调试时输入不悬空：
    // 钮子悬空读作"关"，PI_RUN 悬空读作"Pi 不在"，PFAIL_N 悬空读作"无掉电"
    gpio_config_t sw = {
        .pin_bit_mask = (1ULL << PIN_ST_HOST) | (1ULL << PIN_ST_HV),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = SW_ACTIVE_LEVEL == 0,
        .pull_down_en = SW_ACTIVE_LEVEL != 0,
    };
    gpio_config(&sw);
    // 屏幕钮子：PCB-3 上只有 1 M 上拉，内部上拉一起开更稳；悬空读作"屏亮"
    gpio_config_t scr = { .pin_bit_mask = 1ULL << PIN_ST_SCR, .mode = GPIO_MODE_INPUT, .pull_up_en = 1 };
    gpio_config(&scr);
    gpio_config_t run = { .pin_bit_mask = 1ULL << PIN_PI_RUN, .mode = GPIO_MODE_INPUT, .pull_down_en = 1 };
    gpio_config(&run);
    gpio_config_t pf = {
        .pin_bit_mask = 1ULL << PIN_PFAIL_N, .mode = GPIO_MODE_INPUT, .pull_up_en = 1, .intr_type = GPIO_INTR_NEGEDGE,
    };
    gpio_config(&pf);
    gpio_isr_handler_add(PIN_PFAIL_N, pfail_isr, NULL);

    deb_init(&s_host, sw_on(gpio_get_level(PIN_ST_HOST)));
    deb_init(&s_hv, sw_on(gpio_get_level(PIN_ST_HV)));
    deb_init(&s_scr, scr_on(gpio_get_level(PIN_ST_SCR)));
    deb_init(&s_pirun, gpio_get_level(PIN_PI_RUN));
    if (!gpio_get_level(PIN_PFAIL_N)) s_pfail_latched = true;

    // ESP 中途复位时 Pi 可能正在运行：看到 PI_RUN 高就立刻接住 HOLD
    if (s_pirun.stable) {
        set_hold(true);
        s_state = PWR_RUN;
        if (!s_host.stable) { s_state = PWR_SHUT; s_shut_start_ms = now_ms(); set_shdn_req(true); }
    } else {
        s_state = s_host.stable ? PWR_WAIT : PWR_OFF;
    }
    ESP_LOGI(TAG, "初始：主机钮子=%d 高压钮子=%d 屏幕钮子=%d PI_RUN=%d PFAIL=%d → %s",
             s_host.stable, s_hv.stable, s_scr.stable, s_pirun.stable, power_pfail(), power_state_name());
}

static void enter_shut(bool by_cmd)
{
    s_state = PWR_SHUT;
    s_shut_start_ms = now_ms();
    s_shut_by_cmd = by_cmd;
    if (!by_cmd) {
        set_shdn_req(true);
        proto_report("!SHUTDOWN");
    }
    ESP_LOGI(TAG, "进入 SHUT（%s）", by_cmd ? "Pi 命令" : "钮子关");
}

static void finish_shut(const char *why)
{
    set_hold(false);
    s_wait_pirun_low = true;
    set_shdn_req(false);
    s_shut_by_cmd = false;
    s_state = s_host.stable ? PWR_WAIT : PWR_OFF;
    ESP_LOGI(TAG, "关机完成（%s），松开 HOLD → %s", why, power_state_name());
}

void power_tick(void)
{
    bool ch = false;
    ch |= deb_update(&s_host, sw_on(gpio_get_level(PIN_ST_HOST)));
    ch |= deb_update(&s_hv, sw_on(gpio_get_level(PIN_ST_HV)));
    ch |= deb_update(&s_scr, scr_on(gpio_get_level(PIN_ST_SCR)));
    if (ch) proto_report("!SW HOSTSW=%d HVSW=%d SCRSW=%d", s_host.stable, s_hv.stable, s_scr.stable);

    if (deb_update(&s_pirun, gpio_get_level(PIN_PI_RUN))) {
        if (!s_pirun.stable) { s_pirun_low_ms = now_ms(); dm_all_auto("PI_RUN 变低"); }
    }
    if (gpio_get_level(PIN_PFAIL_N)) s_pfail_latched = false;   // 电平恢复即解除（高压另有 HV_GAP_S 间隔）

    bool pirun = s_pirun.stable;
    uint32_t now = now_ms();
    if (!pirun) s_wait_pirun_low = false;
    switch (s_state) {
    case PWR_OFF:
    case PWR_WAIT:
        if (pirun && !s_wait_pirun_low) {
            set_hold(true);
            s_state = PWR_RUN;
            ESP_LOGI(TAG, "PI_RUN 高 → RUN，拉高 HOLD");
            if (!s_host.stable) enter_shut(false);   // 钮子已经关了（罕见）：直接请关机
        } else {
            s_state = s_host.stable ? PWR_WAIT : PWR_OFF;
        }
        break;
    case PWR_RUN:
        if (!s_host.stable) { enter_shut(false); break; }
        // Pi 自己关机（钮子仍开）：PI_RUN 持续低 5 s 后松开 HOLD；短于 5 s 视为重启
        if (!pirun && now - s_pirun_low_ms >= PI_OFF_CONFIRM_MS) finish_shut("Pi 自行关机");
        break;
    case PWR_SHUT:
        if (s_shdn_req_active && !pirun) set_shdn_req(false);    // PI_RUN 变低即释放请求
        if (!pirun && now - s_pirun_low_ms >= PI_OFF_CONFIRM_MS) finish_shut("PI_RUN 低 5 s");
        else if (now - s_shut_start_ms >= SHUT_TIMEOUT_MS) finish_shut("60 s 超时");
        break;
    }
}

void power_on_pfail_notify(void)
{
    // 高压与 IV-18 已在中断里关掉；这里补做软件状态、日志与上报
    hv_on_pfail();
    vfd_on_pfail();
    // 日志、上报、报警限频：抖动或悬空时不反复写 NVS
    static uint32_t last_ms;
    static bool first = true;
    if (!first && now_ms() - last_ms < 10000) return;
    first = false;
    last_ms = now_ms();
    evlog_add(EV_PFAIL, 0);
    proto_report("!PFAIL");
    bz_alarm(3, 0);
    ESP_LOGW(TAG, "PFAIL：24 V 掉电预警");
}

void power_pi_shutdown_cmd(void)
{
    if (s_state == PWR_SHUT) { s_shut_by_cmd = true; return; }
    if (s_state == PWR_RUN) enter_shut(true);
    else s_shut_by_cmd = false;   // Pi 不在 RUN：没有可接住的电源
}

pwr_state_t power_state(void) { return s_state; }
const char *power_state_name(void)
{
    static const char *n[] = {"OFF", "WAIT", "RUN", "SHUT"};
    return n[s_state];
}
bool power_sw_host(void) { return s_host.stable; }
bool power_sw_hv(void) { return s_hv.stable; }
bool power_sw_scr(void) { return s_scr.stable; }
bool power_pfail(void) { return s_pfail_latched || !gpio_get_level(PIN_PFAIL_N); }
bool power_pi_running(void) { return s_pirun.stable; }
bool power_outputs_blocked(void) { return s_state == PWR_SHUT && s_shut_by_cmd; }
