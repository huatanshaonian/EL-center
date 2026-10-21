// 网页服务器：静态页、密码校验、升级与重启入口。数据接口在 web_api.c。
#include <string.h>
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "esp_http_server.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "mbedtls/base64.h"
#include "web.h"
#include "ota.h"
#include "cfg.h"

static const char *TAG = "web";

extern const char index_html_start[] asm("_binary_index_html_start");
extern const char index_html_end[] asm("_binary_index_html_end");

esp_err_t web_send_json(httpd_req_t *req, const char *json)
{
    httpd_resp_set_type(req, "application/json; charset=utf-8");
    httpd_resp_set_hdr(req, "Cache-Control", "no-store");
    return httpd_resp_sendstr(req, json);
}

// 逐字节比较到底，不因前缀不同提前返回
static bool same(const char *a, const char *b)
{
    size_t la = strlen(a), lb = strlen(b);
    unsigned d = (unsigned)(la ^ lb);
    for (size_t i = 0; i < la; i++) d |= (unsigned char)a[i] ^ (unsigned char)b[i % (lb ? lb : 1)];
    return d == 0;
}

bool web_check_auth(httpd_req_t *req)
{
    char pass[33];
    cfg_lock();
    strlcpy(pass, g_cfg.web_pass, sizeof(pass));
    cfg_unlock();
    if (!pass[0]) {
        httpd_resp_set_status(req, "403 Forbidden");
        web_send_json(req, "{\"ok\":false,\"err\":\"readonly\"}");
        return false;
    }
    char hdr[160];
    if (httpd_req_get_hdr_value_str(req, "Authorization", hdr, sizeof(hdr)) == ESP_OK && !strncmp(hdr, "Basic ", 6)) {
        unsigned char dec[120];
        size_t n = 0;
        if (mbedtls_base64_decode(dec, sizeof(dec) - 1, &n, (const unsigned char *)hdr + 6, strlen(hdr + 6)) == 0) {
            dec[n] = 0;
            char *colon = strchr((char *)dec, ':');
            if (colon && same(colon + 1, pass)) return true;
        }
    }
    httpd_resp_set_status(req, "401 Unauthorized");     // 不带 WWW-Authenticate，免得浏览器弹框；页面自己处理
    web_send_json(req, "{\"ok\":false,\"err\":\"auth\"}");
    return false;
}

static esp_err_t h_index(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html; charset=utf-8");
    return httpd_resp_send(req, index_html_start, index_html_end - index_html_start);
}

static esp_err_t h_auth(httpd_req_t *req)
{
    if (!web_check_auth(req)) return ESP_OK;
    return web_send_json(req, "{\"ok\":true}");
}

static void restart_cb(void *arg) { esp_restart(); }

static esp_err_t h_reboot(httpd_req_t *req)
{
    if (!web_check_auth(req)) return ESP_OK;
    ESP_LOGW(TAG, "网页请求重启");
    web_send_json(req, "{\"ok\":true}");
    static esp_timer_handle_t t;
    if (!t) {
        esp_timer_create_args_t a = { .callback = restart_cb, .name = "web_rst" };
        esp_timer_create(&a, &t);
    }
    esp_timer_start_once(t, 500000);
    return ESP_OK;
}

static esp_err_t h_ota(httpd_req_t *req)
{
    if (!web_check_auth(req)) return ESP_OK;
    return ota_http_upload(req);
}

void web_init(void)
{
    httpd_config_t c = HTTPD_DEFAULT_CONFIG();
    c.stack_size = 8192;
    c.max_uri_handlers = 12;
    c.core_id = 0;
    c.lru_purge_enable = true;
    c.recv_wait_timeout = 10;
    httpd_handle_t srv = NULL;
    if (httpd_start(&srv, &c) != ESP_OK) { ESP_LOGE(TAG, "网页服务启动失败"); return; }
    const httpd_uri_t uris[] = {
        { .uri = "/",            .method = HTTP_GET,  .handler = h_index },
        { .uri = "/api/auth",    .method = HTTP_GET,  .handler = h_auth },
        { .uri = "/api/reboot",  .method = HTTP_POST, .handler = h_reboot },
        { .uri = "/api/ota",     .method = HTTP_POST, .handler = h_ota },
    };
    for (size_t i = 0; i < sizeof(uris) / sizeof(uris[0]); i++) httpd_register_uri_handler(srv, &uris[i]);
    web_register_api(srv);
    ESP_LOGI(TAG, "网页服务已启动（端口 80）");
}
