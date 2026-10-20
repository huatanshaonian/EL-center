from gen import write
names=[]
for cc in ['0.5p','1p','2p']:
  for cesp in ['35p','1n']:
    for tr in ['50n','500n']:
        n=f"pl_cc{cc}_cesp{cesp}_tr{tr}".replace('.','p')
        body=["V33 v33 0 3.3","RPU v33 pulse 10k",f"CL pulse 0 {cesp}",
              # 机箱里 250 V 开关节点：52 kHz 方波，上升/下降 tr
              f"VSW sw 0 PULSE(0 250 2u {tr} {tr} 9.6u 19.2u)", f"CC sw pulse {cc}",
              # Q5 空闲（关断），R62 100 Ω + 线
              "RQ pulse 0 1e12"]
        write(n,body,n,"")
        names.append(n)
open('pl_list.txt','w',newline='\n').write('\n'.join(names))
