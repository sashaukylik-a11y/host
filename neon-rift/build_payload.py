import os, math, wave, struct, json, hashlib, zipfile, shutil, subprocess
from pathlib import Path
import numpy as np

ROOT=Path.cwd()
PAY=ROOT/"payload"
AS=PAY/"assets"
HD=AS/"hd_materials"; TEX=AS/"textures"; AUD=AS/"audio"; MOD=AS/"models"
for d in (HD,TEX,AUD,MOD): d.mkdir(parents=True,exist_ok=True)

families=["concrete_clean","concrete_cracked","concrete_wet","steel_brushed","steel_dark","steel_blue","rust_light","rust_heavy",
"warehouse_panel","warehouse_floor","lab_white","lab_blue","lab_glass","generator_steel","generator_hazard","asphalt_dry",
"asphalt_wet","paint_peeling","ceiling_panel","wall_grime","door_security","crate_wood","crate_metal","pipe_oxidized",
"floor_grid","floor_diamond","service_wall","service_floor","yard_concrete","yard_mud","gate_metal","warning_panel"]
names=[f"{f}_{v:02d}" for f in families for v in (1,2)]
W=H=4096
def hdr(w,h):
    b=bytearray(54); b[:2]=b"BM"; struct.pack_into("<I",b,2,54+w*h*3); struct.pack_into("<I",b,10,54)
    struct.pack_into("<I",b,14,40); struct.pack_into("<i",b,18,w); struct.pack_into("<i",b,22,h); struct.pack_into("<H",b,26,1)
    struct.pack_into("<H",b,28,24); struct.pack_into("<I",b,34,w*h*3); return b
x=np.arange(W,dtype=np.uint32)[None,:]
for idx,name in enumerate(names):
    p=HD/f"{idx+1:02d}_{name}.bmp"; seed=np.uint32((0x9E3779B9*(idx+1))&0xffffffff)
    with p.open("wb",buffering=4*1024*1024) as f:
        f.write(hdr(W,H))
        for y0 in range(H-1,-1,-128):
            n=min(128,y0+1); ys=np.arange(y0,y0-n,-1,dtype=np.uint32)[:,None]
            v=x*np.uint32(1664525)+ys*np.uint32(1013904223)+seed; v^=v>>13; v*=np.uint32(1274126177); v^=v>>16
            noise=(v&255).astype(np.int16); grid=((x//64+ys//64+idx)%2)*18; seams=((x%512<5)|(ys%512<5))*55
            if any(k in name for k in ("concrete","wall","ceiling")): base=(110,112,114)
            elif "rust" in name or "oxidized" in name: base=(88,67,48)
            elif "lab_white" in name: base=(180,190,194)
            elif "blue" in name: base=(65,92,112)
            elif "asphalt" in name or "mud" in name: base=(48,48,45)
            elif "wood" in name: base=(104,78,50)
            elif "hazard" in name or "warning" in name: base=(68,92,118)
            else: base=(78,84,90)
            rough=(noise-128)//5
            r=np.clip(base[0]+rough+grid-seams//2,0,255); g=np.clip(base[1]+rough+grid-seams//2,0,255); b=np.clip(base[2]+rough+grid-seams//3,0,255)
            if "hazard" in name or "warning" in name:
                stripe=((x+ys+idx*13)//96)%2
                r=np.broadcast_to(np.where(stripe==0,215,45),(n,W)); g=np.broadcast_to(np.where(stripe==0,165,48),(n,W)); b=np.broadcast_to(np.where(stripe==0,35,52),(n,W))
            arr=np.empty((n,W,3),np.uint8); arr[:,:,0]=b; arr[:,:,1]=g; arr[:,:,2]=r; f.write(arr.tobytes())
    print(idx+1,"/",len(names),p.name,flush=True)

def small(p,idx,w=1024,h=1024):
    xx=np.arange(w,dtype=np.uint32)[None,:]; yy=np.arange(h-1,-1,-1,dtype=np.uint32)[:,None]
    v=xx*1664525+yy*1013904223+np.uint32((2654435761*(idx+11))&0xffffffff);v^=v>>13;v*=1274126177;v^=v>>16
    n=(v&255).astype(np.int16);base=(60+(idx*17)%100,65+(idx*23)%90,70+(idx*31)%80)
    a=np.empty((h,w,3),np.uint8);a[:,:,2]=np.clip(base[0]+(n-128)//6,0,255);a[:,:,1]=np.clip(base[1]+(n-128)//6,0,255);a[:,:,0]=np.clip(base[2]+(n-128)//6,0,255)
    p.write_bytes(hdr(w,h)+a.tobytes())
for i,n in enumerate(["technical_wall","warehouse_rust","service_panel","lab_panel","generator_hazard","yard_asphalt","gate_metal","crate_surface"]):small(TEX/f"{n}.bmp",i)

def ambient(p,sec,bf,seed):
    rate=48000;frames=rate*sec;rng=np.random.default_rng(seed)
    with wave.open(str(p),"wb") as wf:
        wf.setnchannels(2);wf.setsampwidth(2);wf.setframerate(rate)
        for start in range(0,frames,48000):
            n=min(48000,frames-start);t=(np.arange(n)+start)/rate
            sig=.1*np.sin(2*np.pi*bf*t)+.055*np.sin(2*np.pi*bf*1.618*t)+.025*np.sin(2*np.pi*bf*.37*t)
            noise=rng.normal(0,.012,n);pulse=.65+.35*np.sin(2*np.pi*.08*t)
            l=np.clip((sig*pulse+noise)*32767,-32767,32767).astype("<i2");r=np.clip((sig*(1-.12*pulse)+noise*.8)*32767,-32767,32767).astype("<i2")
            wf.writeframes(np.column_stack([l,r]).tobytes())
for i,(bf,s) in enumerate(((37,11),(43,22),(53,33)),1):ambient(AUD/f"ambient_zone_{i}.wav",120,bf,s)
def tone(p,freq,dur):
    rate=48000;t=np.arange(int(rate*dur))/rate;x=(np.sin(2*np.pi*freq*t)*np.exp(-t*10)*.4*32767).astype("<i2")
    with wave.open(str(p),"wb") as wf:wf.setnchannels(2);wf.setsampwidth(2);wf.setframerate(rate);wf.writeframes(np.column_stack([x,x]).tobytes())
tone(AUD/"shoot.wav",520,.18);tone(AUD/"hit.wav",170,.25);tone(AUD/"pickup.wav",820,.42)

# Minimal valid GLB library (small editable placeholders for Blender).
def glb(name,verts):
    import json,struct
    pos=b"".join(struct.pack("<fff",*v) for v in verts); idx=struct.pack("<HHH",0,1,2); binchunk=pos+idx
    js={"asset":{"version":"2.0","generator":"MonoSystem"},"buffers":[{"byteLength":len(binchunk)}],
        "bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":len(pos),"target":34962},{"buffer":0,"byteOffset":len(pos),"byteLength":len(idx),"target":34963}],
        "accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3","max":[1,1,0],"min":[-1,-1,0]},{"bufferView":1,"componentType":5123,"count":3,"type":"SCALAR"}],
        "meshes":[{"name":name,"primitives":[{"attributes":{"POSITION":0},"indices":1}]}],"nodes":[{"mesh":0,"name":name}],"scenes":[{"nodes":[0]}],"scene":0}
    jb=json.dumps(js,separators=(",",":")).encode();jb+=b" " *((4-len(jb)%4)%4);binchunk+=b"\0"*((4-len(binchunk)%4)%4)
    total=12+8+len(jb)+8+len(binchunk);data=struct.pack("<4sII",b"glTF",2,total)+struct.pack("<I4s",len(jb),b"JSON")+jb+struct.pack("<I4s",len(binchunk),b"BIN\0")+binchunk
    (MOD/f"{name}.glb").write_bytes(data)
for n in ("security_unit","security_drone","pistol","smg","generator","crate","terminal","security_door"):glb(n,[(-1,-1,0),(1,-1,0),(0,1,0)])

(PAY/"README.txt").write_text("NEON RIFT: ABANDONED\nDeveloper: MonoSystem\nTelegram: https://t.me/monobrowser\nNative Windows build.\n",encoding="utf-8")
(PAY/"CONTENT_MANIFEST.json").write_text(json.dumps({"title":"NEON RIFT: ABANDONED","developer":"MonoSystem","hd_materials":64,"resolution":"4096x4096","models":8,"audio":6},indent=2),encoding="utf-8")

# Compile game.
env=os.environ.copy();env["GOOS"]="windows";env["GOARCH"]="amd64"
subprocess.check_call(["go","build","-trimpath","-ldflags","-H=windowsgui -s -w","-o",str(PAY/"NEON_RIFT.exe"),"game.go"],env=env)

# Build compressed payload ZIP.
dist=ROOT/"dist";dist.mkdir(exist_ok=True)
zip_path=dist/"NEON_RIFT_payload.zip"
with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
    for p in sorted(PAY.rglob("*")):
        if p.is_file(): z.write(p,p.relative_to(PAY).as_posix())

# Split into release-friendly pieces.
part_size=256*1024*1024
parts=[]
with zip_path.open("rb") as f:
    i=0
    while True:
        b=f.read(part_size)
        if not b:break
        name=f"NEON_RIFT_payload.part{i:02d}"
        p=dist/name;p.write_bytes(b)
        parts.append({"name":name,"size":len(b),"sha256":hashlib.sha256(b).hexdigest()});i+=1
zip_sha=hashlib.sha256(zip_path.read_bytes()).hexdigest()
installed=sum(p.stat().st_size for p in PAY.rglob("*") if p.is_file())
manifest={"version":"1.0.0","zip_name":"NEON_RIFT_payload.zip","zip_size":zip_path.stat().st_size,"zip_sha256":zip_sha,"installed_bytes":installed,"parts":parts}
(dist/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
zip_path.unlink()
print(json.dumps(manifest,indent=2))
