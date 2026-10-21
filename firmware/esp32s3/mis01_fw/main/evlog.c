// 事件环形缓冲：整块存 NVS（事件很少，写入次数可忽略）
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "nvs.h"
#include "esp_log.h"
#include "evlog.h"
#include "rtc.h"

static const char *TAG = "evlog";

typedef struct {
    uint32_t t_local;
    int32_t  param;
    uint8_t  code;
    uint8_t  pad[3];
} ev_t;

typedef struct {
    uint16_t head;   // 下一条写入位置
    uint16_t count;
    ev_t ev[EVLOG_SIZE];
} ring_t;

static ring_t s_ring;
static SemaphoreHandle_t s_mtx;

static void save(void)
{
    nvs_handle_t h;
    if (nvs_open("mis01", NVS_READWRITE, &h) != ESP_OK) return;
    if (nvs_set_blob(h, "evlog", &s_ring, sizeof(s_ring)) == ESP_OK) nvs_commit(h);
    nvs_close(h);
}

void evlog_init(void)
{
    s_mtx = xSemaphoreCreateMutex();
    nvs_handle_t h;
    size_t len = sizeof(s_ring);
    if (nvs_open("mis01", NVS_READONLY, &h) == ESP_OK) {
        if (nvs_get_blob(h, "evlog", &s_ring, &len) != ESP_OK || len != sizeof(s_ring)
            || s_ring.head >= EVLOG_SIZE || s_ring.count > EVLOG_SIZE)
            memset(&s_ring, 0, sizeof(s_ring));
        nvs_close(h);
    }
}

void evlog_add(ev_code_t code, int32_t param)
{
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    ev_t *e = &s_ring.ev[s_ring.head];
    e->t_local = clk_time_valid() ? clk_now() : 0;
    e->code = (uint8_t)code;
    e->param = param;
    s_ring.head = (s_ring.head + 1) % EVLOG_SIZE;
    if (s_ring.count < EVLOG_SIZE) s_ring.count++;
    save();
    xSemaphoreGive(s_mtx);
    ESP_LOGW(TAG, "事件 %s %ld", evlog_name(code), (long)param);
}

int evlog_count(void) { return s_ring.count; }

int evlog_get(int i, uint32_t *t, ev_code_t *code, int32_t *param)
{
    if (i < 0 || i >= s_ring.count) return -1;
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    int idx = (s_ring.head + EVLOG_SIZE - s_ring.count + i) % EVLOG_SIZE;
    *t = s_ring.ev[idx].t_local;
    *code = (ev_code_t)s_ring.ev[idx].code;
    *param = s_ring.ev[idx].param;
    xSemaphoreGive(s_mtx);
    return 0;
}

void evlog_clear(void)
{
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    memset(&s_ring, 0, sizeof(s_ring));
    save();
    xSemaphoreGive(s_mtx);
}

const char *evlog_name(ev_code_t c)
{
    switch (c) {
    case EV_BOOT:          return "BOOT";
    case EV_WDT_RESET:     return "WDT";
    case EV_PANIC_RESET:   return "PANIC";
    case EV_BROWNOUT:      return "BROWNOUT";
    case EV_PFAIL:         return "PFAIL";
    case EV_SENSOR_LOST:   return "SENSOR_LOST";
    case EV_SCAN_FAULT:    return "SCAN_FAULT";
    case EV_HV_FAULT:      return "HV_FAULT";
    case EV_TIME_SET:      return "TIME_SET";
    case EV_RTC_INVALID:   return "RTC_INVALID";
    case EV_SELFTEST_FAIL: return "SELFTEST_FAIL";
    }
    return "?";
}
