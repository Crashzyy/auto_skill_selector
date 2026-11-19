"""Regression stress permanen (Fase 1.4) — dari fuzz_metamorphic.stress_cases().

Dua lapis:
  1. FAST (default): semua kasus stress lewat jalur produksi
     (_hook_normalize + SkillBrain.analyze_prompt) in-process. Memastikan
     tidak ada exception & hasil memenuhi invarian dasar. Lambat ditandai
     `slow` (payload besar) — tetap dijalankan, hanya diberi label.
  2. SLOW (--slow): subset raw-Rust di SUBPROCESS (tanpa normalisasi hook)
     untuk membuktikan panic-safety mesin itu sendiri: returncode negatif
     (sinyal abort) = temuan kritis. lone_surrogate di jalur raw memang
     ditolak PyO3 (UnicodeEncodeError, rc=1) — itu EXPECTED, hook yang
     menanganinya (dibuang sebagai Cs).

Jalankan:
  HERMES_HOME=/tmp/hermes-sandbox python tests/test_stress_regression.py
  HERMES_HOME=/tmp/hermes-sandbox python tests/test_stress_regression.py --slow
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE))

import benchmark_runner as br  # noqa: E402
import fuzz_metamorphic as fz  # noqa: E402

STATUSES = {"NO_SKILL_NEEDED", "MATCHED_SINGLE", "MATCHED_MULTI",
            "MATCHED_PARTIAL_AND_HUNT", "HUNT_NEW_SKILL", "CLARIFY_AMBIGUOUS"}

# Kasus yang secara desain lambat (payload besar / pengulangan masif).
SLOW_CASES = {"repeat_dan_20000", "repeat_jangan_pakai_2000", "commas_100k", "one_token_1MB"}


def fast_layer() -> int:
    import trainer as t
    mj = t.get_model_path().read_text("utf-8")
    brain = t._import_brain().SkillBrain()
    brain.reload(mj)
    failures = 0
    for name, prompt in fz.stress_cases().items():
        tag = "slow" if name in SLOW_CASES else "fast"
        t0 = time.perf_counter()
        try:
            norm = br._hook_normalize(prompt)
            r = brain.analyze_prompt(norm)
            errs = []
            if r.get("status") not in STATUSES:
                errs.append(f"status tak dikenal: {r.get('status')}")
            if len(r.get("clauses") or []) > 3:
                errs.append(">3 klausa")
            banned = set(r.get("global_banned_set") or [])
            if banned & {s.lower() for s in (r.get("skills") or [])}:
                errs.append("skill terlarang lolos")
            if r.get("status") in ("NO_SKILL_NEEDED", "CLARIFY_AMBIGUOUS") and r.get("skills"):
                errs.append("status tanpa skill tapi skills tak kosong")
            dt = (time.perf_counter() - t0) * 1000
            ok = not errs
            print(f"[{tag}] {'PASS' if ok else 'FAIL'} {name:34s} {dt:8.1f}ms {'; '.join(errs)}")
            failures += (not ok)
        except Exception as e:
            dt = (time.perf_counter() - t0) * 1000
            print(f"[{tag}] FAIL {name:34s} {dt:8.1f}ms EXC {type(e).__name__}: {str(e)[:120]}")
            failures += 1
    return failures


def slow_layer() -> int:
    """Raw-Rust subprocess: bukti panic-safety mesin (tanpa normalisasi hook)."""
    failures = 0
    for name, prompt in fz.stress_cases().items():
        ok, res, dt = fz.run_isolated(prompt, timeout=15)
        if name == "lone_surrogate":
            # EXPECTED: PyO3 menolak surrogate (UnicodeEncodeError, rc=1),
            # BUKAN sinyal abort. Hook membuang Cs sebelum sampai sini.
            expected_reject = (not ok) and isinstance(res, str) and "rc=-" not in res
            flag = "PASS(expected-reject)" if expected_reject else "FAIL"
            print(f"[slow] {flag} {name:34s} {dt*1000:8.1f}ms {'' if ok else str(res)[:100]}")
            failures += (not expected_reject)
            continue
        if not ok:
            print(f"[slow] FAIL {name:34s} {dt*1000:8.1f}ms {res}")
            failures += 1
        else:
            print(f"[slow] PASS {name:34s} {dt*1000:8.1f}ms")
    return failures


def main() -> int:
    print("== FAST layer: jalur produksi (hook normalize + Rust), in-process ==")
    f1 = fast_layer()
    f2 = 0
    if "--slow" in sys.argv:
        print("== SLOW layer: raw-Rust subprocess (panic-safety) ==")
        f2 = slow_layer()
    total = f1 + f2
    print(f"\nRINGKASAN: gagal={total} (fast={f1}, slow={f2})")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())