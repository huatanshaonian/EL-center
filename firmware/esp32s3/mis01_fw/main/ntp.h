// Wi-Fi NTP 对时（F12）：只在 Pi 不在线且 CFG NTP=1、配了 WIFI_SSID 时进行，成功后写回 RTC
#pragma once

void ntp_init(void);
