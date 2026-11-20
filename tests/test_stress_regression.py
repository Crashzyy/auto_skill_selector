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


# ---- A3: generative Unicode fuzz (>=5000 prompts), batch subprocess ----
# Pool exercises every byte-indexing site: Cyrillic/Greek homoglyphs, fullwidth,
# zero-width/Cf, combining marks, multibyte bullet "•", CJK, emoji.
UNICODE_POOL = list(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,;:!?/-_@"
    "•аеорсхАЕОРСХαβγορπ（）ＡＢＣ１２３"
    "\u200b\u200d\u200e\ufeff\u0301\u0308"
    "中文日本語한국어Русскийελληνικάالعربية"
    "😀🔥💡📊✅❌🚀"
)

# Child processes a BATCH in one interpreter: a Rust panic (panic=abort) kills
# the whole subprocess -> rc<0 detected in parent. PLUGIN_DIR/MODEL injected.
UNICODE_CHILD = r'''
import sys, json, os, glob, importlib.util
PLUGIN_DIR, MODEL = %r, %r
sys.path.insert(0, PLUGIN_DIR)
try:
    import hermes_skill_brain as h
except ImportError:
    h = None
    for so in glob.glob(os.path.join(PLUGIN_DIR, "*.so")):
        spec = importlib.util.spec_from_file_location("hermes_skill_brain", so)
        if spec and spec.loader:
            h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h); break
    if h is None: raise ImportError("hermes_skill_brain not found")
b = h.SkillBrain(); b.reload(open(MODEL, encoding="utf-8").read())
batch = json.loads(sys.stdin.read())
out = []
for p in batch:
    r = b.analyze_prompt(p)
    out.append({"status": r.get("status"), "nclauses": len(r.get("clauses") or [])})
sys.stdout.write(json.dumps(out))
''' % (fz.PLUGIN_DIR, fz.MODEL)


def gen_unicode_prompts(n: int, seed: int = 20261120):
    """Deterministic generative Unicode prompts, seeded for reproducibility."""
    import random
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        L = rng.randint(1, 80)
        s = "".join(rng.choice(UNICODE_POOL) for _ in range(L))
        # Mix structured shapes that hit the byte-indexing paths with Unicode
        # adjacent to delimiters/markers.
        shape = rng.randint(0, 4)
        if shape == 0:
            s = f"1. {s} 2. {s[:10]}"
        elif shape == 1:
            s = f"• {s}"
        elif shape == 2:
            s = f"https://example.com/{s[:8]} ringkas {s[:12]}"
        elif shape == 3:
            s = f"jangan pakai {s[:6]}; buat {s[:12]}"
        out.append(s)
    return out


def _run_unicode_batch(batch, timeout=60):
    t = time.perf_counter()
    try:
        r = subprocess.run([sys.executable, "-c", UNICODE_CHILD],
                           input=json.dumps(batch, ensure_ascii=True),
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", time.perf_counter() - t
    if r.returncode != 0:
        return False, f"CRASH rc={r.returncode} {r.stderr[-300:]}", time.perf_counter() - t
    try:
        return True, json.loads(r.stdout), time.perf_counter() - t
    except Exception as e:
        return False, f"BAD-OUTPUT {type(e).__name__}: {r.stdout[:120]}", time.perf_counter() - t


def unicode_fuzz_layer(n: int = 5000, chunk: int = 100, seed: int = 20261120) -> int:
    prompts = gen_unicode_prompts(n, seed)
    print(f"== UNICODE FUZZ layer: {n} prompt, seed={seed}, chunk={chunk} ==")
    failures = 0
    for start in range(0, n, chunk):
        batch = prompts[start:start + chunk]
        ok, res, dt = _run_unicode_batch(batch)
        if not ok:
            failures += 1
            print(f"[ufuzz] FAIL batch {start}-{start+len(batch)-1}: {res}")
            # Isolate the offending prompt with single-subprocess runs.
            for j, p in enumerate(batch):
                sok, sres, _ = fz.run_isolated(p, timeout=15)
                if not sok:
                    failures += 1
                    print(f"[ufuzz]   culprit #{start+j}: {sres[:120]} repr={p[:60]!r}")
            continue
        for j, rr in enumerate(res):
            bad = []
            if rr.get("status") not in STATUSES:
                bad.append(f"status={rr.get('status')}")
            if rr.get("nclauses", 0) > 3:
                bad.append(f"nclauses={rr.get('nclauses')}")
            if bad:
                failures += 1
                print(f"[ufuzz] FAIL #{start+j}: {'; '.join(bad)} repr={batch[j][:60]!r}")
    print(f"[ufuzz] selesai: {n} prompt, gagal={failures}")
    return failures


def main() -> int:
    print("== FAST layer: jalur produksi (hook normalize + Rust), in-process ==")
    f1 = fast_layer()
    f2 = 0
    f3 = 0
    if "--slow" in sys.argv:
        print("== SLOW layer: raw-Rust subprocess (panic-safety) ==")
        f2 = slow_layer()
    if "--unicode-fuzz" in sys.argv:
        n = 5000
        for a in sys.argv[1:]:
            if a.startswith("--unicode-fuzz="):
                n = int(a.split("=", 1)[1])
        f3 = unicode_fuzz_layer(n=n)
    total = f1 + f2 + f3
    print(f"\nRINGKASAN: gagal={total} (fast={f1}, slow={f2}, unicode_fuzz={f3})")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())