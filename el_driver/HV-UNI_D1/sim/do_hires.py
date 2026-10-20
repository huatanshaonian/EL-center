# -*- coding: utf-8 -*-
"""High-resolution switching edge runs (PCB parasitics, snubber variants). python do_hires.py <case>"""
import json, sys
from pathlib import Path
import cases, snap, gen
from do_run import P
SIM = Path(__file__).resolve().parent
CASES = {
    'hr_170_8k5_ideal': P(170, 8.5e3),
    'hr_170_8k5_pcb': P(170, 8.5e3, pcb=True),
    'hr_296_10mA_ideal': P(296, 29.6e3),
    'hr_296_10mA_pcb': P(296, 29.6e3, pcb=True),
    'hr_296_10mA_pcb_snub': P(296, 29.6e3, pcb=True, snub=(100, 47e-12)),
    'hr_296_10mA_pcb_L2x': P(296, 29.6e3, pcb=True, lpar=dict(lsw=18e-9, lhv=26e-9, lgnd=44e-9, lsrc=18e-9)),
}
def main(name):
    p = CASES[name]
    m, r = cases.hires(name, p, 150e-3)
    (SIM / (name + '_summary.json')).write_text(json.dumps(m, indent=1), encoding='utf-8')
    print(name, json.dumps(m))
if __name__ == '__main__':
    for n in sys.argv[1:]:
        main(n)
