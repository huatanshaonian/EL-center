// 天气：每 WX_MIN 分钟 HTTPS 取一次 https://api.open-meteo.com/v1/forecast?...&current=temperature_2m,relative_humidity_2m,weather_code
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_http_client.h"
#include "esp_crt_bundle.h"
#include "esp_log.h"
#include "cJSON.h"
#include "weather.h"
#include "wifi_net.h"
#include "ntp.h"
#include "rtc.h"
#include "cfg.h"
#include "util.h"

static const char *TAG = "wx";

#define WX_VALID_MS    (2u * 3600u * 1000u)
#define WX_RETRY_MS    (5u * 60u * 1000u)
#define WX_BUF         2048

static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;
static int s_t_x10, s_rh, s_code;
static uint32_t s_ok_ms;
static bool s_have;

static bool fetch(float lat, float lon)
{
    char url[200];
    snprintf(url, sizeof(url),
             "https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f"
             "&current=temperature_2m,relative_humidity_2m,weather_code",
             (double)lat, (double)lon);
    esp_http_client_config_t hc = {
        .url = url,
        .crt_bundle_attach = esp_crt_bundle_attach,
        .timeout_ms = 10000,
    };
    esp_http_client_handle_t c = esp_http_client_init(&hc);
    if (!c) return false;
    bool ok = false;
    char *buf = malloc(WX_BUF);
    if (buf && esp_http_client_open(c, 0) == ESP_OK) {
        esp_http_client_fetch_headers(c);
        int status = esp_http_client_get_status_code(c);
        int n = 0, r;
        while (n < WX_BUF - 1 && (r = esp_http_client_read(c, buf + n, WX_BUF - 1 - n)) > 0) n += r;
        buf[n] = 0;
        if (status != 200) {
            ESP_LOGW(TAG, "HTTP %d", status);
        } else {
            cJSON *root = cJSON_Parse(buf);
            cJSON *cur = root ? cJSON_GetObjectItem(root, "current") : NULL;
            cJSON *t = cur ? cJSON_GetObjectItem(cur, "temperature_2m") : NULL;
            cJSON *h = cur ? cJSON_GetObjectItem(cur, "relative_humidity_2m") : NULL;
            cJSON *w = cur ? cJSON_GetObjectItem(cur, "weather_code") : NULL;
            if (cJSON_IsNumber(t)) {
                taskENTER_CRITICAL(&s_mux);
                s_t_x10 = (int)lround(t->valuedouble * 10.0);
                s_rh = cJSON_IsNumber(h) ? (int)lround(h->valuedouble) : -1;
                s_code = cJSON_IsNumber(w) ? w->valueint : -1;
                s_ok_ms = now_ms();
                s_have = true;
                taskEXIT_CRITICAL(&s_mux);
                ok = true;
                ESP_LOGI(TAG, "天气：%.1f °C，湿度 %d %%，代码 %d", t->valuedouble, s_rh, s_code);
            } else {
                ESP_LOGW(TAG, "返回内容解析不了");
            }
            cJSON_Delete(root);
        }
    } else {
        ESP_LOGW(TAG, "连不上 api.open-meteo.com");
    }
    free(buf);
    esp_http_client_cleanup(c);
    return ok;
}

static void wx_task(void *arg)
{
    uint32_t next_ms = 0;
    float last_lat = NAN, last_lon = NAN;
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(5000));
        cfg_lock();
        float lat = g_cfg.wx_lat, lon = g_cfg.wx_lon;
        int period_min = g_cfg.wx_min;
        cfg_unlock();
        if (isnan(lat) || isnan(lon)) { s_have = false; continue; }
        if (lat != last_lat || lon != last_lon) {       // 换了城市：旧数据作废，马上取
            last_lat = lat; last_lon = lon;
            s_have = false;
            next_ms = now_ms();
        }
        if (!net_up() || (int32_t)(now_ms() - next_ms) < 0) continue;
        // TLS 证书要校验有效期：系统时间用 RTC 对齐（没开 NTP 时系统时间是 1970）
        if (!ntp_systime_from_clk()) continue;
        bool ok = fetch(lat, lon);
        next_ms = now_ms() + (ok ? (uint32_t)period_min * 60000u : WX_RETRY_MS);
    }
}

void weather_init(void)
{
    xTaskCreatePinnedToCore(wx_task, "wx", 8192, NULL, 2, NULL, 0);
}

bool weather_get(int *t_x10, int *rh, int *code, int *age_s)
{
    taskENTER_CRITICAL(&s_mux);
    bool have = s_have;
    uint32_t age = now_ms() - s_ok_ms;
    if (t_x10) *t_x10 = s_t_x10;
    if (rh) *rh = s_rh;
    if (code) *code = s_code;
    taskEXIT_CRITICAL(&s_mux);
    if (age_s) *age_s = have ? (int)(age / 1000u) : -1;
    return have && age < WX_VALID_MS;
}
