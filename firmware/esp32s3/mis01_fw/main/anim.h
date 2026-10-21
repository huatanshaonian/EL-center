// 开机动画协调（F4–F7 开机动画，CFG BOOT_ANIM）：只记"哪个显示件还欠一段开机动画"，
// 各显示件在自己能显示时（辉光钟等高压开、6E2 等灯丝预热、IV-18 等开始扫描）取走并播放。
#pragma once
#include <stdbool.h>

typedef enum { ANIM_NIX = 0, ANIM_VFD, ANIM_EYE, ANIM_MTR, ANIM_COUNT } anim_item_t;

void anim_boot_request(void);          // 开机时（CFG BOOT_ANIM=1）与 ANIM BOOT 命令调用
bool anim_take(anim_item_t it);        // 欠着就取走并返回 true
