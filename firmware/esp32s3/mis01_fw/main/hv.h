// 高压管理（F2）。HV_EN 只在本模块里写。
// HV_EN = 高压钮子开 且 需要高压 且 无 PFAIL 且 自检正常；关后再开间隔 ≥ HV_GAP_S。
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "esp_attr.h"

typedef enum { HV_MODE_AUTO = 0, HV_MODE_ON, HV_MODE_OFF } hv_mode_t;

void hv_init(void);
void hv_tick(void);
bool hv_is_on(void);
uint32_t hv_on_ms(void);            // 已连续开了多少毫秒（关时为 0）
hv_mode_t hv_get_mode(void);
void hv_set_mode(hv_mode_t m);      // 协议 HV AUTO|ON|OFF（只是请求，仍受安全条件约束）
void hv_set_fault(const char *why); // 发现高压负载异常：立即关断并锁定，直到 HV OFF→ON/AUTO 或重启

void hv_emergency_off_isr(void);   // PFAIL 中断、panic 用：直接写寄存器（IRAM）
void hv_on_pfail(void);
