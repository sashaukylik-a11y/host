from pathlib import Path
import hashlib, json, wave, struct, sys

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/"project"
DIST=ROOT/"dist"
errors=[]

def need(cond,msg):
    if not cond: errors.append(msg)

need((DIST/"NEON_RIFT.exe").exists(),"Windows EXE missing")
need((DIST/"NEON_RIFT.pck").exists(),"PCK missing")
if (DIST/"NEON_RIFT.exe").exists():
    b=(DIST/"NEON_RIFT.exe").read_bytes()[:2]
    need(b==b"MZ","Windows EXE does not have MZ header")

mats=list((PROJECT/"assets"/"materials").glob("*.png"))
models=list((PROJECT/"assets"/"models").glob("*.glb"))
audio=list((PROJECT/"assets"/"audio").glob("*.wav"))
need(len(mats)>=16,f"runtime materials too few: {len(mats)}")
need(len(models)>=7,f"GLB models too few: {len(models)}")
need(len(audio)>=8,f"audio files too few: {len(audio)}")

for p in models:
    b=p.read_bytes()
    need(len(b)>100 and b[:4]==b"glTF",f"invalid GLB: {p.name}")

for p in audio:
    try:
        with wave.open(str(p),"rb") as wf:
            need(wf.getnchannels()==2,f"{p.name}: not stereo")
            need(wf.getframerate()==48000,f"{p.name}: wrong sample rate")
    except Exception as e:
        errors.append(f"{p.name}: invalid WAV {e}")

for p in PROJECT.rglob("*.gd"):
    text=p.read_text(encoding="utf-8")
    need("http://" not in text.lower() and "https://" not in text.lower(),f"network URL in runtime script {p}")
    need("localhost" not in text.lower() and "127.0.0.1" not in text,f"host reference in runtime script {p}")

manifest_path=DIST/"manifest_v2.json"
need(manifest_path.exists(),"release manifest missing")
if manifest_path.exists():
    m=json.loads(manifest_path.read_text())
    need(6*1024**3 <= m["installed_bytes"] <= 8*1024**3,"installed payload is not 6-8 GiB")
    need(len(m["parts"])>=2,"payload was not split")
    for part in m["parts"]:
        p=DIST/part["name"]
        need(p.exists(),f"missing release part {part['name']}")
        if p.exists():
            need(p.stat().st_size==part["size"],f"size mismatch {p.name}")
            h=hashlib.sha256(p.read_bytes()).hexdigest()
            need(h==part["sha256"],f"hash mismatch {p.name}")

if errors:
    print("AUDIT FAILED")
    for e in errors: print("-",e)
    sys.exit(1)
print("AUDIT PASS")
print("runtime materials",len(mats),"models",len(models),"audio",len(audio))
