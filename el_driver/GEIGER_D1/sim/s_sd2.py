from gen import *
exec(open('s_load.py',encoding='utf-8').read().split("runs=[]")[0])
r=[mk('sd_off_cmrfail',{'t_off':0.05,'lm393':'LM393W'}), mk('sd_off_cmrfail_vr0',{'t_off':0.05,'lm393':'LM393W','vr1':0})]
open('sd2_list.txt','w',newline='\n').write('\n'.join(r))
