# 调用 el_driver/simulation/run_ngspice.py，跑完把 _results.json / _engine.log 挪到本目录
import json, shutil, subprocess, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
SIMDIR = HERE.parent.parent / "simulation"
RUNNER = SIMDIR / "run_ngspice.py"

def run(name, netlist, commands, vectors):
    cir = HERE / f"{name}.cir"
    cir.write_text(netlist, encoding="utf-8", newline="\n")
    p = subprocess.run([sys.executable, str(RUNNER), str(cir), commands, ",".join(vectors)],
                       cwd=str(SIMDIR), capture_output=True, text=True, encoding="utf-8", errors="replace")
    for suf in ("_results.json", "_engine.log"):
        src = SIMDIR / f"{name}{suf}"
        if src.exists():
            shutil.move(str(src), str(HERE / f"{name}{suf}"))
    if p.returncode != 0:
        raise RuntimeError(f"{name}: {p.stdout[-2000:]} {p.stderr[-3000:]}")
    res = json.loads((HERE / f"{name}_results.json").read_text(encoding="utf-8"))
    return {k: np.array(v) for k, v in res["vectors"].items()}

def tavg(t, y, t0, t1):
    m = (t >= t0) & (t <= t1)
    return np.trapz(y[m], t[m]) / (t[m][-1] - t[m][0])

def pp(t, y, t0, t1):
    m = (t >= t0) & (t <= t1)
    return y[m].max() - y[m].min()

def cross_time(t, y, level, t0, rising=True):
    m = t >= t0
    tt, yy = t[m], y[m]
    idx = np.where(yy >= level)[0] if rising else np.where(yy <= level)[0]
    if len(idx) == 0:
        return np.nan
    i = idx[0]
    if i == 0:
        return tt[0]
    return tt[i - 1] + (level - yy[i - 1]) * (tt[i] - tt[i - 1]) / (yy[i] - yy[i - 1])
