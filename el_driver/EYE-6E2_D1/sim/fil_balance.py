# 灯丝串联稳态分压（钨丝 R=R0(T/300)^1.267，辐射散热，6.3 V/0.3 A 时 1400 K），可在偏高那支两端并联均衡电阻 Rp
import numpy as np
from scipy.optimize import brentq
KR = 1.89 / (1400 ** 4 - 300 ** 4)
def heater_i(v, r0, k=KR):
    """给定端电压 v，求热平衡电流"""
    T = brentq(lambda T: v * v / (r0 * (T / 300) ** 1.267) - k * (T ** 4 - 300 ** 4), 300.0001, 3000)
    return v / (r0 * (T / 300) ** 1.267)
def split(ra, rb, rp=None, vs=12.0, rline=0.25, ka=KR, kb=KR):
    def f(va):
        ia = heater_i(va, ra, ka) + (va / rp if rp else 0)
        vb = vs - va - ia * rline
        return ia - heater_i(vb, rb, kb)
    va = brentq(f, 0.5, 11.5)
    ia = heater_i(va, ra, ka) + (va / rp if rp else 0)
    return va, vs - va - ia * rline, ia
for lab, ra, rb in [("nominal", 2.98, 2.98), ("R+-7%", 2.98 * 1.07, 2.98 * 0.93), ("R+-3%", 2.98 * 1.03, 2.98 * 0.97)]:
    print(lab, [round(x, 3) for x in split(ra, rb)])
    for rp in [470, 220, 150, 120, 100]:
        print("   Rp", rp, [round(x, 3) for x in split(ra, rb, rp)], "P_Rp W", round(split(ra, rb, rp)[0] ** 2 / rp, 3))
