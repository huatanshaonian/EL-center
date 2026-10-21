// 无线升级与回滚确认。
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_ota_ops.h"
#include "esp_app_desc.h"
#include "esp_image_format.h"
#include "esp_timer.h"
#include "esp_system.h"
#include "esp_log.h"
#include "ota.h"
#include "evlog.h"
#include "util.h"

static const char *TAG = "ota";

#define CONFIRM_AFTER_MS  60000u
#define CHUNK             4096

static bool s_pending;

void ota_init(void)
{
    const esp_partition_t *run = esp_ota_get_running_partition();
    esp_ota_img_states_t st;
    if (run && esp_ota_get_state_partition(run, &st) == ESP_OK && st == ESP_OTA_IMG_PENDING_VERIFY) {
        s_pending = true;
        ESP_LOGW(TAG, "新固件待确认：运行 %u s 正常后确认，之前复位将退回旧固件", (unsigned)(CONFIRM_AFTER_MS / 1000));
    }
    ESP_LOGI(TAG, "运行分区 %s，版本 %s", run ? run->label : "?", esp_app_get_description()->version);
}

void ota_tick(void)
{
    if (!s_pending || now_ms() < CONFIRM_AFTER_MS) return;
    s_pending = false;
    if (esp_ota_mark_app_valid_cancel_rollback() == ESP_OK) {
        ESP_LOGI(TAG, "新固件已确认");
        evlog_add(EV_OTA, 2);
    }
}

bool ota_pending(void) { return s_pending; }

const char *ota_running_label(void)
{
    const esp_partition_t *run = esp_ota_get_running_partition();
    return run ? run->label : "?";
}

static void restart_cb(void *arg) { esp_restart(); }

static esp_err_t fail(httpd_req_t *req, esp_ota_handle_t h, bool begun, const char *msg)
{
    if (begun) esp_ota_abort(h);
    ESP_LOGE(TAG, "升级失败：%s", msg);
    httpd_resp_set_status(req, "400 Bad Request");
    httpd_resp_set_type(req, "application/json");
    char b[160];
    snprintf(b, sizeof(b), "{\"ok\":false,\"err\":\"%s\"}", msg);
    return httpd_resp_sendstr(req, b);
}

esp_err_t ota_http_upload(httpd_req_t *req)
{
    const esp_partition_t *dst = esp_ota_get_next_update_partition(NULL);
    if (!dst) return fail(req, 0, false, "no ota partition");
    if (req->content_len <= 0 || req->content_len > (int)dst->size) return fail(req, 0, false, "bad size");
    char *buf = malloc(CHUNK);
    if (!buf) return fail(req, 0, false, "no memory");
    esp_ota_handle_t h = 0;
    bool begun = false, checked = false;
    int left = req->content_len, got = 0;
    ESP_LOGI(TAG, "开始接收 %d 字节 → %s", left, dst->label);
    while (left > 0) {
        int r = httpd_req_recv(req, buf, left < CHUNK ? left : CHUNK);
        if (r == HTTPD_SOCK_ERR_TIMEOUT) continue;
        if (r <= 0) { free(buf); return fail(req, h, begun, "receive error"); }
        if (!checked) {
            // 第一块里核对镜像头与工程名，防止传错文件
            size_t off = sizeof(esp_image_header_t) + sizeof(esp_image_segment_header_t);
            if (r < (int)(off + sizeof(esp_app_desc_t))) { free(buf); return fail(req, h, begun, "first chunk too short"); }
            if ((uint8_t)buf[0] != ESP_IMAGE_HEADER_MAGIC) { free(buf); return fail(req, h, begun, "not an ESP image"); }
            const esp_app_desc_t *d = (const esp_app_desc_t *)(buf + off);
            if (strncmp(d->project_name, esp_app_get_description()->project_name, sizeof(d->project_name))) {
                free(buf); return fail(req, h, begun, "wrong project");
            }
            ESP_LOGI(TAG, "新固件 %s %s（%s %s）", d->project_name, d->version, d->date, d->time);
            if (esp_ota_begin(dst, OTA_WITH_SEQUENTIAL_WRITES, &h) != ESP_OK) { free(buf); return fail(req, h, false, "ota begin"); }
            begun = true;
            checked = true;
        }
        if (esp_ota_write(h, buf, r) != ESP_OK) { free(buf); return fail(req, h, begun, "flash write"); }
        left -= r;
        got += r;
    }
    free(buf);
    if (esp_ota_end(h) != ESP_OK) return fail(req, h, false, "image invalid");
    if (esp_ota_set_boot_partition(dst) != ESP_OK) return fail(req, h, false, "set boot");
    evlog_add(EV_OTA, 1);
    ESP_LOGW(TAG, "升级写入完成（%d 字节），1 s 后重启", got);
    httpd_resp_set_type(req, "application/json");
    httpd_resp_sendstr(req, "{\"ok\":true}");
    static esp_timer_handle_t t;
    if (!t) {
        esp_timer_create_args_t a = { .callback = restart_cb, .name = "ota_rst" };
        esp_timer_create(&a, &t);
    }
    esp_timer_start_once(t, 1000000);
    return ESP_OK;
}
