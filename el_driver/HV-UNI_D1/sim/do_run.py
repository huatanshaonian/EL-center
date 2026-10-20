# -*- coding: utf-8 -*-
"""Run one named case: python do_run.py <case> ; writes <case>_summary.json."""
import json, sys
from pathlib import Path
import numpy as np
import gen, run, snap, cases

SIM = Path(__file__).resolve().parent
NOLOAD = None
ORIG = dict(r12=47e3, c10=100e-9)
NEW = dict(r12=680e3, c10=22e-9, chf=100e-12)


def P(v, rl, **k):
    d = dict(rv=gen.rv_for(v), rl=rl)
    d.update(k)
    return d


STARTUP = {
    'su_170_8k5': (P(170, 8.5e3), 150e-3, 170),
    'su_170_nl': (P(170, NOLOAD), 150e-3, 170),
    'su_250_41k7': (P(250, 41.7e3), 150e-3, 250),
    'su_250_nl': (P(250, NOLOAD), 150e-3, 250),
    'su_296_nl': (P(296, NOLOAD), 150e-3, 296),
    'ovp_r8open_nl': (P(250, NOLOAD, r8=1e12), 80e-3, 322),
    'ovp_r8open_41k7': (P(250, 41.7e3, r8=1e12), 80e-3, 322),
    'su_170_8k5_new': (P(170, 8.5e3, **NEW), 60e-3, 170),
    'su_170_nl_new': (P(170, NOLOAD, **NEW), 60e-3, 170),
    'su_250_41k7_new': (P(250, 41.7e3, **NEW), 60e-3, 250),
    'su_250_nl_new': (P(250, NOLOAD, **NEW), 60e-3, 250),
    'su_296_nl_new': (P(296, NOLOAD, **NEW), 60e-3, 296),
}

STEADY = {
    'ss_170_8k5': (P(170, 8.5e3), 150e-3),
    'ss_250_41k7': (P(250, 41.7e3), 150e-3),
    'ss_170_8k5_pcb': (P(170, 8.5e3, pcb=True), 150e-3),
    'ss_250_41k7_pcb': (P(250, 41.7e3, pcb=True), 150e-3),
    'ss_296_10mA_pcb': (P(296, 29.6e3, pcb=True), 150e-3),
    'ss_170_8k5_new': (P(170, 8.5e3, **NEW), 60e-3),
    'ss_170_8k5_nochf': (P(170, 8.5e3, r12=680e3, c10=22e-9), 60e-3),
    'ss_170_8k5_pcb_nochf': (P(170, 8.5e3, pcb=True, r12=680e3, c10=22e-9), 60e-3),
    'ss_170_8k5_pcb_new': (P(170, 8.5e3, pcb=True, **NEW), 80e-3),
    'ss_296_10mA_pcb_new': (P(296, 29.6e3, pcb=True, **NEW), 80e-3),
    'ss_250_41k7_new': (P(250, 41.7e3, **NEW), 60e-3),
}

# load steps: name -> (pre-run params, tsnap, run params (base load + switched extra load), t1, t2, tstop)
# extra load is connected at t=0 (state = pre-run), disconnected at t1, reconnected at t2 (step_inv)
def STP(v, rl_pre, rbase, rx, t1, t2, tstop, tsnap, **k):
    pre = P(v, rl_pre, **k)
    runp = P(v, rbase, **k)
    runp.update(rl_step=(rx, t1, t2), step_inv=True)
    return (pre, tsnap, runp, t1, t2, tstop)


STEP = {
    'step_170_20to5': STP(170, 8.5e3, 34e3, 11.333e3, 5e-3, 65e-3, 125e-3, 150e-3),
    'step_250_6to2': STP(250, 41.7e3, 125e3, 62.5e3, 5e-3, 65e-3, 125e-3, 150e-3),
    'step_170_20to0': STP(170, 8.5e3, None, 8.5e3, 5e-3, 65e-3, 125e-3, 150e-3),
    'step_170_20to5_new': STP(170, 8.5e3, 34e3, 11.333e3, 5e-3, 25e-3, 45e-3, 60e-3, **NEW),
    'step_250_6to2_new': STP(250, 41.7e3, 125e3, 62.5e3, 5e-3, 25e-3, 45e-3, 60e-3, **NEW),
    'step_170_20to0_new': STP(170, 8.5e3, None, 8.5e3, 5e-3, 25e-3, 45e-3, 60e-3, **NEW),
}

# no-load steady state: settle from a loaded state, then fine run (pre, tsnap, run params, t_run)
CHAIN = {
    # settle with the fast (new) compensation, then the fine run uses the final params
    # (DC state is the same for both compensations: COMP is set by the needed peak current)
    'ss_170_nl': (P(170, 8.5e3, **NEW), 60e-3, P(170, NOLOAD, **NEW), 50e-3, P(170, NOLOAD)),
    'ss_250_nl': (P(250, 41.7e3, **NEW), 60e-3, P(250, NOLOAD, **NEW), 50e-3, P(250, NOLOAD)),
    'ss_170_nl_new': (P(170, 8.5e3, **NEW), 60e-3, P(170, NOLOAD, **NEW), 50e-3, P(170, NOLOAD, **NEW)),
    'ss_250_nl_new': (P(250, 41.7e3, **NEW), 60e-3, P(250, NOLOAD, **NEW), 50e-3, P(250, NOLOAD, **NEW)),
}


def do_step(name, pre, tsnap, runp, t1, t2, tstop):
    pf = gen.write(name + '_pre', pre)
    ts, state = snap.capture(pf, tsnap)
    q = dict(runp); q['vdc'] = True
    q['extra'] = snap.ic_lines(state)
    f = gen.write(name, q)
    cmds = ['save v(hv) v(comp) i(vil) v(vfb)',
            'tran 2u %g 0 50n uic' % tstop,
            'meas tran hv0 avg v(hv) from=%g to=%g' % (t1 - 2e-3, t1),
            'meas tran hvmax1 max v(hv) from=%g to=%g' % (t1, t2),
            'meas tran hvmin1 min v(hv) from=%g to=%g' % (t1, t2),
            'meas tran hvend1 avg v(hv) from=%g to=%g' % (t2 - 2e-3, t2),
            'meas tran hvmin2 min v(hv) from=%g to=%g' % (t2, tstop),
            'meas tran hvmax2 max v(hv) from=%g to=%g' % (t2, tstop),
            'meas tran hvend2 avg v(hv) from=%g to=%g' % (tstop - 2e-3, tstop),
            'linearize v(hv) v(comp)']
    r = run.run(f, cmds, ['time', 'v(hv)', 'v(comp)'])
    m = dict(r['meas'])
    t = np.array(r['vectors']['time']); hv = np.array(r['vectors']['v(hv)'])
    for tag, ta, tb, fin in (('1', t1, t2, m.get('hvend1')), ('2', t2, tstop, m.get('hvend2'))):
        sel = (t >= ta) & (t < tb)
        tt, hh = t[sel], hv[sel]
        for pct in (1, 0.5):
            bad = np.where(np.abs(hh - fin) > pct / 100 * fin)[0]
            m['tset%s_%gpct' % (tag, pct)] = float(tt[bad[-1]] - ta) if len(bad) else 0.0
        dev = hh - fin
        sgn = np.sign(np.where(np.abs(dev) > 0.005 * fin, dev, 0))
        nz = sgn[sgn != 0]
        m['nswing%s' % tag] = int((np.diff(nz) != 0).sum()) if len(nz) else 0
    m['tsnap'] = ts
    m['runtime_s'] = r['runtime_s']
    return m


def do_chain(name, pre, tsnap, runp, trun, finalp):
    pf = gen.write(name + '_pre', pre)
    ts, state = snap.capture(pf, tsnap)
    q = dict(runp); q['vdc'] = True; q['extra'] = snap.ic_lines(state)
    mid = gen.write(name + '_mid', q)
    cmds = ['save v(hv) v(comp)', 'tran 2u %g 0 50n uic' % trun,
            'meas tran hvmax max v(hv)', 'meas tran hvmin min v(hv)',
            'meas tran hvend avg v(hv) from=%g to=%g' % (trun - 2e-3, trun), 'linearize v(hv) v(comp)']
    r = run.run(mid, cmds, ['time', 'v(hv)', 'v(comp)'])
    m = {'settle_' + k: v for k, v in r['meas'].items()}
    ts2, state2 = snap.capture(mid, trun, uic=True)
    m2, _ = cases.steady_from_state(name, dict(finalp), state2, tstop=4.2e-3, t0=0.2e-3)
    m.update(m2)
    return m


def main(name):
    if name in STARTUP:
        p, ts, tgt = STARTUP[name]
        out, _ = cases.startup(name, p, ts, tgt)
    elif name in STEADY:
        p, tsnap = STEADY[name]
        out, _ = cases.steady(name, p, tsnap)
    elif name in STEP:
        out = do_step(name, *STEP[name])
    elif name in CHAIN:
        out = do_chain(name, *CHAIN[name])
    else:
        raise SystemExit('unknown case ' + name)
    (SIM / (name + '_summary.json')).write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(name, json.dumps(out))


if __name__ == '__main__':
    for n in sys.argv[1:]:
        main(n)
