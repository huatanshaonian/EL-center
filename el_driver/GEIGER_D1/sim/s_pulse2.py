from gen import *
opts={'base':{}, 'r7r61_220k':{'r7':'220k','r61':'220k'}, 'r61open_r7_220k':{'r7':'220k','r61':'1e12'},
      'cajoe_10k_470k':{'r4':'10k','r60':'10k','r7':'470k','r61':'470k'}, 'r47k_220k':{'r4':'47k','r60':'47k','r7':'220k','r61':'220k'}}
runs=[]
for on,oo in opts.items():
  for q in [0.3e-9,1e-9,3e-9]:
    for td in [10e-6,30e-6,100e-6]:
        n=f"p2_{on}_q{q*1e9:g}_td{int(td*1e6)}".replace('.','p')
        body=["VHV hv 0 400"]+clip(dict(oo,tube_pwl=tube_pwl([1e-3],q=q,tdec=td)))+click({'bz':'hiz_pu'})
        write(n,body,f'pulse {on} q={q} td={td}',".ic v(en)=2.97 v(mt)=0 v(cv4)=3.333\n.save v(ck) v(an) v(pulse) v(gm) v(o4)")
        runs.append(n)
open('pulse2_list.txt','w',newline='\n').write('\n'.join(runs))
