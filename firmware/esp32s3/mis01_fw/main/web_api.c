// 网页数据接口：GET /api/status、GET/POST /api/cfg、GET /api/scan。
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "esp_http_server.h"
#include "esp_timer.h"
#include "esp_app_desc.h"
#include "esp_log.h"
#include "cJSON.h"
#include "web.h"
#include "wifi_net.h"
#include "weather.h"
#include "ntp.h"
#include "ota.h"
#include "power.h"
#include "hv.h"
#include "geiger.h"
#include "sensors.h"
#include "usb_cdc.h"
#include "rtc.h"
#include "cfg.h"
#include "util.h"

static const char *TAG = "web";

#define BODY_MAX 2048

static esp_err_t send_cjson(httpd_req_t *req, cJSON *o)
{
    char *s = cJSON_PrintUnformatted(o);
    cJSON_Delete(o);
    if (!s) return httpd_resp_send_500(req);
    esp_err_t e = web_send_json(req, s);
    free(s);
    return e;
}

static esp_err_t h_status(httpd_req_t *req)
{
    cJSON *o = cJSON_CreateObject();
    const esp_app_desc_t *d = esp_app_get_description();
    cJSON_AddStringToObject(o, "fw", FW_VERSION);
    cJSON_AddStringToObject(o, "spec", FW_SPEC);
    cJSON_AddStringToObject(o, "build", d->date);
    char t[20];
    clk_format(clk_now(), t);
    cJSON_AddStringToObject(o, "time", t);
    cJSON_AddBoolToObject(o, "time_valid", clk_time_valid());
    cJSON_AddStringToObject(o, "time_src", clk_src_name(clk_src()));
    cJSON_AddNumberToObject(o, "uptime", (double)(esp_timer_get_time() / 1000000));
    cJSON_AddStringToObject(o, "pwr", power_state_name());
    cJSON_AddBoolToObject(o, "hostsw", power_sw_host());
    cJSON_AddBoolToObject(o, "hvsw", power_sw_hv());
    cJSON_AddBoolToObject(o, "scrsw", power_sw_scr());
    cJSON_AddBoolToObject(o, "hv", hv_is_on());
    cJSON_AddBoolToObject(o, "pfail", power_pfail());
    cJSON_AddBoolToObject(o, "pi_online", power_pi_running() && usb_cdc_connected());
    cJSON_AddBoolToObject(o, "pres", sens_present());
    cJSON_AddNumberToObject(o, "lux", sens_lux());
    cJSON_AddBoolToObject(o, "gm_valid", gm_valid());
    cJSON_AddNumberToObject(o, "cpm", gm_cpm());
    cJSON_AddNumberToObject(o, "usv", gm_usv());
    int tc = clk_temp_x10();
    if (tc != CLK_TEMP_NONE) cJSON_AddNumberToObject(o, "temp", tc / 10.0);
    else cJSON_AddNullToObject(o, "temp");

    cJSON *w = cJSON_AddObjectToObject(o, "wifi");
    cJSON_AddBoolToObject(w, "up", net_up());
    cJSON_AddStringToObject(w, "ip", net_ip());
    cJSON_AddNumberToObject(w, "rssi", net_rssi());
    cfg_lock();
    cJSON_AddStringToObject(w, "ssid", g_cfg.wifi_ssid);
    cJSON_AddStringToObject(o, "city", g_cfg.wx_city);
    cJSON_AddStringToObject(o, "tz", g_cfg.tz);
    bool web_rw = g_cfg.web_pass[0] != 0;
    bool ntp_on = g_cfg.ntp;
    cfg_unlock();
    cJSON_AddBoolToObject(o, "web_rw", web_rw);

    cJSON *x = cJSON_AddObjectToObject(o, "wx");
    int wt, rh, code, age;
    bool wv = weather_get(&wt, &rh, &code, &age);
    cJSON_AddBoolToObject(x, "valid", wv);
    if (age >= 0) {
        cJSON_AddNumberToObject(x, "t", wt / 10.0);
        cJSON_AddNumberToObject(x, "rh", rh);
        cJSON_AddNumberToObject(x, "code", code);
        cJSON_AddNumberToObject(x, "age", age);
    }
    cJSON *n = cJSON_AddObjectToObject(o, "ntp");
    cJSON_AddBoolToObject(n, "on", ntp_on);
    cJSON_AddNumberToObject(n, "age", ntp_last_ok_age_s());
    cJSON *u = cJSON_AddObjectToObject(o, "ota");
    cJSON_AddStringToObject(u, "part", ota_running_label());
    cJSON_AddBoolToObject(u, "pending", ota_pending());
    return send_cjson(req, o);
}

// 全部 CFG 键当前值（密码类回 "***" 或 ""）
static esp_err_t h_cfg_get(httpd_req_t *req)
{
    cJSON *o = cJSON_CreateObject();
    char kv[128];
    for (int i = 0; i < cfg_key_count(); i++) {
        if (cfg_get(cfg_key_name(i), kv, sizeof(kv)) != CFG_OK) continue;
        char *eq = strchr(kv, '=');
        cJSON_AddStringToObject(o, cfg_key_name(i), eq ? eq + 1 : "");
    }
    return send_cjson(req, o);
}

// 改设置：JSON 对象 {"键":"值",...}；密码类值为 "***" 表示不改。全部成功才 CFG SAVE。
static esp_err_t h_cfg_post(httpd_req_t *req)
{
    if (!web_check_auth(req)) return ESP_OK;
    if (req->content_len <= 0 || req->content_len >= BODY_MAX) {
        httpd_resp_set_status(req, "400 Bad Request");
        return web_send_json(req, "{\"ok\":false,\"err\":\"body size\"}");
    }
    char *body = malloc(req->content_len + 1);
    if (!body) return httpd_resp_send_500(req);
    int got = 0;
    while (got < req->content_len) {
        int r = httpd_req_recv(req, body + got, req->content_len - got);
        if (r == HTTPD_SOCK_ERR_TIMEOUT) continue;
        if (r <= 0) { free(body); return ESP_FAIL; }
        got += r;
    }
    body[got] = 0;
    cJSON *in = cJSON_Parse(body);
    free(body);
    if (!cJSON_IsObject(in)) {
        cJSON_Delete(in);
        httpd_resp_set_status(req, "400 Bad Request");
        return web_send_json(req, "{\"ok\":false,\"err\":\"json\"}");
    }
    cJSON *res = cJSON_CreateObject();
    cJSON *bad = cJSON_AddArrayToObject(res, "bad");
    int changed = 0;
    cfg_lock();
    for (cJSON *it = in->child; it; it = it->next) {
        char val[96];
        if (cJSON_IsString(it)) strlcpy(val, it->valuestring, sizeof(val));
        else if (cJSON_IsBool(it)) strlcpy(val, cJSON_IsTrue(it) ? "1" : "0", sizeof(val));
        else if (cJSON_IsNumber(it)) snprintf(val, sizeof(val), "%g", it->valuedouble);
        else { cJSON_AddItemToArray(bad, cJSON_CreateString(it->string)); continue; }
        if (!strcmp(val, "***")) continue;          // 密码框没动
        if (cfg_set(it->string, val) == CFG_OK) changed++;
        else cJSON_AddItemToArray(bad, cJSON_CreateString(it->string));
    }
    bool saved = changed > 0 && cfg_save();
    cfg_unlock();
    cJSON_Delete(in);
    ESP_LOGI(TAG, "网页改设置：%d 项%s，%d 项无效", changed, saved ? "已保存" : "", cJSON_GetArraySize(bad));
    cJSON_AddBoolToObject(res, "ok", cJSON_GetArraySize(bad) == 0);
    cJSON_AddNumberToObject(res, "changed", changed);
    return send_cjson(req, res);
}

static esp_err_t h_scan(httpd_req_t *req)
{
    if (!web_check_auth(req)) return ESP_OK;
    net_ap_t *ap = calloc(24, sizeof(net_ap_t));
    if (!ap) return httpd_resp_send_500(req);
    int n = net_scan(ap, 24);
    cJSON *a = cJSON_CreateArray();
    for (int i = 0; i < n; i++) {
        cJSON *e = cJSON_CreateObject();
        cJSON_AddStringToObject(e, "ssid", ap[i].ssid);
        cJSON_AddNumberToObject(e, "rssi", ap[i].rssi);
        cJSON_AddBoolToObject(e, "open", ap[i].open);
        cJSON_AddItemToArray(a, e);
    }
    free(ap);
    return send_cjson(req, a);
}

void web_register_api(httpd_handle_t srv)
{
    const httpd_uri_t uris[] = {
        { .uri = "/api/status", .method = HTTP_GET,  .handler = h_status },
        { .uri = "/api/cfg",    .method = HTTP_GET,  .handler = h_cfg_get },
        { .uri = "/api/cfg",    .method = HTTP_POST, .handler = h_cfg_post },
        { .uri = "/api/scan",   .method = HTTP_GET,  .handler = h_scan },
    };
    for (size_t i = 0; i < sizeof(uris) / sizeof(uris[0]); i++) httpd_register_uri_handler(srv, &uris[i]);
}
