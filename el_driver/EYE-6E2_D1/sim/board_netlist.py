# EYE-6E2 D1 整板 ngspice 网表生成（按 EYE-6E2_D1.net 的网络名）
from em87_model import SUBCKT

Q3904 = (".model Q2N3904 NPN(IS=6.734f XTI=3 EG=1.11 VAF=74.03 BF=416.4 NE=1.259 ISE=6.734f IKF=66.78m "
         "XTB=1.5 BR=.7371 NC=2 ISC=0 IKR=0 RC=1 CJC=3.638p MJC=.3085 VJC=.75 FC=.5 CJE=4.493p MJE=.2593 "
         "VJE=.75 TR=239.5n TF=301.2p ITF=.4 VTF=4 XTF=2 RB=10)")

def gpio(ch, mode):
    """mode: 浮点 D(0..1) → PULSE；'float' 悬空；'pu45k'/'pd45k' 复位时弱上/下拉；
       ('pwl', [(t,D),...]) → 锯齿比较产生可变占空比"""
    n = f"GP_{ch}"
    if isinstance(mode, (int, float)):
        d = float(mode)
        if d <= 0:
            return f"VG{ch} {n}0 0 DC 0\nRO{ch} {n}0 {n} 30\n"
        if d >= 1:
            return f"VG{ch} {n}0 0 DC 3.3\nRO{ch} {n}0 {n} 30\n"
        return f"VG{ch} {n}0 0 PULSE(0 3.3 0 5n 5n {d*100:.6g}u 100u)\nRO{ch} {n}0 {n} 30\n"
    if mode == "float":
        return f"RO{ch} {n} 0 1e12\n"
    if mode == "pu45k":
        return f"VU{ch} U{ch} 0 DC 3.3\nRO{ch} U{ch} {n} 45k\n"
    if mode == "pd45k":
        return f"RO{ch} {n} 0 45k\n"
    if mode[0] == "pwl":
        pts = " ".join(f"{t} {d}" for t, d in mode[1])
        return (f"VSAW{ch} SAW{ch} 0 PULSE(0 1 0 99.98u 10n 1p 100u)\n"
                f"VDT{ch} DT{ch} 0 PWL({pts})\n"
                f"BPW{ch} {n}0 0 V = 1.65*(1+tanh((V(DT{ch})-V(SAW{ch}))/0.001))\n"
                f"RO{ch} {n}0 {n} 30\n")
    raise ValueError(mode)

def channel(ch, mode, rf="220k", cf="100n", rt="1m", rb="4.7k", rpu="4.7k"):
    return (gpio(ch, mode) +
            f"R_B{ch} GP_{ch} B_{ch} {rb}\nR_E{ch} B_{ch} 0 47k\nQ_{ch} C_{ch} B_{ch} 0 Q2N3904\n"
            f"R_P{ch} VK C_{ch} {rpu}\nR_F{ch} C_{ch} GF_{ch} {rf}\nC_F{ch} GF_{ch} VK {cf}\n"
            f"R_G{ch} GF_{ch} G_{ch} 47k\nCPG{ch} G_{ch} 0 2p\n"
            f"R_A{ch} HV AN_{ch} 100k\nCPA{ch} AN_{ch} 0 3p\n"
            f"VIT{ch} HV TX_{ch} DC 0\nR_T{ch} TX_{ch} T_{ch} {rt}\n"
            f"VIK{ch} K_{ch} VK DC 0\n"
            f"X{ch} AN_{ch} G_{ch} K_{ch} T_{ch} EM87\n")

def board(title, mode_a, mode_b, v12="DC 12", rline="0.25", vhv="DC 250", rhv="1.5",
          rk="10", ck="470u", extra="", fil=True, **chkw):
    """v12: 板上 +12V 的源（理想源 + rline 线阻）；vhv: HV-UNI 输出源（+ rhv 内阻）"""
    s = f"* {title}\n"
    s += f"VS12 S12S 0 {v12}\nRLINE S12S S12 {rline}\nC_12 S12 0 100n\n"
    s += f"R_K S12 VK {rk}\nC_K VK CKE {ck}\nRESR CKE 0 0.08\nC_K2 VK 0 100n\n"
    if fil:   # 两支灯丝热态，各 21 Ω（另有专门的冷启动网表）
        s += "RFILA S12 FMID 21\nRFILB FMID 0 21\n"
    s += f"VHVS HVS 0 {vhv}\nRHVI HVS HV {rhv}\nC_HV HV 0 100n\nR_BL1 HV BL 470k\nR_BL2 BL 0 470k\n"
    s += channel("A", mode_a, **chkw) + channel("B", mode_b, **chkw)
    s += extra
    s += SUBCKT + Q3904 + "\n.options reltol=1e-5 vntol=1e-7 abstol=1e-12 itl4=100\n.end\n"
    return s
