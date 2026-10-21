// MIS-01 仪器层 ESP32-S3 固件入口：初始化顺序、控制任务主循环
//
// 任务（核 / 优先级）：
//   vfd_scan  1 / 23   IV-18 扫描（GPTimer 中断唤醒，每位一次）
//   ctrl      0 / 10   10 ms 一轮：电源、高压、显示内容、盖革、蜂鸣器；SQW 换秒与 PFAIL 立即唤醒
//   proto     0 / 7    协议命令执行；proto_tx 0 / 6 发送
//   sensors   0 / 5    BH1750、LD2410 串口
//   net       0 / 4    Wi-Fi 常连、重连、mDNS（F15）
//   ntp       0 / 3    Wi-Fi NTP，NTP=1 时每 24 h
//   wx        0 / 2    天气（Open-Meteo）
//   httpd     0 / 5    网页（mis01.local）
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs_flash.h"
#include "driver/gpio.h"
#include "esp_task_wdt.h"
#include "esp_log.h"
#include "cfg.h"
#include "evlog.h"
#include "spibus.h"
#include "i2cbus.h"
#include "rtc.h"
#include "power.h"
#include "hv.h"
#include "vfd.h"
#include "nixie.h"
#include "eye.h"
#include "meter.h"
#include "geiger.h"
#include "buzzer.h"
#include "sensors.h"
#include "dispmode.h"
#include "proto.h"
#include "ntp.h"
#include "wifi_net.h"
#include "web.h"
#include "weather.h"
#include "ota.h"
#include "safety.h"
#include "anim.h"

static const char *TAG = "main";

#define BIT_START  (1u << 0)
#define BIT_SQW    (1u << 1)
#define BIT_PFAIL  (1u << 2)

static TaskHandle_t s_ctrl;

static void ctrl_task(void *arg)
{
    uint32_t bits = 0;
    while (!(bits & BIT_START)) xTaskNotifyWait(0, BIT_START, &bits, portMAX_DELAY);
    esp_task_wdt_add(NULL);
    ESP_LOGI(TAG, "控制循环开始");
    for (;;) {
        bits = 0;
        xTaskNotifyWait(0, UINT32_MAX, &bits, pdMS_TO_TICKS(10));
        esp_task_wdt_reset();
        if (bits & BIT_PFAIL) power_on_pfail_notify();
        clk_tick();
        power_tick();
        sensors_tick();
        dm_tick();
        nixie_tick();          // 先于 hv_tick：每日修复开始的那一轮就要求高压保持
        hv_tick();
        geiger_tick();
        vfd_tick();
        eye_tick();
        meter_tick();
        buzzer_tick();
        ota_tick();
    }
}

void app_main(void)
{
    // 复位后各安全输出已由硬件上下拉保证（第 3 节），这里尽快把它们接管为同样的状态
    hv_init();

    esp_err_t e = nvs_flash_init();
    if (e == ESP_ERR_NVS_NO_FREE_PAGES || e == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }
    cfg_init();
    evlog_init();
    gpio_install_isr_service(0);

    bool spi_ok = spibus_init();
    bool i2c_ok = i2cbus_init();
    vfd_init();

    xTaskCreatePinnedToCore(ctrl_task, "ctrl", 6144, NULL, 10, &s_ctrl, 0);
    clk_init(s_ctrl, BIT_SQW);
    power_init(s_ctrl, BIT_PFAIL);
    safety_init();

    sensors_init();
    geiger_init();
    buzzer_init();
    eye_init();
    meter_init();
    nixie_init();

    safety_selftest(spi_ok, i2c_ok);
    proto_init();
    ota_init();
    net_init();
    ntp_init();
    weather_init();
    web_init();

    if (g_cfg.boot_anim) anim_boot_request();
    xTaskNotify(s_ctrl, BIT_START, eSetBits);
}
