#include "freertos/FreeRTOS.h"
#include "esp_log.h"
#include "dispmode.h"
#include "util.h"
#include "sensors.h"
#include "rtc.h"
#include "cfg.h"

static const char *TAG = "dm";
static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;
static struct { bool host; bool has_to; uint32_t expire_ms; } s_dm[DM_COUNT];
static volatile uint32_t s_resets;

void dm_set_host(dm_item_t it, int timeout_s)
{
    taskENTER_CRITICAL(&s_mux);
    s_dm[it].host = true;
    s_dm[it].has_to = timeout_s > 0;
    s_dm[it].expire_ms = now_ms() + (uint32_t)timeout_s * 1000u;
    taskEXIT_CRITICAL(&s_mux);
}

void dm_set_auto(dm_item_t it)
{
    taskENTER_CRITICAL(&s_mux);
    s_dm[it].host = false;
    taskEXIT_CRITICAL(&s_mux);
}

void dm_all_auto(const char *why)
{
    bool any = false;
    taskENTER_CRITICAL(&s_mux);
    for (int i = 0; i < DM_COUNT; i++) { any |= s_dm[i].host; s_dm[i].host = false; }
    s_resets++;
    taskEXIT_CRITICAL(&s_mux);
    if (any) ESP_LOGI(TAG, "全部退回 AUTO：%s", why);
}

bool dm_is_host(dm_item_t it) { return s_dm[it].host; }
uint32_t dm_reset_count(void) { return s_resets; }

void dm_tick(void)
{
    uint32_t now = now_ms();
    taskENTER_CRITICAL(&s_mux);
    for (int i = 0; i < DM_COUNT; i++)
        if (s_dm[i].host && s_dm[i].has_to && (int32_t)(now - s_dm[i].expire_ms) >= 0) s_dm[i].host = false;
    taskEXIT_CRITICAL(&s_mux);
}

bool dm_local_wanted(void)
{
    if (!sens_present()) return false;
    if (clk_time_valid()) {          // 时间无效时不判夜间
        civil_t c;
        clk_to_civil(clk_now(), &c);
        if (cfg_is_night(c.hour * 60 + c.min)) return false;
    }
    return true;
}
