from gen import *
SV=".save v(hv) v(swg) v(em) v(o1) v(rst) v(fbn) v(refp) i(vhvc) v(v5hv)"
write('open_vr4_cp25',hv_main({'vr1':4,'closed':False,'cp':25e-12}),'open VR1=4',SV)
write('closed_vr4',hv_main({'vr1':4,'closed':True,'cp':25e-12}),'closed VR1=4',SV)
write('closed_vr4_cp15',hv_main({'vr1':4,'closed':True,'cp':15e-12}),'closed VR1=4 cp15',SV)
write('closed_vr4_cp40',hv_main({'vr1':4,'closed':True,'cp':40e-12}),'closed VR1=4 cp40',SV)
