from gen import *
exec(open('s_bz.py',encoding='utf-8').read().split("runs={}")[0])
tog='0 0 0.3 0 0.3000001 3.3 0.7 3.3 0.7000001 0 2 0'
al4='0 3.3 '+sq(0.1,0.3,f=4000,base=3.3,after=3.3).split(' ',2)[2]
al2='0 3.3 '+sq(0.1,0.3,f=2048,base=3.3,after=3.3).split(' ',2)[2]
runs={}
for tag,par in {'swap22':{'ac_swap':1},'swap1k1u':{'ac_swap':1,'r74':'1k','c72':'1u'},'swap1k220n':{'ac_swap':1,'r74':'1k','c72':'220n'}}.items():
    runs[f'bz3_{tag}_pz_alarm']=dict(o=dict(par,bz='pwl',bz_pwl=al4),gm=[0.05,0.5])
    runs[f'bz3_{tag}_pz_toggle']=dict(o=dict(par,bz='pwl',bz_pwl=tog),gm=[0.35,0.5,0.75,0.95])
    runs[f'bz3_{tag}_em_alarm']=dict(o=dict(par,bz='pwl',bz_pwl=al2,buzzer='em'),gm=[0.05,0.5])
    runs[f'bz3_{tag}_em_toggle']=dict(o=dict(par,bz='pwl',bz_pwl=tog,buzzer='em'),gm=[0.35,0.5])
names=[]
for n,r in runs.items():
    sv=SV if r['o'].get('buzzer','piezo')=='piezo' else SV.replace(' i(vlsm)','')
    write(n,click(r['o'])+common(r['gm']),n,sv+" i(vls2x)\n.ic v(en)=0 v(mt)=0 v(cv4)=0")
    names.append(n)
open('bz3_list.txt','w',newline='\n').write('\n'.join(names))
