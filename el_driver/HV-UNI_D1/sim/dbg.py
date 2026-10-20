import ctypes as C, os, sys
from pathlib import Path
DLLDIR=Path(r'E:/modeling/MIS-01/el_driver/tools/lceda-sim/app')
os.add_dll_directory(str(DLLDIR)); lib=C.CDLL(str(DLLDIR/'ngspice.dll'))
logs=[]
@C.CFUNCTYPE(C.c_int,C.c_char_p,C.c_int,C.c_void_p)
def output(s,i,u): logs.append(s.decode('utf-8',errors='replace'));return 0
@C.CFUNCTYPE(C.c_int,C.c_int,C.c_bool,C.c_bool,C.c_int,C.c_void_p)
def exitcb(a,b,c,d,e): logs.append('exit');return 0
lib.ngSpice_Init.argtypes=[C.c_void_p]*7
lib.ngSpice_Init(output,None,exitcb,None,None,None,None)
lines=Path(sys.argv[1]).read_text().splitlines()
arr=(C.c_char_p*(len(lines)+1))(*[s.encode() for s in lines],None)
lib.ngSpice_Circ(arr)
for c in sys.argv[2].split(';'): lib.ngSpice_Command(c.strip().encode())
print('\n'.join(l for l in logs if 'Reference value' not in l))
if len(sys.argv)>3:
    import numpy as np
    class Vec(C.Structure):
        _fields_=[('name',C.c_char_p),('type',C.c_int),('flags',C.c_short),('real',C.POINTER(C.c_double)),('complex',C.c_void_p),('length',C.c_int)]
    lib.ngGet_Vec_Info.argtypes=[C.c_char_p]; lib.ngGet_Vec_Info.restype=C.POINTER(Vec)
    out={}
    for n in sys.argv[3].split(','):
        z=lib.ngGet_Vec_Info(n.encode()).contents
        out[n]=np.ctypeslib.as_array(z.real,shape=(z.length,)).copy()
    np.savez(sys.argv[4] if len(sys.argv)>4 else 'dbg_out.npz',**out)
