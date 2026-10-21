#include <stdbool.h>
#include "esp_system.h"
#include "esp_attr.h"
#include "esp_log.h"
#include "esp_chip_info.h"
#include "esp_rom_sys.h"
#include "driver/gpio.h"
#include "safety.h"
#include "hv.h"
#include "vfd.h"
#include "i2cbus.h"
#include "evlog.h"
#include "proto.h"
#include "pins.h"
#include "util.h"

static const char *TAG = "safety";
static uint32_t s_fail;

// panic（含任务看门狗、断言、异常）进入时先关高压和 IV-18，再走原 panic 流程（打印并复位）。
// 链接时用 -Wl,--wrap=esp_panic_handler（main/CMakeLists.txt）。
void __real_esp_panic_handler(void *info);
void IRAM_ATTR __wrap_esp_panic_handler(void *info)
{
    hv_emergency_off_isr();
    vfd_emergency_off_isr();
    esp_rom_printf("\n[MIS-01] panic: HV_EN=0, BLANK=1, IV18_PWR_EN=0\n");
    __real_esp_panic_handler(info);
}

// esp_restart（REBOOT 命令等）前同样先关
static void on_shutdown(void)
{
    hv_emergency_off_isr();
    vfd_emergency_off_isr();
}

const char *safety_reset_reason_name(void)
{
    switch (esp_reset_reason()) {
    case ESP_RST_INT_WDT:
    case ESP_RST_TASK_WDT:
    case ESP_RST_WDT:       return "WDT";
    case ESP_RST_PANIC:
    case ESP_RST_CPU_LOCKUP: return "PANIC";
    case ESP_RST_SW:
    case ESP_RST_USB:
    case ESP_RST_JTAG:      return "SW";
    case ESP_RST_BROWNOUT:  return "BROWNOUT";
    default:                return "POWERON";
    }
}

void safety_init(void)
{
    esp_register_shutdown_handler(on_shutdown);
    esp_reset_reason_t r = esp_reset_reason();
    evlog_add(EV_BOOT, r);
    switch (r) {
    case ESP_RST_INT_WDT: case ESP_RST_TASK_WDT: case ESP_RST_WDT: evlog_add(EV_WDT_RESET, r); break;
    case ESP_RST_PANIC: case ESP_RST_CPU_LOCKUP: evlog_add(EV_PANIC_RESET, r); break;
    case ESP_RST_BROWNOUT: evlog_add(EV_BROWNOUT, r); break;
    default: break;
    }
}

uint32_t safety_selftest(bool spi_ok, bool i2c_ok)
{
    esp_chip_info_t ci;
    esp_chip_info(&ci);
    ESP_LOGI(TAG, "MIS-01 仪器层固件 %s（规格 v%s，编译 %s %s）", FW_VERSION, FW_SPEC, __DATE__, __TIME__);
    ESP_LOGI(TAG, "芯片 ESP32-S3 rev %d.%d，%d 核；复位原因 %s（%d）", ci.revision / 100, ci.revision % 100, ci.cores,
             safety_reset_reason_name(), esp_reset_reason());
    ESP_LOGI(TAG, "输入脚：ST_HOST=%d ST_HV=%d ST_SCR=%d PFAIL_N=%d PI_RUN=%d RTC_SQW=%d GEIGER_IN=%d LD2410_OUT=%d",
             gpio_get_level(PIN_ST_HOST), gpio_get_level(PIN_ST_HV), gpio_get_level(PIN_ST_SCR),
             gpio_get_level(PIN_PFAIL_N), gpio_get_level(PIN_PI_RUN), gpio_get_level(PIN_RTC_SQW),
             gpio_get_level(PIN_GEIGER_IN), gpio_get_level(PIN_LD2410_OUT));
    s_fail = 0;
    if (!spi_ok) s_fail |= ST_FAIL_SPI;
    if (!i2c_ok) s_fail |= ST_FAIL_I2C;
    bool ds = i2c_ok && i2cbus_probe(I2C_ADDR_DS3231);
    bool bh = i2c_ok && i2cbus_probe(I2C_ADDR_BH1750);
    if (!ds) s_fail |= ST_FAIL_DS3231;
    if (!bh) s_fail |= ST_FAIL_BH1750;
    ESP_LOGI(TAG, "I²C：DS3231(0x68)=%s BH1750(0x23)=%s；SPI=%s", ds ? "在" : "无", bh ? "在" : "无", spi_ok ? "OK" : "失败");
    if (s_fail) {
        evlog_add(EV_SELFTEST_FAIL, (int32_t)s_fail);
        ESP_LOGW(TAG, "自检失败项位图 0x%02lx", (unsigned long)s_fail);
    }
    return s_fail;
}

void safety_report_selftest(void)
{
    if (s_fail & ST_FAIL_SPI) proto_report("!ERR selftest SPI init failed");
    if (s_fail & ST_FAIL_I2C) proto_report("!ERR selftest I2C init failed");
    if (s_fail & ST_FAIL_DS3231) proto_report("!ERR selftest DS3231 not found");
    if (s_fail & ST_FAIL_BH1750) proto_report("!ERR selftest BH1750 not found");
}
