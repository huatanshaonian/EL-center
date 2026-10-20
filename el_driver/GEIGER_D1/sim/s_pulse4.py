from gen import *
opts={'r470k':{'r7':'470k','r61':'470k'}, 'r470k_c100p':{'r7':'470k','r61':'470k','c2':'100p'}}
runs=[]
for on,oo in opts.items():
  for q in [0.2e-9,0.3e-9,0.5e-9,1e-9,2e-9,5e-9]:
        n=f"p4_{on}_q{q*1e9:g}".replace('.','p')
        body=["VHV hv 0 400"]+clip(dict(oo,tube_pwl=tube_pwl_log([1e-3],q=q)))+click({'bz':'hiz_pu'})
        write(n,body,f'pulse log-shape {on} q={q}',".ic v(en)=2.97 v(mt)=0 v(cv4)=3.333\n.save v(ck) v(an) v(pulse) v(gm) v(o4)")
        runs.append(n)
  for td in [30e-6,100e-6]:
        n=f"p4_{on}_q1_exp{int(td*1e6)}"
        body=["VHV hv 0 400"]+clip(dict(oo,tube_pwl=tube_pwl([1e-3],q=1e-9,tdec=td)))+click({'bz':'hiz_pu'})
        write(n,body,f'pulse exp {on}',".ic v(en)=2.97 v(mt)=0 v(cv4)=3.333\n.save v(ck) v(an) v(pulse) v(gm) v(o4)")
        runs.append(n)
open('pulse4_list.txt','w',newline='\n').write('\n'.join(runs))
