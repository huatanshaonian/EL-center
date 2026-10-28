// IV-18 显示内容（F5）：AUTO 本地内容、Pi 文本、G1 特殊位、亮度、开关。扫描与电源见 vfd_scan.c
#pragma once
#include <stdbool.h>
#include "esp_attr.h"

void vfd_init(void);
void vfd_tick(void);                       // 控制任务每轮调用
int  vfd_show(const char *txt, int t_s);   // 0 = OK，-1 = 有不能显示的字符或超过 8 位
int  vfd_radio(const char *txt, int t_s); // 电台项（F5、6.8 VFD RADIO）；txt = NULL 去掉；0 = OK，-1 = 字符不合法
void vfd_sym(int bits, int t_s);           // G1 特殊位：bit0 竖线、bit1 负号、bit2 点（接法按 CFG IV18_TYPE）
void vfd_auto(void);
void vfd_off(void);                        // 按关显示顺序关；vfd_auto / vfd_show 重新打开
void vfd_set_brt(int v);                   // -1 = AUTO，0..1000；存 NVS
bool vfd_is_on(void);

void vfd_emergency_off_isr(void);    // PFAIL 中断、panic 用（IRAM）
void vfd_on_pfail(void);
