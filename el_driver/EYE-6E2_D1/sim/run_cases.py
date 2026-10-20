# EYE-6E2 D1 全部仿真工况；结果汇总写 summary.json
import json, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from board_netlist import board, SUBCKT
from sim_runner import run, tavg, pp, cross_time
import em87_model as M

STEADY_V = ["time", "v(g_a)", "v(g_b)", "v(gf_a)", "v(vk)", "v(s12)", "v(an_a)", "v(an_b)", "v(hv)",
            "v(t_a)", "i(vika)", "i(vikb)", "i(vita)", "i(vitb)", "v(c_a)"]
OUT = {}

def steady(tag, d, **kw):
    name = f"steady_{tag}"
    v = run(name, board(name, d, d, **kw), "tran 1u 200m 170m 2u", STEADY_V)
    t = v["time"]; a = lambda k: tavg(t, v[k], 0.175, 0.2)
    vgk_a = v["v(g_a)"] - v["v(vk)"]; vgk_b = v["v(g_b)"] - v["v(vk)"]
    vk = a("v(vk)"); van = a("v(an_a)"); vt = a("v(t_a)")
    r = dict(D=d, Vgk_A=tavg(t, vgk_a, .175, .2), Vgk_B=tavg(t, vgk_b, .175, .2), VK=vk, Va_gnd=van,
             Vak=van - vk, Vtk=vt - vk, HV=a("v(hv)"), Ia_mA=(a("v(hv)") - van) / 100e3 * 1e3,
             It_mA=a("i(vita)") * 1e3, Ik_mA=a("i(vika)") * 1e3, S12=a("v(s12)"),
             Vgk_ripple_pp_mV=pp(t, vgk_a, .19, .2) * 1e3, Va_ripple_pp_V=pp(t, v["v(an_a)"], .19, .2))
    r["dark_vgk_mm"] = float(M.dark_vgk(r["Vgk_A"]))
    r["dark_ratio_mm"] = float(M.dark_ratio(r["Vak"], r["Vtk"]))
    OUT[name] = r
    return r

def step(name, mode_a, mode_b, t_on=0.02, t_off=0.27, t_end=0.52):
    v = run(name, board(name, mode_a, mode_b),
            f"tran 20u {t_end} 0 1u;linearize v(g_a) v(g_b) v(vk) v(an_a) v(an_b) v(t_a) v(s12)",
            ["time", "v(g_a)", "v(g_b)", "v(vk)", "v(an_a)", "v(an_b)", "v(t_a)", "v(s12)"])
    t = v["time"]
    res = {}
    for ch in "ab":
        vgk = v[f"v(g_{ch})"] - v["v(vk)"]
        vak = v[f"v(an_{ch})"] - v["v(vk)"]; vtk = v["v(t_a)"] - v["v(vk)"]
        dark = M.dark_ratio(vak, vtk)
        lo = tavg(t, vgk, t_on - 0.01, t_on); hi = tavg(t, vgk, t_off - 0.01, t_off)
        lo2 = tavg(t, vgk, t_end - 0.01, t_end)
        d = dict(V_start=lo, V_on=hi, V_end=lo2)
        if abs(hi - lo) > 0.5:
            sp = hi - lo
            t10 = cross_time(t, vgk, lo + 0.1 * sp, t_on, rising=sp > 0); t90 = cross_time(t, vgk, lo + 0.9 * sp, t_on, rising=sp > 0)
            f10 = cross_time(t, vgk, hi - 0.1 * sp, t_off, rising=sp < 0); f90 = cross_time(t, vgk, hi - 0.9 * sp, t_off, rising=sp < 0)
            d.update(rise_10_90_ms=(t90 - t10) * 1e3, fall_10_90_ms=(f90 - f10) * 1e3, rise_delay10_ms=(t10 - t_on) * 1e3)
            a0 = tavg(t, dark, t_on - 0.01, t_on); a1 = tavg(t, dark, t_off - 0.01, t_off); sa = a1 - a0
            g10 = cross_time(t, dark, a0 + 0.1 * sa, t_on, rising=sa > 0); g90 = cross_time(t, dark, a0 + 0.9 * sa, t_on, rising=sa > 0)
            h10 = cross_time(t, dark, a1 - 0.1 * sa, t_off, rising=sa < 0); h90 = cross_time(t, dark, a1 - 0.9 * sa, t_off, rising=sa < 0)
            d.update(dark_start=a0, dark_on=a1, dark_rise_10_90_ms=(g90 - g10) * 1e3, dark_fall_10_90_ms=(h90 - h10) * 1e3)
        else:
            m = (t > t_on) & (t < t_off + 0.2)
            d.update(max_dev_mV=(np.max(np.abs(vgk[m] - lo))) * 1e3,
                     dark_dev_mm=float(np.max(np.abs(dark[m] - tavg(t, dark, t_on - 0.01, t_on)))))
        res[ch] = d
    res["VK_start"] = tavg(t, v["v(vk)"], t_on - 0.01, t_on); res["VK_on"] = tavg(t, v["v(vk)"], t_off - 0.01, t_off)
    res["VK_dip_min"] = float(v["v(vk)"][(t > t_on)].min()); res["VK_max"] = float(v["v(vk)"][(t > t_on)].max())
    OUT[name] = res

def gpio_states():
    r = {}
    for mode in ["float", "pu45k", "pd45k"]:
        name = f"gpio_{mode}"
        v = run(name, board(name, mode, 0.0), "op", ["v(g_a)", "v(vk)", "v(b_a)", "v(c_a)", "i(vika)", "v(an_a)"])
        r[mode] = dict(Vgk=float(v["v(g_a)"][0] - v["v(vk)"][0]), Vb=float(v["v(b_a)"][0]), Vc=float(v["v(c_a)"][0]),
                       Ik_mA=float(v["i(vika)"][0] * 1e3), Va=float(v["v(an_a)"][0]))
    OUT["gpio"] = r

def powerup():
    name = "powerup"
    v12 = "PWL(0 0 1m 0 1.05m 12 400m 12 401m 0 1 0)"
    vhv = "PWL(0 0 3m 0 23m 250 401m 250 1 0)"     # HV-UNI 欠压锁定后约 20 ms 升到 250 V；12 V 断后 0.6 s 线性放到 0
    v = run(name, board(name, 0.5, "float", v12=v12, vhv=vhv),
            "tran 10u 1 0 1u;linearize v(g_a) v(g_b) v(vk) v(s12) v(c_a) i(vika)",
            ["time", "v(g_a)", "v(g_b)", "v(vk)", "v(s12)", "v(c_a)", "i(vika)"])
    t = v["time"]; ga = v["v(g_a)"] - v["v(vk)"]; gb = v["v(g_b)"] - v["v(vk)"]
    irk = (v["v(s12)"] - v["v(vk)"]) / 10
    e_rk = float(np.trapz(irk ** 2 * 10, t))
    m0 = t < 0.05
    OUT[name] = dict(Vgk_A_max=float(ga.max()), Vgk_B_max=float(gb.max()), Vgk_A_min=float(ga.min()),
                     Vgk_A_max_after_off=float(ga[t > 0.4].max()), Vgk_B_max_after_off=float(gb[t > 0.4].max()),
                     IRK_peak_A=float(irk.max()), PRK_peak_W=float((irk ** 2 * 10).max()),
                     E_RK_poweron_mJ=float(np.trapz((irk[m0] ** 2) * 10, t[m0]) * 1e3), E_RK_total_mJ=e_rk * 1e3,
                     Vc_min=float(v["v(c_a)"].min()), Vk_at_450ms=float(np.interp(0.45, t, v["v(vk)"])),
                     Vgk_A_400_420ms=[float(x) for x in np.interp([0.4, 0.402, 0.405, 0.41, 0.42, 0.5], t, ga)])

def ac_transfer(name, src, mode_a=1.0, mode_b=0.0, extra=""):
    kw = dict(v12="DC 12 AC 1") if src == "v12" else dict(vhv="DC 250 AC 1")
    v = run(name, board(name, mode_a, mode_b, extra=extra, **kw),
            "ac dec 10 0.1 1meg;let fr=real(frequency);let ga=mag(v(g_a)-v(vk));let gb=mag(v(g_b)-v(vk));let vkm=mag(v(vk))",
            ["fr", "ga", "gb", "vkm"])
    f = v["fr"]
    pick = [1, 10, 34, 100, 1e3, 1e4, 52e3, 1e5]
    OUT[name] = {f"{p:g}Hz": dict(Vgk_A=float(np.interp(np.log(p), np.log(f), v["ga"])),
                                  Vgk_B=float(np.interp(np.log(p), np.log(f), v["gb"])),
                                  VK=float(np.interp(np.log(p), np.log(f), v["vkm"]))) for p in pick}

def tone(t, y, f, t0, t1, n=2 ** 18):
    """y 在频率 f 处的峰峰值（均匀重采样 + Hann 窗 FFT）"""
    tt = np.linspace(t0, t1, n); yy = np.interp(tt, t, y); yy = yy - yy.mean()
    w = np.hanning(n); Y = np.abs(np.fft.rfft(yy * w)) * 2 / w.sum()
    fr = np.fft.rfftfreq(n, tt[1] - tt[0]); k = np.argmin(np.abs(fr - f))
    return float(Y[max(k - 2, 0):k + 3].max() * 2)

def ripple12(name, v12, da, db):
    v = run(name, board(name, da, db, v12=v12), "tran 0.2u 160m 120m 0.2u", ["time", "v(g_a)", "v(g_b)", "v(vk)", "v(s12)"])
    t = v["time"]; ga = v["v(g_a)"] - v["v(vk)"]; gb = v["v(g_b)"] - v["v(vk)"]
    OUT[name] = dict(S12_mean=tavg(t, v["v(s12)"], .12, .16), S12_pp_mV=pp(t, v["v(s12)"], .15, .16) * 1e3,
                     VK_pp_mV=pp(t, v["v(vk)"], .15, .16) * 1e3, VK_52k_pp_mV=tone(t, v["v(vk)"], 52e3, .12, .16) * 1e3,
                     Vgk_A_mean=tavg(t, ga, .12, .16), Vgk_A_pp_mV=pp(t, ga, .15, .16) * 1e3,
                     Vgk_A_52k_pp_uV=tone(t, ga, 52e3, .12, .16) * 1e6, Vgk_A_10k_pp_mV=tone(t, ga, 10e3, .12, .16) * 1e3,
                     Vgk_B_pp_uV=pp(t, gb, .15, .16) * 1e6, Vgk_B_52k_pp_uV=tone(t, gb, 52e3, .12, .16) * 1e6)

def parasitic(name, extra, vhv):
    mode_b = ("pwl", [(0, -0.01), (0.02, -0.01), (0.02001, 1.01), (0.2, 1.01)])
    v = run(name, board(name, 0.0, mode_b, vhv=vhv, extra=extra), "tran 0.5u 80m 10m 0.5u",
            ["time", "v(g_a)", "v(vk)", "v(an_b)", "v(hv)"])
    t = v["time"]; g = v["v(g_a)"] - v["v(vk)"]
    base = tavg(t, g, .01, .019)
    # 去掉 52 kHz 后看 B 阶跃引起的低频偏移：100 µs 滑动平均（≈5 个 52 kHz 周期）
    tt = np.linspace(.01, .08, 70001); gg = np.interp(tt, t, g); k = 100
    sm = np.convolve(gg, np.ones(k) / k, mode="same")[k:-k]
    OUT[name] = dict(Vgk_A_base=base, Vgk_A_52k_pp_mV=tone(t, g, 52e3, .03, .08) * 1e3,
                     Vgk_A_lowfreq_dev_mV=float(np.max(np.abs(sm - base))) * 1e3,
                     ANB_swing_V=pp(t, v["v(an_b)"], .01, .08), HV_pp_V=pp(t, v["v(hv)"], .07, .08),
                     HV_mean=tavg(t, v["v(hv)"], .01, .08))

def leakage():
    r = {}
    for rl in ["1e14", "10G", "1G", "100Meg", "20Meg"]:
        for node in ["G_A", "GF_A"]:
            name = f"leak_{node}_{rl}"
            v = run(name, board(name, 0.0, 0.0, extra=f"RLK HV {node} {rl}\n"), "op", ["v(g_a)", "v(vk)", "i(vika)"])
            r[f"{node}_{rl}"] = dict(Vgk=float(v["v(g_a)"][0] - v["v(vk)"][0]))
    OUT["leakage"] = r

FIL_HEAD = """* heater string cold start, tungsten R=R0*(T/300)^1.267, radiative loss kr*(T^4-300^4)
VS12 S12S 0 PWL(0 0 1m 0 1.05m 12)
RLINE S12S S12 {rline}
BFA S12 FMID I = {{ V(S12,FMID)/({ra}*pwr(max(V(TA),300)/300,1.267)) }}
BFB FMID 0 I = {{ V(FMID)/({rb}*pwr(max(V(TB),300)/300,1.267)) }}
CTA TA 0 {cth}
BTA 0 TA I = {{ V(S12,FMID)*V(S12,FMID)/({ra}*pwr(max(V(TA),300)/300,1.267)) - {ka}*(pwr(V(TA),4)-8.1e9) }}
CTB TB 0 {cth}
BTB 0 TB I = {{ V(FMID)*V(FMID)/({rb}*pwr(max(V(TB),300)/300,1.267)) - {kb}*(pwr(V(TB),4)-8.1e9) }}
.ic V(TA)=300 V(TB)=300
.options reltol=1e-5
.end
"""
KR = 1.89 / (1400 ** 4 - 300 ** 4)   # 6.3 V / 0.3 A 热平衡在 1400 K（R=21 Ω）

def filament(name, ra=2.98, rb=2.98, ka=KR, kb=KR, cth=0.03, rline=0.25):
    net = FIL_HEAD.format(ra=ra, rb=rb, ka=ka, kb=kb, cth=cth, rline=rline)
    v = run(name, net, "tran 1m 40 0 2m uic", ["time", "v(s12)", "v(fmid)", "v(ta)", "v(tb)"])
    t = v["time"]
    vs = v["v(s12)"]; vm = v["v(fmid)"]
    cur = (vs - vm) / (ra * (np.maximum(v["v(ta)"], 300) / 300) ** 1.267)
    ipk = float(cur.max())
    def t_below(x):
        k = np.where((t > 0.002) & (cur < x))[0]
        return float(t[k[0]]) if len(k) else None
    OUT[name] = dict(I_peak_A=ipk, t_below_1A_s=t_below(1.0), t_below_0p45A_s=t_below(0.45),
                     t_below_1p1x_s=t_below(1.1 * cur[-1]), I_final_A=float(cur[-1]),
                     VA_final=float(vs[-1] - vm[-1]), VB_final=float(vm[-1]),
                     TA_final=float(v["v(ta)"][-1]), TB_final=float(v["v(tb)"][-1]),
                     I2t_first_1s=float(np.trapz(cur[t < 1.0] ** 2, t[t < 1.0])),
                     VA_max_during=float((vs - vm).max()), VB_max_during=float(vm.max()))

def cc_coplanar(w, s, L, er=4.4):
    """两根共面带线之间的耦合电容（无地平面，保角变换），返回 pF"""
    from scipy.special import ellipk
    k = s / (s + 2 * w); kp = np.sqrt(1 - k * k)
    eeff = (1 + er) / 2
    return 8.854e-12 * eeff * ellipk(kp * kp) / ellipk(k * k) * L * 1e12

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    tasks = []
    if which in ("all", "steady"):
        for d in [0, 0.1, 0.2, 0.4, 0.5, 0.6, 0.85, 1.0]:
            tasks.append(lambda d=d: steady(f"D{int(round(d*100)):03d}", d))
    if which in ("all", "step"):
        up = ("pwl", [(0, -0.01), (0.02, -0.01), (0.02001, 0.85), (0.27, 0.85), (0.27001, -0.01), (0.52, -0.01)])
        tasks.append(lambda: step("step_A_0to85_B50", up, 0.5))
        both = ("pwl", [(0, -0.01), (0.02, -0.01), (0.02001, 1.01), (0.27, 1.01), (0.27001, -0.01), (0.52, -0.01)])
        tasks.append(lambda: step("step_both_0to100", both, both))
    if which in ("all", "misc"):
        tasks.append(gpio_states); tasks.append(powerup); tasks.append(leakage)
        tasks.append(lambda: ac_transfer("ac_v12_DA100_DB0", "v12"))
        tasks.append(lambda: ac_transfer("ac_hv_DA100_DB0", "hv"))
        tasks.append(lambda: ac_transfer("ac_hv_cc_DA100_DB0", "hv", extra="CCHV HV G_A 0.5p\n"))
        tasks.append(lambda: ac_transfer("ac_hv_cc_DA0_DB0", "hv", mode_a=0.0, extra="CCHV HV G_A 0.5p\n"))
        tasks.append(lambda: ripple12("rip12_sine500mV_DA100_DB0", "SIN(12 0.25 52k)", 1.0, 0.0))
        tasks.append(lambda: ripple12("rip12_saw500mV_DA50_DB0", "PULSE(11.75 12.25 0 18.7u 0.5u 1n 19.23u)", 0.5, 0.0))
        tasks.append(lambda: ripple12("rip12_none_DA50_DB0", "DC 12", 0.5, 0.0))
        tasks.append(lambda: parasitic("para_none", "", "SIN(250 0.5 52k)"))
        tasks.append(lambda: parasitic("para_cc", "CCHV HV G_A 0.5p\nCCAB AN_B G_A 0.3p\n", "SIN(250 0.5 52k)"))
    if which == "rerun":
        tasks.append(lambda: ripple12("rip12_sine500mV_DA50_DB0", "SIN(12 0.25 52k)", 0.5, 0.0))
        tasks.append(lambda: ripple12("rip12_saw500mV_DA50_DB0", "PULSE(11.75 12.25 0 18.7u 0.5u 1n 19.23u)", 0.5, 0.0))
        tasks.append(lambda: ripple12("rip12_sine500mV_DA100_DB0", "SIN(12 0.25 52k)", 1.0, 0.0))
        tasks.append(lambda: ripple12("rip12_none_DA50_DB0", "DC 12", 0.5, 0.0))
        tasks.append(lambda: parasitic("para_none", "", "SIN(250 0.5 52k)"))
        tasks.append(lambda: parasitic("para_cc", "CCHV HV G_A 0.5p\nCCAB AN_B G_A 0.3p\n", "SIN(250 0.5 52k)"))
        tasks.append(lambda: parasitic("para_cc_x5", "CCHV HV G_A 2.5p\nCCAB AN_B G_A 1.5p\n", "SIN(250 0.5 52k)"))
        b2 = ("pwl", [(0, -0.01), (0.2, -0.01), (0.20001, 1.01), (0.45, 1.01), (0.45001, -0.01), (0.7, -0.01)])
        tasks.append(lambda: step("xtalk_A50_B0to100", 0.5, b2, t_on=0.2, t_off=0.45, t_end=0.7))
        tasks.append(lambda: step("xtalk_A10_B0to100", 0.1, b2, t_on=0.2, t_off=0.45, t_end=0.7))
    if which in ("all", "fil"):
        tasks.append(lambda: filament("fil_nominal"))
        tasks.append(lambda: filament("fil_R_pm7", ra=2.98 * 1.07, rb=2.98 * 0.93))
        tasks.append(lambda: filament("fil_k_pm7", ka=KR * 0.93, kb=KR * 1.07))
        tasks.append(lambda: filament("fil_nominal_cth0p015", cth=0.015))
    if which in ("all", "fix"):
        for d in [0, 0.2, 0.4, 0.6, 0.85, 1.0]:
            tasks.append(lambda d=d: steady(f"RT33k_D{int(round(d*100)):03d}", d, rt="33k"))
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(f) for f in tasks]
        for f in futs:
            try:
                f.result()
            except Exception as e:
                print("ERROR", repr(e)[:3000])
    OUT["cc_estimates_pF"] = {f"w{w}_s{s}_L{L}": cc_coplanar(w, s, L * 1e-3)
                              for (w, s, L) in [(0.25, 1.3, 10), (0.25, 1.3, 20), (0.25, 2.0, 20), (0.5, 1.3, 20), (0.25, 3.0, 30)]}
    fn = f"summary_{which}.json"
    import pathlib
    (pathlib.Path(__file__).parent / fn).write_text(json.dumps(OUT, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print("done", fn)
