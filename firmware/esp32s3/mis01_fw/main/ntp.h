// Wi-Fi NTP 对时（F15 ①）：CFG NTP=1 且 Wi-Fi 已连时每 24 h 一次，成功后写回 RTC
#pragma once
#include <stdbool.h>

void ntp_init(void);
int  ntp_last_ok_age_s(void);        // 上次成功距今秒数，-1 = 本次开机还没成功过
bool ntp_systime_from_clk(void);     // 按 RTC 本地时间 + CFG TZ 设系统 UTC 时间（HTTPS 证书校验用）
