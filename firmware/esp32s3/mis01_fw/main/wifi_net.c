// Wi-Fi 常连（STA）、自动重连、mDNS（mis01.local）。
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_log.h"
#include "mdns.h"
#include "wifi_net.h"
#include "cfg.h"
#include "util.h"

static const char *TAG = "net";

#define BACKOFF_MIN_MS   5000u
#define BACKOFF_MAX_MS   300000u
#define APPLY_QUIET_MS   2000u     // 账号改完 2 s 不再变才生效（SSID、密码通常连着改）

static volatile bool s_up;
static volatile int s_last_reason;
static char s_ip[16] = "-";
static bool s_started, s_configured, s_mdns;
static SemaphoreHandle_t s_wifi_mtx;     // 扫描与连接不同时做

static void on_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        wifi_event_sta_disconnected_t *d = data;
        s_last_reason = d->reason;
        // 常见原因：201 找不到这个网络（名字不对/只有 5 GHz/信号太弱），15/204 密码不对，2/4 认证超时
        ESP_LOGW(TAG, "Wi-Fi %s（原因 %d）", s_up ? "断开" : "连接失败", d->reason);
        s_up = false;
        strcpy(s_ip, "-");
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *e = data;
        snprintf(s_ip, sizeof(s_ip), IPSTR, IP2STR(&e->ip_info.ip));
        s_up = true;
        ESP_LOGI(TAG, "Wi-Fi 已连接，IP %s（http://mis01.local/）", s_ip);
    }
}

static void mdns_start(void)
{
    if (s_mdns) return;
    if (mdns_init() != ESP_OK) return;
    mdns_hostname_set("mis01");
    mdns_instance_name_set("MIS-01");
    mdns_service_add("MIS-01", "_http", "_tcp", 80, NULL, 0);
    s_mdns = true;
}

// 按当前配置（重新）连接。返回是否配了 SSID
static bool apply_config(void)
{
    wifi_config_t wc = {0};
    cfg_lock();
    size_t ls = strnlen(g_cfg.wifi_ssid, sizeof(wc.sta.ssid));
    memcpy(wc.sta.ssid, g_cfg.wifi_ssid, ls);
    memcpy(wc.sta.password, g_cfg.wifi_pass, strnlen(g_cfg.wifi_pass, sizeof(wc.sta.password)));
    cfg_unlock();
    wc.sta.threshold.authmode = WIFI_AUTH_OPEN;     // 开放网络也能连；有密码时驱动自动用 WPA2/WPA3
    wc.sta.pmf_cfg.capable = true;
    if (s_up || s_started) esp_wifi_disconnect();
    s_up = false;
    if (ls == 0) {
        if (s_started) { esp_wifi_stop(); s_started = false; }
        ESP_LOGI(TAG, "未配置 Wi-Fi");
        return false;
    }
    esp_wifi_set_config(WIFI_IF_STA, &wc);
    if (!s_started) { esp_wifi_start(); s_started = true; }
    ESP_LOGI(TAG, "连接 Wi-Fi \"%s\"", (char *)wc.sta.ssid);
    return true;
}

static void net_task(void *arg)
{
    uint32_t gen_applied = cfg_wifi_gen() - 1, gen_seen = gen_applied, gen_ms = 0;
    uint32_t next_try = 0, backoff = BACKOFF_MIN_MS;
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(500));
        uint32_t now = now_ms();
        uint32_t g = cfg_wifi_gen();
        if (g != gen_seen) { gen_seen = g; gen_ms = now; }
        xSemaphoreTake(s_wifi_mtx, portMAX_DELAY);
        if (g != gen_applied && now - gen_ms >= APPLY_QUIET_MS) {
            gen_applied = g;
            s_configured = apply_config();
            backoff = BACKOFF_MIN_MS;
            next_try = now;
        }
        if (s_up) {
            backoff = BACKOFF_MIN_MS;
            mdns_start();
        } else if (s_configured && (int32_t)(now - next_try) >= 0) {
            esp_wifi_connect();
            next_try = now + backoff;
            backoff = backoff * 2 > BACKOFF_MAX_MS ? BACKOFF_MAX_MS : backoff * 2;
        }
        xSemaphoreGive(s_wifi_mtx);
    }
}

void net_init(void)
{
    s_wifi_mtx = xSemaphoreCreateMutex();
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_t *n = esp_netif_create_default_wifi_sta();
    esp_netif_set_hostname(n, "mis01");
    wifi_init_config_t wc = WIFI_INIT_CONFIG_DEFAULT();
    if (esp_wifi_init(&wc) != ESP_OK) { ESP_LOGE(TAG, "Wi-Fi 初始化失败"); return; }
    esp_wifi_set_storage(WIFI_STORAGE_RAM);     // 账号以 CFG 为准，不让驱动另存一份
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, on_event, NULL);
    esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, on_event, NULL);
    xTaskCreatePinnedToCore(net_task, "net", 4096, NULL, 4, NULL, 0);
}

bool net_up(void) { return s_up; }
int net_last_reason(void) { return s_last_reason; }
const char *net_ip(void) { return s_ip; }

int net_rssi(void)
{
    wifi_ap_record_t ap;
    if (!s_up || esp_wifi_sta_get_ap_info(&ap) != ESP_OK) return 0;
    return ap.rssi;
}

int net_scan(net_ap_t *out, int max)
{
    xSemaphoreTake(s_wifi_mtx, portMAX_DELAY);
    bool temp_start = !s_started;
    if (temp_start) {
        wifi_config_t empty = {0};
        esp_wifi_set_config(WIFI_IF_STA, &empty);
        esp_wifi_start();
    }
    int n = -1;
    if (esp_wifi_scan_start(NULL, true) == ESP_OK) {
        uint16_t cnt = 0;
        esp_wifi_scan_get_ap_num(&cnt);
        wifi_ap_record_t *rec = calloc(cnt ? cnt : 1, sizeof(*rec));
        if (rec) {
            esp_wifi_scan_get_ap_records(&cnt, rec);
            n = 0;
            for (int i = 0; i < cnt && n < max; i++) {
                if (!rec[i].ssid[0]) continue;
                bool dup = false;
                for (int j = 0; j < n; j++) if (!strcmp(out[j].ssid, (char *)rec[i].ssid)) dup = true;
                if (dup) continue;
                memcpy(out[n].ssid, rec[i].ssid, 33);
                out[n].ssid[32] = 0;
                out[n].rssi = rec[i].rssi;
                out[n].open = rec[i].authmode == WIFI_AUTH_OPEN;
                n++;
            }
            free(rec);
        } else {
            esp_wifi_clear_ap_list();
        }
    }
    if (temp_start) esp_wifi_stop();
    xSemaphoreGive(s_wifi_mtx);
    return n;
}
