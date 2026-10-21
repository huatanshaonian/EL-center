// 主机电源管理（F1）、PFAIL（F3）、钮子与 PI_RUN 输入。HOLD、PI_SHDN_REQ 只在本模块里写。
#pragma once
#include <stdbool.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

typedef enum { PWR_OFF = 0, PWR_WAIT, PWR_RUN, PWR_SHUT } pwr_state_t;

void power_init(TaskHandle_t ctrl_task, uint32_t pfail_notify_bit);
void power_tick(void);                 // 控制任务 10 ms 一次
void power_on_pfail_notify(void);      // 控制任务收到 PFAIL 通知后调用（记日志、上报、报警）

pwr_state_t power_state(void);
const char *power_state_name(void);
bool power_sw_host(void);
bool power_sw_hv(void);
bool power_sw_scr(void);
bool power_pfail(void);                // PFAIL_N 当前为低
bool power_pi_running(void);           // PI_RUN 为高（去抖后）
bool power_outputs_blocked(void);      // Pi 发了 SHUTDOWN，关机期间高压与 IV-18 保持关
void power_pi_shutdown_cmd(void);      // 协议 SHUTDOWN
