"""Evaluator sekali pakai untuk tests/heldout_v7.json (Fase 3g)."""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
EXPECTED_HASH = "b411991d705321f8a53e5b8e83228f78fd503bf107117da854402a0801905666"

def main():
    import isolate_3m; isolate_3m.guard()
    import benchmark_runner as br, trainer as t
    p = Path("tests/heldout_v7.json")
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    if h != EXPECTED_HASH:
        print(f"HASH MISMATCH: {h}"); sys.exit(2)
    print(f"SHA256 OK {h}")
    b = t._import_brain().SkillBrain(); b.reload(t.get_model_path().read_text("utf-8"))
    data = json.loads(p.read_text())
    passed = 0
    by = {}
    for c in data["cases"]:
        r = b.analyze_prompt(br._hook_normalize(c["prompt"]))
        errs = []
        if r["status"] not in c["expect_status"]:
            errs.append(f"status {r['status']} not in {c['expect_status']}")
        ok = not errs
        passed += ok
        g = c.get("group", "?"); s = by.setdefault(g, [0, 0]); s[1] += 1; s[0] += ok
        print(f"{c['id']:5} {'PASS' if ok else 'FAIL'} | {g} | {r['status']:22} | {c['prompt'][:45]}")
    print("\nBY GROUP")
    for g, (a, n) in sorted(by.items()): print(f"  {g} {a}/{n}")
    print(f"\nHELD-OUT V7 {passed}/{len(data['cases'])}")

if __name__ == "__main__":
    main()
