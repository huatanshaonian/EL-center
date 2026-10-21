// 传感器：BH1750 环境光（F10）、LD2410B 人体感应（F11）
#pragma once
#include <stdbool.h>

#define SENSOR_ID_BH1750 1
#define SENSOR_ID_DS3231 2
#define SENSOR_ID_LD2410 3

void sensors_init(void);       // 起传感器任务（I²C 轮询、LD2410 串口解析）
void sensors_tick(void);       // 控制任务：有人/无人去抖与上报
int  sens_lux(void);           // -1 = 无数据
bool sens_present(void);       // 已按 NOBODY_S 去抖
int  sens_dist_cm(void);       // -1 = 无目标或无串口数据
bool sens_bh1750_ok(void);
bool sens_ld2410_uart_ok(void);
