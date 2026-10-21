// 天气（规格 F15 ④）：Open-Meteo 当前气温、湿度、天气代码。2 h 未更新视为无效。
#pragma once
#include <stdbool.h>

void weather_init(void);
// 有效（2 h 内取到过）时返回 true；t_x10 = 气温 ×10（°C），rh = 相对湿度 %，code = WMO 天气代码，age_s = 距今秒数
bool weather_get(int *t_x10, int *rh, int *code, int *age_s);
