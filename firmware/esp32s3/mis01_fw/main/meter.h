// 指针表头（F6）：正泰 85C1 0–1 mA，LEDC 约 20 kHz、12 位，经 RC 驱动
#pragma once

void meter_init(void);
void meter_tick(void);
void meter_set(int v, int t_s);      // 0..1000 满偏千分比
void meter_raw(int raw, int t_s);    // 0..4095
void meter_auto(void);               // 本地内容：Pi 不在线时归零（AUTO 即 0）
void meter_set_fs(int fs);           // 满偏占空比，存 NVS
