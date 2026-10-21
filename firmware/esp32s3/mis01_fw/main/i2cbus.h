// I²C 总线（GPIO8/9，100 kHz）：BH1750 0x23、DS3231 0x68
#pragma once
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define I2C_ADDR_BH1750  0x23
#define I2C_ADDR_DS3231  0x68

bool i2cbus_init(void);
bool i2cbus_probe(uint8_t addr);
bool i2cbus_write(uint8_t addr, const uint8_t *d, size_t n);
bool i2cbus_read(uint8_t addr, uint8_t *d, size_t n);
bool i2cbus_write_read(uint8_t addr, const uint8_t *w, size_t wn, uint8_t *r, size_t rn);
