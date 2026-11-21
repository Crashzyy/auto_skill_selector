"""Evaluator FMT_ADV_GUARD Fase 3h (hash diverifikasi)."""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
EXPECTED_HASH="17bbb97430d2ff92432a30bad25da90c10c3539e1d0b1531fe3b25da54733a05"
def main():
    import isolate_3m; isolate_3m.guard()
    import benchmark_runner as br, trainer as t
    p=Path("docs/FMT_ADV_GUARD.json"); h=hashlib.sha256(p.read_bytes()).hexdigest()
    if h!=EXPECTED_HASH: print(f"HASH MISMATCH: {h}"); sys.exit(2)
    print(f"SHA256 OK {h}")
    b=t._import_brain().SkillBrain(); b.reload(t.get_model_path().read_text("utf-8"))
    d=json.loads(p.read_text()); ok_n=0
    for c in d["cases"]:
        r=b.analyze_prompt(br._hook_normalize(c["prompt"]))
        ok=r["status"] in c["expect_status"]; ok_n+=ok
        print(f"{c['id']:5} {'PASS' if ok else 'FAIL'} | {c['group']:22} | {r['status']:22} | skills {r['skills']} | {c['prompt'][:45]}")
    print(f"\nFMT_ADV_GUARD {ok_n}/{len(d['cases'])}")
if __name__=="__main__": main()
