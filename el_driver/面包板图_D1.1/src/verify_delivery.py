# -*- coding: utf-8 -*-
from pathlib import Path
from PIL import Image
import json,re,hashlib,zipfile
S=Path(__file__).parent; F=S.parent; E=F.parent; D=E/'D1.1'; M=E/'面包板实验接线与验收_D1.1.md'
hashfile=S/'输入文件哈希.json'; before=json.loads(hashfile.read_text(encoding='utf-8'))
protected=[]
for p,h in before.items():
 now=hashlib.sha256(Path(p).read_bytes()).hexdigest();assert h==now, p
 protected.append({'path':p,'sha256':now,'unchanged':True})
md=M.read_text(encoding='utf-8');labs=(S/'图中文字.txt').read_text(encoding='utf-8')
# 检查只针对新文档与图中文字，源网表和原稿不属于新文档文本。
banned=['LM4040','499k','0.1%','390Ω','10pF','16Ω','6.8Ω','灯泡','NID Remote']
for word in banned:assert word not in md and word not in labs,word
assert len(re.findall(r'^## 实验[0-4]：',md,re.M))==5
for segment in re.split(r'^## 实验[0-4]：',md,flags=re.M)[1:]:
 for heading in ['### 目的','### 所需设备','### 接线表','### 逐步操作','### 测量点与期望值','### 常见问题']:
  assert heading in segment,heading
 assert '记录表' in segment and '实测' in segment
imgs=[]
for p in sorted(F.glob('图*.png')):
 with Image.open(p) as im:
  im.verify()
 with Image.open(p) as im:
  assert im.width>=2000
  imgs.append({'file':p.name,'width':im.width,'height':im.height,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
assert len(imgs)==8
for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',md):
 if link.startswith('https://'):continue
 assert (E/link).exists(),link
mapping=json.loads((S/'11路接线映射.json').read_text(encoding='utf-8'));assert len(mapping)==11
for x in mapping:
 if x['i']>=9:assert x['rb']==47
thresholds=[]
for r in [13150,13200,13000]:
 falling=2.495*(1+100000/r+100000/510000)-4.85*100000/510000
 rising=2.495*(1+100000/r+100000/510000)-.10*100000/510000
 thresholds.append({'下臂Ω':r,'下降估算V':round(falling,3),'回升估算V':round(rising,3),'迟滞V':round(rising-falling,3),'假设':'Vref2.495V, VcompH4.85V, VcompL0.10V；忽略偏置/公差/温漂'})
result={'status':'PASS','protected_inputs':protected,'images':imgs,'markdown_image_links':'PASS','forbidden_legacy_terms':'PASS：新MD与所有绘图文字无9项禁用词','experiment_structure':'PASS：0–4均有设备、接线、步骤、测量期望、实测记录及常见问题','threshold_estimates':thresholds,'remaining':['DF11官方机械视图图像及实物观察方向待核验','FPGA测试程序尚未完成','物理实验未进行','Claude独立审核未进行']}
(S/'交付自检结果.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
# 可交审的完整相对目录；不包含旧图/未检查版本。
pack=[M,F/'交付说明.txt']+list(F.glob('图*.png'))+[S/x for x in ['Claude审核任务.txt','接线校验结果.json','交付自检结果.json','generate_diagrams.py','build_document.py','verify_delivery.py','netlists.json','11路接线映射.json','输入文件哈希.json']]+[D/x for x in ['EL_IF_D1.1.net','PFAIL_D1.1.net','EL_IF_D1.1_原理图.pdf','PFAIL_D1.1_原理图.pdf']]
z=S/'面包板D1.1_Claude交审包.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zz:
 for p in pack:zz.write(p,p.relative_to(E))
with zipfile.ZipFile(z) as zz:assert zz.testzip() is None
print(json.dumps({'status':result['status'],'images':[(q['file'],q['width'],q['height']) for q in imgs],'unchanged_files':len(protected),'threshold_estimates':thresholds,'review_package':str(z),'zip_bytes':z.stat().st_size},ensure_ascii=False,indent=2))
