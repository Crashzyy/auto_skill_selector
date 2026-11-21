"""Evaluator held-out v10 (Fase 3k), hash diverifikasi."""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
EXPECTED_HASH="628bece6e31c6fcc56325a4a2d41d210b3a3d88002c51cdebe63b6a3ad8d11d4"
def main():
    import isolate_3m; isolate_3m.guard()
    import benchmark_runner as br, trainer as t
    p=Path("tests/heldout_v10.json"); h=hashlib.sha256(p.read_bytes()).hexdigest()
    if h!=EXPECTED_HASH: print(f"HASH MISMATCH: {h}"); sys.exit(2)
    print(f"SHA256 OK {h}")
    b=t._import_brain().SkillBrain(); b.reload(t.get_model_path().read_text("utf-8"))
    d=json.loads(p.read_text()); ok_n=0; by={}
    for c in d["cases"]:
        r=b.analyze_prompt(br._hook_normalize(c["prompt"]))
        ok=r["status"] in c["expect_status"]; ok_n+=ok
        g=c["group"]; s=by.setdefault(g,[0,0]); s[1]+=1; s[0]+=ok
        print(f"{c['id']:5} {'PASS' if ok else 'FAIL'} | {g:10} | {r['status']:22} | {c['prompt'][:44]}")
    print("\nBY GROUP")
    for g,(a,n) in sorted(by.items()): print(f"  {g:10} {a}/{n}")
    print(f"\nHELD-OUT V10 {ok_n}/{len(d['cases'])}")
if __name__=="__main__": main()
