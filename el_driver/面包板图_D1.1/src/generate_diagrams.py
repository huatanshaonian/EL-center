# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json, hashlib, math
S=Path(__file__).parent; O=S.parent; E=O.parent
N=json.loads((S/'netlists.json').read_text(encoding='utf-8')); EL=N['el']; PF=N['pf']
FONT='C:/Windows/Fonts/msyh.ttc'; BOLD='C:/Windows/Fonts/msyhbd.ttc'
INK='#172d40'; BLUE='#1769aa'; RED='#bd3431'; GREEN='#147357'; GRAY='#627284'
labels=[]
def font(sz=32,b=False): return ImageFont.truetype(BOLD if b else FONT,sz)
class Canvas:
 def __init__(self,w,h,title,sub=''):
  self.im=Image.new('RGB',(w,h),'white'); self.d=ImageDraw.Draw(self.im); self.w=w; self.h=h
  self.d.rectangle((0,0,w,170),fill='#eef4fa'); self.text(65,30,title,50,b=True)
  if sub:self.text(65,105,sub,28)
 def text(self,x,y,t,sz=32,c=INK,b=False,anchor=None):
  labels.append(t); self.d.multiline_text((x,y),t,font=font(sz,b),fill=c,spacing=10,anchor=anchor)
 def wire(self,*p,c=INK,width=5): self.d.line(p,fill=c,width=width,joint='curve')
 def dot(self,x,y,c=INK):self.d.ellipse((x-9,y-9,x+9,y+9),fill=c)
 def terminal(self,x,y):self.d.ellipse((x-9,y-9,x+9,y+9),fill='white',outline=INK,width=4)
 def box(self,x,y,w,h,t='',sz=32,fill='#f5f8fb'):
  self.d.rounded_rectangle((x,y,x+w,y+h),radius=14,outline=INK,width=4,fill=fill)
  if t:self.text(x+w/2,y+h/2,t,sz,b=True,anchor='mm')
 def res(self,x1,y1,x2,y2,t,tx=None,ty=None,sz=30):
  if y1==y2:
   a=x1+(x2-x1)*.25; b=x1+(x2-x1)*.75
   self.wire((x1,y1),(a,y1));self.wire((b,y1),(x2,y2));self.d.rectangle((a,y1-18,b,y1+18),fill='white',outline=INK,width=4)
   self.text(tx if tx is not None else (x1+x2)/2,ty if ty is not None else y1-70,t,sz,anchor='mm')
  else:
   a=y1+(y2-y1)*.25;b=y1+(y2-y1)*.75
   self.wire((x1,y1),(x1,a));self.wire((x1,b),(x2,y2));self.d.rectangle((x1-18,a,x1+18,b),fill='white',outline=INK,width=4)
   self.text(tx if tx is not None else x1+42,ty if ty is not None else (y1+y2)/2-35,t,sz)
 def cap(self,x,y1,y2,t,polar=False):
  m=(y1+y2)/2;self.wire((x,y1),(x,m-14));self.wire((x,m+14),(x,y2));self.wire((x-35,m-14),(x+35,m-14));self.wire((x-35,m+14),(x+35,m+14))
  self.text(x+48,m-38,t,29)
  if polar:self.text(x-65,m-65,'+',32,c=RED,b=True)
 def gnd(self,x,y,c=INK):
  self.wire((x,y),(x,y+22),c=c)
  for i,hw in enumerate((34,22,10)):self.wire((x-hw,y+22+i*12),(x+hw,y+22+i*12),c=c,width=5)
 def save(self,name):self.im.save(O/name,dpi=(180,180)); return name
 def table(self,x,y,width,heads,rows,weights=None,rowh=65,sz=28):
  weights=weights or [1]*len(heads); xs=[x]
  for q in weights:xs.append(xs[-1]+width*q/sum(weights))
  for i,row in enumerate([heads]+rows):
   yy=y+i*rowh
   self.d.rectangle((x,yy,x+width,yy+rowh),fill='#eaf1f8' if i==0 else ('white' if i%2 else '#f7f9fb'),outline='#bac7d4',width=2)
   for j,v in enumerate(row):self.text(xs[j]+14,yy+14,str(v),sz,b=(i==0))
  for xx in xs:self.wire((xx,y),(xx,y+rowh*(len(rows)+1)),c='#bac7d4',width=2)
# 独立预期端点；与网表核对后供表格和图使用。
pf_expected={
'PF_COMP':['U_PF-1','RPFPU-2','RPFH-1','RPFIB-1'],
'PF_REF':['U_PF-2','U_PF-6','U_REF-1','U_REF-3','RREF-2'],
'PF_SENSE':['U_PF-3','RPFT-2','RPFH-2','RPFB1-1'],
'GND':['U_PF-4','U_PF-5','U_REF-2','RPFB2-2','Q_PFI-1','Q_PFD-1','Q_PFO-1','CPF-2','TPPFG-1'],
'+5V_IN':['U_PF-8','RREF-1','RPFPU-1','RPFIP-1','CPF-1','TPPF5-1'],
'+24V_SENSE':['RPFT-1','TPPF24-1'],'PF_DIV':['RPFB1-2','RPFB2-1'],
'PF_INV_B':['RPFIB-2','Q_PFI-2'],'PF_INV':['RPFIP-2','Q_PFI-3','RPFD_B-1','RPFO_B-1'],
'PF_D_B':['RPFD_B-2','Q_PFD-2'],'PF_O_B':['RPFO_B-2','Q_PFO-2'],
'PFAIL_DOCK_N':['Q_PFD-3','TPPFD-1'],'PFAIL_OPI_N':['Q_PFO-3','TPPFO-1']}
for net,pins in pf_expected.items(): assert set(pins)==set(PF['nets'][net]),(net,pins)
assert set(PF['nets'])==set(pf_expected)
assert 'U_PF-7' not in PF['pins']
for p,v in {'RREF':'1kΩ','RPFT':'100kΩ','RPFH':'510kΩ','RPFB1':'13kΩ','RPFB2':'150Ω','RPFPU':'2.2kΩ','RPFIB':'68kΩ','RPFIP':'10kΩ','RPFD_B':'10kΩ','RPFO_B':'10kΩ'}.items():assert PF['parts'][p]['Value']==v,(p,v)
chs=[]
for i,sig in enumerate(['UD0','UD1','UD2','UD3','LD0','LD1','LD2','LD3','CP2','CP1','S'],1):
 u='U1' if i<=8 else 'U2'; a=i+1 if i<=8 else i-7;b=20-a
 p='P1' if i<=8 else 'P2'; dp=i+4 if i<=8 else i-4; cn=[2,1,4,3,6,5,8,7,9,11,13][i-1]
 checks={p+'-'+str(dp):'EL_'+sig+'_3V3','RA%d-1'%i:'EL_'+sig+'_3V3','RA%d-2'%i:'BUF_'+sig+'_A','RPA%d-1'%i:'BUF_'+sig+'_A','RPA%d-2'%i:'GND',u+'-'+str(a):'BUF_'+sig+'_A',u+'-'+str(b):'BUF_'+sig+'_B','RB%d-1'%i:'BUF_'+sig+'_B','RB%d-2'%i:'EL_'+sig+'_5V','RPB%d-1'%i:'EL_'+sig+'_5V','RPB%d-2'%i:'GND','J_EL-'+str(cn):'EL_'+sig+'_5V'}
 for k,v in checks.items():assert EL['pins'][k]==v,(k,v)
 for pfx,val in [('RA','1kΩ'),('RPA','100kΩ'),('RPB','100kΩ'),('RB','33Ω' if i<=8 else '47Ω')]:assert EL['parts'][pfx+str(i)]['Value']==val
 chs.append(dict(i=i,signal=sig,dock=('J5' if i<=8 else 'J6')+'-'+str(dp),design=p+'-'+str(dp),u=u,a=a,b=b,cn=cn,rb=33 if i<=8 else 47))
for u in ['U1','U2']:
 for pin,net in {1:'+5V_EL',20:'+5V_EL',10:'GND',19:'OE_N'}.items():assert EL['pins'][u+'-'+str(pin)]==net
for pin in range(5,10):assert EL['pins']['U2-'+str(pin)]=='GND'
for pin in range(11,16):assert 'U2-'+str(pin) not in EL['pins']
for pin in [10,12,14,15,16]:assert EL['pins']['J_EL-'+str(pin)]=='GND'
for pin in [17,18]:assert EL['pins']['J_EL-'+str(pin)]=='+5V_EL'
for pin in [19,20]:assert EL['pins']['J_EL-'+str(pin)]=='+12V_EL'
for k,v in {'ROE-1':'3V3_FPGA','ROE-2':'OE_N','P2-8':'OE_N','C1-1':'+5V_EL','C1-2':'GND','C2-1':'+5V_EL','C2-2':'GND','C3-1':'+5V_EL','C3-2':'GND'}.items():assert EL['pins'][k]==v
(S/'11路接线映射.json').write_text(json.dumps(chs,ensure_ascii=False,indent=2),encoding='utf-8')
# 图1：方框是逐脚器件符号，所有电源和地均画实线。
c=Canvas(4800,2900,'图1  PFAIL 完整实验电路（实验1：不接屏、不接任何处理器 IO）','D1.1 标称接法；全部电阻 1%；实心圆点=相连，无圆点交叉=不相连。器件方框内标的是脚号。')
c.wire((120,290),(4030,290),c=RED);c.text(130,210,'USB-A 充电头红线：+5V_IN；先用万用表确认',34,c=RED)
c.wire((120,2450),(4030,2450),width=7);c.text(130,2490,'公共 GND：USB 黑线、可调电源负端、所有器件地脚直接相连',32)
# USB电源实物连接框
c.box(80,420,360,330,'USB-A充电头\n5V / ≥2A\n红正、黑负',30)
c.wire((200,420),(200,290));c.dot(200,290)
c.wire((120,750),(40,750),(40,2450),(120,2450));c.dot(120,2450)
# 参考源
c.dot(650,290)
c.res(650,290,650,690,'RREF\n1kΩ',720,430);c.wire((650,690),(650,1050),(1300,1050));c.dot(650,1050);c.dot(1100,1050)
c.box(570,1700,360,240,'U_REF\nTL431AILP',30)
c.wire((650,1050),(650,1700));c.wire((850,1050),(850,1700));c.dot(850,1050)
c.text(590,1625,'1 K',27);c.text(880,1625,'3 REF',27);c.wire((750,1940),(750,2450));c.dot(750,2450);c.text(780,1960,'2 ANODE',27)
c.text(690,950,'PF_REF ≈2.495V',31,c=BLUE)
# 比较器全部8脚
c.box(1300,850,600,800,'U_PF\nLM393P\nDIP-8',40)
for x,y,t in [(1320,1000,'2  −'),(1320,1250,'3  +'),(1320,1400,'5  +（备用）'),(1320,1530,'6  −（备用）'),(1730,1000,'1 OUT'),(1740,1530,'7 NC'),(1550,870,'8 VCC'),(1550,1580,'4 GND')]:c.text(x,y,t,27)
c.wire((1600,290),(1600,850));c.dot(1600,290)
c.wire((1600,1650),(1600,1710),(1750,1710),(1750,2450));c.dot(1750,2450)
c.wire((1300,1450),(1190,1450),(1190,2450));c.dot(1190,2450)
c.wire((1300,1550),(1100,1550),(1100,1050))
c.wire((1900,1550),(2000,1550));c.text(1970,1590,'悬空',28,c=RED)
# 模拟输入与分压
c.box(70,1450,260,320,'可调电源\n模拟24V\n限流20mA',29)
c.wire((160,1450),(160,1300),(220,1300));c.res(220,1300,420,1300,'RPFT 100kΩ')
c.wire((420,1300),(1300,1300));c.text(470,1190,'PF_SENSE',24,c=BLUE)
c.wire((160,1770),(160,2450));c.dot(160,2450);c.text(70,1350,'+24V_SENSE',25)
c.res(450,1490,450,1730,'RPFB1\n13kΩ',480,1490,25);c.wire((450,1300),(450,1490));c.dot(450,1300)
c.wire((450,1730),(450,1870));c.text(420,1800,'PF_DIV',24,c=BLUE,anchor='ra')
c.res(450,1870,450,2130,'RPFB2\n150Ω',480,1980,25);c.wire((450,2130),(450,2450));c.dot(450,2450)
# 正反馈闭环
c.wire((1000,1300),(1000,2220),(1330,2220));c.dot(1000,1300)
c.res(1330,2220,1830,2220,'RPFH 510kΩ（迟滞）',1580,2150)
c.wire((1830,2220),(2350,2220),(2350,1050));c.dot(2350,1050)
c.wire((1900,1050),(2500,1050));c.text(2020,950,'PF_COMP',30,c=BLUE)
c.res(2350,290,2350,690,'RPFPU\n2.2kΩ',2420,425);c.wire((2350,690),(2350,1050));c.dot(2350,290)
# 去耦独立画实线接至电源轨/地轨
c.wire((2050,290),(2050,430));c.dot(2050,290);c.cap(2050,430,710,'CPF\n100nF');c.wire((2050,710),(2200,710),(2200,2450));c.dot(2200,2450)
# 反相级
c.res(2500,1050,2800,1050,'RPFIB 68kΩ',2650,980)
c.box(2900,900,340,360,'Q_PFI\n2N3904',30);c.wire((2800,1050),(2900,1050));c.text(2910,1065,'2 B',26)
c.wire((3070,1260),(3070,2450));c.dot(3070,2450);c.text(3090,1300,'1 E',26)
c.wire((3070,900),(3070,760),(3390,760));c.text(3090,815,'3 C',26)
c.res(3070,290,3070,600,'RPFIP\n10kΩ',3140,390);c.wire((3070,600),(3070,760));c.dot(3070,760);c.dot(3070,290)
c.text(3150,670,'PF_INV',30,c=BLUE)
c.wire((3390,760),(3390,2010));c.dot(3390,1460)
# 双路独立开集电极，两个额外上拉实际画出
for name,y,resn,rb,xx,outnet in [('Q_PFD',1310,'RPFD_B',1460,3700,'PFAIL_DOCK_N'),('Q_PFO',1860,'RPFO_B',2010,3700,'PFAIL_OPI_N')]:
 c.res(3390,rb,3550,rb,resn+'\n10kΩ',3470,rb-100,24)
 c.box(3550,y,300,320,name+'\n2N3904',28);c.text(3560,rb+25,'2 B',25)
 cy=y-170;c.wire((3700,y),(3700,cy),(4050,cy));c.text(3720,y-70,'3 C',25)
 if name=='Q_PFD':
  c.res(3700,290,3700,690,'测试上拉\nR_TEST_D\n10kΩ',3460,390,27);c.wire((3700,690),(3700,cy));c.dot(3700,cy);c.dot(3700,290)
  c.wire((3700,y+320),(3700,y+350),(3300,y+350),(3300,2450));c.dot(3300,2450)
 else:
  c.res(3970,290,3970,690,'测试上拉\nR_TEST_O\n10kΩ',4005,390,25);c.wire((3970,690),(3970,cy));c.dot(3970,cy);c.dot(3970,290)
  c.wire((3700,y+320),(3700,2450));c.dot(3700,2450)
 c.text(3720,y+330,'1 E',25);c.terminal(4050,cy);c.text(4110,cy-30,outnet,30,c=BLUE)
c.text(140,2600,'24V 只进入 RPFT 上端，绝不能接 LM393 的 8 脚。两路输出测试上拉仅供本实验使用。',36,c=RED,b=True)
c.text(140,2670,'转接 Dock/OPi 前拆除两只测试上拉；分别改用接收端的 3.3V 上拉，两个输出不能并接。',33)
c.text(140,2750,'13k 未到货：分压下臂整体改成 12k + 1.2k（不再串 150Ω）；12k 也没有：10k+1k+1k+1k 串联代替 13k，150Ω 照常。',33)
c.save('图1_掉电检测PFAIL.png')
# 图2A/B 顶视
for u in ['U1','U2']:
 c=Canvas(2800,2050,'图2'+('A' if u=='U1' else 'B')+'  '+u+' SN74AHCT245N 顶视（从有字的一面看）','缺口向上；左侧自上而下1–10，右侧自上而下20–11。不要从底部焊脚面读此图。')
 c.box(1100,320,600,1420,'SN74\nAHCT245N\n'+u,52)
 c.d.arc((1310,250,1490,430),0,180,fill=INK,width=7);c.d.ellipse((1140,360,1160,380),fill=INK);c.text(1150,230,'缺口 / 1脚圆点',30)
 for j in range(10):
  y=440+j*125; lp=j+1;rp=20-j
  for pin,x,side in [(lp,1100,'L'),(rp,1700,'R')]:
   net=EL['pins'].get(u+'-'+str(pin),'NC 悬空（不接线）')
   col=RED if u=='U2' and (5<=pin<=9 or 11<=pin<=15) else INK
   if side=='L':c.wire((970,y),(1100,y));c.text(1015,y-45,str(pin),32,c=col,b=True);c.text(930,y-23,net,31,c=col,anchor='ra')
   else:c.wire((1700,y),(1830,y));c.text(1730,y-45,str(pin),32,c=col,b=True);c.text(1870,y-23,net,31,c=col)
 c.text(160,1820,'1 DIR 接 +5V_EL；20 VCC 接 +5V_EL；10 接 GND；19 /OE 接 OE_N。',32)
 c.text(160,1890,'U2：5–9脚必须接地；11–15脚必须悬空。' if u=='U2' else '2脚(A1)→18脚(B1)，3脚(A2)→17脚(B2)……；DIR=高、/OE=低时 A→B。',34,c=RED,b=True)
 c.save('图2'+('A_U1' if u=='U1' else 'B_U2')+'_245顶视引脚.png')
# 图3 单路完整示范+总对照（走线不横穿信号线；去耦电容就近接地符号）
c=Canvas(4000,2700,'图3  一路信号链 + 芯片供电 / 使能（以 UD0 为例）','其余10路按下方表格重复；RPA/RPB接在线的两侧，不能放错到串阻另一端。接地符号＝接公共 GND。')
c.wire((1700,300),(3240,300),c=RED);c.text(1750,215,'USB 5V：+5V_EL（U1、U2共同供电）',32,c=RED)
c.box(1760,600,500,600,'U1\n245\nA → B',43)
c.wire((1900,300),(1900,600));c.dot(1900,300);c.text(1915,535,'1 DIR',28)
c.wire((2100,300),(2100,600));c.dot(2100,300);c.text(2115,535,'20 VCC',28)
# OE：3V3 → ROE → OE_N 横线在芯片上方，从芯片顶边进 19 脚
c.text(200,250,'Dock 3V3_FPGA（P2-1/2）',31,c=GREEN);c.wire((200,320),(900,320),c=GREEN);c.res(900,320,900,500,'ROE\n10kΩ',950,350)
c.wire((900,500),(1800,500),(1800,600));c.dot(900,500);c.text(1640,535,'19 /OE',28)
c.wire((900,500),(300,500));c.text(140,520,'Dock J6-8 / P2-8：OE_N',29,c=GREEN)
# 信号链
c.text(120,690,'Dock J5-5\n（P1-5）',30);c.wire((170,830),(490,830));c.res(490,830,790,830,'RA1 1kΩ')
c.wire((790,830),(1760,830));c.dot(1100,830);c.text(1200,720,'BUF_UD0_A',29,c=BLUE);c.text(1775,760,'2 A',28)
c.res(1100,940,1100,1170,'RPA1\n100kΩ',1160,970);c.wire((1100,830),(1100,940));c.wire((1100,1170),(1100,1440));c.dot(1100,1440)
c.wire((2260,830),(2490,830));c.text(2190,760,'18 B',28);c.res(2490,830,2790,830,'RB1 33Ω',None,900)
c.wire((2790,830),(3750,830));c.dot(3400,830);c.text(3450,860,'EL_UD0_5V',29,c=BLUE);c.text(3540,690,'屏线末端\nCN5-2',31)
c.res(3400,940,3400,1170,'RPB1\n100kΩ',3470,970);c.wire((3400,830),(3400,940));c.wire((3400,1170),(3400,1440));c.dot(3400,1440)
c.wire((2000,1200),(2000,1440));c.text(2030,1220,'10 GND',28);c.dot(2000,1440)
c.wire((140,1440),(3750,1440));c.text(150,1480,'共同 GND',29)
# 去耦：5V 轨 → 电容 → 接地符号，全部在信号线上方
c.wire((2450,300),(2450,380));c.dot(2450,300);c.cap(2450,380,560,'C1 100nF\nU1就近');c.gnd(2450,560)
c.wire((2850,300),(2850,380));c.dot(2850,300);c.cap(2850,380,560,'C3 10µF\n正极朝5V',polar=True);c.gnd(2850,560)
c.text(120,1580,'U2同样接1/20/10/19脚，另装C2=100nF；C3两片共用一只。RB9–RB11标称47Ω。',31,c=RED)
rows=[[x['signal'],x['dock']+' / '+x['design'],'RA'+str(x['i'])+' 1k',x['u']+'-'+str(x['a']),x['u']+'-'+str(x['b']),'RB'+str(x['i'])+' '+str(x['rb'])+'Ω',str(x['cn'])] for x in chs]
c.table(100,1680,3800,['信号','Dock / 原理图脚','A串阻','245 A脚','245 B脚','B串阻','CN5脚'],rows,[.7,1.8,1.15,1,1,1.2,.7],rowh=72,sz=28)
c.save('图3_单路信号链与11路对照.png')
# 图4 静态实验完整接法，一路示例（OE 从芯片顶边进；跳线②与去耦用就近接地符号）
c=Canvas(3600,2050,'图4  实验2：静态测试（不接屏，不接 Dock IO）','实线示例为 A 输入高电平、/OE 禁用；改变状态用图中的单根可移跳线，先拔再插。接地符号＝接公共 GND。')
c.box(100,280,540,230,'Dock（USB-C供电）\n仅取3.3V和GND',32)
c.box(2750,280,650,230,'USB-A充电头\n5V / ≥2A',34)
c.wire((640,350),(1150,350),(1150,420),c=GREEN);c.dot(800,350);c.text(680,250,'3V3_FPGA',30,c=GREEN)
c.wire((640,450),(720,450),(720,1690));c.dot(720,1690)
c.wire((100,1690),(3400,1690),width=7);c.text(150,1740,'公共 GND',32)
c.wire((3050,510),(3050,620),(1950,620),c=RED);c.text(2650,550,'+5V_EL',29,c=RED)
c.wire((3350,510),(3350,1690));c.dot(3350,1690)
c.box(1800,850,520,590,'U1 / U2\nSN74AHCT245N\nA → B',34)
c.wire((1950,620),(1950,850));c.dot(1950,620);c.text(1965,770,'1 DIR',28)
c.wire((2250,620),(2250,850));c.dot(2250,620);c.text(2265,770,'20 VCC',28)
c.wire((2070,1440),(2070,1690));c.dot(2070,1690);c.text(2110,1480,'10 GND',28)
# ROE 与 OE_N：全部在信号线上方，从芯片顶边进 19 脚
c.res(1150,420,1150,660,'ROE 10kΩ',1200,440);c.wire((1150,660),(1150,750),(1850,750),(1850,850));c.dot(1150,750);c.text(1690,775,'19 /OE',27)
c.wire((1150,750),(1020,750));c.terminal(1000,750);c.terminal(1000,830);c.gnd(1000,840)
c.text(1060,790,'跳线②：开路=禁用\n短接这两孔=使能',29,c=BLUE)
# A源为单极切换示意，只有一根线
c.wire((800,350),(800,880));c.terminal(800,880);c.text(150,820,'高：接3.3V',30,c=GREEN)
c.wire((800,1300),(800,1690));c.terminal(800,1300);c.dot(800,1690);c.text(160,1240,'低：接GND',30)
c.wire((800,880),(970,1090),(1100,1090),c=GREEN);c.text(370,960,'可移跳线①\n只能接一端',30,c=GREEN)
c.res(1100,1090,1380,1090,'RAi 1kΩ');c.wire((1380,1090),(1800,1090));c.dot(1510,1090)
c.res(1510,1190,1510,1420,'RPAi\n100kΩ',1570,1220);c.wire((1510,1090),(1510,1190));c.wire((1510,1420),(1510,1690));c.dot(1510,1690)
c.text(1810,1020,'A脚见图3',26)
c.wire((2320,1090),(2450,1090));c.res(2450,1090,2740,1090,'RBi 33/47Ω');c.wire((2740,1090),(3150,1090));c.terminal(3150,1090);c.text(3000,980,'测这里\n串阻之后',30,c=BLUE)
c.res(2850,1190,2850,1420,'RPBi\n100kΩ',2920,1220);c.wire((2850,1090),(2850,1190));c.dot(2850,1090);c.wire((2850,1420),(2850,1690));c.dot(2850,1690)
# 去耦：5V 轨 → 电容 → 接地符号，在信号线上方
c.wire((2550,620),(2550,660));c.dot(2550,620);c.cap(2550,660,820,'C1/C2 100nF');c.gnd(2550,820)
c.text(150,1840,'每片各一只100nF；C3 10µF仍按图3接5V与GND。图中的i按图3替换为1–11。',32)
c.text(150,1910,'先有5V，再加A侧3.3V；关闭5V前，先把全部A输入改接GND，再断Dock。',33,c=RED,b=True)
c.save('图4_静态测试接线.png')
# 图5 大电流回路全连线框图（VD 单独走最上层；各电源地经左侧地线汇到公共地点，正线与地线互不交叉）
c=Canvas(3600,2100,'图5  真屏供电：VL先上后下；VD后上先下','粗线为屏的供电与回流，直接走端子/线束；面包板只给缓冲器小电流，不承载屏电流。')
c.box(100,250,670,300,'单路可调电源\n12.0V → VD\n实验3保持输出关',36)
c.box(100,700,670,290,'USB-A 5V ≥2A\n红 +5V / 黑 GND\n先用表确认极性',36)
c.box(100,1400,670,220,'Dock GND\n只取地，屏不用Dock 5V',32)
c.box(1330,700,700,200,'5V分线端子 / Wago',36)
c.box(1330,1050,700,220,'245面包板\n+5V轨 / GND轨',34)
c.box(1330,1460,700,210,'公共地点 / 地端子',36)
c.box(2620,250,820,1450,'',36)
c.text(2780,280,'屏 CN5 / J_EL',44,b=True)
for y,t in [(420,'19、20：VD +12V'),(820,'17、18：VL +5V'),(1450,'10 / 12 / 14 / 15 / 16\n全部为GND')]:c.text(2780,y,t,36)
# VD：可调电源 → CN5 19/20，最上层，无任何交叉
c.wire((770,330),(2400,330),(2400,460),(2620,460),c='#bd6d14',width=12);c.text(1300,250,'VD粗线：19、20 两只针都接',31,c='#bd6d14')
# VL：USB → Wago → CN5 17/18；Wago → 面包板细线
c.wire((770,780),(1330,780),c=RED,width=12);c.wire((2030,780),(2400,780),(2400,860),(2620,860),c=RED,width=12)
c.wire((1500,900),(1500,1050),c=RED,width=5);c.text(1530,935,'细线：只给245供电',29,c=RED)
c.text(2050,690,'屏电流直达CN5，不经面包板',31,c=RED)
# 地：三路电源地从左侧汇流，到公共地点；面包板地、CN5地各自接公共地点
c.wire((100,480),(50,480),(50,1850),(1500,1850),(1500,1670),width=12)
c.wire((100,920),(50,920),width=12);c.dot(50,920)
c.wire((100,1510),(50,1510),width=6);c.dot(50,1510)
c.text(70,1880,'各电源负端 / 黑线 → 公共地点',30)
c.wire((1680,1270),(1680,1460));c.text(1710,1330,'面包板GND',29)
c.wire((2030,1560),(2620,1560),width=12)
c.text(120,1960,'USB绿/白线分别剪短绝缘。USB充电头不能设限流，上电前必须加倍检查。两路正电源彼此独立；所有GND共地。',31,c=RED,b=True)
c.text(120,2030,'VD未降至1V以下时，继续保持VL和扫描。',31)
c.save('图5_真屏供电端子接线.png')
# 图6：明确的编号归一化视图，不假称已确认实际镜像方向
c=Canvas(3600,2050,'图6  DF11-20 屏线针号与功能（先确认实物1脚，再用此图）','编号归一化示意：将1脚标记放在左上。不是已确认的屏插座正视图或线尾视图，不能凭图的左右直接插线。')
c.text(120,250,'▲ = 1脚识别基准；实物三角/腔号位置、插合面与出线面的镜像关系：待实物确认。',33,c=RED,b=True)
c.d.rounded_rectangle((220,490,3370,980),radius=25,outline=INK,width=6,fill='#f5f8fb')
c.text(130,390,'▲ 1脚',37,c=RED,b=True)
for j in range(10):
 x=390+j*305
 for pin,y in [(2*j+1,630),(2*j+2,850)]:
  net=EL['pins']['J_EL-'+str(pin)];short=net.replace('EL_','').replace('_5V','').replace('+5V_EL','VL +5V').replace('+12V_EL','VD +12V')
  c.d.ellipse((x-42,y-42,x+42,y+42),fill='white',outline=RED if pin==1 else INK,width=4)
  c.text(x,y,str(pin),32,c=RED if pin==1 else INK,b=True,anchor='mm');c.text(x,y+70,short,27,anchor='mm')
c.text(90,620,'奇数排',27);c.text(90,840,'偶数排',27)
c.text(150,1100,'电气定义来自 D1.1 网表 J_EL-1～20；屏幕端名称为 CN5。两者编号必须逐针直通。',32)
c.text(150,1200,'先依据壳体极性标记/腔号 + 官方原图确认视向，再断电测线束1–1至20–20。',33,c=RED,b=True)
c.text(150,1270,'蜂鸣档核对GND组、VL组、VD组，只作交叉检查；它不能单独证明1脚方向。',33)
c.text(150,1410,'出处：Hirose《DF11 Series Catalog》2026-08-01版，印刷第5页（PDF第5页）',31)
c.text(150,1470,'Crimping Socket：DF11-20DS-2C；第9页 Right Angle Pin Header：DF11-20DP-2DS。',30)
c.text(150,1580,'官方2D图：DF11-20DS-2C，文档0000995267，第1页（1页文件）。',31)
c.text(150,1670,'已核实：2mm双排、20针、官方标有No.1/No.2与极性标记。',31)
c.text(150,1740,'尚未核实：你手上成品线与屏插座的具体观察方向；未确认前不进行实验3、4。',33,c=RED,b=True)
c.save('图6_DF11针号与待确认视向.png')
# 图7 布局是分区，不冒充逐孔接线图。
c=Canvas(3600,2400,'图7  两块面包板的摆放分区（俯视，缺口均朝图上方）','这是摆放示意，不是逐孔布线照片；实际连线遵循图1/3/4与逐脚表，每插一根线就核对两端。')
def board(x,y,title,items):
 c.box(x,y,1500,1720,'',fill='#fcfcf7');c.text(x+60,y+35,title,38,b=True)
 for xx,t,col in [(x+80,'+5V',RED),(x+210,'GND',INK),(x+1240,'3.3V',GREEN),(x+1380,'GND',INK)]:
  c.wire((xx,y+160),(xx,y+1560),c=col,width=6);c.text(xx-45,y+110,t,26,c=col)
 for row in range(32):
  yy=y+225+row*39
  for col in range(10):
   xx=x+350+col*75+(75 if col>=5 else 0)
   c.d.ellipse((xx-5,yy-5,xx+5,yy+5),fill='#a2a9ac')
 c.d.rectangle((x+710,y+190,x+765,y+1510),fill='#ecece5');c.text(x+700,y+1570,'中央隔离沟',27)
 for xx,yy,w,h,t in items:c.box(x+xx,y+yy,w,h,t,30)
board(120,300,'面包板A：PFAIL 独立实验',[(600,300,280,220,'LM393P\n缺口向上'),(340,750,320,170,'TL431\n逐脚接线'),(820,750,370,200,'三只2N3904\n各脚用独立孔排'),(340,1100,850,180,'按图1布置分压、反馈、基极电阻')])
board(1950,300,'面包板B：两片245',[(600,300,280,420,'U1\n缺口向上\n跨中央沟'),(600,870,280,420,'U2\n缺口向上\n跨中央沟'),(310,760,860,80,'RA/RPA在左；RB/RPB在右')])
c.text(220,2080,'每片IC跨中央沟，左右两排脚不能插进同一组相通的5孔。电源轨中断处先测通断。',33,c=RED,b=True)
c.text(220,2150,'3.3V轨与5V轨绝不相连；两板不必同时上电。图1的24V输入只放在A板指定输入端。',32)
c.text(220,2220,'100nF靠近各IC电源脚，地回路要短；屏大电流端子放面包板外，参见图5。',32)
c.save('图7_面包板摆放分区.png')
# 输出审计数据：端点电气核对与图形检查分开。
report={'PFAIL':{'net_count':len(pf_expected),'pin_count':len(PF['pins']),'status':'PASS：全部46个端点与网表一致，7脚无网络，另加两只10k测试上拉'},'channels':{'count':len(chs),'status':'PASS：每路12个连接端点及4个电阻值核对'},'U2_unused':'PASS：5–9 GND；11–15 无网络','power_control':'PASS：两片245电源、DIR、OE、ROE、C1/C2/C3与CN5电源组核对','scope':'仅新建文档/图；未修改原理图、网表、BOM','limitations':['图6为编号归一化示意，实物视向尚待确认；不能当作已核实的机械正视图','尚未进行实物实验，也未由Claude审核','端点断言不等同于自动识别PNG连通性；图形另作目视检查']}
(S/'接线校验结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(S/'图中文字.txt').write_text('\n'.join(labels),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
