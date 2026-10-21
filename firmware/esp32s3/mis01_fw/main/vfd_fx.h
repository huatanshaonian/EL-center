// IV-18 效果（F5）：开机跑马灯、换内容擦除动画
#pragma once
#include <stdint.h>
#include <stdbool.h>

void vfdfx_boot_start(void);
bool vfdfx_boot_active(void);
void vfdfx_boot_apply(uint8_t segs[8]);         // 开机动画期间直接给出整屏字形

void vfdfx_wipe_start(const uint8_t old_segs[8]);
void vfdfx_wipe_apply(uint8_t segs[8]);         // segs 进来是新内容，出去是擦除过程中的画面
