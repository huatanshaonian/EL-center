// 595 链（辉光钟）与 MAX6921（IV-18）共用的 SPI 总线。
// 两者 DIN/CLK 并联：发一方的帧时另一方的移位寄存器也会被移入数据，但只要不动它的锁存脚就没有影响。
// 规格 7：同一互斥锁下发帧；发 595 帧不动 LOAD_6921，发 MAX6921 帧不动 LATCH_595；MAX6921 时钟 ≤ 5 MHz。
#pragma once
#include <stdint.h>
#include <stdbool.h>

bool spibus_init(void);

// IV-18 扫描任务用：短时间自旋抢锁，抢不到返回 false（这一位就不亮，安全）
bool spibus_try_lock_us(uint32_t max_wait_us);
void spibus_unlock(void);
// 已持锁时调用：发 20 位（bit n → OUTn，先发 bit19），再给 LOAD 一个脉冲
void spibus_send_6921_locked(uint32_t bits20);

// 辉光钟用：发 4 字节（先发 b[0]），再给 LATCH_595 上升沿。自己拿锁，返回 false = 总线忙超时
bool spibus_send_595(const uint8_t b[4]);
