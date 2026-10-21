// 公用小工具
#pragma once
#include <stdint.h>
#include <stdbool.h>
#include "esp_timer.h"

#define FW_VERSION   "0.1.0"
#define FW_SPEC      "0.9.2"

static inline uint32_t now_ms(void) { return (uint32_t)(esp_timer_get_time() / 1000); }

// 无符号毫秒差，回绕安全
static inline uint32_t ms_since(uint32_t t) { return now_ms() - t; }

static inline int clampi(int v, int lo, int hi) { return v < lo ? lo : (v > hi ? hi : v); }
