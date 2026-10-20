from gen import *
def gmpulses(ts,w=20e-6):
    pts=["0 0"]
    for t in ts: pts+= [f"{t} 0",f"{t+1e-7} 1",f"{t+w} 1",f"{t+w+1e-7} 0"]
    return ' '.join(pts)
def sq(t0,t1,f=4000,hi=3.3,base=0.0,after=0.0):
    pts=[f"0 {base}",f"{t0} {base}"]
    h=0.5/f; t=t0; s=hi
    while t<t1:
        pts+= [f"{t+1e-7:.9f} {s}", f"{t+h:.9f} {s}"]; s= (0.0 if s==hi else hi); t+=h
    pts+= [f"{t+2e-7:.9f} {after}"]
    return ' '.join(pts)
SV=".save v(bz) v(bzp) v(en) v(gm) v(o4) v(qb6) v(bzn) v(ac) i(vlsm) i(vbz)"
common=lambda ts: ["R3 v5 gm 10k","CGMIN gm 0 5p",f"VGMC gmctl 0 PWL({gmpulses(ts)})","SGM gm 0 gmctl 0 SWX"]
runs={}
runs['bz_high']=dict(o={'bz':'pwl','bz_pwl':'0 3.3 1 3.3'},gm=[0.5,0.8])
runs['bz_low']=dict(o={'bz':'pwl','bz_pwl':'0 0 1 0'},gm=[0.5,0.8])
runs['bz_hiz_pu']=dict(o={'bz':'hiz_pu'},gm=[0.5,0.8])
runs['bz_hiz_pd']=dict(o={'bz':'hiz_pd'},gm=[0.5,0.8])
runs['bz_hiz_pu_leak3u']=dict(o={'bz':'hiz_pu','c71_leak':3e-6},gm=[0.5,0.8])
# 静音状态下报警 0.1–0.6 s，之后回低；GM 在报警中 0.3/0.5 s 和之后 0.9 s
runs['bz_alarm_muted']=dict(o={'bz':'pwl','bz_pwl':sq(0.1,0.6,after=0.0)},gm=[0.05,0.3,0.5,0.9])
# 咔哒开状态下报警，之后回高
runs['bz_alarm_on']=dict(o={'bz':'pwl','bz_pwl':'0 3.3 '+sq(0.1,0.6,base=3.3,after=3.3).split(' ',2)[2]},gm=[0.05,0.3,0.9])
# 低→高（开咔哒，'嗒'）在 0.3 s，高→低（静音）在 0.7 s
runs['bz_toggle']=dict(o={'bz':'pwl','bz_pwl':'0 0 0.3 0 0.3000001 3.3 0.7 3.3 0.7000001 0 2 0'},gm=[0.1,0.32,0.35,0.4,0.45,0.6,0.72,0.75,0.8,0.85,0.9,1.0])
# 电磁式蜂鸣器：报警驱动与咔哒
runs['bz_alarm_em']=dict(o={'bz':'pwl','bz_pwl':'0 3.3 '+sq(0.1,0.3,f=2048,base=3.3,after=3.3).split(' ',2)[2],'buzzer':'em'},gm=[0.05,0.5])
names=[]
for n,r in runs.items():
    sv=SV if r['o'].get('buzzer','piezo')=='piezo' else SV.replace(' i(vlsm)',' i(llls2)')
    write(n,click(r['o'])+common(r['gm']),n,sv+"\n.ic v(en)=0 v(mt)=0 v(cv4)=0")
    names.append(n)
open('bz_list.txt','w',newline='\n').write('\n'.join(names))
