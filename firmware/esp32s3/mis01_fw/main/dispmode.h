// 显示件 AUTO/HOST 状态机（规格 6.4，集中在这一处）
// 任一发生时全部退回 AUTO：CDC 的 DTR 掉；PI_RUN 变低；命令带的 T=<秒> 到期而 Pi 没有续发。
#pragma once
#include <stdbool.h>

typedef enum { DM_NIX = 0, DM_VFD, DM_EYE_A, DM_EYE_B, DM_MTR, DM_COUNT } dm_item_t;

void dm_set_host(dm_item_t it, int timeout_s);   // timeout_s ≤ 0：不超时
void dm_set_auto(dm_item_t it);
void dm_all_auto(const char *why);
bool dm_is_host(dm_item_t it);
void dm_tick(void);                              // 处理 T= 到期

// 本地显示（辉光钟高压、IV-18）要不要开：有人 且 不在夜间时段（F2、F5）
bool dm_local_wanted(void);
