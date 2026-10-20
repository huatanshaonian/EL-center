# -*- coding: utf-8 -*-
"""Run a netlist through el_driver/simulation/run_ngspice.py and move the outputs into this folder."""
import json, re, shutil, subprocess, sys, time
from pathlib import Path

SIM = Path(__file__).resolve().parent
RUNNER = SIM.parent.parent / 'simulation' / 'run_ngspice.py'


def run(cir, commands, vectors):
    cir = Path(cir).resolve()
    t0 = time.time()
    r = subprocess.run([sys.executable, str(RUNNER), str(cir), ';'.join(commands), ','.join(vectors)],
                       capture_output=True, text=True, cwd=str(RUNNER.parent))
    dt = time.time() - t0
    for ext in ('_results.json', '_engine.log'):
        src = RUNNER.parent / (cir.stem + ext)
        if src.exists():
            shutil.move(str(src), str(SIM / (cir.stem + ext)))
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise RuntimeError('ngspice failed: %s' % cir.name)
    res = json.loads((SIM / (cir.stem + '_results.json')).read_text(encoding='utf-8'))
    meas = {}
    for line in res['log']:
        m = re.match(r'stdout\s+(\w+)\s+=\s+([-+0-9.eE]+)', line)
        if m:
            try:
                meas[m.group(1).lower()] = float(m.group(2))
            except ValueError:
                pass
    res['meas'] = meas
    res['runtime_s'] = dt
    return res
