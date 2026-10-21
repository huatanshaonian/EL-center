// 网页（规格 F15 ②）：http://mis01.local/ 状态、设置、扫描 Wi-Fi、固件升级、重启。
// 看状态不用密码；其余要 HTTP Basic 密码 = CFG WEB_PASS（空 = 只读）。
#pragma once
#include "esp_http_server.h"

void web_init(void);

// web.c 内部给 web_api.c 用
bool      web_check_auth(httpd_req_t *req);     // 不通过时已回 401/403
esp_err_t web_send_json(httpd_req_t *req, const char *json);
void      web_register_api(httpd_handle_t srv); // web_api.c
