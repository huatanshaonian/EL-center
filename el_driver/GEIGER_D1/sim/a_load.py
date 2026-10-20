from ana import *
def at(t,v,x): return float(v[min(np.searchsorted(t,x),len(t)-1)])
def stat(n,a=0.2,b=0.6):
    d=load(n); t=d['time']; hv=d['v_hv']; m=(t>a)&(t<b)
    c=cycles(t[m],d['v_o1'][m]); g=np.diff(c); st=c[1:][g>1e-3] if len(c)>2 else []
    bf=1/np.diff(st).mean() if len(st)>2 else float('nan')
    ii=-d['i_vhvc']
    return d,t,hv,m,f"HV 平均 {hv[m].mean():.2f} V，最低 {hv[m].min():.2f}，最高 {hv[m].max():.2f}，p-p {np.ptp(hv[m]):.2f} V；突发 {bf:.0f} Hz；输入平均 {ii[m].mean()*1e3:.2f} mA，最大 {ii[m].max()*1e3:.1f} mA"
import sys
for n in sys.argv[1:]:
    d,t,hv,m,s=stat(n); print(n,':',s)
    if n=='ld_meter': print('   TP1 读数 %.3f V → ×10 = %.1f V'%(d['v_tpv'][m].mean(), d['v_tpv'][m].mean()*10))
    if n.startswith('ld_tube'):
        pu=d['v_pulse']; fall=np.where((pu[:-1]>1.65)&(pu[1:]<=1.65))[0]; gm=d['v_gm']; gf=np.where((gm[:-1]>1.67)&(gm[1:]<=1.67))[0]
        of=[]
        print(f'   PULSE 下降沿 {len(fall)} 个, GM 触发 {len(gf)} 个, U4 输出 {len(of)} 次')
    if n=='ld_vstep':
        for a,b,l in [(0.05,0.15,'4.75V'),(0.17,0.3,'5.25V'),(0.32,0.6,'4.75V')]:
            mm=(t>a)&(t<b); print(f'   {l} 段 HV 平均 {hv[mm].mean():.2f}  p-p {np.ptp(hv[mm]):.2f}')
