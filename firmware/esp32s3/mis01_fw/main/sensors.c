// BH1750：连续高分辨率模式，每 LUX_MS 读一次。
// LD2410B：OUT 脚作主判据（高 = 有人，立即生效；连续低 NOBODY_S 秒才算无人）；
//          UART1 256000 8N1 解析上报帧取探测距离（可选信息）。
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "esp_task_wdt.h"
#include "sensors.h"
#include "i2cbus.h"
#include "cfg.h"
#include "proto.h"
#include "evlog.h"
#include "pins.h"
#include "util.h"

static const char *TAG = "sens";

#define LD_UART     UART_NUM_1
#define LD_BAUD     256000
#define LD_SILENT_MS 5000

static volatile int s_lux = -1;
static volatile bool s_bh_ok;
static volatile int s_dist = -1;
static volatile uint32_t s_ld_last_ms;
static bool s_ld_ok_reported = true;
static bool s_present = true;           // 开机先按"有人"，显示先亮起来
static uint32_t s_last_seen_ms;

// ---------------- BH1750 ----------------
static bool bh_start(void)
{
    uint8_t on = 0x01, mode = 0x10;     // Power On；Continuously H-Resolution Mode（1 lx，120 ms）
    return i2cbus_write(I2C_ADDR_BH1750, &on, 1) && i2cbus_write(I2C_ADDR_BH1750, &mode, 1);
}

static void bh_poll(void)
{
    uint8_t r[2];
    bool ok = i2cbus_read(I2C_ADDR_BH1750, r, 2);
    if (ok) s_lux = (int)(((r[0] << 8) | r[1]) / 1.2f);
    if (ok != s_bh_ok) {
        s_bh_ok = ok;
        if (!ok) {
            s_lux = -1;
            evlog_add(EV_SENSOR_LOST, SENSOR_ID_BH1750);
            proto_report("!ERR BH1750 lost");
        } else {
            bh_start();
        }
    }
}

// ---------------- LD2410 上报帧 ----------------
// 帧：F4 F3 F2 F1 | 长度(2, LE) | 数据 | F8 F7 F6 F5
// 数据：类型(0x01 工程 / 0x02 基本) AA 状态 运动距离(2) 运动能量 静止距离(2) 静止能量 探测距离(2) ... 55 00
static void ld_parse_byte(uint8_t b)
{
    static uint8_t buf[64];
    static int n, need;
    static const uint8_t HDR[4] = {0xF4, 0xF3, 0xF2, 0xF1};
    if (n < 4) {
        if (b == HDR[n]) buf[n++] = b; else n = (b == HDR[0]) ? 1 : 0;
        return;
    }
    buf[n++] = b;
    if (n == 6) {
        need = 6 + (buf[4] | (buf[5] << 8)) + 4;
        if (need > (int)sizeof(buf) || need < 6 + 13 + 4) { n = 0; return; }
    }
    if (n >= 6 && n == need) {
        const uint8_t *d = buf + 6;
        if (buf[n - 4] == 0xF8 && buf[n - 1] == 0xF5 && d[1] == 0xAA) {
            uint8_t state = d[2];
            int det = d[9] | (d[10] << 8);
            s_dist = state ? det : -1;
            s_ld_last_ms = now_ms();
        }
        n = 0;
    }
}

static void sensors_task(void *arg)
{
    esp_task_wdt_add(NULL);
    s_bh_ok = bh_start();
    if (!s_bh_ok) ESP_LOGE(TAG, "BH1750 无应答");
    uint32_t last_lux = 0;
    uint8_t rx[64];
    for (;;) {
        esp_task_wdt_reset();
        int n = uart_read_bytes(LD_UART, rx, sizeof(rx), pdMS_TO_TICKS(20));
        for (int i = 0; i < n; i++) ld_parse_byte(rx[i]);
        if (now_ms() - last_lux >= (uint32_t)g_cfg.lux_ms) {
            last_lux = now_ms();
            bh_poll();
        }
    }
}

void sensors_init(void)
{
    gpio_config_t io = { .pin_bit_mask = 1ULL << PIN_LD2410_OUT, .mode = GPIO_MODE_INPUT, .pull_down_en = 1 };
    gpio_config(&io);
    uart_config_t uc = {
        .baud_rate = LD_BAUD, .data_bits = UART_DATA_8_BITS, .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1, .flow_ctrl = UART_HW_FLOWCTRL_DISABLE, .source_clk = UART_SCLK_DEFAULT,
    };
    uart_driver_install(LD_UART, 1024, 0, 0, NULL, 0);
    uart_param_config(LD_UART, &uc);
    uart_set_pin(LD_UART, PIN_LD2410_TX, PIN_LD2410_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    s_last_seen_ms = now_ms();
    s_ld_last_ms = now_ms();
    xTaskCreatePinnedToCore(sensors_task, "sensors", 4096, NULL, 5, NULL, 0);
}

void sensors_tick(void)
{
    uint32_t now = now_ms();
    if (gpio_get_level(PIN_LD2410_OUT)) s_last_seen_ms = now;
    bool p = (now - s_last_seen_ms) < (uint32_t)g_cfg.nobody_s * 1000u;
    if (p != s_present) {
        s_present = p;
        ESP_LOGI(TAG, "%s", p ? "有人" : "无人");
        proto_report("!PRES %d", p);
    }
    bool ld_ok = sens_ld2410_uart_ok();
    if (ld_ok != s_ld_ok_reported) {
        s_ld_ok_reported = ld_ok;
        if (!ld_ok) { evlog_add(EV_SENSOR_LOST, SENSOR_ID_LD2410); proto_report("!ERR LD2410 uart silent"); }
    }
}

int  sens_lux(void) { return s_lux; }
bool sens_present(void) { return s_present; }
int  sens_dist_cm(void) { return sens_ld2410_uart_ok() ? s_dist : -1; }
bool sens_bh1750_ok(void) { return s_bh_ok; }
bool sens_ld2410_uart_ok(void) { return now_ms() - s_ld_last_ms < LD_SILENT_MS; }
