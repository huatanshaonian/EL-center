// 安全与自检（S1–S3、F14）：panic 钩子、关机钩子、复位原因、开机自检
#pragma once
#include <stdint.h>
#include <stdbool.h>

#define ST_FAIL_DS3231  (1u << 0)
#define ST_FAIL_BH1750  (1u << 1)
#define ST_FAIL_SPI     (1u << 2)
#define ST_FAIL_I2C     (1u << 3)

void safety_init(void);                   // 尽早调：注册关机钩子、记录复位原因
const char *safety_reset_reason_name(void);
uint32_t safety_selftest(bool spi_ok, bool i2c_ok);   // 打印自检结果到日志口，返回失败位图
void safety_report_selftest(void);        // CDC 连上后把自检失败项用 !ERR 报给 Pi
