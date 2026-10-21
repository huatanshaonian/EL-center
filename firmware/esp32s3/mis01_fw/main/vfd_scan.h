// IV-18 扫描与电源时序（F5、S1、S6）。BLANK、IV18_PWR_EN、IV18_FIL 只在这里写。
#pragma once
#include <stdint.h>
#include "esp_attr.h"
#include <stdbool.h>

#define VFD_GRIDS 9

void vfd_scan_init(void);
void vfd_scan_set_frames(const uint32_t f[VFD_GRIDS]);   // 每位 20 位 MAX6921 数据
void vfd_scan_set_brightness(int permille);              // 0..1000
void vfd_scan_power(bool want);     // 每 10 ms 调：按开/关显示顺序推进
void vfd_scan_check(void);          // 每 10 ms 调：扫描心跳检查
bool vfd_scan_is_on(void);          // 正在扫描（已过预热）
bool vfd_scan_fault(void);
void vfd_scan_clear_fault(void);
// 诊断用：片计数、装好数据的片数、放开 BLANK 的片数；当前第 i 位帧
void vfd_scan_stats(uint32_t *slots, uint32_t *loaded, uint32_t *lit);
uint32_t vfd_scan_frame(int i);

void vfd_scan_emergency_off_isr(void);   // IRAM
