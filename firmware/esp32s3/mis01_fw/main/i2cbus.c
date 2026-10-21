// I²C 总线封装：新版 i2c_master 驱动，自带互斥，再按地址缓存设备句柄
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "driver/i2c_master.h"
#include "esp_log.h"
#include "i2cbus.h"
#include "pins.h"

static const char *TAG = "i2c";
static i2c_master_bus_handle_t s_bus;
static SemaphoreHandle_t s_mtx;

#define MAX_DEV 4
static struct { uint8_t addr; i2c_master_dev_handle_t h; } s_devs[MAX_DEV];
#define I2C_TIMEOUT_MS 20

bool i2cbus_init(void)
{
    s_mtx = xSemaphoreCreateMutex();
    i2c_master_bus_config_t cfg = {
        .i2c_port = I2C_NUM_0,
        .sda_io_num = PIN_I2C_SDA,
        .scl_io_num = PIN_I2C_SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = false,   // 底板 4.7 k 上拉
    };
    if (i2c_new_master_bus(&cfg, &s_bus) != ESP_OK) { ESP_LOGE(TAG, "总线初始化失败"); return false; }
    return true;
}

static i2c_master_dev_handle_t dev(uint8_t addr)
{
    for (int i = 0; i < MAX_DEV; i++) if (s_devs[i].h && s_devs[i].addr == addr) return s_devs[i].h;
    for (int i = 0; i < MAX_DEV; i++) {
        if (s_devs[i].h) continue;
        i2c_device_config_t dc = {
            .dev_addr_length = I2C_ADDR_BIT_LEN_7,
            .device_address = addr,
            .scl_speed_hz = 100000,
        };
        if (i2c_master_bus_add_device(s_bus, &dc, &s_devs[i].h) != ESP_OK) return NULL;
        s_devs[i].addr = addr;
        return s_devs[i].h;
    }
    return NULL;
}

bool i2cbus_probe(uint8_t addr)
{
    if (!s_bus) return false;
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    bool ok = i2c_master_probe(s_bus, addr, I2C_TIMEOUT_MS) == ESP_OK;
    xSemaphoreGive(s_mtx);
    return ok;
}

bool i2cbus_write(uint8_t addr, const uint8_t *d, size_t n)
{
    if (!s_bus) return false;
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    i2c_master_dev_handle_t h = dev(addr);
    bool ok = h && i2c_master_transmit(h, d, n, I2C_TIMEOUT_MS) == ESP_OK;
    xSemaphoreGive(s_mtx);
    return ok;
}

bool i2cbus_read(uint8_t addr, uint8_t *d, size_t n)
{
    if (!s_bus) return false;
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    i2c_master_dev_handle_t h = dev(addr);
    bool ok = h && i2c_master_receive(h, d, n, I2C_TIMEOUT_MS) == ESP_OK;
    xSemaphoreGive(s_mtx);
    return ok;
}

bool i2cbus_write_read(uint8_t addr, const uint8_t *w, size_t wn, uint8_t *r, size_t rn)
{
    if (!s_bus) return false;
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    i2c_master_dev_handle_t h = dev(addr);
    bool ok = h && i2c_master_transmit_receive(h, w, wn, r, rn, I2C_TIMEOUT_MS) == ESP_OK;
    xSemaphoreGive(s_mtx);
    return ok;
}
