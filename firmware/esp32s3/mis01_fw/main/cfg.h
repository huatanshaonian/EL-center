// 可配置参数与校准值（规格 6.9 CFG 键、EYE/MTR CAL、GM K、BZ CLICK、VFD BRT）。
// CFG 键：改了立即生效，CFG SAVE 才写 NVS；校准、静音、亮度、NTP 命令：改了立即写 NVS。
#pragma once
#include <stdint.h>
#include <stdbool.h>

#define EYE_CAL_N   11

typedef struct {
    // ---- CFG 键 ----
    int  nobody_s;          // 无人判定延时
    int  night_start_min;   // 夜间开始（一天中的分钟数）
    int  night_end_min;     // 夜间结束；start == end 表示不设夜间
    int  hv_gap_s;          // 高压关后再开最小间隔
    int  nix_cycle_min;     // 防阴极中毒轮换周期
    int  fil_hz;            // IV-18 灯丝方波频率
    int  bz_hz;             // 报警频率
    int  lux_ms;            // BH1750 读取周期
    int  gm_period_s;       // !GM 上报周期
    bool ntp;               // Pi 不在线时允许 Wi-Fi NTP
    char wifi_ssid[33];
    char wifi_pass[65];
    bool boot_anim;         // 开机动画
    bool nix_slot;          // 辉光钟换分滚动
    int  nix_acp_min;       // 每日防中毒修复时长（0 = 不做）
    int  vfd_rot_s;         // IV-18 本地内容轮换间隔
    int  iv18_type;         // IV-18 管子版本：1 = G1 位有独立 6/7/8 脚阳极，2 = 常见货（点、负号并在 dp、g 上）
    char tz[32];            // Wi-Fi NTP 用的 POSIX 时区串
    int  vfd_brt_min;       // 自动亮度：全黑时的亮度（0..1000）
    int  vfd_brt_lux;       // 自动亮度：达到满亮度的照度（lux）
    // ---- 网络（F15），NVS 里单独存一块 "cfg2"，旧配置块不动 ----
    char  web_pass[33];     // 网页改设置/升级的密码；空 = 网页只读
    char  wx_city[49];      // 天气城市名（只用于显示）
    float wx_lat, wx_lon;   // 天气坐标；NAN = 未设（不取天气）
    int   wx_min;           // 天气刷新间隔（分钟）
    // ---- 校准与持久设置 ----
    uint16_t eye_cal[2][EYE_CAL_N];  // 0,100..1000 → 占空比（12 位）
    uint16_t mtr_fs;                 // 表头满偏占空比
    float    gm_k;                   // CPM → µSv/h
    bool     bz_click;               // 咔哒开
    int      vfd_brt;                // -1 = AUTO，否则 0..1000
} cfg_t;

extern cfg_t g_cfg;

typedef enum { CFG_OK = 0, CFG_ERR_KEY, CFG_ERR_RANGE } cfg_err_t;

void      cfg_init(void);                       // 读 NVS（无记录用默认）
cfg_err_t cfg_get(const char *key, char *out, int out_len);  // out = "键=值"
cfg_err_t cfg_set(const char *key, const char *val);
void      cfg_lock(void);                       // 多步读写配置时加锁（递归锁）
void      cfg_unlock(void);
bool      cfg_save(void);                       // CFG 键写 NVS
void      cfg_default(void);                    // CFG 键恢复默认（不写 NVS，需 CFG SAVE）
bool      cfg_is_night(int minute_of_day);

// 键表遍历（网页设置用）
int         cfg_key_count(void);
const char *cfg_key_name(int i);
bool        cfg_key_secret(int i);             // 密码类：cfg_get 回 *** 或空
uint32_t    cfg_wifi_gen(void);                // WIFI_SSID/WIFI_PASS 每改一次 +1（网络模块据此重连）
bool        cfg_wx_set(void);                  // 配了天气坐标

// 持久设置：改了立即写 NVS
bool cfg_save_eye_cal(int ch);
bool cfg_save_mtr_fs(void);
bool cfg_save_gm_k(void);
bool cfg_save_bz_click(void);
bool cfg_save_vfd_brt(void);
bool cfg_save_ntp(void);
