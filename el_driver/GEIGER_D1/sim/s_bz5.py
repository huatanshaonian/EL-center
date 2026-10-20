from gen import *
exec(open('s_bz.py',encoding='utf-8').read().split("runs={}")[0])
runs={}
runs['bz5_alarm_muted_d']=dict(o={'bz':'pwl','bz_pwl':sq(0.1,0.6,after=0.0),'en_diode':1,'ac_swap':1,'r74':'470','c72':'1u'},gm=[0.05,0.3,0.5,0.9])
runs['bz5_alarm_on_d']=dict(o={'bz':'pwl','bz_pwl':'0 3.3 '+sq(0.1,0.6,base=3.3,after=3.3).split(' ',2)[2],'en_diode':1,'ac_swap':1,'r74':'470','c72':'1u'},gm=[0.05,0.3,0.65,0.7,0.9])
runs['bz5_toggle_d']=dict(o={'bz':'pwl','bz_pwl':'0 0 0.3 0 0.3000001 3.3 0.7 3.3 0.7000001 0 2 0','en_diode':1,'ac_swap':1,'r74':'470','c72':'1u'},gm=[0.32,0.35,0.4,0.6,0.705,0.72,0.8])
runs['bz5_hiz_pu_d']=dict(o={'bz':'hiz_pu','en_diode':1,'ac_swap':1,'r74':'470','c72':'1u'},gm=[0.5,0.8])
names=[]
for n,r in runs.items():
    write(n,click(r['o'])+common(r['gm']),n,SV+"\n.ic v(en)=0 v(mt)=0 v(cv4)=0"); names.append(n)
open('bz5_list.txt','w',newline='\n').write('\n'.join(names))
