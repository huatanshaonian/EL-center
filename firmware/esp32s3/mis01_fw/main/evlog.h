// 事件环形缓冲（F14）：存 NVS，64 条，Pi 用 LOG? 读
#pragma once
#include <stdint.h>

typedef enum {
    EV_BOOT = 1,        // 参数 = 复位原因（esp_reset_reason_t）
    EV_WDT_RESET,       // 看门狗复位
    EV_PANIC_RESET,     // 异常复位
    EV_BROWNOUT,        // 欠压复位
    EV_PFAIL,           // 24 V 掉电预警（"异常断电"）
    EV_SENSOR_LOST,     // 参数 = sensor_id_t
    EV_SCAN_FAULT,      // IV-18 扫描心跳丢失，已强制关显示
    EV_HV_FAULT,        // 高压负载异常
    EV_TIME_SET,        // 参数 = 时间来源（1 HOST、2 NTP）
    EV_RTC_INVALID,     // DS3231 掉电标志置位
    EV_SELFTEST_FAIL,   // 参数 = 失败项位图
    EV_OTA,             // 无线升级：参数 1 = 新固件已写入待重启，2 = 新固件运行 60 s 已确认
} ev_code_t;

#define EVLOG_SIZE 64

void evlog_init(void);
void evlog_add(ev_code_t code, int32_t param);   // 只能在任务里调（写 NVS）
int  evlog_count(void);
// 第 i 条（0 = 最早）；返回 0 表示成功。t_local = 本地时间秒（0 = 当时时间无效）
int  evlog_get(int i, uint32_t *t_local, ev_code_t *code, int32_t *param);
void evlog_clear(void);
const char *evlog_name(ev_code_t code);
