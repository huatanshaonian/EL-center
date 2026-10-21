#include <string.h>
#include "esp_log.h"
#include "tinyusb.h"
#include "tinyusb_default_config.h"
#include "tinyusb_cdc_acm.h"
#include "usb_cdc.h"
#include "dispmode.h"

static const char *TAG = "cdc";

static QueueHandle_t s_rxq;
static volatile bool s_dtr, s_connect_evt;
static cdc_line_t s_cur;
static int s_len;

// 在 TinyUSB 任务里运行：拼行，投队列
static void on_rx(int itf, cdcacm_event_t *ev)
{
    uint8_t buf[64];
    size_t n = 0;
    while (tinyusb_cdcacm_read(itf, buf, sizeof(buf), &n) == ESP_OK && n > 0) {
        for (size_t i = 0; i < n; i++) {
            char c = (char)buf[i];
            if (c == '\r') continue;          // 兼容 \r\n
            if (c == '\n') {
                s_cur.text[s_len] = 0;
                if (s_len > 0 || s_cur.too_long) xQueueSend(s_rxq, &s_cur, 0);
                s_len = 0;
                s_cur.too_long = false;
                continue;
            }
            if (s_len < CDC_LINE_MAX) s_cur.text[s_len++] = c;
            else s_cur.too_long = true;
        }
    }
}

static void on_line_state(int itf, cdcacm_event_t *ev)
{
    bool dtr = ev->line_state_changed_data.dtr;
    if (dtr && !s_dtr) s_connect_evt = true;
    if (!dtr && s_dtr) dm_all_auto("CDC DTR 掉");
    s_dtr = dtr;
    ESP_LOGI(TAG, "DTR=%d", dtr);
}

void usb_cdc_init(QueueHandle_t rx_lines)
{
    s_rxq = rx_lines;
    tinyusb_config_t tc = TINYUSB_DEFAULT_CONFIG();
    ESP_ERROR_CHECK(tinyusb_driver_install(&tc));
    tinyusb_config_cdcacm_t ac = {
        .cdc_port = TINYUSB_CDC_ACM_0,
        .callback_rx = on_rx,
        .callback_line_state_changed = on_line_state,
    };
    ESP_ERROR_CHECK(tinyusb_cdcacm_init(&ac));
}

bool usb_cdc_connected(void) { return s_dtr; }

bool usb_cdc_take_connect_event(void)
{
    if (!s_connect_evt) return false;
    s_connect_evt = false;
    return true;
}

void usb_cdc_write(const char *s, int len)
{
    if (!s_dtr) return;
    int off = 0;
    for (int tries = 0; off < len && tries < 5; tries++) {
        off += tinyusb_cdcacm_write_queue(TINYUSB_CDC_ACM_0, (const uint8_t *)s + off, len - off);
        tinyusb_cdcacm_write_flush(TINYUSB_CDC_ACM_0, pdMS_TO_TICKS(20));
    }
}
