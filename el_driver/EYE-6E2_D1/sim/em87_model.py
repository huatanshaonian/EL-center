# EM87 / 北京 6E2 行为模型 + 暗区换算
# 三极管部分：两段 Koren 并联（变 μ / 远截止），x=1.4、kvb=300 固定，
#   拟合原厂工作点表（Vb=250 V、Ra=100 kΩ：Vg 0/−10/−15 V → Ia+D 2.0/0.5/0.2 mA），三点误差 < 1e-7。
# 荧光屏：It = (0.8074 + 3.4815e-3·Vdk + 7.407e-6·Vdk²) mA × (Vtk/250)^1.5，
#   过原厂三点 (Vdk 50/200/230 V → 1.0/1.8/2.0 mA)。
# 栅流：接触电位 0.7 V + 二极管（n·Vt ≈ 0.09 V，Vgk=0 时约 0.5 µA，RS 2 kΩ）。
import numpy as np
from scipy.optimize import brentq

MU1, MU2, KP, KGA, KGB, EX, KVB = 30.0, 8.0, 85.4989909, 1071.77158, 329315.841, 1.4, 300.0
IT_A, IT_B, IT_C = 0.807407407, 3.48148148e-3, 7.40740741e-6   # mA, mA/V, mA/V²

SUBCKT = f"""
.subckt EM87 A G K T
B1 A K I = {{ pwr(max(V(A,K)/{KP}*ln(1+exp({KP}*(1/{MU1}+V(G,K)/sqrt({KVB}+V(A,K)*V(A,K))))),0),{EX})/{KGA}
+ + pwr(max(V(A,K)/{KP}*ln(1+exp({KP}*(1/{MU2}+V(G,K)/sqrt({KVB}+V(A,K)*V(A,K))))),0),{EX})/{KGB} }}
B2 T K I = {{ 1e-3*({IT_A}+{IT_B}*max(V(A,K),0)+{IT_C}*max(V(A,K),0)*max(V(A,K),0))*pwr(max(V(T,K),0)/250,1.5) }}
VCP GX G DC 0.7
DGK GX K DGRID
CGK G K 2.5p
CGA G A 1.7p
CAK A K 3p
CTK T K 2p
.model DGRID D(IS=2.09e-10 N=3.48 RS=2k)
.ends EM87
"""

def ia(va, vg):
    va = np.asarray(va, float)
    def k(mu, kg):
        e1 = va / KP * np.log1p(np.exp(KP * (1 / mu + vg / np.sqrt(KVB + va * va))))
        return np.maximum(e1, 0) ** EX / kg
    return k(MU1, KGA) + k(MU2, KGB)

def it(vdk, vtk):
    vdk = max(vdk, 0)
    return 1e-3 * (IT_A + IT_B * vdk + IT_C * vdk * vdk) * (max(vtk, 0) / 250) ** 1.5

def op(vg, vb=250.0, ra=100e3):
    i = brentq(lambda x: x - ia(vb - x * ra, vg), 0, vb / ra)
    return i, vb - i * ra

# 调研_6E2.txt 第 3 节：栅压—暗区读数（Vb=250、Ra=100k、屏不串电阻），EM87 屏长 32.6 mm
VG_TAB = np.array([0, -1, -2, -3, -4, -5, -6, -7, -8, -10, -15.])
A_TAB = np.array([21, 17, 14, 11, 8, 6, 4, 2.5, 1.5, 0, -1.5])

def dark_vgk(vgk):
    """直接按 Vgk 查表（线性插值；超出 −15 V 外推，>0 按 0 V 处理）"""
    v = np.clip(np.asarray(vgk, float), -20, 0)
    return np.interp(-v, -VG_TAB, A_TAB)

# 比值换算：静电偏转无空间电荷时电子轨迹只取决于电极电压之比，暗区 a = f(Vdk/Vtk)。
# 用模型把读数表的 Vg 换成原厂条件下的 Va，得到 r = Va/250 → a。
R_TAB = np.array([op(v)[1] / 250 for v in VG_TAB])

def dark_ratio(vdk, vtk):
    r = np.asarray(vdk, float) / np.asarray(vtk, float)
    a = np.interp(r, R_TAB, A_TAB)
    slope = (A_TAB[-1] - A_TAB[-2]) / (R_TAB[-1] - R_TAB[-2])   # 超过 −15 V 点按最后一段线性外推
    return np.where(r > R_TAB[-1], A_TAB[-1] + slope * (r - R_TAB[-1]), a)

if __name__ == "__main__":
    print("Vg  Ia(mA)  Va  r  a")
    for v, r, a in zip(VG_TAB, R_TAB, A_TAB):
        i, va = op(v)
        print(v, round(i * 1e3, 3), round(va, 1), round(r, 3), a)
    # 校验：荧光屏串 33 k（原厂：0 V 暗区约 17.5 mm，−6.5~−7.5 V 闭合）
    for v in [0, -2, -4, -5, -6, -6.5, -7, -7.5, -8, -10, -15]:
        i, va = op(v)
        vt = brentq(lambda x: 250 - x - 33e3 * it(va, x), 1, 250)
        print("RT33k", v, round(va, 1), round(vt, 1), round(float(dark_ratio(va, vt)), 2))
