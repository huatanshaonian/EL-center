from ana import *
import json
gms={'bz_high':[0.5,0.8],'bz_low':[0.5,0.8],'bz_hiz_pu':[0.5,0.8],'bz_hiz_pd':[0.5,0.8],'bz_hiz_pu_leak3u':[0.5,0.8],
 'bz_alarm_muted':[0.05,0.3,0.5,0.9],'bz_alarm_on':[0.05,0.3,0.9],'bz_toggle':[0.1,0.32,0.35,0.4,0.45,0.6,0.72,0.75,0.8,0.85,0.9,1.0],'bz_alarm_em':[0.05,0.5]}
def at(t,v,x): return float(v[min(np.searchsorted(t,x),len(t)-1)])
def energy(t,i,a,b):
    m=(t>=a)&(t<b); return float(np.trapz(i[m]**2,t[m]))
for n,g in gms.items():
    d=load(n); t=d['time']; o4=d['v_o4']; en=d['v_en']; qb=d['v_qb6']
    clicks=[]
    for x in g:
        m=(t>x)&(t<x+3e-3); clicks.append(round(width(t[m],o4[m],2.5,False)*1e3,2))
    s=f"{n}: EN@0.45s={at(t,en,0.45):.3f}V EN@0.25s={at(t,en,0.25):.3f} EN末={en[-1]:.3f}; GM脉冲时刻{g} -> U4输出宽(ms) {clicks}"
    print(s)
    if 'i_vlsm' in d:
        im=d['i_vlsm']
        # 一次咔哒的动态支路能量（声输出相对量）
        for x,w in zip(g,clicks):
            if w>0: e1=energy(t,im,x,x+5e-3); print(f"   咔哒@{x}s 动态支路∫i²dt={e1*1e9:.3f} nA²s"); break
    if n.startswith('bz_alarm') :
        m=(t>0.15)&(t<0.55)
        print(f"   报警段 Q6 基极>0.6V 占空 {np.mean(qb[m]>0.6)*100:.1f}%  BZN 最低 {d['v_bzn'][m].min():.3f}V  EN 报警段 {en[m].min():.2f}..{en[m].max():.2f}V")
        if 'i_vlsm' in d: 
            im=d['i_vlsm']; print(f"   报警动态支路电流 RMS {np.sqrt(np.mean(im[m]**2))*1e3:.3f} mA, 每 0.25 ms 周期能量 {energy(t,im,0.3,0.3025)/10*1e9:.3f} nA²s")
    if n=='bz_toggle':
        im=d['i_vlsm']
        e=energy(t,im,0.3,0.305); print(f"   BZ低→高'嗒'：动态支路∫i²dt={e*1e9:.3f} nA²s；Q6 基极>0.6V 持续 {width(t[(t>0.3)&(t<0.31)],qb[(t>0.3)&(t<0.31)],0.6,False)*1e3:.3f} ms")
        e2=energy(t,im,0.7,0.705); print(f"   BZ高→低：动态支路∫i²dt={e2*1e9:.4f} nA²s")
        m=t>0.3; i1=np.argmax(m&(en>1.1)); i2=np.argmax(m&(en>1.5)); print(f"   使能延迟：EN>1.1V 用 {(t[i1]-0.3)*1e3:.0f} ms，>1.5V 用 {(t[i2]-0.3)*1e3:.0f} ms")
        m=t>0.7; i1=np.argmax(m&(en<1.1)); i2=np.argmax(m&(en<0.4)); print(f"   静音延迟：EN<1.1V 用 {(t[i1]-0.7)*1e3:.0f} ms，<0.4V 用 {(t[i2]-0.7)*1e3:.0f} ms")
    if n=='bz_alarm_em':
        m=(t>0.15)&(t<0.3); print(f"   电磁式：报警段 BZN 最低 {d['v_bzn'][m].min():.3f}V，Q6 导通时 BZN 中位 {np.median(d['v_bzn'][m][qb[m]>0.6]):.2f}V")
        m=(t>0.05)&(t<0.052); print(f"   电磁式咔哒：BZN 最低 {d['v_bzn'][m].min():.3f} V")
