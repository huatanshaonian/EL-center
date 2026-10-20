# 盖革板仿真网表生成器：按 GEIGER-MAIN_D1.net / GEIGER-CLIP_D1.net 的网络名生成 .cir
# 节点名与原理图网络名一致（小写）：hv swg em ev qb o1 tr da rst cv1 fbn fb0 refp vr4 tpv / an ck b2 b5 gm pq pulse
from pathlib import Path
import random
SIM = Path(__file__).resolve().parent
LIB = (SIM / 'models.lib').as_posix()


def hv_main(o):
    """高压部分（U1/Q1/L1/D1/C1/Q3/闭环/测试链）。o: dict 参数"""
    vr1 = o.get('vr1', 10.0)
    cp = o.get('cp', 25e-12)        # 开关节点总寄生电容（电感自容为主）
    rp = o.get('rp', 1e6)           # 电感并联损耗等效
    L = []
    a = L.append
    # 5V_HV 来自 PCB-3 HV-C：理想源 + 0.3 Ω（PTC + P-MOS），可在 t_off 断开
    v5 = o.get('v5hv', 5.0)
    if 'v5pwl' in o:
        a(f"VHVC hvc 0 PWL({o['v5pwl']})")
    else:
        a(f"VHVC hvc 0 PWL(0 0 {o.get('t_on',100e-6)} {v5})")
    a("RHVC hvc hvs 0.3")
    if 't_off' in o:
        a(f"VOFF ctl 0 PWL(0 1 {o['t_off']} 1 {o['t_off']+1e-6} 0)")
        a("SHVC hvs v5hv ctl 0 SWX")
    else:
        a("RHVS hvs v5hv 1m")
    a("C10 v5hv c10x 100u")
    a("RC10 c10x 0 0.3")
    a("C11 v5hv 0 100n")
    # U1 TLC555：GND TRIG OUT RESET CV THRES DISCH VDD
    a(f"XU1 0 tr o1 rst cv1 0 qb v5hv TLC555B params: VRST={o.get('vrst1',1.1)}")
    a("C15 cv1 0 100n")
    a("R1 v5hv rst 100k")
    a("R5 o1 da 1k")
    a("D2 da tr D1N4148")
    a("C3 tr 0 1n")
    a("R9 tr 0 220k")
    a("R6 o1 qb 1k")
    a("Q1 swg qb em KSP44")
    a("DQ1BV em swg DKSPBV")
    a("R8 em ev 15")
    if vr1 > 0:
        a(f"RVR1 ev 0 {vr1}")
    else:
        a("RVR1 ev 0 1m")
    a("Q3 rst em 0 Q2N3904")
    # L1 10 mH，DCR 30 Ω，寄生电容 cp，并联损耗 rp
    a("L1 v5hv lx 10m")
    a("RL1 lx swg 30")
    a(f"CP1 v5hv swg {cp}")
    a(f"RP1 v5hv swg {rp}")
    a("D1 swg hv UF4007")
    a("C1 hv 0 10n")
    a("RC1LK hv 0 100G")
    # 闭环：100 MΩ / (560k + VR2)，C30 1 nF
    a("R30_39 hv fbn 100Meg")
    a("CR30 hv fbn 0.05p")
    a(f"R40 fbn fb0 {o.get('r40','560k')}")
    if o.get('fb_half'):
        a("R44 refp 0 100k")
    a(f"RVR2 fb0 0 {o.get('vr2', 67.7e3)}")
    a("C30 fbn 0 1n")
    if o.get('closed', True):
        a(f"XU2 refp fbn rst v5hv 0 {o.get('lm393','LM393B')}")
    a("R41 v5hv vr4 2.2k")
    a("XU3 vr4 0 TL431B")
    a("R42 vr4 refp 100k")
    a("R43 rst refp 10Meg")
    a("CREFP refp 0 2p")
    # 测试链 9×10 MΩ → TP1；万用表 10 MΩ（可选）
    a("R50_58 hv tpv 90Meg")
    a(f"RMETER tpv 0 {o.get('rmeter', 1e15)}")
    # 版图寄生：开关节点 → 反馈分压点
    if o.get('c_sw_fb', 0) > 0:
        a(f"CSWFB swg fbn {o['c_sw_fb']}")
    return L


def tube_pwl(times, q=1e-9, trise=1e-6, tdec=30e-6, dt_on=None):
    """管子放电电流（单位 µA，作为电压源 vshape 的值）：1-exp 上升 + 指数衰减，电荷 q"""
    # 波形 i(t)=I0*(1-exp(-t/tr))*exp(-t/td)，电荷 = I0*(td - td*tr/(tr+td))... 数值积分归一
    import math
    n = 40
    tot = 6 * tdec
    ts = [tot * (k / n) ** 2 for k in range(n + 1)]
    sh = [(1 - math.exp(-t / trise)) * math.exp(-t / tdec) for t in ts]
    area = sum((sh[k] + sh[k + 1]) / 2 * (ts[k + 1] - ts[k]) for k in range(n))
    I0 = q / area
    pts = [(0.0, 0.0)]
    for t0 in times:
        if t0 < pts[-1][0] + 1e-9:
            continue
        pts.append((t0, 0.0))
        for t, s in zip(ts[1:], sh[1:]):
            pts.append((t0 + t, I0 * s * 1e6))
        pts.append((t0 + tot + 1e-7, 0.0))
    return ' '.join(f"{t:.12g} {v:.6g}" for t, v in pts)


def clip(o):
    """夹子长板 + 3 芯线到主板 + PULSE 到 ESP 底板；o['hv_node'] 为高压来源节点"""
    L = []
    a = L.append
    hv = o.get('hv_node', 'hv')
    # 400 V 线：主板 J_HV → 长板 J_HVI（120 mm 耐压线）
    a(f"RWHV {hv} hvin 0.1")
    # 长板地与主板地之间的线（120 mm）
    a("RWG 0 gcw 0.05")
    a("LWG gcw gc 150n")
    a("R2 hvin an 4.7Meg")
    a("CAN an gc 3p")          # 阳极 + 夹子 + 焊盘对地
    a("CAK an ck 1.5p")        # 管子阳极-阴极电容（估）
    # 管子：放电电流 = vshape(µA)，阳-阴压降低于 50 V 时按比例截止（防止电流源把阳极拉成负压）
    a(f"VSHAPE shp 0 PWL({o.get('tube_pwl', '0 0 1 0')})")
    a("BTUBE an ck I={ V(shp)*1e-6*( V(an,ck)>50 ? 1 : max(V(an,ck),0)/50 ) }")
    a(f"C2 ck gc {o.get('c2','220p')}")
    a(f"R4 ck b2 {o.get('r4','22k')}")
    a(f"R7 b2 gc {o.get('r7','100k')}")
    a("Q2 gmc b2 gc Q2N3904")
    a(f"R60 ck b5 {o.get('r60','22k')}")
    a(f"R61 b5 gc {o.get('r61','100k')}")
    a("Q5 pq b5 gc Q2N3904")
    a("R62 pq pulc 100")
    # 3 芯线 GM / PULSE（120 mm，单线对地 5 pF，串 150 nH）
    a("LWGM gmc gmw 150n")
    a("RWGM gmw gm 0.1")
    a("CWGM1 gmc 0 2.5p")
    a("CWGM2 gm 0 2.5p")
    a("LWPU pulc pulw 150n")
    a("RWPU pulw pulm 0.1")
    a("CWPU1 pulc 0 2.5p")
    a("CWPU2 pulm 0 2.5p")
    # 主板 J3→J2→ESP 底板（再按 300 mm 线：30 pF 对地），ESP 底板 10 k 上拉到 3.3 V，GPIO 输入 5 pF
    a("RWPE pulm pulse 0.2")
    a("CWPE pulse 0 30p")
    a("V33 v33 0 3.3")
    a("RPUESP v33 pulse 10k")
    a("CGPIO pulse 0 5p")
    # 主板 GM 上拉 R3 10 k 到 5 V 常电
    a("R3 v5 gm 10k")
    a(f"CGMIN gm 0 {o.get('c_gm','5p')}")
    # 400 V 线与 GM/PULSE 线并行的线间电容（可选）
    if o.get('c_hv_gm', 0) > 0:
        a(f"CHVGM hvin gmc {o['c_hv_gm']}")
    if o.get('c_hv_pu', 0) > 0:
        a(f"CHVPU hvin pulc {o['c_hv_pu']}")
    if o.get('c_sw_gm', 0) > 0:
        a(f"CSWGM swg gm {o['c_sw_gm']}")
    return L


def click(o):
    """5 V 常电 + U4 单稳 + Q6 + 蜂鸣器 + BZ 单线"""
    L = []
    a = L.append
    a(f"V5 v5s 0 {o.get('v5', 5.0)}")
    a("RV5 v5s v5 0.2")
    a("C12 v5 0 47u")
    a("C13 v5 0 100n")
    a(f"XU4 0 gm o4 en cv4 mt mt v5 TLC555B params: VRST={o.get('vrst4',1.1)}")
    a("C73 cv4 0 100n")
    a("R70 v5 mt 10k")
    a("C70 mt 0 100n")
    a("R75 o4 qb6 2.2k")
    a("R76 qb6 0 10k")
    a("Q6 bzn qb6 0 S8050")
    if o.get('buzzer', 'piezo') == 'piezo':
        # PS1740P02E：BVD 模型 C0 16 nF + 动态支路（4 kHz，Q≈20）；动态支路电流 = 声输出的相对量
        a("CLS0 v5 bzn 16n")
        a("LLSm v5 lsm1 0.99")
        a("CLSm lsm1 lsm2 1.6n")
        a("RLSm lsm2 lsm2x 1244")
        a("VLSm lsm2x bzn 0")
        a("R77 v5 bzn 1k")
    else:
        # YS-MBZ12085C05R42 电磁式：42 Ω + 估 3 mH，D4 续流
        a("RLS2 v5 ls2x 42")
        a("LLS2 ls2x bzn 3m")
        a("D4 bzn v5 D1N4148")
    # BZ 单线
    a("R71 bz bzp 1k")
    a("R72 bzp 0 100k")
    a("R73 bzp en 100k")
    a("C71 en 0 1u")
    if o.get('en_diode'):
        # 可选改法：R73 并肖特基（阳极 EN、阴极 BZP），BZ 一变低 EN 立即放电
        a("DEN en bzp DBAT43")
        a(".model DBAT43 D(Is=5e-8 N=1.05 Rs=1 Cjo=10p BV=30 IBV=1u)")
    if o.get('c71_leak', 0) > 0:
        a(f"IC71LK en 0 {o['c71_leak']}")
    if o.get('ac_swap'):
        # 改法：BZ → R74 → C72 → Q6 基极，D3 钳在基极；ESP 引脚电流被 R74 限住
        a(f"R74 bz acx {o.get('r74','2.2k')}")
        a(f"C72 acx qb6 {o.get('c72','100n')}")
        a("D3 0 qb6 D1N4148")
        a("RACD ac 0 1G")
    else:
        a(f"C72 bz ac {o.get('c72','100n')}")
        a("D3 0 ac D1N4148")
        a(f"R74 ac qb6 {o.get('r74','2.2k')}")
    # ESP 侧：GPIO（推挽 30 Ω）或高阻 + 底板跳线 10 k 上拉/下拉
    bz = o.get('bz', 'none')
    if bz == 'pwl':
        a(f"VBZ bzd 0 PWL({o['bz_pwl']})")
        a("RBZ bzd bz 30")
    elif bz == 'hiz_pu':
        a("V33B v33b 0 3.3")
        a("RJP v33b bz 10k")
    elif bz == 'hiz_pd':
        a("RJP bz 0 10k")
    else:
        a("RBZ0 bz 0 1G")
    a("CBZ bz 0 20p")
    return L


def write(name, body, title, extra=''):
    txt = [title, f".include {LIB}"] + body + [extra, ".options method=gear reltol=1e-4 abstol=1e-11 vntol=1e-5 itl4=50", ".end"]
    p = SIM / (name + '.cir')
    p.write_text('\n'.join(txt), encoding='utf-8')
    return p


def poisson_times(rate_hz, t0, t1, seed=1, dead=180e-6):
    rnd = random.Random(seed)
    t = t0
    out = []
    while True:
        t += rnd.expovariate(rate_hz)
        if t > t1:
            break
        if out and t - out[-1] < dead:
            continue
        out.append(t)
    return out


def tube_pwl_log(times, q=1e-9, t0=1e-6, T=150e-6, trise=0.5e-6):
    """圆柱计数管感应电流：Q(t)=k·ln(1+t/t0)，t0 由放电沿阳极扩展时间决定（~1 µs），T=离子收集时间（≈死时间）
    i(t)=k/(t+t0)，乘 (1-exp(-t/trise)) 上升沿；单位 µA"""
    import math
    n = 60
    ts = [T * (k / n) ** 3 for k in range(n + 1)]
    sh = [(1 - math.exp(-t / trise)) / (t + t0) for t in ts]
    area = sum((sh[k] + sh[k + 1]) / 2 * (ts[k + 1] - ts[k]) for k in range(n))
    k0 = q / area
    pts = [(0.0, 0.0)]
    for tt in times:
        if tt < pts[-1][0] + 1e-9:
            continue
        pts.append((tt, 0.0))
        for t, s in zip(ts[1:], sh[1:]):
            pts.append((tt + t, k0 * s * 1e6))
        pts.append((tt + T + 1e-7, 0.0))
    return ' '.join(f"{t:.12g} {v:.6g}" for t, v in pts)
