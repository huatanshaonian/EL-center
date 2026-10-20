from gen import *
opts={'base':{}, 'r220k':{'r7':'220k','r61':'220k'}, 'r220k_c100p':{'r7':'220k','r61':'220k','c2':'100p'}, 'base_c100p':{'c2':'100p'}}
runs=[]
for on,oo in opts.items():
  for q in [0.1e-9,0.2e-9,0.3e-9,0.5e-9,1e-9,2e-9]:
        n=f"p3_{on}_q{q*1e9:g}".replace('.','p')
        body=["VHV hv 0 400"]+clip(dict(oo,tube_pwl=tube_pwl_log([1e-3],q=q)))+click({'bz':'hiz_pu'})
        write(n,body,f'pulse log-shape {on} q={q}',".ic v(en)=2.97 v(mt)=0 v(cv4)=3.333\n.save v(ck) v(an) v(pulse) v(gm) v(o4)")
        runs.append(n)
open('pulse3_list.txt','w',newline='\n').write('\n'.join(runs))
