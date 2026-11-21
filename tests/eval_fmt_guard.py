"""Evaluator FMT_GUARD Fase 3g. Hash diverifikasi."""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
EXPECTED_HASH = "fea04dbd860c2911c1fb8013fbd24a1d6ed55b5c15b8495113bdd0390a1d3ddd"

def main():
    import benchmark_runner as br, trainer as t
    p = Path("docs/FMT_GUARD.json")
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    if h != EXPECTED_HASH:
        print(f"HASH MISMATCH: {h}"); sys.exit(2)
    print(f"SHA256 OK {h}")
    b = t._import_brain().SkillBrain(); b.reload(t.get_model_path().read_text("utf-8"))
    data = json.loads(p.read_text())
    passed = 0
    for c in data["cases"]:
        r = b.analyze_prompt(br._hook_normalize(c["prompt"]))
        errs = []
        if r["status"] not in c["expect_status"]:
            errs.append(f"status {r['status']} not in {c['expect_status']}")
        skills = set(s.lower() for s in r.get("skills", []))
        for s in c.get("forbid_skills", []):
            if s.lower() in skills:
                errs.append(f"skill {s} activated (forbidden)")
        ok = not errs
        passed += ok
        print(f"{c['id']:5} {'PASS' if ok else 'FAIL'} | {c['group']:20} | {r['status']:22} | {c['prompt'][:45]}"
              + ("" if ok else "  <- " + "; ".join(errs)))
    print(f"\nFMT_GUARD {passed}/{len(data['cases'])}")

if __name__ == "__main__":
    main()
