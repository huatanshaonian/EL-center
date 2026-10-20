# -*- coding: utf-8 -*-
"""Simulation cases for HV-UNI D1.
startup(): full power-up from 0 V (coarse, tmax 50 ns) with run_ngspice.py
steady():  all node voltages captured at the end of a power-up run (at an oscillator reset), then a fine
           (tmax 2 ns) continuation run with UIC for detailed switching waveforms, losses, ripple.
"""
import json
import numpy as np
from pathlib import Path
import gen, run, snap

SIM = Path(__file__).resolve().parent


def startup(name, p, tstop, target, tmax=50e-9, step=2e-6, extra_meas=()):
    f = gen.write(name, p)
    cmds = ['save v(hv) v(comp) i(vil) v(ovc) v(ovs) i(viin) v(sw) v(vcc) v(isns)',
            'tran %g %g 0 %g' % (step, tstop, tmax),
            'meas tran ipk max i(vil)',
            'meas tran iinmax max i(viin)',
            'meas tran hvmax max v(hv)',
            'meas tran swmax max v(sw)',
            'meas tran t50 when v(hv)=%g cross=1' % (0.5 * target),
            'meas tran t95 when v(hv)=%g cross=1' % (0.95 * target),
            'meas tran hvend avg v(hv) from=%g to=%g' % (tstop - 2e-3, tstop),
            'meas tran ovsmax max v(ovs)',
            'meas tran ovcmax max v(ovc)',
            'meas tran compmax max v(comp)',
            'meas tran vccmin min v(vcc) from=1m to=%g' % tstop]
    cmds += list(extra_meas)
    cmds.append('linearize v(hv) v(comp) i(viin) v(ovc)')
    r = run.run(f, cmds, ['time', 'v(hv)', 'v(comp)', 'i(viin)', 'v(ovc)'])
    out = dict(r['meas'])
    t = np.array(r['vectors']['time']); hv = np.array(r['vectors']['v(hv)'])
    fin = out.get('hvend', hv[-1])
    for pct in (1, 2, 5):
        bad = np.where(np.abs(hv - fin) > pct / 100 * fin)[0]
        out['tsettle_%dpct' % pct] = float(t[bad[-1]]) if len(bad) else 0.0
    # undershoot after the first peak
    ipk = int(np.argmax(hv))
    out['hvmin_after_peak'] = float(hv[ipk:].min())
    out['runtime_s'] = r['runtime_s']
    return out, r


def steady(name, p, tsnap, tstop=1.2e-3, t0=0.2e-3, tmax=2e-9, step=5e-9, snapfile=None):
    """Capture state at tsnap of the power-up run of p, then run a fine continuation."""
    pre = gen.write(name + '_pre', p)
    ts, state = snap.capture(pre, tsnap)
    if snapfile:
        Path(snapfile).write_text(json.dumps({'t': ts, 'state': state}), encoding='utf-8')
    return steady_from_state(name, p, state, tstop, t0, tmax, step)


def steady_from_state(name, p, state, tstop=1.2e-3, t0=0.2e-3, tmax=2e-9, step=5e-9):
    q = dict(p)
    q['vdc'] = True
    q['extra'] = (q.get('extra') or []) + snap.ic_lines(state)
    f = gen.write(name, q)
    pc = q.get('pcb')
    qs = 'qs' if pc else 'sns'
    d1k = 'd1k' if pc else 'hv'
    sv = 'save v(qd) v(sns) v(d1a) v(hv) v(src) v(c8e) v(gate) v(isns) v(comp) v(sw) v(vcc) v(vfb) ' \
         'i(vqd) i(vd1) i(vil) i(viin)' + (' v(qs) v(d1k) v(c8l)' if pc else '')
    cmds = [sv,
            'tran %g %g %g %g uic' % (step, tstop, t0, tmax),
            'let pq = (v(qd)-v(%s))*i(vqd)' % qs,
            'let pd = (v(d1a)-v(%s))*i(vd1)' % d1k,
            'let prs = i(vqd)*i(vqd)*0.5',
            'let pl = i(vil)*i(vil)*0.22',
            'let pin = v(src)*i(viin)',
            'let ic8 = (v(c8e)-v(c8l))/3' if pc else 'let ic8 = v(c8e)/3',
            'meas tran pq avg pq', 'meas tran pd avg pd', 'meas tran prs avg prs', 'meas tran pl avg pl',
            'meas tran pin avg pin', 'meas tran hvavg avg v(hv)', 'meas tran hvpp pp v(hv)',
            'meas tran iqrms rms i(vqd)', 'meas tran idrms rms i(vd1)', 'meas tran ilrms rms i(vil)',
            'meas tran ilavg avg i(vil)', 'meas tran idavg avg i(vd1)',
            'meas tran ilpk max i(vil)', 'meas tran iqpk max i(vqd)', 'meas tran iqmin min i(vqd)',
            'meas tran idpk max i(vd1)', 'meas tran idmin min i(vd1)',
            'meas tran vqdmax max v(qd)', 'meas tran vswmax max v(sw)', 'meas tran vswmin min v(sw)',
            'meas tran ic8rms rms ic8', 'meas tran compavg avg v(comp)', 'meas tran comppp pp v(comp)',
            'meas tran isnsmax max v(isns)', 'meas tran vgsmax max v(gate)', 'meas tran vgsmin min v(gate)',
            'meas tran vccavg avg v(vcc)', 'meas tran iinavg avg i(viin)', 'meas tran vfbpp pp v(vfb)']
    if pc:
        cmds += ['meas tran vqdsmax max v(qd,qs)', 'meas tran vsnsmax max v(sns)', 'meas tran vsnsmin min v(sns)']
    cmds.append('linearize v(sw) i(vil) v(gate) v(hv) v(isns) v(comp) i(vd1) v(qd)')
    r = run.run(f, cmds, ['time', 'v(sw)', 'i(vil)', 'v(gate)', 'v(hv)', 'v(isns)', 'v(comp)', 'i(vd1)', 'v(qd)'])
    m = dict(r['meas'])
    v = {k: np.array(x) for k, x in r['vectors'].items()}
    t = v['time']; il = v['i(vil)']; g = v['v(gate)']; dt = t[1] - t[0]
    on = g > 4.5
    # debounce: drop on-intervals shorter than 0.3 us (Miller/ringing glitches on the gate)
    edges = np.flatnonzero(np.diff(on.astype(int)))
    st = list(edges[on[edges + 1]] + 1) if len(edges) else []
    en = list(edges[~on[edges + 1]] + 1) if len(edges) else []
    rises = []
    for a in st:
        b = next((e for e in en if e > a), len(on))
        if (b - a) * dt >= 0.3e-6:
            rises.append(a)
        else:
            on[a:b] = False
    rises = np.array(rises, dtype=int)
    tons, tzeros, periods, ipks = [], [], [], []
    for a, b in zip(rises[:-1], rises[1:]):
        tons.append(on[a:b].sum() * dt)
        periods.append(t[b] - t[a])
        tzeros.append((np.abs(il[a:b]) < 0.05).sum() * dt)
        ipks.append(il[a:b].max())
    if tons:
        m.update(ton_us=float(np.mean(tons) * 1e6), ton_min_us=float(np.min(tons) * 1e6),
                 ton_max_us=float(np.max(tons) * 1e6), period_us=float(np.mean(periods) * 1e6),
                 period_min_us=float(np.min(periods) * 1e6), period_max_us=float(np.max(periods) * 1e6),
                 tzero_us=float(np.mean(tzeros) * 1e6), tzero_min_us=float(np.min(tzeros) * 1e6),
                 ipk_cyc_mean=float(np.mean(ipks)), ipk_cyc_min=float(np.min(ipks)),
                 ipk_cyc_max=float(np.max(ipks)), ncycles=len(tons))
    m['ilmin'] = float(il.min())
    m['runtime_s'] = r['runtime_s']
    return m, r


def hires(name, p, tsnap, tw0=10e-6, tw1=13.5e-6, tmax=0.1e-9, state=None):
    """High time resolution look at one switching cycle (for PCB parasitic ringing)."""
    if state is None:
        pre = gen.write(name + '_pre', p)
        ts, state = snap.capture(pre, tsnap)
    q = dict(p); q['vdc'] = True
    q['extra'] = (q.get('extra') or []) + snap.ic_lines(state)
    f = gen.write(name, q)
    pc = q.get('pcb')
    qs = 'qs' if pc else 'sns'
    cmds = ['save v(qd) v(%s) v(sw) v(hv) v(gate) v(sns) v(isns) i(vqd) i(vd1) i(vil)' % qs + (' v(d1k)' if pc else ''),
            'tran %g %g %g %g uic' % (tmax, tw1, tw0, tmax),
            'let vds = v(qd)-v(%s)' % qs,
            'meas tran vdsmax max vds', 'meas tran vswmax max v(sw)', 'meas tran hvmax max v(hv)',
            'meas tran hvmin min v(hv)', 'meas tran vsnsmin min v(sns)', 'meas tran vsnsmax max v(sns)',
            'meas tran isnsmax max v(isns)', 'meas tran idpk max i(vd1)', 'meas tran iqmin min i(vqd)',
            'linearize v(qd) v(%s) v(sw) v(hv) v(gate) v(sns) i(vqd) i(vd1)' % qs]
    r = run.run(f, cmds, ['time', 'v(qd)', 'v(%s)' % qs, 'v(sw)', 'v(hv)', 'v(gate)', 'v(sns)', 'i(vqd)', 'i(vd1)'])
    m = dict(r['meas'])
    v = {k: np.array(x) for k, x in r['vectors'].items()}
    t = v['time']; vds = v['v(qd)'] - v['v(%s)' % qs]
    # ringing after turn-off: find time vds first exceeds 0.9*max, then measure ring frequency/decay
    i0 = int(np.argmax(vds > 0.5 * vds.max()))
    seg = vds[i0:i0 + int(300e-9 / (t[1] - t[0]))]
    base = float(np.mean(v['v(hv)'])) + 1.0  # diode-clamped plateau ~ Vout + Vf
    m['vds_plateau'] = float(base)
    m['vds_overshoot'] = float(vds.max() - base)
    pk = [j for j in range(1, len(seg) - 1) if seg[j] > seg[j - 1] and seg[j] >= seg[j + 1] and seg[j] - base > 1.0]
    if len(pk) >= 2:
        m['ring_freq_MHz'] = float(1e-6 / np.mean(np.diff(t[i0:][pk][:4])))
        m['ring_peaks'] = [float(seg[j] - base) for j in pk[:6]]
    m['t_rise_ns'] = float((np.argmax(vds > 0.9 * base) - np.argmax(vds > 0.1 * base)) * (t[1] - t[0]) * 1e9)
    m['runtime_s'] = r['runtime_s']
    return m, r
