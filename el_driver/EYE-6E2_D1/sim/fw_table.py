# 固件查表：占空比 D ↔ Vgk ↔ 暗区 a（用整板仿真结果标定的解析式 + 管子模型）
import json
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
import em87_model as M

HERE = Path(__file__).resolve().parent
S = json.loads((HERE / "summary_steady.json").read_text(encoding="utf-8"))
pts = sorted((v["D"], v["Vgk_A"], v["VK"]) for k, v in S.items() if k.startswith("steady_"))
Ds = np.array([p[0] for p in pts]); Vs = np.array([p[1] for p in pts]); VKs = np.array([p[2] for p in pts])
VCS = 0.061          # 2N3904 饱和压降（D=100% 点反算）
R_F, R_P = 220e3, 4.7e3

def vgk_formula(d, ts):
    vk = np.interp(d, Ds, VKs)
    de = np.clip(d + ts * 1e4 * (d > 0), 0, 1)           # 存储时间把导通延长 ts
    f = de / (de + (1 - de) * R_F / (R_F + R_P))
    return -(vk - VCS) * f - 0.065 * np.exp(-np.abs(vk * f) / 0.15)   # 末项：零偏附近的栅流自偏

ts = brentq(lambda x: vgk_formula(0.5, x) - Vs[Ds == 0.5][0], 0, 2e-6)

def dark_of_vgk(vgk, hv=250.0, vk=11.95):
    i, va = M.op(vgk, vb=hv - vk)
    return float(M.dark_ratio(va, hv - vk))

if __name__ == "__main__":
    print(f"ts = {ts*1e6:.3f} us")
    print("D   Vgk_sim  Vgk_formula  err_mV")
    for d, v in zip(Ds, Vs):
        print(d, round(v, 4), round(float(vgk_formula(d, ts)), 4), round((float(vgk_formula(d, ts)) - v) * 1e3, 2))
    print("\n反查表：目标暗区 a(EM87 mm) → Vgk → D → 12 位 LEDC 计数")
    rows = []
    for a in [20.5, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, -0.5]:
        vg = brentq(lambda x: dark_of_vgk(x) - a, -15, 0)
        d = brentq(lambda x: float(vgk_formula(x, ts)) - vg, 0, 1)
        rows.append((a, vg, d))
        print(f"{a:5.1f}  {vg:7.3f}  {d*100:6.2f}%  {round(d*4095):5d}")
    # 灵敏度（mm/V，mm/%D）
    print("\n灵敏度")
    for d in [0.02, 0.1, 0.2, 0.4, 0.5, 0.6, 0.85]:
        v1 = float(vgk_formula(d - 0.005, ts)); v2 = float(vgk_formula(d + 0.005, ts))
        a1, a2 = dark_of_vgk(v1), dark_of_vgk(v2)
        print(d, "mm/V", round((a2 - a1) / (v2 - v1), 3), "mm/%D", round((a2 - a1) / 1.0, 3))
