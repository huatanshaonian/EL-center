# 与 el_driver/simulation/run_ngspice.py 相同的嘉立创仿真包 ngspice-42 DLL 调用方式，
# 区别：结果存成 sim/<网表名>.npz（全部时间点，体积小），日志存 sim/<网表名>_engine.log。
# 用法：python ngrun.py <cir> "tran ...;..." "time,v(hv),..."
import ctypes as C, os, sys, json
from pathlib import Path
import numpy as np
SIM = Path(__file__).resolve().parent
DLLDIR = SIM.parent.parent / 'tools' / 'lceda-sim' / 'app'
os.add_dll_directory(str(DLLDIR))
lib = C.CDLL(str(DLLDIR / 'ngspice.dll'))
logs = []
@C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)
def output(s, i, u):
    logs.append(s.decode('utf-8', errors='replace')); return 0
@C.CFUNCTYPE(C.c_int, C.c_int, C.c_bool, C.c_bool, C.c_int, C.c_void_p)
def exitcb(a, b, c, d, e):
    logs.append('controlled_exit ' + str(a)); return 0
lib.ngSpice_Init.argtypes = [C.c_void_p] * 7
lib.ngSpice_Command.argtypes = [C.c_char_p]
lib.ngSpice_Circ.argtypes = [C.POINTER(C.c_char_p)]
class Complex(C.Structure):
    _fields_ = [('real', C.c_double), ('imag', C.c_double)]
class Vec(C.Structure):
    _fields_ = [('name', C.c_char_p), ('type', C.c_int), ('flags', C.c_short),
                ('real', C.POINTER(C.c_double)), ('complex', C.POINTER(Complex)), ('length', C.c_int)]
lib.ngGet_Vec_Info.argtypes = [C.c_char_p]
lib.ngGet_Vec_Info.restype = C.POINTER(Vec)
assert lib.ngSpice_Init(output, None, exitcb, None, None, None, None) == 0
p = Path(sys.argv[1])
lines = p.read_text(encoding='utf-8').splitlines()
arr = (C.c_char_p * (len(lines) + 1))(*[s.encode() for s in lines], None)
assert lib.ngSpice_Circ(arr) == 0
for cmd in sys.argv[2].split(';'):
    if cmd.strip():
        st = lib.ngSpice_Command(cmd.strip().encode()); assert st == 0, (cmd, st)
out = {}
for name in sys.argv[3].split(','):
    v = lib.ngGet_Vec_Info(name.encode())
    if not v or not v.contents.real:
        logs.append('MISSING ' + name); continue
    z = v.contents
    out[name] = np.ctypeslib.as_array(z.real, shape=(z.length,)).copy()
ext = {}
dt = float(os.environ.get('NG_DT', '0'))
if dt > 0 and 'time' in out:
    t = out['time']; tg = np.arange(t[0], t[-1], dt)
    for k, v in list(out.items()):
        if k == 'time': continue
        ext[k + '_max'] = np.array([v.max()]); ext[k + '_min'] = np.array([v.min()])
        out[k] = np.interp(tg, t, v).astype(np.float32)
    out['time'] = tg
np.savez_compressed(SIM / (p.stem + '.npz'), **{k.replace('(', '_').replace(')', '').replace(',', '_'): v for k, v in list(out.items()) + list(ext.items())})
(SIM / (p.stem + '_engine.log')).write_text('\n'.join(logs), encoding='utf-8')
print(json.dumps({'netlist': p.name, 'points': {k: len(v) for k, v in out.items()},
                  'tail': [l for l in logs if 'rror' in l or 'arn' in l][-6:] + logs[-3:]}, ensure_ascii=False))
