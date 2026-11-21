"""Evaluator held-out v9 (Fase 3j), hash diverifikasi."""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
EXPECTED_HASH="9ae2a6d7b9b3eebbfc748f7e1e8339680e4c2485a5694435d70e6c57a3b927fa"
def main():
    import isolate_3m; isolate_3m.guard()
    import benchmark_runner as br, trainer as t
    p=Path("tests/heldout_v9.json"); h=hashlib.sha256(p.read_bytes()).hexdigest()
    if h!=EXPECTED_HASH: print(f"HASH MISMATCH: {h}"); sys.exit(2)
    print(f"SHA256 OK {h}")
    b=t._import_brain().SkillBrain(); b.reload(t.get_model_path().read_text("utf-8"))
    d=json.loads(p.read_text()); ok_n=0; by={}
    for c in d["cases"]:
        r=b.analyze_prompt(br._hook_normalize(c["prompt"]))
        ok=r["status"] in c["expect_status"]; ok_n+=ok
        g=c["group"]; s=by.setdefault(g,[0,0]); s[1]+=1; s[0]+=ok
        print(f"{c['id']:5} {'PASS' if ok else 'FAIL'} | {g:12} | {r['status']:22} | {c['prompt'][:44]}")
    print("\nBY GROUP")
    for g,(a,n) in sorted(by.items()): print(f"  {g:12} {a}/{n}")
    print(f"\nHELD-OUT V9 {ok_n}/{len(d['cases'])}")
if __name__=="__main__": main()
