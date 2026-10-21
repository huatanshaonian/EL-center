// NTP 给出 UTC，ESP 内部只存本地时间，需要时区。规格未给时区键，暂用固定 NTP_TZ（见回复里的待补项）。
#include <string.h>
#include <time.h>
#include <sys/time.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_netif_sntp.h"
#include "esp_log.h"
#include "ntp.h"
#include "rtc.h"
#include "power.h"
#include "usb_cdc.h"
#include "evlog.h"
#include "cfg.h"
#include "util.h"

static const char *TAG = "ntp";

#define NTP_RESYNC_MS   (6u * 3600u * 1000u)
#define NTP_RETRY_MS    (10u * 60u * 1000u)
#define WIFI_CONNECTED  BIT0

static EventGroupHandle_t s_evt;
static bool s_wifi_inited;

static void on_wifi(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) xEventGroupSetBits(s_evt, WIFI_CONNECTED);
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) xEventGroupClearBits(s_evt, WIFI_CONNECTED);
}

static bool wifi_up(void)
{
    if (!s_wifi_inited) {
        esp_netif_init();
        esp_event_loop_create_default();
        esp_netif_create_default_wifi_sta();
        wifi_init_config_t wc = WIFI_INIT_CONFIG_DEFAULT();
        if (esp_wifi_init(&wc) != ESP_OK) return false;
        esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, on_wifi, NULL);
        esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, on_wifi, NULL);
        esp_wifi_set_mode(WIFI_MODE_STA);
        s_wifi_inited = true;
    }
    wifi_config_t cfg = {0};
    memcpy(cfg.sta.ssid, g_cfg.wifi_ssid, strnlen(g_cfg.wifi_ssid, sizeof(cfg.sta.ssid)));
    memcpy(cfg.sta.password, g_cfg.wifi_pass, strnlen(g_cfg.wifi_pass, sizeof(cfg.sta.password)));
    esp_wifi_set_config(WIFI_IF_STA, &cfg);
    if (esp_wifi_start() != ESP_OK) return false;
    esp_wifi_connect();
    EventBits_t b = xEventGroupWaitBits(s_evt, WIFI_CONNECTED, pdFALSE, pdTRUE, pdMS_TO_TICKS(15000));
    return b & WIFI_CONNECTED;
}

static void wifi_down(void)
{
    esp_wifi_disconnect();
    esp_wifi_stop();
}

static bool do_sync(void)
{
    ESP_LOGI(TAG, "Wi-Fi NTP 对时开始（SSID=%s）", g_cfg.wifi_ssid);
    bool ok = false;
    if (wifi_up()) {
        esp_sntp_config_t sc = ESP_NETIF_SNTP_DEFAULT_CONFIG_MULTIPLE(2, ESP_SNTP_SERVER_LIST("ntp.aliyun.com", "cn.pool.ntp.org"));
        esp_netif_sntp_init(&sc);
        if (esp_netif_sntp_sync_wait(pdMS_TO_TICKS(15000)) == ESP_OK) {
            time_t now;
            time(&now);
            setenv("TZ", g_cfg.tz, 1);      // CFG TZ，默认 CST-8
            tzset();
            struct tm lt;
            localtime_r(&now, &lt);
            civil_t c = { lt.tm_year + 1900, lt.tm_mon + 1, lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec };
            // Pi 可能刚好上线：此时以 Pi 为准，不再写
            if (!(power_pi_running() && usb_cdc_connected())) {
                clk_set_local(clk_from_civil(&c), TSRC_NTP);
                evlog_add(EV_TIME_SET, 2);
                ok = true;
            }
        }
        esp_netif_sntp_deinit();
    }
    wifi_down();
    ESP_LOGI(TAG, "NTP 对时%s", ok ? "成功" : "失败");
    return ok;
}

static void ntp_task(void *arg)
{
    uint32_t next_ms = now_ms() + 30000;    // 开机先等 30 s，给 Pi 上线留时间
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(5000));
        bool pi_online = power_pi_running() && usb_cdc_connected();
        if (!g_cfg.ntp || pi_online || !g_cfg.wifi_ssid[0]) continue;
        if ((int32_t)(now_ms() - next_ms) < 0) continue;
        next_ms = now_ms() + (do_sync() ? NTP_RESYNC_MS : NTP_RETRY_MS);
    }
}

void ntp_init(void)
{
    s_evt = xEventGroupCreate();
    xTaskCreatePinnedToCore(ntp_task, "ntp", 4096, NULL, 3, NULL, 0);
}
