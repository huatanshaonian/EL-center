# Fit EM87/6E2 triode (Koren) to Philips/Mullard operating table: Vb=250, Ra=100k
import numpy as np
from scipy.optimize import least_squares
Vg=np.array([0,-10,-15.]); Ia=np.array([2.0e-3,0.5e-3,0.2e-3]); Va=250-Ia*100e3
def koren(va,vg,mu,kp,kg1,x=1.5,kvb=300.):
    e1=va/kp*np.log1p(np.exp(np.clip(kp*(1/mu+vg/np.sqrt(kvb+va*va)),-50,50)))
    return np.where(e1>0,e1**x/kg1,0)
def res(p):
    mu,kp,kg1=p
    return np.log(koren(Va,Vg,mu,kp,kg1)/Ia)
for x0 in ([20,300,1500],[30,200,1000],[15,100,2000]):
    r=least_squares(res,x0,bounds=([3,5,10],[100,2000,1e5]))
    print(r.x, np.exp(r.fun))
mu,kp,kg1=r.x
# operating point solve at Vb, Ra
from scipy.optimize import brentq
def op(vg,vb=250.):
    return brentq(lambda ia: ia-koren(vb-ia*1e5,vg,mu,kp,kg1),0,vb/1e5)
for vg in [0,-1,-2,-3,-4,-5,-6,-7,-8,-10,-12,-15]:
    ia=op(vg); print(vg, round(ia*1e3,3), round(250-ia*1e5,1))
