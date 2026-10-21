// 辉光钟（F4）：6×IN-14，4 片 74AHCT595（字节 0 = 6 个右小数点，字节 1–3 = 时/分/秒 BCD）
#pragma once
#include <stdint.h>
#include <stdbool.h>

void nixie_init(void);
void nixie_tick(void);
int  nixie_show(const char *txt, int t_s);   // 0 = OK，-1 = 字符非法或超过 6 位
void nixie_off(int t_s);
void nixie_auto(void);
void nixie_cycle_now(void);
bool nixie_needs_hv(void);
void nixie_last_frame(uint8_t f[4]);   // 诊断用：最近发给 595 的 4 字节    // 每日修复进行中：无人/夜间也要高压（F2）
