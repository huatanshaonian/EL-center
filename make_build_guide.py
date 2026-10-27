"""生成“组装 / 调试流程”网页：el_driver/焊接图/装配调试流程.html（浏览器打开即用，不联网）。

内容在 build_guide_steps.py；每个阶段的测试步骤直接从 el_driver/上电测试清单.txt 按节号截取嵌进去，
所以清单改了重跑本脚本就同步。勾选状态存在浏览器里。焊接图链接是同一文件夹里的相对路径。
用法：python make_build_guide.py
"""
import html
import json
import os
import re
import time

from build_guide_steps import GENERAL, STAGES

ROOT = os.path.dirname(os.path.abspath(__file__))
ED = os.path.join(ROOT, 'el_driver')
OUT = os.path.join(ED, '焊接图', '装配调试流程.html')
CHECKLIST = os.path.join(ED, '上电测试清单.txt')


def checklist_sections():
    """上电测试清单：节号 -> (标题, 正文)。节标题行上下各有一行 ----。"""
    lines = open(CHECKLIST, encoding='utf-8').read().splitlines()
    heads = []
    for i in range(1, len(lines) - 1):
        m = re.match(r'^(\d+[a-z]?)\.\s+(.+)$', lines[i])
        if m and lines[i - 1].startswith('---') and lines[i + 1].startswith('---'):
            heads.append((i, m.group(1), m.group(2).strip()))
    out = {}
    for k, (i, num, title) in enumerate(heads):
        end = heads[k + 1][0] - 1 if k + 1 < len(heads) else len(lines)
        out[num] = (title, '\n'.join(lines[i + 2:end]).strip('\n'))
    return out


def board_title(tag):
    fn = os.path.join(ED, '焊接图', f'{tag}.html')
    if not os.path.exists(fn):
        return None
    m = re.search(r'<title>(.*?)</title>', open(fn, encoding='utf-8').read())
    return html.unescape(m.group(1)) if m else tag


def stage_html(st, secs):
    e = html.escape
    boards = []
    for t in st['boards']:
        name = board_title(t)
        boards.append(f'<a class="bd" href="{e(t)}.html">{e(name or t)}</a>' if name else f'<span class="bd miss">{e(t)}（没有焊接图）</span>')
    steps = ''.join(f'<li><label><input type="checkbox" data-k="{st["id"]}:{i}"> <span>{e(s)}</span></label></li>'
                    for i, s in enumerate(st['steps']))
    tests = []
    for n in st['tests']:
        if n not in secs:
            raise KeyError(f'上电测试清单里找不到第 {n} 节')
        title, body = secs[n]
        tests.append(f'<details><summary>上电测试清单 {e(n)}. {e(title)}</summary><pre>{e(body)}</pre></details>')
    return f'''<section id="{st["id"]}"><h2><span class="pg" data-s="{st["id"]}"></span>{e(st["title"])}</h2>
<p class="why">{e(st["why"])}</p>{"<div class='bds'>焊接图：" + "".join(boards) + "</div>" if boards else ""}
<ol>{steps}</ol>{"".join(tests)}</section>'''


def main():
    secs = checklist_sections()
    toc = ''.join(f'<li><a href="#{s["id"]}">{html.escape(s["title"])}</a> <span class="pg" data-s="{s["id"]}"></span></li>' for s in STAGES)
    gen = ''.join(f'<li>{html.escape(g)}</li>' for g in GENERAL)
    body = ''.join(stage_html(s, secs) for s in STAGES)
    page = TEMPLATE.replace('__TOC__', toc).replace('__GEN__', gen).replace('__BODY__', body) \
        .replace('__WHEN__', time.strftime('%Y-%m-%d %H:%M')) \
        .replace('__COUNTS__', json.dumps({s['id']: len(s['steps']) for s in STAGES}))
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(page)
    print(OUT, f'{len(STAGES)} 个阶段，{sum(len(s["steps"]) for s in STAGES)} 步，嵌入清单 {sum(len(s["tests"]) for s in STAGES)} 节')


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MIS-01 装配调试流程</title>
<style>
:root{--bg:#f6f5f1;--fg:#1d1d1b;--muted:#6b6a64;--card:#fff;--line:#dcdad3;--hl:#c2410c;--ok:#15803d}
@media (prefers-color-scheme: dark){:root{--bg:#161614;--fg:#ecebe6;--muted:#9a9890;--card:#1f1f1c;--line:#34332f;--hl:#fb923c;--ok:#4ade80}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.65 system-ui,"Microsoft YaHei",sans-serif}
.wrap{max-width:920px;margin:0 auto;padding:16px}h1{font-size:22px;margin:8px 0 4px}.sub{color:var(--muted);font-size:13px}
.box{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 16px;margin:14px 0}
.box h3{margin:4px 0;font-size:15px}.box ul,.box ol{margin:4px 0;padding-left:20px}
section{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 16px 12px;margin:16px 0}
h2{font-size:17px;margin:10px 0 4px}.why{color:var(--muted);margin:4px 0 8px}
.bds{margin:4px 0 8px;font-size:14px}.bd{display:inline-block;border:1px solid var(--line);border-radius:6px;padding:1px 8px;margin:2px 6px 2px 0;color:var(--fg);text-decoration:none}
.bd:hover{border-color:var(--hl)}.bd.miss{color:var(--muted)}
ol{padding-left:22px;margin:6px 0}li{margin:5px 0}label{cursor:pointer}input[type=checkbox]{transform:scale(1.15);margin-right:4px}
li.done span{color:var(--muted);text-decoration:line-through}
details{margin:6px 0;border-top:1px dashed var(--line);padding-top:6px}summary{cursor:pointer;color:var(--hl);font-size:14px}
pre{white-space:pre-wrap;font:13px/1.6 ui-monospace,Consolas,"Microsoft YaHei",monospace;background:var(--bg);padding:8px 10px;border-radius:6px;overflow-x:auto}
.pg{font-size:12px;color:var(--muted);margin-right:6px}.pg.all{color:var(--ok)}
.toc li{margin:2px 0}.toc a{color:var(--fg)}
</style></head><body><div class="wrap">
<h1>MIS-01 装配调试流程</h1>
<div class="sub">按顺序一个阶段一个阶段做；每步做完打勾（记在这个浏览器里）。各板的元件作用、电路原理点“焊接图”看；测试数值嵌在每个阶段末尾（来自 el_driver/上电测试清单.txt，__WHEN__ 生成）。写“（叫我）”的步骤是要我在电脑上做的。</div>
<div class="box"><h3>目录</h3><ol class="toc">__TOC__</ol></div>
<div class="box"><h3>每块板都适用的规矩</h3><ul>__GEN__</ul></div>
__BODY__
</div><script>
const COUNTS = __COUNTS__, KEY = 'mis01-guide';
let st = {}; try { st = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) {}
function refresh() {
  const done = {};
  for (const cb of document.querySelectorAll('input[data-k]')) {
    cb.checked = !!st[cb.dataset.k]; cb.closest('li').classList.toggle('done', cb.checked);
    const s = cb.dataset.k.split(':')[0]; if (cb.checked) done[s] = (done[s] || 0) + 1;
  }
  for (const el of document.querySelectorAll('.pg')) {
    const s = el.dataset.s, n = done[s] || 0; el.textContent = `${n}/${COUNTS[s]}`; el.classList.toggle('all', n === COUNTS[s]);
  }
}
document.addEventListener('change', e => {
  const k = e.target.dataset && e.target.dataset.k; if (!k) return;
  st[k] = e.target.checked; try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (err) {} refresh();
});
refresh();
</script></body></html>'''

if __name__ == '__main__':
    main()
