# 荧光屏串联电阻 R_T 与高压对闭合点的影响（阴极 12 V 抬高，Vb_eff = HV − 12）
import numpy as np
from scipy.optimize import brentq
import em87_model as M
def point(vgk, hv=250., vk=12., rt=0.):
    vb = hv - vk
    i, va = M.op(vgk, vb=vb)
    vt = brentq(lambda x: vb - x - rt * M.it(va, x), 1, vb) if rt > 0 else vb
    return va, vt, float(M.dark_ratio(va, vt)), i, M.it(va, vt)
def closure(**kw):
    return brentq(lambda v: point(v, **kw)[2], -20, 0)
print("case  a(0V)  a(-6) a(-10) a(-11.9)  closure_V  Ik(0V)mA")
for hv, rt in [(250,0),(262,0),(240,0),(230,0),(250,10e3),(250,22e3),(250,33e3),(250,47e3)]:
    a=[point(v,hv=hv,rt=rt)[2] for v in (0,-6,-10,-11.9)]
    va,vt,_,i,itt=point(0,hv=hv,rt=rt)
    print(f"HV{hv} RT{rt/1e3:.0f}k", [round(x,2) for x in a], round(closure(hv=hv,rt=rt),2), round((i+itt)*1e3,2), "Vtk0",round(vt,1))
