import numpy as np, sys
def load(n):
    d=np.load(n+'.npz'); return {k:d[k] for k in d.files}
def cycles(t,o1,th=2.5):
    up=np.where((o1[:-1]<th)&(o1[1:]>=th))[0]; return t[up]
def width(t,v,th,below=True,t0=0):
    m=(v<th) if below else (v>th)
    m&=t>=t0
    if not m.any(): return 0.0
    idx=np.where(m)[0]; return t[idx[-1]]-t[idx[0]]
