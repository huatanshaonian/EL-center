// IV-18 七段字形表：bit0..6 = a..g，bit7 = dp
#pragma once
#include <stdint.h>

#define SEG_DP 0x80

// 返回字形；不能显示的字符返回 -1
int vfd_glyph(char c);

// 文本 → 8 位字形（左对齐）；"." 并到前一位的 dp。返回 0 = OK，-1 = 有不能显示的字符或超过 8 位
int vfd_text_to_segs(const char *t, uint8_t out[8]);
// 文本占几位（"." 不占位）
int vfd_visual_len(const char *t);
