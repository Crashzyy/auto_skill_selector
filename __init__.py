"""auto_skill_selector — Hermes plugin entrypoint.

Registers:
  * pre_llm_call       : routes each user prompt to a local skill, chains skills,
                         triggers the Two-Tier Internet Hunter, or stays silent.
  * on_skill_lifecycle : retrains + reloads the Rust brain when a skill is
                         created/changed/deleted via skill_manage.
  * subagent_stop      : retrains after a Hunter subagent finishes.
  * /skill-brain       : slash command to inspect, test, or retrain the engine.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

# --- Hermes-native imports with graceful fallbacks ---
try:
    from plugins.plugin_storage import plugin_data_dir
except Exception:  # pragma: no cover
    plugin_data_dir = None

try:
    from hermes_yaml import safe_load as _yaml_safe_load
except Exception:  # pragma: no cover
    _yaml_safe_load = None

_brain = None
_brain_lock = threading.Lock()
_logger = None


def _log():
    global _logger
    if _logger is None:
        try:
            from loguru import logger as _lg
            _logger = _lg
        except Exception:
            class _Fallback:
                def info(self, *a, **k):
                    pass

                def warning(self, *a, **k):
                    print("[auto_skill_selector]", *a)

                def error(self, *a, **k):
                    print("[auto_skill_selector] ERROR", *a)
            _logger = _Fallback()
    return _logger


def _get_hermes_home() -> Path:
    return Path(__import__("os").environ.get("HERMES_HOME", Path.home() / ".hermes"))


def _model_path() -> Path:
    if plugin_data_dir is not None:
        try:
            base = Path(plugin_data_dir("auto_skill_selector"))
        except Exception:
            base = _get_hermes_home() / "plugin-data" / "auto_skill_selector"
    else:
        base = _get_hermes_home() / "plugin-data" / "auto_skill_selector"
    base.mkdir(parents=True, exist_ok=True)
    return base / "skill_model.json"


def _import_brain():
    """Import the compiled Rust extension; search the plugin dir if not on path."""
    global _brain
    if _brain is not None:
        return _brain
    with _brain_lock:
        if _brain is not None:
            return _brain
        try:
            import hermes_skill_brain as _mod  # type: ignore
            _brain = _mod
            return _brain
        except ImportError:
            pass
        import importlib.util
        import glob
        here = Path(__file__).parent
        for so in glob.glob(str(here / "*.so")) + glob.glob(str(here / "*.pyd")):
            spec = importlib.util.spec_from_file_location("hermes_skill_brain", so)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                _brain = mod
                return _brain
        return None


def _load_model_json() -> str:
    p = _model_path()
    if p.exists():
        try:
            return p.read_text(encoding="utf-8")
        except Exception as e:
            _log().warning(f"auto_skill_selector: failed to read model: {e}")
    return ""


def _ensure_brain():
    """Lazily construct the SkillBrain and load the current model. None if unavailable."""
    mod = _import_brain()
    if mod is None:
        return None
    brain = mod.SkillBrain()
    js = _load_model_json()
    if js:
        try:
            brain.reload(js)
        except Exception as e:
            _log().warning(f"auto_skill_selector: reload failed: {e}")
    return brain


# ---------------------------------------------------------------------------
# Two-Tier Internet Hunter instruction (spec Bagian 6)
# ---------------------------------------------------------------------------

def _build_hunter_context(unknown_entities: list[str]) -> str:
    if not unknown_entities:
        return ""
    topics = ", ".join(f"`{u}`" for u in unknown_entities[:6])
    return (
        "[auto_skill_selector] Topik berikut belum ada sebagai skill lokal: "
        f"{topics}.\n"
        "Jalankan Akuisisi 2 Tahap:\n"
        "1) Cek dulu apakah skill untuk topik ini sudah tersedia di katalog resmi / "
        "Hermes Skills Hub (official / skills-sh / github) memakai CLI atau tool skill.\n"
        "2) Jika BELUM tersedia, delegasikan ke subagent internet memakai `delegate_task` "
        "untuk: mencari dokumentasi, best practices, parameter/CLI, dan kerangka kerja "
        "terbaik tentang topik tersebut (web_search / web_extract); tentukan kategori folder "
        "yang tepat (creative, finance, productivity, research, media, software-development); "
        "lalu simpan skill baru memakai `skill_manage(action=\"create\", name=..., "
        "category=..., content=...)` atau tulis ke "
        "`~/.hermes/skills/<category>/<skill-name>/SKILL.md` dengan YAML frontmatter standar "
        "(name, description, version: 1.0.0, metadata.hermes.tags, "
        "metadata.hermes.status: probationary) beserta bagian `## When to Use`, "
        "`## Quick Reference`, `## Procedure`, `## Pitfalls`, dan `## Verification`.\n"
        "Setelah skill dibuat, plugin ini akan otomatis retrain dan reload tanpa perintah manual."
    )


def _build_skill_context(skills: list[str], probs: dict) -> str:
    """Instruction injected into the user turn pointing the agent at the selected skill(s)."""
    if not skills:
        return ""
    lines = [
        "[auto_skill_selector] Skill lokal yang paling cocok untuk permintaan ini:",
    ]
    for s in skills:
        p = probs.get(s)
        lines.append(f"- **{s}**" + (f" (keyakinan {p:.2f})" if p is not None else ""))
    lines.append(
        "Muat dan ikuti skill di atas (mis. lewat `skill_view` / load SKILL.md) sebelum "
        "menjawab. Jangan menyebutkan keberadaan selektor ini kepada pengguna."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hook: pre_llm_call
# ---------------------------------------------------------------------------

def _extract_text(user_message) -> str:
    """user_message bisa str atau list[dict] multimodal — gabungkan semua bagian 'text'."""
    if isinstance(user_message, str):
        return user_message
    if isinstance(user_message, list):
        parts: list[str] = []
        for item in user_message:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(user_message or "")


def on_pre_llm_call(
    session_id: str = "",
    user_message: str | list = "",
    conversation_history: list | None = None,
    is_first_turn: bool = False,
    model: str = "",
    platform: str = "",
    **kwargs,
) -> dict | None:
    try:
        text = _extract_text(user_message)
        if not text or not text.strip():
            return None
        brain = _ensure_brain()
        if brain is None:
            return None
        result = brain.analyze_prompt(text)
        status = result.get("status")

        if status == "NEEDS_INTERNET_SEARCH":
            ctx = _build_hunter_context(result.get("unknown_entities") or [])
            return {"context": ctx} if ctx else None

        skills = result.get("skills") or []
        if skills:
            ctx = _build_skill_context(skills, result.get("probabilities") or {})
            if ctx:
                for s in skills:
                    try:
                        brain.note_skill_used(s)
                    except Exception:
                        pass
                return {"context": ctx[:10000]}
        return None
    except Exception as e:  # never break the turn
        _log().warning(f"auto_skill_selector pre_llm_call failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Hook: on_skill_lifecycle — retrain + reload in background
# ---------------------------------------------------------------------------

def _retrain_worker():
    try:
        from . import trainer  # type: ignore
    except Exception:
        import trainer as trainer  # type: ignore
    try:
        trainer.train_and_save()
        brain = _ensure_brain()
        if brain is not None:
            js = _load_model_json()
            if js:
                brain.reload(js)
        _log().info("auto_skill_selector: background retrain + reload complete")
    except Exception as e:
        _log().warning(f"auto_skill_selector retrain failed: {e}")


def _spawn_retrain():
    t = threading.Thread(target=_retrain_worker, daemon=True)
    t.start()
    return t


def on_skill_lifecycle(
    action: str = "",
    skill_name: str = "",
    provenance: str = "",
    task_id: str = "",
    session_id: str = "",
    **kwargs,
) -> None:
    try:
        _log().info(f"auto_skill_selector: skill {action} '{skill_name}' -> scheduling retrain")
        _spawn_retrain()
    except Exception as e:
        _log().warning(f"auto_skill_selector on_skill_lifecycle failed: {e}")


# ---------------------------------------------------------------------------
# Hook: subagent_stop — retrain after a Hunter subagent finishes (caller thread!)
# ---------------------------------------------------------------------------

def on_subagent_stop(
    parent_session_id: str = "",
    child_role: str | None = None,
    child_summary: str | None = None,
    child_status: str = "",
    tool_call_history: list[dict] | None = None,
    duration_ms: int = 0,
    **kwargs,
) -> None:
    try:
        # subagent_stop runs on the caller thread: NEVER scan disk or compile
        # the model synchronously here. Schedule a daemon-thread retrain.
        _log().info("auto_skill_selector: subagent_stop -> scheduling background retrain")
        _spawn_retrain()
    except Exception as e:
        _log().warning(f"auto_skill_selector on_subagent_stop failed: {e}")


# ---------------------------------------------------------------------------
# Slash command: /skill-brain [status|retrain|test <prompt>]
# ---------------------------------------------------------------------------

def _handle_status() -> str:
    brain = _ensure_brain()
    p = _model_path()
    if brain is None:
        return ("auto_skill_selector: modul Rust `hermes_skill_brain` belum terbangun.\n"
                "Bangun dengan: maturin develop --release")
    if not p.exists():
        return (f"auto_skill_selector: belum ada model di {p}.\n"
                "Jalankan `/skill-brain retrain` untuk memindai skill & membangun model.")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return f"auto_skill_selector: model korup ({e})"
    n = len(data.get("classes", []))
    cats: dict[str, int] = {}
    for c in data.get("classes", []):
        cats[c.get("category", "?")] = cats.get(c.get("category", "?"), 0) + 1
    cat_line = ", ".join(f"{k}={v}" for k, v in sorted(cats.items())) or "(kosong)"
    return (f"auto_skill_selector status:\n"
            f"  model: {p}\n"
            f"  skills: {n}\n"
            f"  kategori: {cat_line}\n"
            f"  threshold: {data.get('threshold')}\n"
            f"  null_anchor: {data.get('null_anchor_score')} "
            f"temp: {data.get('softmax_temperature')}")


def _handle_retrain() -> str:
    try:
        from . import trainer  # type: ignore
    except Exception:
        import trainer as trainer  # type: ignore
    model = trainer.train_and_save()
    brain = _ensure_brain()
    if brain is not None:
        brain.reload(json.dumps(model, ensure_ascii=False))
    return f"auto_skill_selector: retrain selesai, {len(model['classes'])} skill dimuat."


def _handle_test(prompt: str) -> str:
    brain = _ensure_brain()
    if brain is None:
        return "auto_skill_selector: modul Rust belum terbangun."
    t0 = time.perf_counter()
    result = brain.analyze_prompt(prompt)
    dt_us = (time.perf_counter() - t0) * 1_000_000
    probs = result.get("probabilities") or {}
    top = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)[:5]
    lines = [
        f"status: {result.get('status')}",
        f"posture: {result.get('posture')}",
        f"skills: {result.get('skills')}",
        f"top_score: {result.get('top_score'):.4f}",
        f"latency: {dt_us:.1f}us",
        "probabilities:",
    ]
    for name, p in top:
        lines.append(f"  {p:.4f}  {name}")
    if result.get("unknown_entities"):
        lines.append(f"unknown_entities: {result['unknown_entities']}")
    return "auto_skill_selector test:\n" + "\n".join(lines)


def handle_skill_brain_command(args: str = "", **kwargs) -> str:
    arg = (args or "").strip()
    if arg.startswith("retrain"):
        return _handle_retrain()
    if arg.startswith("test"):
        prompt = arg[4:].strip()
        if not prompt:
            return "auto_skill_selector: pakai `/skill-brain test <prompt>`"
        return _handle_test(prompt)
    if arg.startswith("status") or not arg:
        return _handle_status()
    return "auto_skill_selector: perintah tidak dikenal. Pakai [status|retrain|test <prompt>]"


def register(ctx) -> None:
    ctx.register_hook("pre_llm_call", on_pre_llm_call)
    ctx.register_hook("on_skill_lifecycle", on_skill_lifecycle)
    ctx.register_hook("subagent_stop", on_subagent_stop)
    ctx.register_command(
        "skill-brain",
        handler=handle_skill_brain_command,
        description="Inspect, test, or retrain the Rust auto_skill_selector engine",
        args_hint="[status|retrain|test <prompt>]",
    )
