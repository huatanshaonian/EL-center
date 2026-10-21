// IV-18 内容层。MAX6921 位序（规格 F5）：OUT0–8 = 栅 G1–G9（G1 最左特殊位），OUT9–16 = 阳极 a–g、dp，OUT17–19 备用。
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "esp_log.h"
#include "vfd.h"
#include "vfd_scan.h"
#include "vfd_font.h"
#include "vfd_fx.h"
#include "anim.h"
#include "dispmode.h"
#include "power.h"
#include "sensors.h"
#include "geiger.h"
#include "rtc.h"
#include "weather.h"
#include "cfg.h"
#include "util.h"

static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;
static uint8_t s_host_segs[8];
static uint8_t s_host_sym;
static bool s_forced_off;

void vfd_init(void) { vfd_scan_init(); }

int vfd_show(const char *txt, int t_s)
{
    uint8_t segs[8];
    if (vfd_text_to_segs(txt, segs) < 0) return -1;
    taskENTER_CRITICAL(&s_mux);
    memcpy(s_host_segs, segs, 8);
    s_forced_off = false;
    taskEXIT_CRITICAL(&s_mux);
    dm_set_host(DM_VFD, t_s);
    return 0;
}

void vfd_sym(int bits, int t_s)
{
    s_host_sym = bits & 7;
    dm_set_host(DM_VFD, t_s);
}

void vfd_auto(void) { s_forced_off = false; dm_set_auto(DM_VFD); }
void vfd_off(void) { s_forced_off = true; }

void vfd_set_brt(int v)
{
    g_cfg.vfd_brt = v;
    cfg_save_vfd_brt();
}

bool vfd_is_on(void) { return vfd_scan_is_on(); }

void IRAM_ATTR vfd_emergency_off_isr(void) { vfd_scan_emergency_off_isr(); }
void vfd_on_pfail(void) { vfd_scan_power(false); }

// AUTO 本地内容（F5 防烧屏）：日期 → CPM → 温度 → 室外温度轮换（时间无效时没有日期；没有天气数据时没有室外温度）
enum { ITEM_DATE = 0, ITEM_CPM, ITEM_TEMP, ITEM_WX, ITEM_N };

static bool item_ok(int item)
{
    if (item == ITEM_DATE) return clk_time_valid();
    if (item == ITEM_WX) return weather_get(NULL, NULL, NULL, NULL);
    return true;
}

static void right_align(char *out, int n, const char *body, const char *suffix)
{
    int pad = 8 - vfd_visual_len(body) - vfd_visual_len(suffix);
    snprintf(out, n, "%*s%s%s", pad > 0 ? pad : 0, "", body, suffix);
}

static void item_text(int item, char *buf, int n)
{
    char num[16];
    switch (item) {
    case ITEM_DATE: {
        civil_t c;
        clk_to_civil(clk_now(), &c);
        snprintf(buf, n, "%02d-%02d-%02d", c.year % 100, c.mon, c.day);
        break;
    }
    case ITEM_CPM:
        if (gm_valid()) snprintf(buf, n, "CP%6d", clampi(gm_cpm(), 0, 999999));
        else snprintf(buf, n, "CP  ----");
        break;
    case ITEM_WX: {
        int t = 0;
        weather_get(&t, NULL, NULL, NULL);
        int a = t < 0 ? -t : t;
        snprintf(num, sizeof(num), "%s%d.%d", t < 0 ? "-" : "", a / 10, a % 10);
        right_align(buf, n, num, "*C");
        buf[0] = 'o';                   // 最左位 "o" 表示室外（F5）
        break;
    }
    default: {
        int t = clk_temp_x10();
        if (t == CLK_TEMP_NONE) { snprintf(buf, n, "   --.-*C"); break; }   // "." 并位，正好 8 位
        int a = t < 0 ? -t : t;
        snprintf(num, sizeof(num), "%s%d.%d", t < 0 ? "-" : "", a / 10, a % 10);
        right_align(buf, n, num, "*C");
        break;
    }
    }
}

static int s_item = ITEM_DATE;
static uint32_t s_item_ms;
static uint8_t s_shown[8];        // 上一帧实际显示的字形（擦除动画的起点）

static void auto_segs(uint8_t segs[8])
{
    if (!item_ok(s_item)) s_item = ITEM_CPM;
    if (now_ms() - s_item_ms >= (uint32_t)g_cfg.vfd_rot_s * 1000u) {
        s_item_ms = now_ms();
        do { s_item = (s_item + 1) % ITEM_N; } while (!item_ok(s_item));
        vfdfx_wipe_start(s_shown);
    }
    char buf[20];
    item_text(s_item, buf, sizeof(buf));
    vfd_text_to_segs(buf, segs);
    vfdfx_wipe_apply(segs);
}

// 自动亮度：随环境光对数变化，全黑 = VFD_BRT_MIN，VFD_BRT_LUX 以上满亮度（默认 250 / 1000 lux）
static int auto_brightness(void)
{
    int lux = sens_lux();
    if (lux < 0) return 700;
    float lo = (float)g_cfg.vfd_brt_min;
    float b = lo + (1000.0f - lo) * log10f((float)lux + 1.0f) / log10f((float)g_cfg.vfd_brt_lux + 1.0f);
    return clampi((int)b, 150, 1000);
}

void vfd_tick(void)
{
    bool want = !s_forced_off && dm_local_wanted() && !power_pfail() && !power_outputs_blocked();
    vfd_scan_power(want);
    vfd_scan_check();

    // 开机动画：开始扫描后播放（Pi 已接管时不播）
    if (vfd_scan_is_on() && anim_take(ANIM_VFD) && !dm_is_host(DM_VFD)) vfdfx_boot_start();

    uint8_t segs[8], sym = 0;
    if (vfdfx_boot_active()) {
        vfdfx_boot_apply(segs);
        s_item_ms = now_ms();          // 动画后从第一样内容开始计时
    } else if (dm_is_host(DM_VFD)) {
        taskENTER_CRITICAL(&s_mux);
        memcpy(segs, s_host_segs, 8);
        sym = s_host_sym;
        taskEXIT_CRITICAL(&s_mux);
    } else {
        auto_segs(segs);
    }
    memcpy(s_shown, segs, 8);
    uint32_t f[VFD_GRIDS];
    // G1 特殊位：bit0 竖线、bit1 负号、bit2 点。тип 1 → OUT17/18/19；тип 2 → 负号用 g（OUT15）、点用 dp（OUT16），无竖线
    if (g_cfg.iv18_type == 1) f[0] = (1u << 0) | ((uint32_t)sym << 17);
    else f[0] = (1u << 0) | ((sym & 2) ? (1u << 15) : 0) | ((sym & 4) ? (1u << 16) : 0);
    for (int i = 0; i < 8; i++) f[i + 1] = (1u << (i + 1)) | ((uint32_t)segs[i] << 9);
    vfd_scan_set_frames(f);
    vfd_scan_set_brightness(g_cfg.vfd_brt < 0 ? auto_brightness() : g_cfg.vfd_brt);
}
