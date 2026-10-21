// DS3231 驱动与本地时钟。
// 换秒：SQW 下降沿中断计一秒（F4 换秒对齐 RTC_SQW 下降沿）；秒脉冲丢失时退回 esp_timer 走时。
// 每 60 s 在秒中间读一次 DS3231 校正（避开换秒瞬间的歧义）。
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "rtc.h"
#include "i2cbus.h"
#include "evlog.h"
#include "pins.h"
#include "util.h"

static const char *TAG = "rtc";

static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;
static volatile uint32_t s_edge_cnt;      // ISR 计的下降沿数
static volatile uint32_t s_edge_ms;       // 最近一次下降沿时刻
static uint32_t s_edge_seen;              // 已处理的下降沿数
static uint32_t s_sec;                    // 本地时间秒
static uint32_t s_sec_ms;                 // 本秒开始时刻
static uint32_t s_sec_seq;
static bool s_valid, s_chip_ok;
static time_src_t s_src = TSRC_RTC;
static uint32_t s_last_sync_ms, s_last_temp_ms;
static volatile int s_temp_x10 = CLK_TEMP_NONE;
static TaskHandle_t s_notify_task;
static uint32_t s_notify_bit;

// ---------------- 日期换算（Howard Hinnant days_from_civil） ----------------
static int32_t days_from_civil(int y, int m, int d)
{
    y -= m <= 2;
    int era = (y >= 0 ? y : y - 399) / 400;
    int yoe = y - era * 400;
    int doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    int doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + doe - 719468;
}
#define DAYS_2000 10957   // days_from_civil(2000,1,1)

void clk_to_civil(uint32_t secs, civil_t *c)
{
    int32_t z = (int32_t)(secs / 86400) + DAYS_2000 + 719468;
    uint32_t sod = secs % 86400;
    int era = z / 146097;
    int doe = z - era * 146097;
    int yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    int y = yoe + era * 400;
    int doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    int mp = (5 * doy + 2) / 153;
    c->day = doy - (153 * mp + 2) / 5 + 1;
    c->mon = mp + (mp < 10 ? 3 : -9);
    c->year = y + (c->mon <= 2);
    c->hour = sod / 3600;
    c->min = (sod / 60) % 60;
    c->sec = sod % 60;
}

uint32_t clk_from_civil(const civil_t *c)
{
    int32_t days = days_from_civil(c->year, c->mon, c->day) - DAYS_2000;
    return (uint32_t)days * 86400u + c->hour * 3600 + c->min * 60 + c->sec;
}

void clk_format(uint32_t secs, char *out)
{
    civil_t c;
    clk_to_civil(secs, &c);
    snprintf(out, 20, "%04d-%02d-%02dT%02d:%02d:%02d", c.year, c.mon, c.day, c.hour, c.min, c.sec);
}

bool clk_parse(const char *s, uint32_t *secs)
{
    civil_t c;
    char t;
    if (sscanf(s, "%4d-%2d-%2d%c%2d:%2d:%2d", &c.year, &c.mon, &c.day, &t, &c.hour, &c.min, &c.sec) != 7) return false;
    if ((t != 'T' && t != 't' && t != ' ') || c.year < 2000 || c.year > 2099 || c.mon < 1 || c.mon > 12 || c.day < 1
        || c.hour > 23 || c.min > 59 || c.sec > 59) return false;
    static const uint8_t mdays[] = {31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    if (c.day > mdays[c.mon - 1]) return false;
    if (c.mon == 2 && c.day == 29 && (c.year % 4)) return false;
    *secs = clk_from_civil(&c);
    return true;
}

const char *clk_src_name(time_src_t s) { return s == TSRC_HOST ? "HOST" : (s == TSRC_NTP ? "NTP" : "RTC"); }

// ---------------- DS3231 ----------------
static void ds_read_temp(void)
{
    uint8_t reg = 0x11, r[2];
    if (!i2cbus_write_read(I2C_ADDR_DS3231, &reg, 1, r, 2)) { s_temp_x10 = CLK_TEMP_NONE; return; }
    int q = (int16_t)((r[0] << 8) | r[1]) >> 6;      // 单位 0.25 °C，带符号
    s_temp_x10 = (q * 25 + (q >= 0 ? 5 : -5)) / 10;
}

static uint8_t bcd2bin(uint8_t v) { return (v >> 4) * 10 + (v & 0xF); }
static uint8_t bin2bcd(int v) { return (uint8_t)(((v / 10) << 4) | (v % 10)); }

static bool ds_read_time(uint32_t *secs)
{
    uint8_t reg = 0, r[7];
    if (!i2cbus_write_read(I2C_ADDR_DS3231, &reg, 1, r, 7)) return false;
    civil_t c = {
        .sec = bcd2bin(r[0] & 0x7F), .min = bcd2bin(r[1] & 0x7F),
        .hour = (r[2] & 0x40) ? (bcd2bin(r[2] & 0x1F) % 12 + ((r[2] & 0x20) ? 12 : 0)) : bcd2bin(r[2] & 0x3F),
        .day = bcd2bin(r[4] & 0x3F), .mon = bcd2bin(r[5] & 0x1F), .year = 2000 + bcd2bin(r[6]),
    };
    if (c.mon < 1 || c.mon > 12 || c.day < 1 || c.day > 31 || c.hour > 23 || c.min > 59 || c.sec > 59) return false;
    *secs = clk_from_civil(&c);
    return true;
}

static bool ds_write_time(uint32_t secs)
{
    civil_t c;
    clk_to_civil(secs, &c);
    int dow = (int)((secs / 86400 + 6) % 7) + 1;   // 2000-01-01 是星期六；DS3231 星期 1..7，按 1 = 星期日
    uint8_t w[8] = {0x00, bin2bcd(c.sec), bin2bcd(c.min), bin2bcd(c.hour), (uint8_t)dow,
                    bin2bcd(c.day), bin2bcd(c.mon), bin2bcd(c.year - 2000)};
    if (!i2cbus_write(I2C_ADDR_DS3231, w, sizeof(w))) return false;
    uint8_t st[2] = {0x0F, 0x00};   // 清 OSF、关 32 kHz 输出
    return i2cbus_write(I2C_ADDR_DS3231, st, 2);
}

static void IRAM_ATTR sqw_isr(void *arg)
{
    s_edge_cnt++;
    s_edge_ms = (uint32_t)(esp_timer_get_time() / 1000);
    BaseType_t hp = pdFALSE;
    if (s_notify_task) xTaskNotifyFromISR(s_notify_task, s_notify_bit, eSetBits, &hp);
    if (hp) portYIELD_FROM_ISR();
}

void clk_init(TaskHandle_t task, uint32_t bit)
{
    s_notify_task = task;
    s_notify_bit = bit;
    s_sec_ms = now_ms();

    uint8_t reg = 0x0F, st = 0;
    s_chip_ok = i2cbus_write_read(I2C_ADDR_DS3231, &reg, 1, &st, 1);
    if (s_chip_ok) {
        uint8_t ctl[2] = {0x0E, 0x00};   // EOSC=0（电池也走时）、INTCN=0、RS=00 → SQW 1 Hz
        i2cbus_write(I2C_ADDR_DS3231, ctl, 2);
        uint32_t t;
        if (ds_read_time(&t)) s_sec = t;
        s_valid = !(st & 0x80);          // OSF = 1：曾经停振，时间无效
        if (!s_valid) evlog_add(EV_RTC_INVALID, st);
        ds_read_temp();
        ESP_LOGI(TAG, "DS3231 在线，OSF=%d，温度 %d.%d °C", (st >> 7) & 1, s_temp_x10 / 10, abs(s_temp_x10 % 10));
    } else {
        ESP_LOGE(TAG, "DS3231 无应答，时间无效");
        s_valid = false;
    }
    s_last_sync_ms = now_ms();

    gpio_config_t io = {
        .pin_bit_mask = 1ULL << PIN_RTC_SQW,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = 1,                 // 与底板 10 k 上拉同向
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    gpio_config(&io);
    gpio_isr_handler_add(PIN_RTC_SQW, sqw_isr, NULL);
    s_edge_seen = s_edge_cnt;
}

void clk_tick(void)
{
    uint32_t now = now_ms();
    uint32_t edges = s_edge_cnt, edge_ms = s_edge_ms;

    taskENTER_CRITICAL(&s_mux);
    if (edges != s_edge_seen) {
        s_sec += edges - s_edge_seen;
        s_sec_seq += edges - s_edge_seen;
        s_edge_seen = edges;
        s_sec_ms = edge_ms;
    } else if (now - s_sec_ms >= ((edges && now - edge_ms < 1500) ? 1500u : 1000u)) {
        // 秒脉冲丢了（1.5 s 没来）或根本没有：按本机定时器每 1 s 走一秒
        s_sec++;
        s_sec_seq++;
        s_sec_ms += 1000;
        if (now - s_sec_ms >= 1000) s_sec_ms = now;   // 落后太多不补
    }
    taskEXIT_CRITICAL(&s_mux);

    // 每 10 s 读一次温度（芯片每 64 s 才更新一次，读得勤也无妨）
    if (now - s_last_temp_ms >= 10000) {
        s_last_temp_ms = now;
        if (s_chip_ok) ds_read_temp();
    }

    // 每 60 s 在秒中间（约 400–700 ms）读一次 DS3231 校正
    uint32_t into = now - s_sec_ms;
    if (now - s_last_sync_ms >= 60000 && into >= 400 && into <= 700) {
        s_last_sync_ms = now;
        uint32_t t;
        bool ok = ds_read_time(&t);
        if (ok) {
            taskENTER_CRITICAL(&s_mux);
            if (t != s_sec) { s_sec = t; s_sec_seq++; }
            taskEXIT_CRITICAL(&s_mux);
        }
        if (ok != s_chip_ok) {
            s_chip_ok = ok;
            if (!ok) evlog_add(EV_SENSOR_LOST, 2);
        }
    }
}

uint32_t clk_now(void)
{
    taskENTER_CRITICAL(&s_mux);
    uint32_t v = s_sec;
    taskEXIT_CRITICAL(&s_mux);
    return v;
}

bool clk_time_valid(void) { return s_valid; }
int clk_temp_x10(void) { return s_temp_x10; }
bool clk_chip_ok(void) { return s_chip_ok; }
bool clk_sqw_ok(void) { return now_ms() - s_edge_ms < 1500; }
time_src_t clk_src(void) { return s_src; }
uint32_t clk_sec_seq(void) { return s_sec_seq; }
uint32_t clk_ms_into_second(void) { return now_ms() - s_sec_ms; }

bool clk_set_local(uint32_t secs, time_src_t src)
{
    bool ok = ds_write_time(secs);
    taskENTER_CRITICAL(&s_mux);
    s_sec = secs;
    s_sec_seq++;
    s_sec_ms = now_ms();          // 写秒寄存器会复位 DS3231 分频链，秒脉冲从现在重新计
    s_edge_seen = s_edge_cnt;
    taskEXIT_CRITICAL(&s_mux);
    s_valid = true;
    s_src = src;
    s_last_sync_ms = now_ms();
    if (ok) s_chip_ok = true;
    return ok;
}
