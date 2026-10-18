from PIL import Image,ImageDraw
from pathlib import Path
p=Path(__file__).parent
files=sorted(p.parent.glob('图*.png'))
for i,f in enumerate(files):
 im=Image.open(f); im.thumbnail((1500,1200)); im.save(p/(f.stem+'_预览.png'))
