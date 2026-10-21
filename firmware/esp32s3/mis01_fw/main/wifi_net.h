// Wi-Fi 常连与 mDNS（规格 F15）。配了 WIFI_SSID 就连，断线按 5 s 起翻倍到 5 min 重连；改了账号 2 s 后按新账号重连。
#pragma once
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    char ssid[33];
    int  rssi;
    bool open;          // 无密码
} net_ap_t;

void        net_init(void);
bool        net_up(void);               // 已拿到 IP
const char *net_ip(void);               // "-" = 无
int         net_rssi(void);             // 未连上回 0
int         net_last_reason(void);      // 最近一次断开/失败的原因码（wifi_err_reason_t），0 = 无
int         net_scan(net_ap_t *out, int max);   // 阻塞约 2–3 s；返回个数，<0 失败
