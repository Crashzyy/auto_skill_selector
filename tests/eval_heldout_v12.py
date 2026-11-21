"""Evaluator held-out v12 (Fase 3p), hash diverifikasi."""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
import isolate_3m_guard; isolate_3m_guard.guard()
EXPECTED_HASH="a049524c0fea81eb7d5ed0adda41644b3c61259302d4e35da10e6e5ce8b5cfaf"
def main():
    import benchmark_runner as br, trainer as t
    p=Path("tests/heldout_v12.json"); h=hashlib.sha256(p.read_bytes()).hexdigest()
    if h!=EXPECTED_HASH: print(f"HASH MISMATCH: {h}"); sys.exit(2)
    print(f"SHA256 OK {h}")
    b=t._import_brain().SkillBrain(); b.reload(t.get_model_path().read_text("utf-8"))
    d=json.loads(p.read_text()); ok_n=0; by={}
    for c in d["cases"]:
        r=b.analyze_prompt(br._hook_normalize(c["prompt"]))
        ok=r["status"] in c["expect_status"]; ok_n+=ok
        g=c["group"]; s=by.setdefault(g,[0,0]); s[1]+=1; s[0]+=ok
        print(f"{c['id']:5} {'PASS' if ok else 'FAIL'} | {g:10} | {r['status']:22} | {c['prompt'][:42]}")
    print("\nBY GROUP")
    for g,(a,n) in sorted(by.items()): print(f"  {g:10} {a}/{n}")
    print(f"\nHELD-OUT V12 {ok_n}/{len(d['cases'])}")
if __name__=="__main__": main()
