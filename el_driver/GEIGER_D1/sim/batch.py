# python batch.py "<tran cmd>" "<vectors>" name1 name2 ...  并行跑多个网表
import sys, subprocess
from concurrent.futures import ThreadPoolExecutor
cmd, vecs, names = sys.argv[1], sys.argv[2], sys.argv[3:]
def run(n):
    r = subprocess.run([sys.executable, 'ngrun.py', n + '.cir', cmd, vecs], capture_output=True, text=True, encoding='utf-8', errors='replace')
    return n, (r.stdout[-300:] + r.stderr[-300:]).strip()
with ThreadPoolExecutor(12) as ex:
    for n, s in ex.map(run, names):
        print(n, '|', s[:300])
