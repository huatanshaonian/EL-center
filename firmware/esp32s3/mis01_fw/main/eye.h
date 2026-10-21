// 6E2 猫眼 ×2（F7）：LEDC 10 kHz 12 位；0..1000 经 11 点校准表换算成占空比
#pragma once
#include <stdint.h>

void eye_init(void);
void eye_tick(void);
void eye_set(int ch, int v, int t_s);        // ch 0 = A，1 = B；v 0..1000
void eye_raw(int ch, int raw, int t_s);      // 直接写占空比 0..4095
void eye_auto(int ch);
void eye_set_cal(int ch, const uint16_t cal[11]);   // 存 NVS
