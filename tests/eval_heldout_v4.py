"""Evaluator sekali pakai untuk tests/heldout_v4.json (Fase 3 gerbang akhir).

TIDAK mengubah file held-out v4 (hash tetap a2c082fd...). Hash diverifikasi
sebelum evaluasi. Mendukung: expect_status, expect_status_not,
expect_banned_contains, expect_banned_excludes, forbid_skills.
"""
import hashlib, json, sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

EXPECTED_HASH = "a2c082fd5ab90eedd3e68712040262da88fd677652caf8aed77ea2e7b80902d8"

def eval_case(case, r):
    errs = []
    status = r["status"]
    banned = set(r.get("global_banned_set", []))
    skills = set(s.lower() for s in r.get("skills", []))
    if case.get("expect_status") and status not in case.get("expect_status", []):
        errs.append(f"status {status} not in {case.get('expect_status')}")
    for s in case.get("expect_status_not", []):
        if status == s:
            errs.append(f"status {status} == forbidden {s}")
    for s in case.get("expect_banned_contains", []):
        if s not in banned:
            errs.append(f"banned missing {s}")
    for s in case.get("expect_banned_excludes", []):
        if s in banned:
            errs.append(f"banned has {s} (should exclude)")
    for s in case.get("forbid_skills", []):
        if s.lower() in skills:
            errs.append(f"skill {s} activated (forbidden)")
    return errs

def main():
    import benchmark_runner as br, trainer as t
    p = Path("tests/heldout_v4.json")
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    if h != EXPECTED_HASH:
        print(f"HASH MISMATCH: {h}"); sys.exit(2)
    print(f"SHA256 OK {h}")
    b = t._import_brain().SkillBrain(); b.reload(t.get_model_path().read_text("utf-8"))
    data = json.loads(p.read_text())
    passed = 0
    for c in data["cases"]:
        r = b.analyze_prompt(br._hook_normalize(c["prompt"]))
        errs = eval_case(c, r)
        ok = not errs
        passed += ok
        print(f"{c['id']:5} {'PASS' if ok else 'FAIL'} | {r['status']:22} | {c['prompt'][:45]}"
              + ("" if ok else "  <- " + "; ".join(errs)))
    print(f"\nHELD-OUT {passed}/{len(data['cases'])}")

if __name__ == "__main__":
    main()