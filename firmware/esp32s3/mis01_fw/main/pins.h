// 引脚分配：与《ESP32-S3功能规格.txt》第 1 节逐条一致，改这里必须先改规格。
#pragma once

#define PIN_ST_HOST       1   // 入  "主机"钮子
#define PIN_ST_HV         2   // 入  "高压"钮子
#define PIN_RTC_SQW       3   // 入  DS3231 1 Hz 秒脉冲（开漏，底板 10 k 上拉）
#define PIN_ST_SCR        4   // 入  "屏幕"钮子（只读）
#define PIN_PFAIL_N       5   // 入  24 V 掉电预警，低有效
#define PIN_HOLD          6   // 出  保持主机电源（PCB-3 100 k 下拉）
#define PIN_HV_EN         7   // 出  高压使能（PCB-3 100 k 下拉）
#define PIN_I2C_SDA       8
#define PIN_I2C_SCL       9
#define PIN_LATCH_595     10  // 出  74HCT595 锁存
#define PIN_SPI_SDO       11  // 出  595 链与 MAX6921 共用
#define PIN_SPI_SCK       12
#define PIN_LOAD_6921     13  // 出  MAX6921 锁存
#define PIN_BLANK_6921    14  // 出  MAX6921 消隐（板上上拉 = 全灭）
#define PIN_PI_RUN        15  // 入  高 = Pi 在运行（底板 100 k 下拉）
#define PIN_GEIGER_IN     16  // 入  盖革脉冲，低有效（PCNT）
#define PIN_METER_PWM     17  // 出  指针表头
#define PIN_BZ            18  // 出  盖革板蜂鸣器单线控制
#define PIN_PI_SHDN_REQ   21  // 出  开漏，拉低 = 请 Pi 关机
#define PIN_E2_A          39  // 出  6E2 A 栅压 PWM
#define PIN_E2_B          40  // 出  6E2 B 栅压 PWM
#define PIN_LD2410_OUT    41  // 入  高 = 有人
#define PIN_LD2410_TX     42  // 出  ESP TX → LD2410 RX
#define PIN_LD2410_RX     47  // 入  ESP RX ← LD2410 TX
#define PIN_IV18_PWR_EN   46  // 出  XL6009 + 灯丝电源（底板 10 k 下拉）
#define PIN_IV18_FIL      48  // 出  灯丝 H 桥方波
#define PIN_STATUS_LED    38  // 板载 WS2812B（初版未用）

// 钮子读回极性（PCB-3 网表已核，规格 v0.9.2 第 1 节）。协议里统一按"功能开 = 1"上报。
#define SW_ACTIVE_LEVEL   0   // 主机、高压钮子：低 = 钮子合上 = 开
#define SCR_ON_LEVEL      1   // 屏幕钮子：拨下闭合 = 低 = 关屏，所以高 = 屏亮
