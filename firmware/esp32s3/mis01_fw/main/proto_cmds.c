// 协议命令执行（规格 6.5–6.9）。命令只是"请求"，安全条件由各模块自己把关（S9）。
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "proto.h"
#include "power.h"
#include "hv.h"
#include "nixie.h"
#include "vfd.h"
#include "eye.h"
#include "meter.h"
#include "geiger.h"
#include "buzzer.h"
#include "sensors.h"
#include "rtc.h"
#include "cfg.h"
#include "evlog.h"
#include "util.h"
#include "anim.h"
#include "wifi_net.h"
#include "weather.h"

#define OK(...)        proto_send("OK" __VA_ARGS__)
#define ERR(code, msg) proto_send("ERR " code " %s", msg)

static bool is(const char *a, const char *b) { return a && strcasecmp(a, b) == 0; }

static bool to_int(const char *s, int lo, int hi, int *out)
{
    if (!s || !*s) return false;
    char *e;
    long v = strtol(s, &e, 10);
    if (*e || v < lo || v > hi) return false;
    *out = (int)v;
    return true;
}

// 找 "KEY=值" 形式的字段（从 argv[from] 起）
static const char *find_opt(proto_cmd_t *c, int from, const char *key)
{
    size_t n = strlen(key);
    for (int i = from; i < c->argc; i++)
        if (!c->quoted[i] && strncasecmp(c->argv[i], key, n) == 0 && c->argv[i][n] == '=') return c->argv[i] + n + 1;
    return NULL;
}

// ---------------- 6.5 查询与系统 ----------------
static void temp_text(char *out, int n)
{
    int t = clk_temp_x10();
    if (t == CLK_TEMP_NONE) { snprintf(out, n, "-"); return; }
    int a = t < 0 ? -t : t;
    snprintf(out, n, "%s%d.%d", t < 0 ? "-" : "", a / 10, a % 10);
}

static void cmd_status(void)
{
    char t[20], tp[16];
    clk_format(clk_now(), t);
    temp_text(tp, sizeof(tp));
    proto_send("OK PWR=%s HOSTSW=%d HVSW=%d SCRSW=%d HV=%d PF=%d PRES=%d LUX=%d CPM=%d GMV=%d TIME=%s RTC=%d TEMP=%s UP=%lu",
               power_state_name(), power_sw_host(), power_sw_hv(), power_sw_scr(), hv_is_on(), power_pfail(),
               sens_present(), sens_lux(), gm_cpm(), gm_valid(), t, clk_time_valid(), tp,
               (unsigned long)(esp_timer_get_time() / 1000000));
}

static void cmd_log_dump(void)
{
    int n = evlog_count();
    for (int i = 0; i < n; i++) {
        uint32_t t; ev_code_t code; int32_t param;
        if (evlog_get(i, &t, &code, &param)) break;
        char ts[20] = "-";
        if (t) clk_format(t, ts);
        proto_send("#LOG %s %s %ld", ts, evlog_name(code), (long)param);
    }
    proto_send("OK %d", n);
}

// ---------------- 6.6 时间 ----------------
static void cmd_time(proto_cmd_t *c)
{
    if (is(c->argv[0], "TIME?")) {
        char t[20];
        clk_format(clk_now(), t);
        proto_send("OK %s SRC=%s", t, clk_src_name(clk_src()));
        return;
    }
    uint32_t secs;
    if (c->argc != 2) { ERR("SYNTAX", "TIME <YYYY-MM-DDTHH:MM:SS>"); return; }
    if (!clk_parse(c->argv[1], &secs)) { ERR("RANGE", "bad time"); return; }
    bool ok = clk_set_local(secs, TSRC_HOST);
    evlog_add(EV_TIME_SET, 1);
    if (!ok) { ERR("HW", "RTC write failed"); return; }
    OK();
}

// ---------------- 6.7 电源与高压 ----------------
static void cmd_hv(proto_cmd_t *c)
{
    if (c->argc != 2) { ERR("SYNTAX", "HV AUTO|ON|OFF"); return; }
    if (is(c->argv[1], "AUTO")) hv_set_mode(HV_MODE_AUTO);
    else if (is(c->argv[1], "ON")) hv_set_mode(HV_MODE_ON);
    else if (is(c->argv[1], "OFF")) hv_set_mode(HV_MODE_OFF);
    else { ERR("SYNTAX", "HV AUTO|ON|OFF"); return; }
    vTaskDelay(pdMS_TO_TICKS(30));          // 等控制任务执行一轮，回实际状态
    proto_send("OK HV=%d", hv_is_on());
}

// ---------------- 6.8 显示件 ----------------
static void cmd_nix(proto_cmd_t *c)
{
    const char *a = c->argc > 1 ? c->argv[1] : NULL;
    if (is(a, "AUTO")) { nixie_auto(); OK(); }
    else if (is(a, "OFF")) { nixie_off(c->t_s); OK(); }
    else if (is(a, "CYCLE")) { nixie_cycle_now(); OK(); }
    else if (is(a, "SHOW") && c->argc == 3) {
        if (nixie_show(c->argv[2], c->t_s)) ERR("RANGE", "6 digits of 0-9/space, '.' after a digit");
        else OK();
    } else ERR("SYNTAX", "NIX AUTO|SHOW \"text\"|OFF|CYCLE");
}

static void cmd_vfd(proto_cmd_t *c)
{
    const char *a = c->argc > 1 ? c->argv[1] : NULL;
    int v;
    if (is(a, "AUTO")) { vfd_auto(); OK(); }
    else if (is(a, "OFF")) { vfd_off(); OK(); }
    else if (is(a, "SHOW") && c->argc == 3) {
        if (vfd_show(c->argv[2], c->t_s)) ERR("RANGE", "undisplayable char or more than 8");
        else OK();
    } else if (is(a, "SYM") && c->argc == 3) {
        if (!to_int(c->argv[2], 0, 7, &v)) { ERR("RANGE", "SYM 0..7"); return; }
        vfd_sym(v, c->t_s);
        OK();
    } else if (is(a, "BRT") && c->argc == 3) {
        if (is(c->argv[2], "AUTO")) vfd_set_brt(-1);
        else if (to_int(c->argv[2], 0, 1000, &v)) vfd_set_brt(v);
        else { ERR("RANGE", "BRT AUTO|0..1000"); return; }
        OK();
    } else ERR("SYNTAX", "VFD AUTO|SHOW|SYM|BRT|OFF");
}

static void cmd_eye(proto_cmd_t *c)
{
    if (c->argc < 3) { ERR("SYNTAX", "EYE A|B ..."); return; }
    int ch;
    if (is(c->argv[1], "A")) ch = 0;
    else if (is(c->argv[1], "B")) ch = 1;
    else { ERR("SYNTAX", "EYE A|B ..."); return; }
    const char *a = c->argv[2];
    int v;
    if (is(a, "AUTO")) { eye_auto(ch); OK(); }
    else if (is(a, "RAW")) {
        if (c->argc != 4 || !to_int(c->argv[3], 0, 4095, &v)) { ERR("RANGE", "RAW 0..4095"); return; }
        eye_raw(ch, v, c->t_s);
        OK();
    } else if (is(a, "CAL?")) {
        char buf[100]; int n = 0;
        for (int i = 0; i < EYE_CAL_N; i++) n += snprintf(buf + n, sizeof(buf) - n, " %u", g_cfg.eye_cal[ch][i]);
        proto_send("OK%s", buf);
    } else if (is(a, "CAL")) {
        if (c->argc != 3 + EYE_CAL_N) { ERR("SYNTAX", "CAL needs 11 duties"); return; }
        uint16_t cal[EYE_CAL_N];
        for (int i = 0; i < EYE_CAL_N; i++) {
            if (!to_int(c->argv[3 + i], 0, 4095, &v)) { ERR("RANGE", "duty 0..4095"); return; }
            cal[i] = (uint16_t)v;
        }
        eye_set_cal(ch, cal);
        OK();
    } else if (to_int(a, 0, 1000, &v)) { eye_set(ch, v, c->t_s); OK(); }
    else ERR("RANGE", "0..1000");
}

static void cmd_mtr(proto_cmd_t *c)
{
    const char *a = c->argc > 1 ? c->argv[1] : NULL;
    int v;
    if (is(a, "AUTO")) { meter_auto(); OK(); }
    else if (is(a, "RAW")) {
        if (c->argc != 3 || !to_int(c->argv[2], 0, 4095, &v)) { ERR("RANGE", "RAW 0..4095"); return; }
        meter_raw(v, c->t_s);
        OK();
    } else if (is(a, "CAL?")) proto_send("OK FS=%u", g_cfg.mtr_fs);
    else if (is(a, "CAL")) {
        const char *fs = find_opt(c, 2, "FS");
        if (!fs || !to_int(fs, 0, 4095, &v)) { ERR("RANGE", "CAL FS=0..4095"); return; }
        meter_set_fs(v);
        OK();
    } else if (to_int(a, 0, 1000, &v)) { meter_set(v, c->t_s); OK(); }
    else if (a && to_int(a, -2147483647, 2147483647, &v)) ERR("RANGE", "0..1000");
    else ERR("SYNTAX", "MTR AUTO|<0..1000>|RAW|CAL");
}

// ---------------- 6.9 盖革、蜂鸣器、传感器、配置 ----------------
static void cmd_gm(proto_cmd_t *c)
{
    if (is(c->argv[0], "GM?")) {
        proto_send("OK CPM=%d TOTAL=%lu USV=%.3f VALID=%d", gm_cpm(), (unsigned long)gm_total(), gm_usv(), gm_valid());
        return;
    }
    if (is(c->argv[1], "RESET")) { gm_reset(); OK(); return; }
    if (is(c->argv[1], "K") && c->argc == 3) {
        char *e;
        float k = strtof(c->argv[2], &e);
        if (*e || !(k > 0.0f && k < 1.0f)) { ERR("RANGE", "0<K<1"); return; }
        g_cfg.gm_k = k;
        cfg_save_gm_k();
        OK();
        return;
    }
    ERR("SYNTAX", "GM?|GM RESET|GM K <k>");
}

static void cmd_bz(proto_cmd_t *c)
{
    const char *a = c->argc > 1 ? c->argv[1] : NULL;
    int n, hz = 0;
    if (is(a, "CLICK") && c->argc == 3) {
        if (is(c->argv[2], "ON")) bz_set_click(true);
        else if (is(c->argv[2], "OFF")) bz_set_click(false);
        else { ERR("SYNTAX", "BZ CLICK ON|OFF"); return; }
        OK();
    } else if (is(a, "ALARM") && c->argc >= 3) {
        if (!to_int(c->argv[2], 1, 20, &n)) { ERR("RANGE", "count 1..20"); return; }
        const char *h = find_opt(c, 3, "HZ");
        if (h && !to_int(h, 200, 10000, &hz)) { ERR("RANGE", "HZ 200..10000"); return; }
        bz_alarm(n, hz);
        OK();
    } else ERR("SYNTAX", "BZ CLICK ON|OFF|ALARM <n> [HZ=f]");
}

static void cmd_cfg(proto_cmd_t *c)
{
    char out[100];
    if (is(c->argv[0], "CFG?")) {
        if (c->argc != 2) { ERR("SYNTAX", "CFG? <key>"); return; }
        if (cfg_get(c->argv[1], out, sizeof(out)) != CFG_OK) { ERR("RANGE", "unknown key"); return; }
        proto_send("OK %s", out);
        return;
    }
    if (c->argc == 2 && is(c->argv[1], "SAVE")) { if (cfg_save()) OK(); else ERR("HW", "NVS write failed"); return; }
    if (c->argc == 2 && is(c->argv[1], "DEFAULT")) { cfg_default(); OK(); return; }
    if (c->argc != 3) { ERR("SYNTAX", "CFG <key> <value>|SAVE|DEFAULT"); return; }
    switch (cfg_set(c->argv[1], c->argv[2])) {
    case CFG_OK: OK(); break;
    case CFG_ERR_KEY: ERR("RANGE", "unknown key"); break;
    default: ERR("RANGE", "bad value"); break;
    }
}

// 诊断命令入口：正式固件里不处理（回 unknown command）；测试固件由外部诊断组件提供强符号覆盖
__attribute__((weak)) bool proto_diag_exec(proto_cmd_t *c) { return false; }

void proto_exec(proto_cmd_t *c)
{
    const char *k = c->argv[0];
    if (is(k, "?")) cmd_status();
    else if (is(k, "VER")) proto_send("OK FW=%s SPEC=%s BUILD=%s", FW_VERSION, FW_SPEC, __DATE__);
    else if (is(k, "PING")) proto_send("OK PONG");
    else if (is(k, "LOG?")) cmd_log_dump();
    else if (is(k, "LOG") && c->argc == 2 && is(c->argv[1], "CLR")) { evlog_clear(); OK(); }
    else if (is(k, "REBOOT")) { OK(); vTaskDelay(pdMS_TO_TICKS(200)); esp_restart(); }
    else if (is(k, "TIME?") || is(k, "TIME")) cmd_time(c);
    else if (is(k, "NTP") && c->argc == 2 && (is(c->argv[1], "ON") || is(c->argv[1], "OFF"))) {
        g_cfg.ntp = is(c->argv[1], "ON");
        if (cfg_save_ntp()) OK(); else ERR("HW", "NVS write failed");
    }
    else if (is(k, "HV")) cmd_hv(c);
    else if (is(k, "SHUTDOWN")) { power_pi_shutdown_cmd(); OK(); }
    else if (is(k, "NIX")) cmd_nix(c);
    else if (is(k, "VFD")) cmd_vfd(c);
    else if (is(k, "EYE")) cmd_eye(c);
    else if (is(k, "MTR")) cmd_mtr(c);
    else if (is(k, "GM?") || (is(k, "GM") && c->argc >= 2)) cmd_gm(c);
    else if (is(k, "BZ")) cmd_bz(c);
    else if (is(k, "NET?")) {
        char ssid[33];
        cfg_lock(); strlcpy(ssid, g_cfg.wifi_ssid, sizeof(ssid)); cfg_unlock();
        if (net_up()) proto_send("OK WIFI=1 IP=%s RSSI=%d SSID=\"%s\"", net_ip(), net_rssi(), ssid);
        else proto_send("OK WIFI=0 IP=- RSSI=- REASON=%d SSID=\"%s\"", net_last_reason(), ssid);
    }
    else if (is(k, "NET") && c->argc == 2 && is(c->argv[1], "SCAN")) {
        net_ap_t *ap = calloc(24, sizeof(net_ap_t));
        int n = ap ? net_scan(ap, 24) : -1;
        for (int i = 0; i < n; i++) proto_send("#AP %d %s \"%s\"", ap[i].rssi, ap[i].open ? "OPEN" : "SEC", ap[i].ssid);
        free(ap);
        if (n < 0) ERR("HW", "scan failed"); else proto_send("OK %d", n);
    }
    else if (is(k, "WX?")) {
        int t, rh, code, age;
        bool v = weather_get(&t, &rh, &code, &age);
        if (age < 0) proto_send("OK T=- RH=- CODE=- AGE=-");
        else proto_send("OK T=%s%d.%d RH=%d CODE=%d AGE=%d VALID=%d", t < 0 ? "-" : "", (t < 0 ? -t : t) / 10,
                        (t < 0 ? -t : t) % 10, rh, code, age, v);
    }
    else if (is(k, "LUX?")) proto_send("OK LUX=%d", sens_lux());
    else if (is(k, "TEMP?")) { char tp[16]; temp_text(tp, sizeof(tp)); proto_send("OK TEMP=%s", tp); }
    else if (is(k, "ANIM") && c->argc == 2 && is(c->argv[1], "BOOT")) { anim_boot_request(); OK(); }
    else if (is(k, "PRES?")) {
        int d = sens_dist_cm();
        if (d >= 0) proto_send("OK PRES=%d DIST=%d", sens_present(), d);
        else proto_send("OK PRES=%d DIST=-", sens_present());
    }
    else if (is(k, "CFG?") || (is(k, "CFG") && c->argc >= 2)) cmd_cfg(c);
    else if (is(k, "DBG") && proto_diag_exec(c)) { }
    else ERR("SYNTAX", "unknown command");
}
