"""Uji gateway HIDUP Fase 2 (Master Prompt §4) — dispatcher resmi Hermes.

Memanggil `hermes_cli.plugins.invoke_hook("pre_llm_call", ...)` secara
end-to-end (plugin ditemukan & di-load oleh PluginManager asli dari
$HERMES_HOME sandbox) untuk 6 skenario wajib:
  1. Single, 2. Multi, 3. Negasi Global + Multi, 4. Partial + Hunt,
  5. Conversational Bypass, 6. Clarify Ambiguous.

Juga memverifikasi:
  * ruamel.yaml terpasang di venv sandbox (bukan produksi).
  * Injeksi masuk sebagai {"context": ...} (user message, bukan system prompt).
  * Total injeksi MATCHED_MULTI < 10.000 karakter.
  * `hermes plugins validate` & `hermes plugins doctor` PASS (dicatat terpisah).

Hasil ditulis ke tests/gateway_live_result.json untuk scorecard gerbang 6.
Jalankan dengan venv sandbox:
  HERMES_HOME=/tmp/hermes-sandbox /tmp/hermes-sandbox/fase2-venv/bin/python \
      tests/test_gateway_live.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_HERMES_SRC = Path(os.environ.get("HERMES_HOME", "/tmp/hermes-sandbox")) / "hermes-agent"
if not _HERMES_SRC.exists():
    # Checkout sumber Hermes produksi dipakai READ-ONLY sebagai library dispatcher.
    _HERMES_SRC = Path.home() / ".hermes" / "hermes-agent"

SCENARIOS = [
    ("single", "Gabungkan tiga berkas PDF kontrak ini jadi satu dokumen",
     lambda out: out is not None and "pdf-extraction-manipulation" in out.get("context", "")),
    ("multi", "Ambil data penjualan dari PDF, buat grafik tren, lalu susun slide presentasi",
     lambda out: out is not None and "step_1" in out.get("context", "")
     and "step_3" in out.get("context", "") and len(out.get("context", "")) < 10000),
    ("negation_global_multi", "Jangan pakai Excel, tapi ambil datanya dari PDF lalu visualisasikan pakai infografis",
     lambda out: out is not None and "pdf-extraction-manipulation" in out.get("context", "")
     and "infographic-design" in out.get("context", "")
     and "excel-xlsx-automation" not in out.get("context", "")),
    ("partial_hunt", "Bersihkan data CSV ini lalu buatkan animasi rig karakter 3D di Houdini",
     lambda out: out is not None and "tabular-pivot-cleaning" in out.get("context", "")
     and "delegate_task" in out.get("context", "")),
    ("conversational_bypass", "Halo! Menurutmu tren desain web tahun ini lagi condong ke arah mana ya?",
     lambda out: out is None),
    ("clarify_ambiguous", "Buatkan workbook .xlsx tapi dilarang pakai Excel atau spreadsheet",
     lambda out: out is not None and "klarifikasi" in out.get("context", "").lower()),
]


def main() -> int:
    result = {"ruamel_yaml_installed": False, "invoke_hook_scenarios": [],
              "plugins_validate": None, "plugins_doctor": None, "pass": False}

    # 1. ruamel.yaml di venv sandbox.
    try:
        import ruamel.yaml
        result["ruamel_yaml_installed"] = True
        result["ruamel_version"] = ruamel.yaml.__version__
        result["python_prefix"] = sys.prefix
    except ImportError:
        print("FAIL: ruamel.yaml tidak terpasang di interpreter ini")

    # 2. Dispatcher resmi Hermes (read-only source, HERMES_HOME sandbox).
    sys.path.insert(0, str(_HERMES_SRC))
    os.environ.setdefault("HERMES_HOME", "/tmp/hermes-sandbox")
    try:
        from hermes_cli.plugins import invoke_hook
    except Exception as e:
        print(f"FAIL: tidak bisa import dispatcher Hermes: {e}")
        result["dispatcher_error"] = str(e)
        _write(result)
        return 1

    all_ok = True
    for name, prompt, check in SCENARIOS:
        try:
            outputs = invoke_hook(
                "pre_llm_call",
                session_id="fase2-live-test",
                task_id="fase2",
                turn_id=1,
                user_message=prompt,
                conversation_history=[],
                is_first_turn=True,
                model="test-model",
                platform="cli",
                parent_session_id=None,
                sender_id="tester",
            )
        except Exception as e:
            print(f"[FAIL] {name}: exception {e}")
            result["invoke_hook_scenarios"].append({"name": name, "pass": False, "error": str(e)})
            all_ok = False
            continue
        # Ambil hasil plugin kita (dict dengan 'context' atau None).
        ours = None
        for o in outputs:
            if isinstance(o, dict) and ("context" in o or "action" in o):
                ours = o
                break
        ok = check(ours)
        ctx_len = len(ours.get("context", "")) if isinstance(ours, dict) else 0
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: "
              f"{'None' if ours is None else f'context {ctx_len} chars'}")
        if isinstance(ours, dict) and ctx_len:
            print(f"       {ours['context'][:110].replace(chr(10), ' ')}...")
        result["invoke_hook_scenarios"].append(
            {"name": name, "pass": ok, "context_chars": ctx_len,
             "context_head": (ours.get("context", "")[:200] if isinstance(ours, dict) else None)})
        all_ok = all_ok and ok

    result["invoke_hook_all_pass"] = all_ok

    # 3. CLI resmi: hermes plugins validate & doctor di HERMES_HOME sandbox.
    import subprocess
    plug_dir = str(_HERE.parent)
    env = dict(os.environ)
    env["HERMES_HOME"] = os.environ.get("HERMES_HOME", "/tmp/hermes-sandbox")
    try:
        v = subprocess.run(["hermes", "plugins", "validate", plug_dir],
                           capture_output=True, text=True, timeout=180, env=env)
        result["plugins_validate"] = "Validation passed." in v.stdout
        result["plugins_validate_tail"] = v.stdout.strip().splitlines()[-1] if v.stdout.strip() else ""
    except Exception as e:
        result["plugins_validate"] = False
        result["plugins_validate_error"] = str(e)
    try:
        d = subprocess.run(["hermes", "plugins", "doctor", "auto_skill_selector"],
                           capture_output=True, text=True, timeout=180, env=env)
        result["plugins_doctor"] = "registration passed" in d.stdout
        result["plugins_doctor_tail"] = d.stdout.strip().splitlines()[-1] if d.stdout.strip() else ""
    except Exception as e:
        result["plugins_doctor"] = False
        result["plugins_doctor_error"] = str(e)

    result["pass"] = bool(result["ruamel_yaml_installed"] and all_ok
                          and result.get("plugins_validate") and result.get("plugins_doctor"))
    _write(result)
    print("-" * 60)
    print("invoke_hook 6 skenario:", "SEMUA LULUS" if all_ok else "ADA GAGAL")
    print("plugins validate:", result.get("plugins_validate"),
          "| plugins doctor:", result.get("plugins_doctor"))
    print("GERBANG 6:", "PASS" if result["pass"] else "FAIL")
    return 0 if result["pass"] else 1


def _write(result: dict) -> None:
    (_HERE / "gateway_live_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), "utf-8")


if __name__ == "__main__":
    sys.exit(main())