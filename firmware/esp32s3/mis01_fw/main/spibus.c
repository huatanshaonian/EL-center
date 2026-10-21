// 共用 SPI 总线实现：SPI2，模式 0，MSB 先发，4 MHz，无片选
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_rom_sys.h"
#include "esp_log.h"
#include "spibus.h"
#include "pins.h"

static const char *TAG = "spibus";
static spi_device_handle_t s_dev;
static SemaphoreHandle_t s_mtx;

#define SPI_CLK_HZ  4000000

bool spibus_init(void)
{
    s_mtx = xSemaphoreCreateMutex();
    gpio_config_t io = {
        .pin_bit_mask = (1ULL << PIN_LATCH_595) | (1ULL << PIN_LOAD_6921),
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_set_level(PIN_LATCH_595, 0);
    gpio_set_level(PIN_LOAD_6921, 0);
    gpio_config(&io);

    spi_bus_config_t bus = {
        .mosi_io_num = PIN_SPI_SDO,
        .miso_io_num = -1,
        .sclk_io_num = PIN_SPI_SCK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 8,
    };
    if (spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_DISABLED) != ESP_OK) { ESP_LOGE(TAG, "总线初始化失败"); return false; }
    spi_device_interface_config_t dev = {
        .mode = 0,
        .clock_speed_hz = SPI_CLK_HZ,
        .spics_io_num = -1,
        .queue_size = 1,
    };
    if (spi_bus_add_device(SPI2_HOST, &dev, &s_dev) != ESP_OK) { ESP_LOGE(TAG, "加设备失败"); return false; }
    return true;
}

bool spibus_try_lock_us(uint32_t max_wait_us)
{
    for (uint32_t t = 0;; t += 5) {
        if (xSemaphoreTake(s_mtx, 0) == pdTRUE) return true;
        if (t >= max_wait_us) return false;
        esp_rom_delay_us(5);
    }
}

void spibus_unlock(void) { xSemaphoreGive(s_mtx); }

static void tx_bits(const uint8_t *d, int nbits)
{
    spi_transaction_t t = {
        .flags = SPI_TRANS_USE_TXDATA,
        .length = nbits,
    };
    for (int i = 0; i < 4; i++) t.tx_data[i] = d[i];
    spi_device_polling_transmit(s_dev, &t);
}

void spibus_send_6921_locked(uint32_t bits20)
{
    // 左对齐到 24 位：第一个发出的位 = bit19（进 OUT19），最后一位 = bit0（OUT0）
    uint32_t v = (bits20 & 0xFFFFF) << 4;
    uint8_t d[4] = {(uint8_t)(v >> 16), (uint8_t)(v >> 8), (uint8_t)v, 0};
    tx_bits(d, 20);
    // LOAD 平时为低；正脉冲 ≥ 55 ns：高电平透明、下降沿锁存（MAX6921 规格书正文）
    gpio_set_level(PIN_LOAD_6921, 1);
    esp_rom_delay_us(1);
    gpio_set_level(PIN_LOAD_6921, 0);
}

bool spibus_send_595(const uint8_t b[4])
{
    if (xSemaphoreTake(s_mtx, pdMS_TO_TICKS(5)) != pdTRUE) return false;
    tx_bits(b, 32);
    gpio_set_level(PIN_LATCH_595, 1);
    esp_rom_delay_us(1);
    gpio_set_level(PIN_LATCH_595, 0);
    xSemaphoreGive(s_mtx);
    return true;
}
