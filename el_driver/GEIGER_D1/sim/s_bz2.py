from gen import *
exec(open('s_bz.py',encoding='utf-8').read().split("runs={}")[0])
runs={}
alarm='0 3.3 '+sq(0.1,0.3,f=2048,base=3.3,after=3.3).split(' ',2)[2]
runs['bz2_em_fix']=dict(o={'bz':'pwl','bz_pwl':alarm,'buzzer':'em','r74':'1k','c72':'1u'},gm=[0.05,0.5])
runs['bz2_pz_fix_alarm']=dict(o={'bz':'pwl','bz_pwl':'0 3.3 '+sq(0.1,0.3,f=4000,base=3.3,after=3.3).split(' ',2)[2],'r74':'1k','c72':'1u'},gm=[0.05,0.5])
runs['bz2_pz_fix_toggle']=dict(o={'bz':'pwl','bz_pwl':'0 0 0.3 0 0.3000001 3.3 0.7 3.3 0.7000001 0 2 0','r74':'1k','c72':'1u'},gm=[0.35,0.5])
runs['bz2_em_toggle']=dict(o={'bz':'pwl','bz_pwl':'0 0 0.3 0 0.3000001 3.3 0.7 3.3 0.7000001 0 2 0','buzzer':'em'},gm=[0.35,0.5])
runs['bz2_em_fix_toggle']=dict(o={'bz':'pwl','bz_pwl':'0 0 0.3 0 0.3000001 3.3 0.7 3.3 0.7000001 0 2 0','buzzer':'em','r74':'1k','c72':'1u'},gm=[0.35,0.5])
names=[]
for n,r in runs.items():
    sv=SV if r['o'].get('buzzer','piezo')=='piezo' else SV.replace(' i(vlsm)','')
    write(n,click(r['o'])+common(r['gm']),n,sv+"\n.ic v(en)=0 v(mt)=0 v(cv4)=0")
    names.append(n)
open('bz2_list.txt','w',newline='\n').write('\n'.join(names))
