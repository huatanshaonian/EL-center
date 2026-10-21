// 盖革计数（F8）：J305，PCNT 计下降沿 + 1 µs 毛刺滤波 + 50 µs 软件死区；60 s 滑动窗口
#pragma once
#include <stdint.h>
#include <stdbool.h>

void geiger_init(void);
void geiger_tick(void);
int  gm_cpm(void);
uint32_t gm_total(void);
float gm_usv(void);
bool gm_valid(void);       // 高压开且已过 2 s
void gm_reset(void);       // 累计清零
