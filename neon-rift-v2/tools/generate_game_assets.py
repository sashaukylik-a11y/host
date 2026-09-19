from pathlib import Path
import math, wave, struct, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT=Path(__file__).resolve().parents[1]
MAT=ROOT/"project"/"assets"/"materials"
AUD=ROOT/"project"/"assets"/"audio"
MAT.mkdir(parents=True,exist_ok=True)
AUD.mkdir(parents=True,exist_ok=True)

def texture(name, base, kind, seed):
    rng=np.random.default_rng(seed)
    w=h=1024
    yy,xx=np.mgrid[0:h,0:w]
    noise=rng.normal(0,1,(h,w))
    # Layered low-frequency structure without external dependencies.
    low=np.sin(xx/47.0+seed)*0.35+np.sin(yy/61.0+seed*.7)*0.35+np.sin((xx+yy)/103.0)*0.3
    grit=noise*12+low*18
    rgb=np.zeros((h,w,3),dtype=np.float32)
    rgb[:]=np.array(base,dtype=np.float32)
    rgb+=grit[:,:,None]
    if kind=="concrete":
        cracks=((np.sin(xx/19.0+np.sin(yy/53.0)*3.0)>0.993)|(np.sin(yy/23.0+np.sin(xx/71.0)*2.0)>0.995))
        rgb[cracks]*=.35
    elif kind=="metal":
        brushed=np.sin(yy/2.7)*7+np.sin(yy/11.0)*4
        rgb+=brushed[:,:,None]
        seams=(xx%256<4)|(yy%256<3)
        rgb[seams]*=.45
    elif kind=="rust":
        spots=(np.sin(xx/29.0)+np.sin(yy/37.0)+noise*.8)>1.2
        rgb[spots,0]+=45;rgb[spots,1]-=15;rgb[spots,2]-=28
    elif kind=="floor":
        seams=(xx%192<5)|(yy%192<5)
        rgb[seams]*=.48
        speck=rng.random((h,w))>.995
        rgb[speck]+=35
    elif kind=="lab":
        seams=(xx%256<5)|(yy%256<5)
        rgb[seams]*=.6
        stripe=(yy%256>210)&(yy%256<226)
        rgb[stripe]=np.array([35,105,145])
    elif kind=="asphalt":
        pebbles=rng.random((h,w))>.985
        rgb[pebbles]+=rng.integers(15,55,(pebbles.sum(),1))
    elif kind=="hazard":
        band=((xx+yy)//96)%2
        rgb[band==0]=np.array([215,158,22]);rgb[band==1]=np.array([34,38,43])
        rgb+=noise[:,:,None]*5
    elif kind=="crate":
        grain=np.sin(xx/9.0)*8+np.sin(xx/31.0)*5
        rgb+=grain[:,:,None]
        seams=(xx%256<6)|(yy%256<6)
        rgb[seams]*=.5
    arr=np.clip(rgb,0,255).astype(np.uint8)
    Image.fromarray(arr,"RGB").save(MAT/f"{name}.png",compress_level=6)

specs=[
 ("concrete",(92,96,100),"concrete",11),
 ("metal",(48,55,62),"metal",22),
 ("rust",(92,55,32),"rust",33),
 ("floor",(55,58,61),"floor",44),
 ("lab",(126,139,150),"lab",55),
 ("asphalt",(35,38,42),"asphalt",66),
 ("hazard",(170,124,24),"hazard",77),
 ("crate",(105,72,42),"crate",88),
]
for s in specs:
    texture(*s)

# Additional wall variants used by the source pack and future levels.
for i in range(1,9):
    texture(f"panel_{i:02d}",(52+i*4,60+i*3,68+i*2),"metal",100+i)

def wav(path, seconds, base_freq, seed, volume=.15):
    rate=48000
    rng=np.random.default_rng(seed)
    total=rate*seconds
    with wave.open(str(path),"wb") as wf:
        wf.setnchannels(2);wf.setsampwidth(2);wf.setframerate(rate)
        for start in range(0,total,rate):
            n=min(rate,total-start)
            t=(np.arange(n)+start)/rate
            drone=np.sin(2*np.pi*base_freq*t)*.52+np.sin(2*np.pi*base_freq*1.618*t)*.28+np.sin(2*np.pi*base_freq*.51*t)*.2
            pulse=.65+.35*np.sin(2*np.pi*.075*t+seed)
            hiss=rng.normal(0,.11,n)
            sig=np.clip((drone*pulse+hiss)*volume,-1,1)
            l=(sig*32767).astype("<i2")
            r=(np.clip(sig*.9+np.sin(2*np.pi*(base_freq+.7)*t)*.015,-1,1)*32767).astype("<i2")
            wf.writeframes(np.column_stack([l,r]).tobytes())

wav(AUD/"ambient_technical.wav",90,38,10,.12)
wav(AUD/"ambient_lab.wav",90,48,20,.11)
wav(AUD/"ambient_yard.wav",90,29,30,.13)

def tone(path, freq, dur, amp, fall=8.0):
    rate=48000
    t=np.arange(int(rate*dur))/rate
    env=np.exp(-t*fall)
    sig=(np.sin(2*np.pi*freq*t)+.25*np.sin(2*np.pi*freq*2.03*t))*amp*env
    s=np.clip(sig,-1,1)
    q=(s*32767).astype("<i2")
    with wave.open(str(path),"wb") as wf:
        wf.setnchannels(2);wf.setsampwidth(2);wf.setframerate(rate)
        wf.writeframes(np.column_stack([q,q]).tobytes())

tone(AUD/"shoot.wav",145,.18,.7,10)
tone(AUD/"hit.wav",82,.24,.55,9)
tone(AUD/"pickup.wav",760,.5,.3,4)
tone(AUD/"alarm.wav",410,1.2,.2,1.2)
tone(AUD/"reload.wav",190,.42,.22,4)

# App icon: dark rounded tile with a single luminous N.
icon=Image.new("RGBA",(256,256),(5,9,18,255))
d=ImageDraw.Draw(icon)
d.rounded_rectangle((14,14,242,242),radius=52,fill=(10,18,33,255),outline=(42,126,230,255),width=5)
try:
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",160)
except Exception:
    font=ImageFont.load_default()
bbox=d.textbbox((0,0),"N",font=font)
x=(256-(bbox[2]-bbox[0]))//2
y=(256-(bbox[3]-bbox[1]))//2-14
glow=Image.new("RGBA",(256,256),(0,0,0,0))
gd=ImageDraw.Draw(glow);gd.text((x,y),"N",font=font,fill=(45,155,255,220))
glow=glow.filter(ImageFilter.GaussianBlur(13));icon.alpha_composite(glow)
d=ImageDraw.Draw(icon);d.text((x,y),"N",font=font,fill=(220,242,255,255))
icon.save(ROOT/"project"/"icon.png")
icon.save(ROOT/"project"/"icon.ico",sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
print("Generated runtime art/audio.")
