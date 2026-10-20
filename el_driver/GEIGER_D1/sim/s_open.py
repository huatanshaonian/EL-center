from gen import *
import itertools
for vr1,cp in itertools.product([0,5,10],[15e-12,25e-12,40e-12]):
    n=f"open_vr{vr1}_cp{int(cp*1e12)}"
    write(n,hv_main({'vr1':vr1,'closed':False,'cp':cp}),f'open loop VR1={vr1} Cp={cp}',
          ".save v(hv) v(swg) v(em) v(o1) i(vhvc) i(dq1bv)")
    print(n)
