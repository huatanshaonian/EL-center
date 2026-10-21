// 配置模块：默认值、键值读写、NVS 存取
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <strings.h>
#include "nvs.h"
#include "esp_log.h"
#include "cfg.h"
#include "util.h"

static const char *TAG = "cfg";
#define NVS_NS "mis01"

cfg_t g_cfg;

// 6E2 校准初值：按仿真报告"目标暗区 → 计数"表，暗区按 20.7 mm × (1 − v/1000) 线性插值得到
static const uint16_t EYE_CAL_DEFAULT[EYE_CAL_N] = {0, 167, 347, 569, 790, 1014, 1240, 1561, 1900, 2393, 3245};

// CFG 键部分（存一个 blob）
typedef struct {
    uint32_t magic;
    int nobody_s, night_start_min, night_end_min, hv_gap_s, nix_cycle_min;
    int fil_hz, bz_hz, lux_ms, gm_period_s;
    char wifi_ssid[33];
    char wifi_pass[65];
    int boot_anim, nix_slot, nix_acp_min, vfd_rot_s, iv18_type;
    char tz[32];
    int vfd_brt_min, vfd_brt_lux;
} cfg_blob_t;
#define CFG_MAGIC 0x4D490004u

static void set_defaults_cfg_keys(void)
{
    g_cfg.nobody_s = 300;
    g_cfg.night_start_min = 23 * 60;
    g_cfg.night_end_min = 7 * 60;
    g_cfg.hv_gap_s = 2;
    g_cfg.nix_cycle_min = 60;
    g_cfg.fil_hz = 20000;
    g_cfg.bz_hz = 4000;
    g_cfg.lux_ms = 1000;
    g_cfg.gm_period_s = 60;
    g_cfg.ntp = false;
    g_cfg.wifi_ssid[0] = 0;
    g_cfg.wifi_pass[0] = 0;
    g_cfg.boot_anim = true;
    g_cfg.nix_slot = true;
    g_cfg.nix_acp_min = 5;
    g_cfg.vfd_rot_s = 10;
    g_cfg.iv18_type = 2;
    strcpy(g_cfg.tz, "CST-8");
    g_cfg.vfd_brt_min = 250;
    g_cfg.vfd_brt_lux = 1000;
}

static nvs_handle_t open_nvs(nvs_open_mode_t mode)
{
    nvs_handle_t h = 0;
    if (nvs_open(NVS_NS, mode, &h) != ESP_OK) return 0;
    return h;
}

void cfg_init(void)
{
    set_defaults_cfg_keys();
    for (int c = 0; c < 2; c++) memcpy(g_cfg.eye_cal[c], EYE_CAL_DEFAULT, sizeof(EYE_CAL_DEFAULT));
    g_cfg.mtr_fs = 3350;   // 约 1.0 mA（3.3 V、2.7 k、内阻 0）：保守初值，实测后 MTR CAL 改
    g_cfg.gm_k = 0.00812f;
    g_cfg.bz_click = true;
    g_cfg.vfd_brt = -1;

    nvs_handle_t h = open_nvs(NVS_READONLY);
    if (!h) { ESP_LOGW(TAG, "NVS 无记录，全部用默认值"); return; }

    cfg_blob_t b; size_t len = sizeof(b);
    if (nvs_get_blob(h, "cfg", &b, &len) == ESP_OK && len == sizeof(b) && b.magic == CFG_MAGIC) {
        g_cfg.nobody_s = b.nobody_s; g_cfg.night_start_min = b.night_start_min; g_cfg.night_end_min = b.night_end_min;
        g_cfg.hv_gap_s = b.hv_gap_s; g_cfg.nix_cycle_min = b.nix_cycle_min; g_cfg.fil_hz = b.fil_hz;
        g_cfg.bz_hz = b.bz_hz; g_cfg.lux_ms = b.lux_ms; g_cfg.gm_period_s = b.gm_period_s;
        memcpy(g_cfg.wifi_ssid, b.wifi_ssid, sizeof(b.wifi_ssid));
        memcpy(g_cfg.wifi_pass, b.wifi_pass, sizeof(b.wifi_pass));
        g_cfg.wifi_ssid[32] = 0; g_cfg.wifi_pass[64] = 0;
        g_cfg.boot_anim = b.boot_anim; g_cfg.nix_slot = b.nix_slot;
        g_cfg.nix_acp_min = b.nix_acp_min; g_cfg.vfd_rot_s = b.vfd_rot_s; g_cfg.iv18_type = b.iv18_type;
        memcpy(g_cfg.tz, b.tz, sizeof(b.tz)); g_cfg.tz[31] = 0;
        if (!g_cfg.tz[0]) strcpy(g_cfg.tz, "CST-8");
        if (g_cfg.fil_hz < 10000 || g_cfg.fil_hz > 20000) g_cfg.fil_hz = 20000;   // 旧版允许更低，现不成立
        g_cfg.vfd_brt_min = b.vfd_brt_min; g_cfg.vfd_brt_lux = b.vfd_brt_lux;
    }
    const char *eyek[2] = {"eyecal_a", "eyecal_b"};
    for (int c = 0; c < 2; c++) {
        uint16_t t[EYE_CAL_N]; len = sizeof(t);
        if (nvs_get_blob(h, eyek[c], t, &len) == ESP_OK && len == sizeof(t)) memcpy(g_cfg.eye_cal[c], t, sizeof(t));
    }
    uint16_t u16; uint8_t u8; uint32_t u32; int32_t i32;
    if (nvs_get_u16(h, "mtr_fs", &u16) == ESP_OK && u16 <= 4095) g_cfg.mtr_fs = u16;
    if (nvs_get_u32(h, "gm_k", &u32) == ESP_OK) { float f; memcpy(&f, &u32, 4); if (f > 0 && f < 1) g_cfg.gm_k = f; }
    if (nvs_get_u8(h, "bz_click", &u8) == ESP_OK) g_cfg.bz_click = u8 != 0;
    if (nvs_get_i32(h, "vfd_brt", &i32) == ESP_OK && i32 >= -1 && i32 <= 1000) g_cfg.vfd_brt = i32;
    if (nvs_get_u8(h, "ntp", &u8) == ESP_OK) g_cfg.ntp = u8 != 0;
    nvs_close(h);
}

static bool commit_close(nvs_handle_t h, esp_err_t e)
{
    if (e == ESP_OK) e = nvs_commit(h);
    nvs_close(h);
    if (e != ESP_OK) ESP_LOGE(TAG, "NVS 写失败 %s", esp_err_to_name(e));
    return e == ESP_OK;
}

bool cfg_save(void)
{
    cfg_blob_t b = {0};
    b.magic = CFG_MAGIC;
    b.nobody_s = g_cfg.nobody_s; b.night_start_min = g_cfg.night_start_min; b.night_end_min = g_cfg.night_end_min;
    b.hv_gap_s = g_cfg.hv_gap_s; b.nix_cycle_min = g_cfg.nix_cycle_min; b.fil_hz = g_cfg.fil_hz;
    b.bz_hz = g_cfg.bz_hz; b.lux_ms = g_cfg.lux_ms; b.gm_period_s = g_cfg.gm_period_s;
    memcpy(b.wifi_ssid, g_cfg.wifi_ssid, sizeof(b.wifi_ssid));
    memcpy(b.wifi_pass, g_cfg.wifi_pass, sizeof(b.wifi_pass));
    b.boot_anim = g_cfg.boot_anim; b.nix_slot = g_cfg.nix_slot;
    b.nix_acp_min = g_cfg.nix_acp_min; b.vfd_rot_s = g_cfg.vfd_rot_s; b.iv18_type = g_cfg.iv18_type;
    memcpy(b.tz, g_cfg.tz, sizeof(b.tz));
    b.vfd_brt_min = g_cfg.vfd_brt_min; b.vfd_brt_lux = g_cfg.vfd_brt_lux;
    nvs_handle_t h = open_nvs(NVS_READWRITE);
    if (!h) return false;
    esp_err_t e = nvs_set_blob(h, "cfg", &b, sizeof(b));
    if (e == ESP_OK) e = nvs_set_u8(h, "ntp", g_cfg.ntp);
    return commit_close(h, e);
}

void cfg_default(void) { set_defaults_cfg_keys(); }

bool cfg_save_eye_cal(int ch)
{
    nvs_handle_t h = open_nvs(NVS_READWRITE);
    if (!h) return false;
    return commit_close(h, nvs_set_blob(h, ch ? "eyecal_b" : "eyecal_a", g_cfg.eye_cal[ch], sizeof(g_cfg.eye_cal[ch])));
}
bool cfg_save_mtr_fs(void)
{
    nvs_handle_t h = open_nvs(NVS_READWRITE);
    if (!h) return false;
    return commit_close(h, nvs_set_u16(h, "mtr_fs", g_cfg.mtr_fs));
}
bool cfg_save_gm_k(void)
{
    nvs_handle_t h = open_nvs(NVS_READWRITE);
    if (!h) return false;
    uint32_t u; memcpy(&u, &g_cfg.gm_k, 4);
    return commit_close(h, nvs_set_u32(h, "gm_k", u));
}
bool cfg_save_bz_click(void)
{
    nvs_handle_t h = open_nvs(NVS_READWRITE);
    if (!h) return false;
    return commit_close(h, nvs_set_u8(h, "bz_click", g_cfg.bz_click));
}
bool cfg_save_vfd_brt(void)
{
    nvs_handle_t h = open_nvs(NVS_READWRITE);
    if (!h) return false;
    return commit_close(h, nvs_set_i32(h, "vfd_brt", g_cfg.vfd_brt));
}
bool cfg_save_ntp(void)
{
    nvs_handle_t h = open_nvs(NVS_READWRITE);
    if (!h) return false;
    return commit_close(h, nvs_set_u8(h, "ntp", g_cfg.ntp));
}

bool cfg_is_night(int m)
{
    int s = g_cfg.night_start_min, e = g_cfg.night_end_min;
    if (s == e) return false;
    if (s < e) return m >= s && m < e;
    return m >= s || m < e;     // 跨午夜
}

// ---------------- 键值表 ----------------
typedef enum { K_INT, K_NIGHT, K_BOOL, K_STR } ktype_t;
typedef struct { const char *name; ktype_t type; void *p; int lo, hi; } cfgkey_t;

static const cfgkey_t KEYS[] = {
    {"NOBODY_S",      K_INT,   &g_cfg.nobody_s,      10, 86400},
    {"NIGHT",         K_NIGHT, NULL,                 0, 0},
    {"HV_GAP_S",      K_INT,   &g_cfg.hv_gap_s,      1, 600},
    {"NIX_CYCLE_MIN", K_INT,   &g_cfg.nix_cycle_min, 1, 1440},
    {"FIL_HZ",        K_INT,   &g_cfg.fil_hz,        10000, 20000},   // IV-18 板 FIL_OK 检测要 ≥ 10 kHz
    {"BZ_HZ",         K_INT,   &g_cfg.bz_hz,         200, 10000},
    {"LUX_MS",        K_INT,   &g_cfg.lux_ms,        200, 60000},
    {"GM_PERIOD_S",   K_INT,   &g_cfg.gm_period_s,   1, 3600},
    {"NTP",           K_BOOL,  &g_cfg.ntp,           0, 1},
    {"WIFI_SSID",     K_STR,   g_cfg.wifi_ssid,      0, 32},
    {"WIFI_PASS",     K_STR,   g_cfg.wifi_pass,      0, 64},
    {"BOOT_ANIM",     K_BOOL,  &g_cfg.boot_anim,     0, 1},
    {"NIX_SLOT",      K_BOOL,  &g_cfg.nix_slot,      0, 1},
    {"NIX_ACP_MIN",   K_INT,   &g_cfg.nix_acp_min,   0, 60},
    {"VFD_ROT_S",     K_INT,   &g_cfg.vfd_rot_s,     2, 600},
    {"IV18_TYPE",     K_INT,   &g_cfg.iv18_type,     1, 2},
    {"TZ",            K_STR,   g_cfg.tz,             1, 31},
    {"VFD_BRT_MIN",   K_INT,   &g_cfg.vfd_brt_min,   50, 1000},
    {"VFD_BRT_LUX",   K_INT,   &g_cfg.vfd_brt_lux,   10, 65535},
};

static const cfgkey_t *find_key(const char *k)
{
    for (size_t i = 0; i < sizeof(KEYS) / sizeof(KEYS[0]); i++)
        if (strcasecmp(k, KEYS[i].name) == 0) return &KEYS[i];
    return NULL;
}

cfg_err_t cfg_get(const char *key, char *out, int n)
{
    const cfgkey_t *k = find_key(key);
    if (!k) return CFG_ERR_KEY;
    switch (k->type) {
    case K_INT:   snprintf(out, n, "%s=%d", k->name, *(int *)k->p); break;
    case K_BOOL:  snprintf(out, n, "%s=%d", k->name, *(bool *)k->p ? 1 : 0); break;
    case K_NIGHT: snprintf(out, n, "%s=%02d:%02d-%02d:%02d", k->name, g_cfg.night_start_min / 60, g_cfg.night_start_min % 60,
                           g_cfg.night_end_min / 60, g_cfg.night_end_min % 60); break;
    case K_STR:
        // 密码不回显明文
        if (k->p == g_cfg.wifi_pass) snprintf(out, n, "%s=%s", k->name, g_cfg.wifi_pass[0] ? "***" : "");
        else snprintf(out, n, "%s=%s", k->name, (char *)k->p);
        break;
    }
    return CFG_OK;
}

static bool parse_hhmm(const char *s, int *min)
{
    int h, m;
    if (sscanf(s, "%d:%d", &h, &m) != 2 || h < 0 || h > 23 || m < 0 || m > 59) return false;
    *min = h * 60 + m;
    return true;
}

cfg_err_t cfg_set(const char *key, const char *val)
{
    const cfgkey_t *k = find_key(key);
    if (!k) return CFG_ERR_KEY;
    char *end;
    switch (k->type) {
    case K_INT: {
        long v = strtol(val, &end, 10);
        if (*val == 0 || *end || v < k->lo || v > k->hi) return CFG_ERR_RANGE;
        *(int *)k->p = (int)v;
        break;
    }
    case K_BOOL:
        if (strcmp(val, "0") && strcmp(val, "1")) return CFG_ERR_RANGE;
        *(bool *)k->p = val[0] == '1';
        break;
    case K_NIGHT: {
        const char *dash = strchr(val, '-');
        int s, e;
        if (!dash || !parse_hhmm(val, &s) || !parse_hhmm(dash + 1, &e)) return CFG_ERR_RANGE;
        g_cfg.night_start_min = s; g_cfg.night_end_min = e;
        break;
    }
    case K_STR:
        if ((int)strlen(val) > k->hi || (int)strlen(val) < k->lo) return CFG_ERR_RANGE;
        strcpy((char *)k->p, val);
        break;
    }
    return CFG_OK;
}
