"""Evaluator guard P2a' Fase 3e. Hash diverifikasi. Tidak mengubah file guard."""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
EXPECTED_HASH = "975197fe9cc3e7ceea6d15b6c89762542b9c440b8e2a85e93704f8bea3eca7cb"

def main():
    import benchmark_runner as br, trainer as t
    p = Path("docs/P2A_GUARD.json")
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    if h != EXPECTED_HASH:
        print(f"HASH MISMATCH: {h}"); sys.exit(2)
    print(f"SHA256 OK {h}")
    b = t._import_brain().SkillBrain(); b.reload(t.get_model_path().read_text("utf-8"))
    data = json.loads(p.read_text())
    passed = 0
    for c in data["cases"]:
        r = b.analyze_prompt(br._hook_normalize(c["prompt"]))
        ok = r["status"] in c["expect_status"]
        passed += ok
        print(f"{c['id']:5} {'PASS' if ok else 'FAIL'} | {c['group']:18} | {r['status']:22} | {c['prompt'][:45]}")
    print(f"\nGUARD {passed}/{len(data['cases'])}")

if __name__ == "__main__":
    main()
