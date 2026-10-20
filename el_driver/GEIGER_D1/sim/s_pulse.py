from gen import *
runs=[]
for q in [0.3e-9,1e-9,3e-9]:
    for td in [10e-6,30e-6,100e-6]:
        n=f"pulse_q{q*1e9:g}_td{int(td*1e6)}".replace('.','p')
        body=["VHV hv 0 400"]+clip({'tube_pwl':tube_pwl([1e-3],q=q,tdec=td)})+click({'bz':'hiz_pu'})
        write(n,body,f'single pulse q={q} td={td}',".ic v(en)=2.97 v(mt)=0 v(cv4)=3.333\n.save v(ck) v(an) v(b5) v(pq) v(pulse) v(gm) v(o4) v(bzn) v(en) v(mt) i(vlsm) i(vshape)")
        runs.append(n)
open('pulse_list.txt','w').write('\n'.join(runs))
