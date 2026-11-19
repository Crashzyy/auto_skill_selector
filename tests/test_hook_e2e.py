"""Uji end-to-end hook on_pre_llm_call (Fase 2) di lingkungan sandbox.

Memanggil hook persis seperti Hermes memanggilnya (tanpa dispatcher penuh;
uji dispatcher resmi ada di test_gateway_live.py), lalu memeriksa:
  1. Return value berbentuk {"context": ...} atau None.
  2. Konteks skill menyebut nama skill yang benar / instruksi hunter.
  3. Brainstorming & curhat menghasilkan None (tidak menyuntik apa pun).
  4. Tidak ada exception yang bocor ke caller.

Jalankan: HERMES_HOME=/tmp/hermes-sandbox python tests/test_hook_e2e.py
"""
import importlib.util
import sys
from pathlib import Path

_PLUG_DIR = Path("/tmp/hermes-sandbox/plugins/auto_skill_selector")
_spec = importlib.util.spec_from_file_location("auto_skill_selector", _PLUG_DIR / "__init__.py")
plug = importlib.util.module_from_spec(_spec)
sys.modules["auto_skill_selector"] = plug
_spec.loader.exec_module(plug)

# (prompt, expect, substring_wajib_di_konteks)
CASES = [
    ("Hitung valuasi perusahaan dengan metode DCF dan WACC", "skill", "financial-model-dcf"),
    ("Render scene karakter 3D di Blender dengan pencahayaan sinematik", "skill", "blender-3d-modeling"),
    ("Jangan pakai Excel, tapi ambil datanya dari PDF lalu visualisasikan pakai infografis",
     "skill", "infographic-design"),
    ("Jangan langsung buat kode, menurutmu lebih bagus Blender atau Cinema4D?", "none", None),
    ("Saya lagi gak punya duit buat beli kopi", "none", None),
    ("Bersihkan data CSV ini lalu buatkan animasi rig karakter 3D di Houdini", "hunter", "delegate_task"),
]

failures = 0
for prompt, expect, needle in CASES:
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
        ok = expect in ("skill", "hunter") and (needle is None or needle in ctx)
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