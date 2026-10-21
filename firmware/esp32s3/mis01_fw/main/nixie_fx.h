// 辉光钟效果（F4）：滚动（开机、换分）与每日防中毒修复
#pragma once
#include <stdint.h>
#include <stdbool.h>

// 滚动：6 位一起滚，管 i（0..5）在 first_stop_ms + i × step_ms 时停到目标值
void nixfx_roll_start(int first_stop_ms, int step_ms);
bool nixfx_roll_active(void);
void nixfx_roll_apply(uint8_t d[6]);          // 还没停的位换成滚动数字

// 每日修复：每天进入夜间时段时开始，持续 CFG NIX_ACP_MIN 分钟
void nixfx_acp_tick(void);
bool nixfx_acp_active(void);
void nixfx_acp_apply(uint8_t d[6], uint8_t *dp);
