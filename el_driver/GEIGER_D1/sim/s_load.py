from gen import *
IC=".ic v(hv)=394.5 v(fbn)=2.477 v(hvin)=394.5 v(an)=394.5 v(tpv)=1e-3"
SV=".save v(hv) v(swg) v(o1) v(rst) v(fbn) v(refp) i(vhvc) v(v5hv) v(gm) v(pulse) v(ck) v(an) v(tpv) v(o4) v(en)"
base={'vr1':4,'cp':25e-12,'v5pwl':'0 5 10 5'}
def mk(n,o=None,clipo=None,with_click=False,t_end=0.4,extra=''):
    oo=dict(base,**(o or {}))
    body=hv_main(oo)
    co=dict(clipo or {})
    for k in ('c_sw_gm',):
        if k in oo: co[k]=oo[k]
    body+=clip(co)
    if with_click: body+=click({'bz':'hiz_pu'})
    else: body+=["V5 v5 0 5"]
    write(n,body,n,SV+"\n"+IC+(" v(en)=2.97 v(cv4)=3.333" if with_click else "")+"\n"+extra)
    return n
runs=[]
runs.append(mk('ld_base'))
runs.append(mk('ld_meter',{'rmeter':10e6}))
for cpm in [1000,10000]:
    ts=poisson_times(cpm/60,0.02,0.6,seed=cpm)
    runs.append(mk(f'ld_tube{cpm}',clipo={'tube_pwl':tube_pwl_log(ts,q=1e-9)}))
runs.append(mk('ld_v475',{'v5pwl':'0 4.75 10 4.75'}))
runs.append(mk('ld_v525',{'v5pwl':'0 5.25 10 5.25'}))
runs.append(mk('ld_vstep',{'v5pwl':'0 4.75 0.15 4.75 0.1501 5.25 0.3 5.25 0.3001 4.75 10 4.75'}))
runs.append(mk('sd_off',{'t_off':0.05}))
runs.append(mk('sd_off_meter',{'t_off':0.05,'rmeter':10e6}))
for c in [0.2e-12,0.5e-12,1e-12]:
    runs.append(mk(f'cp_swfb{c*1e12:g}'.replace('.','p'),{'c_sw_fb':c}))
for c in [0.2e-12,0.5e-12,1e-12]:
    runs.append(mk(f'cp_swgm{c*1e12:g}'.replace('.','p'),{'c_sw_gm':c},with_click=True))
runs.append(mk('cp_hvline5p',clipo={'c_hv_gm':5e-12,'c_hv_pu':5e-12},with_click=True))
open('load_list.txt','w',newline='\n').write('\n'.join(runs))
