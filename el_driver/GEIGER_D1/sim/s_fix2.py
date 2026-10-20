from gen import *
exec(open('s_load.py',encoding='utf-8').read().split("runs=[]")[0])
r=[mk('fx_swgm1_cgm470p',{'c_sw_gm':1e-12},clipo={'c_gm':'470p'},with_click=True), mk('fx_swgm2_cgm470p',{'c_sw_gm':2e-12},clipo={'c_gm':'470p'},with_click=True)]
open('fix3_list.txt','w',newline='\n').write('\n'.join(r))
runs=[]
for on,oo in {'base':{},'base_cgm470p':{'c_gm':'470p'},'r220k':{'r7':'220k','r61':'220k'},'r220k_cgm470p':{'r7':'220k','r61':'220k','c_gm':'470p'},'r220k_c100p_cgm470p':{'r7':'220k','r61':'220k','c2':'100p','c_gm':'470p'}}.items():
  for q in [0.5e-9,0.7e-9,1e-9,2e-9,5e-9]:
    n=f"p6_{on}_q{q*1e9:g}".replace('.','p')
    body=["VHV hv 0 400"]+clip(dict(oo,tube_pwl=tube_pwl_log([3e-3],q=q)))+click({'bz':'hiz_pu'})
    write(n,body,n,".ic v(en)=2.97 v(cv4)=3.333\n.save v(ck) v(an) v(pulse) v(gm) v(o4)")
    runs.append(n)
open('pulse6_list.txt','w',newline='\n').write('\n'.join(runs))
