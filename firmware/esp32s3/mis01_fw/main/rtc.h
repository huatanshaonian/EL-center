// 时间（F12）：DS3231 + SQW 秒脉冲。内部只存本地时间，单位为"自 2000-01-01 00:00:00 起的秒"
#pragma once
#include <stdint.h>
#include <stdbool.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

typedef enum { TSRC_RTC = 0, TSRC_HOST, TSRC_NTP } time_src_t;

typedef struct { int year, mon, day, hour, min, sec; } civil_t;

void     clk_init(TaskHandle_t sec_notify_task, uint32_t notify_bit);
void     clk_tick(void);                 // 控制任务里每轮调用
uint32_t clk_now(void);
bool     clk_time_valid(void);
bool     clk_chip_ok(void);              // DS3231 在线
bool     clk_sqw_ok(void);               // 最近 1.5 s 内收到过秒脉冲
time_src_t clk_src(void);
uint32_t clk_sec_seq(void);              // 每换一秒 +1
uint32_t clk_ms_into_second(void);       // 距本秒开始的毫秒数
bool     clk_set_local(uint32_t secs, time_src_t src);   // 写 DS3231 并设为有效

void     clk_to_civil(uint32_t secs, civil_t *c);
uint32_t clk_from_civil(const civil_t *c);
void     clk_format(uint32_t secs, char *out);           // "YYYY-MM-DDTHH:MM:SS"，out ≥ 20 字节
bool     clk_parse(const char *s, uint32_t *secs);
const char *clk_src_name(time_src_t s);

#define CLK_TEMP_NONE (-10000)
int      clk_temp_x10(void);             // DS3231 芯片温度 ×10（°C）；CLK_TEMP_NONE = 无数据
