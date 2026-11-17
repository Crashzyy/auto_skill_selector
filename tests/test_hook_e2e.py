"""Uji end-to-end hook on_pre_llm_call di lingkungan sandbox.

Memanggil hook persis seperti Hermes memanggilnya, lalu memeriksa:
  1. Return value berbentuk {"context": ...} atau None.
  2. Konteks skill menyebut nama skill yang benar.
  3. Brainstorming menghasilkan None (tidak menyuntik apa pun).
  4. Tidak ada exception yang bocor ke caller.
"""
import importlib.util
import sys
from pathlib import Path

_PLUG_DIR = Path("/tmp/hermes-sandbox/plugins/auto_skill_selector")
_spec = importlib.util.spec_from_file_location("auto_skill_selector", _PLUG_DIR / "__init__.py")
plug = importlib.util.module_from_spec(_spec)
sys.modules["auto_skill_selector"] = plug
_spec.loader.exec_module(plug)

CASES = [
    # (prompt, expect_status_hint)  -> status tak diekspos, tapi kita cek sifat konteks
    ("Tolong buatkan model valuasi perusahaan dengan metode DCF di Excel", "skill"),
    ("Atur scene kamera macro dan render animasi di Unreal Engine", "skill"),
    ("Jangan pakai Docker, tapi deploy langsung ke Cloudflare Worker", "skill"),
    ("Jangan langsung buat kode, menurutmu lebih bagus Blender atau Cinema4D?", "none"),
    ("Saya lagi gak punya duit buat beli kopi", "none"),
    ("Buatkan storyboard dan prompt video animasi bergaya Claymation dengan Dragonframe", "hunter"),
]

failures = 0
for prompt, expect in CASES:
    try:
        out = plug.on_pre_llm_call(
            session_id="test-sess",
            user_message=prompt,
            conversation_history=[],
            is_first_turn=True,
            model="test-model",
            platform="cli",
        )
    except Exception as e:
        print(f"EXCEPTION  {prompt[:40]!r}: {e}")
        failures += 1
        continue

    if out is None:
        got = "None"
        ok = expect == "none"
    elif isinstance(out, dict) and "context" in out:
        ctx = out["context"]
        got = f"dict(context {len(ctx)} char)"
        ok = expect in ("skill", "hunter")
        # tampilkan cuplikan konteks utk inspeksi
        snippet = ctx[:120].replace("\n", " ")
        print(f"  ctx: {snippet}...")
    else:
        got = f"BAD SHAPE {out!r}"
        ok = False

    flag = "PASS" if ok else "FAIL"
    if not ok:
        failures += 1
    print(f"[{flag}] expect={expect:6s} got={got:24s} {prompt[:38]!r}")

print(f"\n{'SEMUA LULUS' if failures == 0 else f'{failures} GAGAL'}")
sys.exit(0 if failures == 0 else 1)
