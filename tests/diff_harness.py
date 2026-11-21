#!/usr/bin/env python3
"""Harness diferensial Fase 3i: bandingkan dua binary pada SEMUA kasus.

Usage: python tests/diff_harness.py <path_binary_A> <path_binary_B>
Mencetak setiap kasus yang status atau skill terpilihnya berubah A -> B.
"""
import sys, json, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def load_engine(path):
    for m in list(sys.modules):
        if m.startswith("hermes_skill_brain"): del sys.modules[m]
    sys.path.insert(0, path)
    import hermes_skill_brain as h, trainer as t, benchmark_runner as br
    b = h.SkillBrain(); b.reload(t.get_model_path().read_text("utf-8"))
    sys.path.remove(path)
    return b, br

def all_cases():
    files = (sorted(glob.glob(str(ROOT/"tests"/"benchmark*.json"))) +
             sorted(glob.glob(str(ROOT/"tests"/"heldout_v*.json"))) +
             sorted(ROOT.glob("docs/*GUARD.json")))
    seen = set()
    for f in files:
        d = json.load(open(f))
        cs = d.get("cases") if isinstance(d, dict) else d
        if not cs and isinstance(d, dict):
            for v in d.values():
                if isinstance(v, list) and v and isinstance(v[0], dict) and "prompt" in v[0]:
                    cs = v; break
        for c in cs or []:
            if not isinstance(c, dict) or not c.get("prompt"): continue
            p = c["prompt"].strip().lower()
            key = (Path(f).name, c.get("id", "?"), p)
            if key in seen: continue
            seen.add(key)
            yield Path(f).name, c.get("id", "?"), c["prompt"], c.get("expect_status")

def main():
    import isolate_3m; isolate_3m.guard()
    if len(sys.argv) < 3:
        print("usage: diff_harness.py <binaryA> <binaryB>"); sys.exit(2)
    a, br = load_engine(sys.argv[1])
    b, _ = load_engine(sys.argv[2])
    deltas = []
    total = 0
    for f, i, p, exp in all_cases():
        total += 1
        ra = a.analyze_prompt(br._hook_normalize(p))
        rb = b.analyze_prompt(br._hook_normalize(p))
        if ra["status"] != rb["status"] or ra.get("skills") != rb.get("skills"):
            deltas.append((f, i, p, exp, ra["status"], ra["skills"], rb["status"], rb["skills"]))
    print(f"TOTAL CASES {total} | DELTAS {len(deltas)}")
    for f, i, p, exp, sa, ka, sb, kb in deltas:
        print(f"{f:28} {i:5} | {sa:20} {str(ka):50} -> {sb:20} {str(kb):50} | exp {exp} | {p[:55]}")
    print("\nDELTA IDS:", ", ".join(d[1] for d in deltas))

if __name__ == "__main__": main()
