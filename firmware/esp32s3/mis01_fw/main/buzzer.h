// 蜂鸣器（F9）：BZ 单线。高 = 咔哒开；低 = 静音；方波 = 报警（不受静音影响）
#pragma once
#include <stdbool.h>

void buzzer_init(void);
void buzzer_tick(void);
void bz_set_click(bool on);          // 存 NVS
void bz_alarm(int count, int hz);    // 响 count 声（150 ms 响 / 150 ms 停）；hz ≤ 0 用 CFG BZ_HZ
