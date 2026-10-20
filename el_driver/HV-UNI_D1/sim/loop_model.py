# -*- coding: utf-8 -*-
"""Averaged small-signal loop model of HV-UNI D1 (DCM boost, peak current mode)."""
import numpy as np
L=100e-6; fs=52.3e3; Vin=12.0; C=4.8e-6; Resr=3.0; Rs=0.5; Rtop=1.41e6
def loop(Vo, Rl, R12, C10, Chf=0.0, eta=0.85, f=np.logspace(0,5,4000)):
    Rt = 1/(1/Rl + 1/280e3)            # load || bleeder || dividers
    Io = Vo/Rt
    M = Vo/Vin
    P = Vo*Io/eta
    Ipk = np.sqrt(P/(0.5*L*fs*M/(M-1)))
    g = (1/Rt)*(2*M-1)/(M-1)
    s = 2j*np.pi*f
    Zc = Resr + 1/(s*4.7e-6)
    Zc = 1/(1/Zc + s*100e-9)
    Gp = (2*Io/Ipk) / (1/Zc + g) * (1/(3*Rs))
    Zf = R12 + 1/(s*C10)
    if Chf: Zf = 1/(1/Zf + s*Chf)
    H = Zf/Rtop
    T = Gp*H
    mag = np.abs(T)
    i = np.where(mag < 1)[0]
    if not len(i): return None
    i = i[0]
    fc = f[i]; pm = 180 + np.degrees(np.angle(T[i])) - 180 # inverting stage sign removed
    pm = 180 + np.degrees(np.angle(T[i]))
    # gain margin not relevant (no 180 crossing at low f)
    return dict(Ipk=Ipk, fc=fc, pm=pm, Vcomp=1.4+3*Rs*Ipk, Gdc=abs(Gp[0]))
if __name__=='__main__':
    for comp in [(47e3,100e-9,0),(1e6,22e-9,100e-12),(680e3,22e-9,100e-12),(470e3,33e-9,100e-12)]:
        print('R12=%g C10=%g Chf=%g'%comp)
        for Vo,Rl in [(170,8.5e3),(170,34e3),(170,1e12),(250,41.7e3),(250,1e12),(296,1e12),(112,1e12)]:
            r=loop(Vo,Rl,*comp)
            print('  %3dV RL=%-8g Ipk=%.3f Vcomp=%.2f fc=%6.1f Hz PM=%5.1f'%(Vo,Rl,r['Ipk'],r['Vcomp'],r['fc'],r['pm']))
