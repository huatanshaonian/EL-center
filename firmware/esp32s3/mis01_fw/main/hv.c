#include "driver/gpio.h"
#include "hal/gpio_ll.h"
#include "esp_attr.h"
#include "esp_log.h"
#include "hv.h"
#include "power.h"
#include "dispmode.h"
#include "nixie.h"
#include "cfg.h"
#include "proto.h"
#include "evlog.h"
#include "pins.h"
#include "util.h"

static const char *TAG = "hv";

static bool s_on;
static volatile bool s_isr_off;
static bool s_fault;
static hv_mode_t s_mode = HV_MODE_AUTO;
static uint32_t s_off_since_ms, s_on_since_ms;

void hv_init(void)
{
    gpio_set_level(PIN_HV_EN, 0);
    gpio_config_t io = { .pin_bit_mask = 1ULL << PIN_HV_EN, .mode = GPIO_MODE_OUTPUT };
    gpio_config(&io);
    s_on = false;
    s_off_since_ms = now_ms();
}

void IRAM_ATTR hv_emergency_off_isr(void)
{
    gpio_ll_set_level(&GPIO, PIN_HV_EN, 0);
    s_isr_off = true;
}

static void set_hv(bool on, const char *why)
{
    gpio_set_level(PIN_HV_EN, on);
    if (on == s_on) return;
    s_on = on;
    if (on) s_on_since_ms = now_ms(); else s_off_since_ms = now_ms();
    ESP_LOGI(TAG, "HV_EN=%d（%s）", on, why);
    proto_report("!HV %d", on);
}

void hv_tick(void)
{
    if (s_isr_off) {
        // 中断里已经拉低引脚，这里同步软件状态
        s_isr_off = false;
        if (s_on) set_hv(false, "PFAIL/紧急关断");
    }
    bool need = s_mode == HV_MODE_ON || (s_mode == HV_MODE_AUTO && (dm_local_wanted() || nixie_needs_hv()));
    bool want = power_sw_hv() && need && !power_pfail() && !s_fault && !power_outputs_blocked();

    if (!want && s_on) set_hv(false, !power_sw_hv() ? "钮子关" : (power_pfail() ? "PFAIL" : "不需要"));
    else if (want && !s_on && now_ms() - s_off_since_ms >= (uint32_t)g_cfg.hv_gap_s * 1000u) set_hv(true, "需要高压");
}

bool hv_is_on(void) { return s_on; }
hv_mode_t hv_get_mode(void) { return s_mode; }
uint32_t hv_on_ms(void) { return s_on ? now_ms() - s_on_since_ms : 0; }

void hv_set_mode(hv_mode_t m)
{
    s_mode = m;
    if (m != HV_MODE_ON && s_fault) { s_fault = false; ESP_LOGI(TAG, "高压故障锁定已清除"); }
    // 实际开关由控制任务的 hv_tick 执行（单一写入者）
}

void hv_set_fault(const char *why)
{
    s_fault = true;
    set_hv(false, why);
    evlog_add(EV_HV_FAULT, 0);
    proto_report("!ERR HV %s", why);
}

void hv_on_pfail(void)
{
    gpio_set_level(PIN_HV_EN, 0);
    if (s_on) set_hv(false, "PFAIL");
    s_isr_off = false;
}
