// 与 Orange Pi 的通信协议（规格第 6 节）：ASCII 行协议，经 USB CDC。
// proto.c 负责收发、拆字段；proto_cmds.c 负责执行命令。
#pragma once
#include <stdbool.h>

#define PROTO_MAX_ARGS 16

typedef struct {
    int   argc;
    char *argv[PROTO_MAX_ARGS];
    bool  quoted[PROTO_MAX_ARGS];
    int   t_s;          // T=<秒>，没给为 0
} proto_cmd_t;

void proto_init(void);
// 发一行（自动补 \n）。主动上报以 "!" 开头、日志以 "#" 开头、应答以 OK/ERR 开头。任何任务都可调用（队列满时最多等 20 ms），不能在中断里调
void proto_send(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
#define proto_report proto_send

// proto_cmds.c
void proto_exec(proto_cmd_t *c);
bool proto_diag_exec(proto_cmd_t *c);   // 弱符号，测试固件覆盖
