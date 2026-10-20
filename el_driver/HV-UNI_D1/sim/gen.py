# -*- coding: utf-8 -*-
"""HV-UNI D1 netlist generator (component values/connections taken from HV-UNI_D1.net)."""
from pathlib import Path

SIM = Path(__file__).resolve().parent
M = (SIM / 'models').as_posix()


def rv_for(vout, vref=2.5):
    """RV1 value (ohm) for a given output voltage: Vo = 2.5*(1 + 1.41M/(12k + RV1))."""
    return 1.41e6 / (vout / vref - 1) - 12e3


def build(p):
    """p: dict of options; returns netlist text."""
    g = dict(
        title='HV-UNI D1', rv=rv_for(170), rl=8.5e3, rl_step=None,
        r8=470e3, pcb=False, snub=None, dsnub=None,
        r12=47e3, c10=100e-9, chf=None, ss=None,
        v12_ramp=0.5e-3, ic_hv=None, vin=12.0, rsrc=0.3,
        lpar=None, vdc=False, extra=None,
    )
    g.update(p)
    L = []
    a = L.append
    a('* ' + g['title'])
    a('.include %s/uc3843a_beh.lib' % M)
    a('.include %s/sihf840.lib' % M)
    a('.include %s/uf4007.txt' % M)
    a('.include %s/misc.lib' % M)
    # ---- input: 12 V (PCB-3 P-MOS switch + 1.1 A PPTC + wiring ~0.3 ohm) ----
    if g['vdc']:
        a('VSRC src 0 %g' % g['vin'])
    else:
        a('VSRC src 0 PWL(0 0 %g %g)' % (g['v12_ramp'], g['vin']))
    a('VIIN src src1 0')
    a('RSRC src1 vin %g' % g['rsrc'])
    a('C1 vin c1e 47u')
    a('RC1 c1e 0 0.3')
    a('C2 vin 0 100n')
    # LED indicator
    a('R23 vin leda 4.7k')
    a('D2 leda 0 DLED')
    # ---- UC3843 supply ----
    a('R1 vin vcc 10')
    a('C3 vcc 0 10u')
    a('C4 vcc 0 100n')
    a('C5 vref 0 100n')
    a('R2 vref rtct 33k')
    a('C6 rtct 0 1n')
    a('XU1 comp vfb isns rtct 0 drv vcc vref UC3843A')
    # ---- gate ----
    a('R3 drv gate 22')
    a('R4 gate 0 10k')
    # ---- power stage ----
    a('VIL vin l1a 0')
    a('L1 l1a l1b 100u')
    a('RL1 l1b sw 0.22')
    a('CL1 l1a sw 8p')
    pcb = g['pcb']
    if pcb:
        lp = g['lpar'] or {}
        ld = lp.get('ld', 4.5e-9); ls = lp.get('ls', 7.5e-9)
        lsw = lp.get('lsw', 9e-9); lhv = lp.get('lhv', 13e-9)
        lgnd = lp.get('lgnd', 22e-9); lsrc = lp.get('lsrc', 9e-9)
        # Q1 die nodes qd/qs; package leads LD/LS; traces to D1, C8/C9, RS1
        a('LSW sw swd %g' % lsw)
        a('LD swd qdp %g' % ld)
        a('VQD qdp qd 0')
        a('XQ1 qd gate qs irf840')
        a('LS qs qsp %g' % ls)
        a('LSRC qsp sns %g' % lsrc)
        a('RS1 sns rsm 0.5')
        a('LRS rsm 0 1n')
        a('VD1 sw d1a 0')
        a('XD1 d1a d1k D1WRAP')
        a('LHV d1k hv %g' % lhv)
        a('C8 hv c8e 4.7u')
        a('RC8 c8e c8l 3')
        a('LC8 c8l gc 15n')
        a('C9 hv c9e 100n')
        a('RC9 c9e c9l 0.03')
        a('LC9 c9l gc 8n')
        a('LGND gc 0 %g' % lgnd)
    else:
        a('VQD sw qd 0')
        a('XQ1 qd gate sns irf840')
        a('RS1 sns 0 0.5')
        a('VD1 sw d1a 0')
        a('XD1 d1a hv D1WRAP')
        a('C8 hv c8e 4.7u')
        a('RC8 c8e 0 3')
        a('C9 hv c9e 100n')
        a('RC9 c9e 0 0.03')
    a('.subckt D1WRAP a k')
    a('D1 a k UF4007')
    a('.ends')
    if g['snub']:
        rs, cs = g['snub']  # RC snubber drain->GND
        a('RSN sw snm %g' % rs)
        a('CSN snm 0 %g' % cs)
    if g['dsnub']:
        rs, cs = g['dsnub']  # RC across D1
        a('RDS sw dsm %g' % rs)
        a('CDS dsm hv %g' % cs)
    # ---- current sense filter + OVP injection ----
    a('R7 sns isns 1k')
    a('C7 isns 0 1n')
    a('R20 ovc isns 1k')
    # ---- feedback ----
    a('R8 hv fb1 %g' % g['r8'])
    a('R9 fb1 fb2 470k')
    a('R10 fb2 vfb 470k')
    a('R11 vfb fb3 12k')
    a('RV1 fb3 0 %g' % max(g['rv'], 1e-3))
    a('R12 comp cmp1 %g' % g['r12'])
    a('C10 cmp1 vfb %g' % g['c10'])
    if g['chf']:
        a('CHF comp vfb %g' % g['chf'])
    if g['ss']:
        # soft start: VREF -> Rss -> Css, PNP-less version: diode from COMP to Css node
        rss, css = g['ss']
        a('RSS vref ssn %g' % rss)
        a('CSS ssn 0 %g' % css)
        a('DSS comp ssn DSS1')
        a('.model DSS1 D(IS=1e-14 N=1)')
    # ---- overvoltage protection ----
    a('R13 hv ov1 470k')
    a('R14 ov1 ov2 470k')
    a('R15 ov2 ovs 470k')
    a('R16 ovs ov3 10k')
    a('R17 ov3 0 1k')
    a('XU2 ovs ovk 0 TL431B')
    a('R19 ovb ovk 2.2k')
    a('R18 vref ovb 10k')
    a('Q2 ovc ovb vref Q2N3906')
    # ---- bleeder + load ----
    a('R21 hv bl1 220k')
    a('R22 bl1 0 220k')
    if g['rl']:
        a('RLOAD hv 0 %g' % g['rl'])
    if g['rl_step']:
        rextra, t1, t2 = g['rl_step']  # extra load connected between t1 and t2
        a('RLX hv rlx %g' % rextra)
        a('SLX rlx 0 ctl 0 SWL')
        if g.get('step_inv'):  # extra load connected except between t1 and t2
            a('VCTL ctl 0 PWL(0 1 %g 1 %g 0 %g 0 %g 1)' % (t1, t1 + 1e-6, t2, t2 + 1e-6))
        else:
            a('VCTL ctl 0 PWL(0 0 %g 0 %g 1 %g 1 %g 0)' % (t1, t1 + 1e-6, t2, t2 + 1e-6))
        a('.model SWL SW(Ron=0.1 Roff=1e9 Vt=0.5 Vh=0)')
    if g['ic_hv'] is not None:
        a('.ic v(hv)=%g' % g['ic_hv'])
    if g['extra']:
        L.extend(g['extra'])
    a('.options method=gear reltol=1e-3 abstol=1e-9 vntol=1e-5 itl4=100 chgtol=1e-14')
    a('.end')
    return '\n'.join(L) + '\n'


def write(name, p):
    f = SIM / (name + '.cir')
    f.write_text(build(p), encoding='utf-8', newline='\n')
    return f
