// Wi-Fi NTP 对时（规格 F15 ①）：CFG NTP=1 且 Wi-Fi 已连时，每 24 h 对一次（失败 10 min 后重试），不论 Pi 在不在线。
// NTP 给 UTC，按 CFG TZ 换成本地时间写 RTC。另外把系统时间（UTC）跟 RTC 对齐，HTTPS 校验证书要用。
#include <string.h>
#include <time.h>
#include <sys/time.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_netif_sntp.h"
#include "esp_log.h"
#include "ntp.h"
#include "wifi_net.h"
#include "rtc.h"
#include "evlog.h"
#include "cfg.h"
#include "util.h"

static const char *TAG = "ntp";

#define NTP_RESYNC_MS   (24u * 3600u * 1000u)
#define NTP_RETRY_MS    (10u * 60u * 1000u)

static uint32_t s_last_ok_ms;
static bool s_ever_ok;

static void apply_tz(void)
{
    char tz[32];
    cfg_lock();
    strlcpy(tz, g_cfg.tz, sizeof(tz));
    cfg_unlock();
    setenv("TZ", tz, 1);
    tzset();
}

bool ntp_systime_from_clk(void)
{
    if (!clk_time_valid()) return false;
    civil_t c;
    clk_to_civil(clk_now(), &c);
    struct tm t = { .tm_year = c.year - 1900, .tm_mon = c.mon - 1, .tm_mday = c.day,
                    .tm_hour = c.hour, .tm_min = c.min, .tm_sec = c.sec, .tm_isdst = -1 };
    apply_tz();
    time_t utc = mktime(&t);
    if (utc < 0) return false;
    struct timeval tv = { .tv_sec = utc };
    settimeofday(&tv, NULL);
    return true;
}

static bool do_sync(void)
{
    ESP_LOGI(TAG, "Wi-Fi NTP 对时开始");
    bool ok = false;
    esp_sntp_config_t sc = ESP_NETIF_SNTP_DEFAULT_CONFIG_MULTIPLE(2, ESP_SNTP_SERVER_LIST("ntp.aliyun.com", "cn.pool.ntp.org"));
    esp_netif_sntp_init(&sc);
    if (esp_netif_sntp_sync_wait(pdMS_TO_TICKS(15000)) == ESP_OK) {
        time_t now;
        time(&now);
        apply_tz();
        struct tm lt;
        localtime_r(&now, &lt);
        civil_t c = { lt.tm_year + 1900, lt.tm_mon + 1, lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec };
        clk_set_local(clk_from_civil(&c), TSRC_NTP);
        evlog_add(EV_TIME_SET, 2);
        ok = true;
    }
    esp_netif_sntp_deinit();
    ESP_LOGI(TAG, "NTP 对时%s", ok ? "成功" : "失败");
    return ok;
}

static void ntp_task(void *arg)
{
    uint32_t next_ms = now_ms() + 20000;    // 开机先等 Wi-Fi 连上
    bool was_on = false;
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(5000));
        bool on = g_cfg.ntp;
        if (on && !was_on) next_ms = now_ms();     // 刚打开 NTP：尽快对一次
        was_on = on;
        if (!on || !net_up()) continue;
        if ((int32_t)(now_ms() - next_ms) < 0) continue;
        bool ok = do_sync();
        if (ok) { s_last_ok_ms = now_ms(); s_ever_ok = true; }
        next_ms = now_ms() + (ok ? NTP_RESYNC_MS : NTP_RETRY_MS);
    }
}

void ntp_init(void)
{
    xTaskCreatePinnedToCore(ntp_task, "ntp", 4096, NULL, 3, NULL, 0);
}

int ntp_last_ok_age_s(void)
{
    return s_ever_ok ? (int)((now_ms() - s_last_ok_ms) / 1000u) : -1;
}
