# -*- coding: utf-8 -*-
"""Snapshot helpers: list all nodes of a netlist, capture all node voltages at the last oscillator reset."""
import subprocess, sys, re
from pathlib import Path
SIM = Path(__file__).resolve().parent

def ng(cir, cmds, timeout=None):
    r = subprocess.run([sys.executable, str(SIM / 'dbg.py'), str(cir), ';'.join(cmds)],
                       capture_output=True, text=True, timeout=timeout)
    return r.stdout

def nodes(cir):
    out = ng(cir, ['tran 1n 2n'])
    names = re.findall(r'^stdout ([a-z0-9._]+) +[-0-9.e+]+$', out, re.M)
    return [n for n in names if n not in ('src',)]

def capture(cir, tend, timeout=None, uic=False):
    ns = nodes(cir)
    save = 'save ' + ' '.join('v(%s)' % n for n in ns)
    cmds = [save, 'tran 1u %g %g 50n%s' % (tend, tend - 60e-6, ' uic' if uic else ''),
            'meas tran tsnap when v(xu1.dd)=0.5 rise=last']
    for i, n in enumerate(ns):
        cmds.append('meas tran s%d find v(%s) at=$&tsnap' % (i, n))
    out = ng(cir, cmds, timeout)
    vals = dict(re.findall(r'^stdout (s\d+|tsnap) += +([-0-9.e+]+)', out, re.M))
    st = {n: float(vals['s%d' % i]) for i, n in enumerate(ns) if 's%d' % i in vals}
    return float(vals['tsnap']), st

def ic_lines(state):
    items = ['v(%s)=%.7g' % (n, v) for n, v in state.items()]
    lines = []
    for k in range(0, len(items), 8):
        lines.append('.ic ' + ' '.join(items[k:k + 8]))
    return lines
