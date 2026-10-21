#include <stdio.h>
#include <string.h>
#include "vfd_fx.h"
#include "vfd_font.h"
#include "util.h"

// 段位：a=0x01 b=0x02 c=0x04 d=0x08 e=0x10 f=0x20 g=0x40
#define SA 0x01
#define SB 0x02
#define SC 0x04
#define SD 0x08
#define SE 0x10
#define SF 0x20

// ---------------- 开机：外圈跑马灯 ×2 → 全段 0.5 s → 版本号 1 s ----------------
#define CHASE_STEPS  20
#define CHASE_MS     40
#define CHASE_LOOPS  2
#define LAMP_MS      500
#define VER_MS       1000

static bool s_boot;
static uint32_t s_boot_t0;

// 外圈路径第 k 步：位置与段
static void chase_step(int k, int *pos, uint8_t *seg)
{
    if (k < 8)       { *pos = k;          *seg = SA; }   // 顶边从左到右
    else if (k == 8) { *pos = 7;          *seg = SB; }   // 右边往下
    else if (k == 9) { *pos = 7;          *seg = SC; }
    else if (k < 18) { *pos = 17 - k;     *seg = SD; }   // 底边从右到左
    else if (k == 18){ *pos = 0;          *seg = SE; }   // 左边往上
    else             { *pos = 0;          *seg = SF; }
}

void vfdfx_boot_start(void) { s_boot = true; s_boot_t0 = now_ms(); }

bool vfdfx_boot_active(void)
{
    if (s_boot && now_ms() - s_boot_t0 >= CHASE_STEPS * CHASE_MS * CHASE_LOOPS + LAMP_MS + VER_MS) s_boot = false;
    return s_boot;
}

void vfdfx_boot_apply(uint8_t segs[8])
{
    uint32_t el = now_ms() - s_boot_t0;
    memset(segs, 0, 8);
    uint32_t chase_end = CHASE_STEPS * CHASE_MS * CHASE_LOOPS;
    if (el < chase_end) {
        int k = (int)(el / CHASE_MS);
        for (int tail = 0; tail < 3 && k - tail >= 0; tail++) {   // 亮段带 2 段尾巴
            int pos; uint8_t seg;
            chase_step((k - tail) % CHASE_STEPS, &pos, &seg);
            segs[pos] |= seg;
        }
    } else if (el < chase_end + LAMP_MS) {
        memset(segs, 0xFF, 8);                                     // 全段（含 dp）自检
    } else {
        char buf[16];
        int pad = 8 - vfd_visual_len(FW_VERSION);
        snprintf(buf, sizeof(buf), "%*s%s", pad > 0 ? pad : 0, "", FW_VERSION);
        vfd_text_to_segs(buf, segs);
    }
}

// ---------------- 擦除：旧内容逐位熄灭，新内容逐位出现 ----------------
#define WIPE_MS 25

static bool s_wipe;
static uint32_t s_wipe_t0;
static uint8_t s_old[8];

void vfdfx_wipe_start(const uint8_t old_segs[8])
{
    memcpy(s_old, old_segs, 8);
    s_wipe = true;
    s_wipe_t0 = now_ms();
}

void vfdfx_wipe_apply(uint8_t segs[8])
{
    if (!s_wipe) return;
    int k = (int)((now_ms() - s_wipe_t0) / WIPE_MS);
    if (k >= 16) { s_wipe = false; return; }
    for (int i = 0; i < 8; i++) {
        if (k < 8) segs[i] = i < k ? 0 : s_old[i];        // 擦旧
        else segs[i] = i <= k - 8 ? segs[i] : 0;          // 写新
    }
}
