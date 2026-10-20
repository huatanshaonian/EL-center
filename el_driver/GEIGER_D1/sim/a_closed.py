from ana import *
import sys
def bursts(t,o1,tmin):
    c=cycles(t,o1); c=c[c>tmin]
    if len(c)<3: return c,np.array([])
    g=np.diff(c); starts=c[1:][g>1e-3]   # 间隔 >1 ms 视为新突发
    return c,starts
def report(n,tss=0.25):
    d=load(n); t=d['time']; hv=d['v_hv']
    m=t>tss
    vss=hv[m].mean(); 
    i95=np.argmax(hv>0.95*vss); i99=np.argmax(hv>0.99*vss)
    c,st=bursts(t,d['v_o1'],tss)
    bf=1/np.diff(st).mean() if len(st)>2 else float('nan')
    cyc_per_burst=len(c)/max(len(st),1)
    print(f"{n}: Vss={vss:.1f} V (min {hv[m].min():.1f} max {hv[m].max():.1f} p-p {np.ptp(hv[m]):.2f} V) t95={t[i95]*1e3:.1f} ms t99={t[i99]*1e3:.1f} ms 首次过冲max={hv[t<tss].max():.1f}")
    print(f"   突发频率={bf:.1f} Hz 每突发≈{cyc_per_burst:.1f} 个开关周期  SWGmax={(d['v_swg_max'][0] if 'v_swg_max' in d else d['v_swg'][m].max()):.1f}")
    ii=-d['i_vhvc']
    print(f"   5V_HV 输入电流(电源侧,含C10): 启动段平均 {ii[(t>1e-3)&(t<t[i95])].mean()*1e3:.2f} mA, 稳态平均 {ii[m].mean()*1e3:.2f} mA, 稳态最大 {ii[m].max()*1e3:.1f} mA, 0-1ms 浪涌峰值 {ii[t<1e-3].max():.2f} A")
    if 'v_fbn' in d: print(f"   FBN 稳态 {d['v_fbn'][m].mean():.4f} V, REFP {d['v_refp'][m].min():.4f}..{d['v_refp'][m].max():.4f}")
    return d
for n in sys.argv[1:]: report(n)
