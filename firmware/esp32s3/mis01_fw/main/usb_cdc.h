// 原生 USB CDC（TinyUSB），Pi 上为 /dev/ttyACM0（规格 6.1）
#pragma once
#include <stdbool.h>
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

#define CDC_LINE_MAX 128

typedef struct {
    char text[CDC_LINE_MAX + 1];
    bool too_long;
} cdc_line_t;

void usb_cdc_init(QueueHandle_t rx_lines);   // 收到的完整行投到这个队列
bool usb_cdc_connected(void);                // DTR 有效
bool usb_cdc_take_connect_event(void);       // DTR 刚变有效（取一次即清）
void usb_cdc_write(const char *s, int len);  // 不在 TinyUSB 任务里调
