// 协议收发与拆字段。每条命令恰好回一行；字段用空格分隔，带空格的文本用双引号；关键字不分大小写（执行时比较）。
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <strings.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "esp_task_wdt.h"
#include "proto.h"
#include "usb_cdc.h"
#include "safety.h"
#include "util.h"

static const char *TAG = "proto";

#define TX_LINE_MAX 200
#define TX_QUEUE_N  48

typedef struct { char s[TX_LINE_MAX]; } tx_line_t;

static QueueHandle_t s_rxq, s_txq;

void proto_send(const char *fmt, ...)
{
    if (!s_txq) return;
    tx_line_t l;
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(l.s, sizeof(l.s) - 1, fmt, ap);
    va_end(ap);
    if (n < 0) return;
    if (n > (int)sizeof(l.s) - 2) n = sizeof(l.s) - 2;
    l.s[n] = '\n';
    l.s[n + 1] = 0;
    // 最多等 20 ms（LOG? 一次要发几十行）；Pi 不读时丢行，不卡调用者
    if (xQueueSend(s_txq, &l, pdMS_TO_TICKS(20)) != pdTRUE) ESP_LOGW(TAG, "发送队列满，丢一行");
}

static void tx_task(void *arg)
{
    tx_line_t l;
    for (;;) {
        if (xQueueReceive(s_txq, &l, portMAX_DELAY) == pdTRUE) {
            ESP_LOGD(TAG, "→ %s", l.s);
            usb_cdc_write(l.s, strlen(l.s));
        }
    }
}

// 拆字段：空格分隔，"..." 为一个字段（去掉引号）；T=<秒> 单独取出
// 返回 false = 格式错（引号不配对、字段太多、T= 非法）
static bool tokenize(char *s, proto_cmd_t *c, const char **err)
{
    c->argc = 0;
    c->t_s = 0;
    char *p = s;
    for (;;) {
        while (*p == ' ' || *p == '\t') p++;
        if (!*p) break;
        if (c->argc >= PROTO_MAX_ARGS) { *err = "too many fields"; return false; }
        bool q = false;
        char *start;
        if (*p == '"') {
            q = true;
            start = ++p;
            while (*p && *p != '"') p++;
            if (*p != '"') { *err = "unterminated quote"; return false; }
            *p++ = 0;
        } else {
            start = p;
            while (*p && *p != ' ' && *p != '\t') p++;
            if (*p) *p++ = 0;
        }
        if (!q && c->argc > 0 && strncasecmp(start, "T=", 2) == 0) {
            char *e;
            long t = strtol(start + 2, &e, 10);
            if (*e || t < 1 || t > 86400) { *err = "T out of range"; return false; }
            c->t_s = (int)t;
            continue;
        }
        c->quoted[c->argc] = q;
        c->argv[c->argc++] = start;
    }
    return true;
}

static void proto_task(void *arg)
{
    esp_task_wdt_add(NULL);
    cdc_line_t line;
    for (;;) {
        esp_task_wdt_reset();
        if (usb_cdc_take_connect_event()) {
            vTaskDelay(pdMS_TO_TICKS(50));     // 等 Pi 端打开完成
            proto_send("!BOOT FW=%s RST=%s", FW_VERSION, safety_reset_reason_name());
            safety_report_selftest();
        }
        if (xQueueReceive(s_rxq, &line, pdMS_TO_TICKS(100)) != pdTRUE) continue;
        ESP_LOGD(TAG, "← %s", line.text);
        if (line.too_long) { proto_send("ERR SYNTAX line too long"); continue; }
        proto_cmd_t c;
        const char *err = NULL;
        if (!tokenize(line.text, &c, &err)) { proto_send("ERR SYNTAX %s", err); continue; }
        if (c.argc == 0) { proto_send("ERR SYNTAX empty"); continue; }
        proto_exec(&c);
    }
}

void proto_init(void)
{
    s_rxq = xQueueCreate(8, sizeof(cdc_line_t));
    s_txq = xQueueCreate(TX_QUEUE_N, sizeof(tx_line_t));
    xTaskCreatePinnedToCore(tx_task, "proto_tx", 3072, NULL, 6, NULL, 0);
    xTaskCreatePinnedToCore(proto_task, "proto", 6144, NULL, 7, NULL, 0);
    usb_cdc_init(s_rxq);
}
