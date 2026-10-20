from ana import *
import glob
for vr in [0,5,10]:
  for cp in [15,25,40]:
    n=f"open_vr{vr}_cp{cp}"
    try: d=load(n)
    except Exception as e: print(n,'missing'); continue
    t=d['time']; hv=d['v_hv']; sw=d['v_swg']; em=d['v_em']
    def at(x): return hv[min(np.searchsorted(t,x),len(t)-1)]
    m=t>t[-1]-20e-3
    c=cycles(t[m],d['v_o1'][m]); f=1/np.diff(c).mean() if len(c)>2 else 0
    # 拟合渐近值：最后 0.3 s 按指数趋近外推
    t1,t2,t3=t[-1]-0.4,t[-1]-0.2,t[-1]
    v1,v2,v3=at(t1),at(t2),at(t3)
    vinf = v3 + (v3-v2)**2/((v2-v1)-(v3-v2)) if (v2-v1)-(v3-v2)>1e-6 else v3
    print(f"{n:16s} HV@0.1s={at(0.1):6.1f} @0.4s={at(0.4):6.1f} @0.8s={v3:6.1f} 外推={vinf:6.1f}  SWGmax={sw[m].max():6.1f}  Ipk={em[m].max()/(15+vr)*1e3:5.1f}mA f={f:6.0f}Hz Iin_avg={-d['i_vhvc'][m].mean()*1e3:5.2f}mA")
