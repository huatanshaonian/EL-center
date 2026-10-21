// LEDC 定时器与通道分配（S3 低速模式共 4 个定时器、8 个通道）
#pragma once
#include "driver/ledc.h"

#define LEDC_MODE        LEDC_LOW_SPEED_MODE

#define LEDC_TMR_EYE     LEDC_TIMER_0   // 10 kHz，12 位
#define LEDC_TMR_METER   LEDC_TIMER_1   // 19.53 kHz，12 位（80 MHz / 4096；规格写 20 kHz，12 位时 APB 时钟最高到这里）
#define LEDC_TMR_BZ      LEDC_TIMER_2   // BZ_HZ，10 位
#define LEDC_TMR_FIL     LEDC_TIMER_3   // FIL_HZ，8 位

#define LEDC_CH_EYE_A    LEDC_CHANNEL_0
#define LEDC_CH_EYE_B    LEDC_CHANNEL_1
#define LEDC_CH_METER    LEDC_CHANNEL_2
#define LEDC_CH_BZ       LEDC_CHANNEL_3
#define LEDC_CH_FIL      LEDC_CHANNEL_4
