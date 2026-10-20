from gen import *
exec(open('s_load.py',encoding='utf-8').read().split("runs=[]")[0])
r=[]
r.append(mk('fx_swgm1_cgm1n',{'c_sw_gm':1e-12},clipo={'c_gm':'1n'},with_click=True))
r.append(mk('fx_swgm2_cgm1n',{'c_sw_gm':2e-12},clipo={'c_gm':'1n'},with_click=True))
open('fix_list.txt','w',newline='\n').write('\n'.join(r))
SV=".save v(hv) v(swg) v(em) v(o1) v(rst) v(fbn) v(refp) i(vhvc) v(v5hv)"
write('fx_fbhalf_closed',hv_main({'vr1':4,'cp':25e-12,'fb_half':1,'r40':'270k','vr2':42.8e3}),'closed fb_half',SV)
write('fx_fbhalf_sd_cmrfail',hv_main({'vr1':4,'cp':25e-12,'fb_half':1,'r40':'270k','vr2':42.8e3,'t_off':0.15,'lm393':'LM393W','v5pwl':'0 0 100u 5 10 5'}),'fb_half shutdown cmrfail',SV)
write('fx_fbhalf_swfb1',hv_main({'vr1':4,'cp':25e-12,'fb_half':1,'r40':'270k','vr2':42.8e3,'c_sw_fb':1e-12}),'fb_half swfb 1p',SV)
# 脉冲检测：GM 加 1 nF 后，基准与推荐改法
runs=[]
for on,oo in {'base_cgm1n':{'c_gm':'1n'},'r220k_cgm1n':{'r7':'220k','r61':'220k','c_gm':'1n'}}.items():
  for q in [1e-9,2e-9]:
    n=f"p5_{on}_q{q*1e9:g}"
    body=["VHV hv 0 400"]+clip(dict(oo,tube_pwl=tube_pwl_log([1e-3],q=q)))+click({'bz':'hiz_pu'})
    write(n,body,n,".ic v(en)=2.97 v(mt)=0 v(cv4)=3.333\n.save v(ck) v(an) v(pulse) v(gm) v(o4)")
    runs.append(n)
open('pulse5_list.txt','w',newline='\n').write('\n'.join(runs))
