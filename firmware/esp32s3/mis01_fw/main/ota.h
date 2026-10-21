// 无线升级（规格 F15 ③）：网页上传 .bin 写入另一个程序区；新固件运行 60 s 正常才确认，否则引导程序退回旧固件。
#pragma once
#include <stdbool.h>
#include "esp_http_server.h"

void        ota_init(void);           // 开机时调：记下本固件是否"待确认"
void        ota_tick(void);           // 控制循环里调：运行满 60 s 确认
bool        ota_pending(void);        // 本固件还没确认
const char *ota_running_label(void);  // "ota_0" / "ota_1"
esp_err_t   ota_http_upload(httpd_req_t *req);   // POST 体就是 .bin；成功后 1 s 重启
