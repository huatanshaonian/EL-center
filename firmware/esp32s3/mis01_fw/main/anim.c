#include "freertos/FreeRTOS.h"
#include "anim.h"
#include "util.h"

#define PENDING_MAX_MS 120000  // 两分钟内没机会播（如夜间高压不开）就作废

static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;
static bool s_pending[ANIM_COUNT];
static uint32_t s_req_ms;

void anim_boot_request(void)
{
    taskENTER_CRITICAL(&s_mux);
    for (int i = 0; i < ANIM_COUNT; i++) s_pending[i] = true;
    s_req_ms = now_ms();
    taskEXIT_CRITICAL(&s_mux);
}

bool anim_take(anim_item_t it)
{
    bool r;
    taskENTER_CRITICAL(&s_mux);
    if (s_pending[it] && now_ms() - s_req_ms > PENDING_MAX_MS) s_pending[it] = false;
    r = s_pending[it];
    s_pending[it] = false;
    taskEXIT_CRITICAL(&s_mux);
    return r;
}
