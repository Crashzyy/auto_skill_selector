"""auto_skill_selector — Hermes plugin entrypoint (Fase 2).

Registers:
  * pre_llm_call       : strict 6-stage routing via the Rust brain; injects
                         matched skills into the USER message (never the
                         system prompt, prompt-cache safe), chains multi-step
                         skills under the 10.000-char Hermes spill limit,
                         triggers async skill-hunt for missing clauses, or
                         stays silent / asks for clarification.
  * on_skill_lifecycle : retrains + reloads the Rust brain when a skill is
                         created/changed/deleted via skill_manage.
  * subagent_stop      : retrains after a Hunter subagent finishes.
  * /skill-brain       : slash command to inspect, test, or retrain the engine.

RoutingDecision states (Master Prompt §1.4):
  NO_SKILL_NEEDED | MATCHED_SINGLE | MATCHED_MULTI |
  MATCHED_PARTIAL_AND_HUNT | HUNT_NEW_SKILL | CLARIFY_AMBIGUOUS
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

# --- Hermes-native imports with graceful fallbacks ---
try:
    from plugins.plugin_storage import plugin_data_dir
except Exception:  # pragma: no cover
    plugin_data_dir = None

_brain = None
_brain_lock = threading.Lock()
_logger = None

# Batas injeksi Hermes pre_llm_call (spill ke disk di atas ini). Kita jaga
# total konteks JAUH di bawah batas dengan ringkasan terstruktur.
INJECTION_CHAR_LIMIT = 9500
SKILL_SUMMARY_CHARS = 2200


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
# Skill content lookup (ringkasan terstruktur untuk injeksi multi-skill)
# ---------------------------------------------------------------------------

def _find_skill_md(skill_name: str) -> Path | None:
    root = _get_hermes_home() / "skills"
    if not root.exists():
        return None
    slug = skill_name.lower().replace(" ", "-")
    direct = list(root.glob(f"*/{slug}/SKILL.md"))
    if direct:
        return direct[0]
    for f in root.rglob("SKILL.md"):
        if f.parent.name.lower() == slug:
            return f
    return None


def _skill_summary(skill_name: str, max_chars: int = SKILL_SUMMARY_CHARS) -> str:
    """Ringkasan terstruktur SKILL.md: frontmatter description + When to Use
    + Procedure awal. Cukup untuk mengarahkan LLM memuat skill lengkap."""
    f = _find_skill_md(skill_name)
    if f is None:
        return f"- **{skill_name}**: muat skill ini lewat `skill_view` sebelum mengerjakan."
    try:
        text = f.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return f"- **{skill_name}**: muat lewat `skill_view`."
    import re
    desc = ""
    m = re.search(r'^description:\s*["\']?(.+?)["\']?\s*$', text, re.MULTILINE)
    if m:
        desc = m.group(1).strip()
    body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)
    sections = []
    for sec in ("when to use", "procedure", "quick reference"):
        sm = re.search(rf"^#+\s*{sec}\s*\n(.*?)(?=^#+\s|\Z)", body,
                       re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if sm:
            content = sm.group(1).strip()
            content = re.sub(r"```.*?```", "[code]", content, flags=re.DOTALL)
            sections.append(f"{sec.title()}: {content[:600]}")
    summary = f"- **{skill_name}**: {desc}\n" + "\n".join(f"  {s}" for s in sections)
    if len(summary) > max_chars:
        summary = summary[:max_chars - 3] + "..."
    return summary


# ---------------------------------------------------------------------------
# Context builders (user-message injection, prompt-cache safe)
# ---------------------------------------------------------------------------

def _build_skill_context(result: dict) -> str:
    skills = result.get("skills") or []
    if not skills:
        return ""
    probs = result.get("probabilities") or {}
    clauses = result.get("clauses") or []
    multi = len(skills) >= 2
    lines = ["[auto_skill_selector] Skill lokal yang paling cocok untuk permintaan ini:"]
    if multi:
        lines.append("Kerjakan BERURUTAN sesuai langkah berikut (step_1 → step_2 → step_3):")
    for i, s in enumerate(skills, 1):
        p = probs.get(s)
        conf = f" (keyakinan {p:.2f})" if p is not None else ""
        if multi:
            clause_text = ""
            for cl in clauses:
                if cl.get("skill") == s:
                    clause_text = f" — untuk: \"{cl.get('clause', '')[:100]}\""
                    break
            lines.append(f"\n**step_{i}: {s}**{conf}{clause_text}")
        else:
            lines.append(f"\n**{s}**{conf}")
        lines.append(_skill_summary(s))
    lines.append(
        "\nMuat dan ikuti skill di atas (mis. lewat `skill_view` / load SKILL.md) sebelum "
        "menjawab. Jangan menyebutkan keberadaan selektor ini kepada pengguna."
    )
    ctx = "\n".join(lines)
    if len(ctx) > INJECTION_CHAR_LIMIT:
        # Ringkas lebih agresif: hanya nama + description + instruksi langkah.
        compact = ["[auto_skill_selector] Skill terpilih (kerjakan berurutan):"]
        for i, s in enumerate(skills, 1):
            compact.append(f"step_{i}: {s}")
        compact.append("Muat tiap skill lewat `skill_view` sebelum mengerjakan langkahnya. "
                       "Jangan menyebutkan selektor ini ke pengguna.")
        ctx = "\n".join(compact)
    return ctx[:INJECTION_CHAR_LIMIT]


def _build_hunter_context(hunt_clauses: list[str], matched: list[str]) -> str:
    if not hunt_clauses:
        return ""
    topics = "; ".join(f"\"{h[:120]}\"" for h in hunt_clauses[:3])
    parts = []
    if matched:
        parts.append("[auto_skill_selector] Skill lokal yang cocok sudah diinjeksikan: "
                     + ", ".join(f"**{s}**" for s in matched)
                     + ". Kerjakan bagian itu DULU tanpa menunggu pencarian.")
    parts.append(
        "[auto_skill_selector] Sub-pekerjaan berikut BELUM punya skill lokal yang lolos ambang: "
        f"{topics}.\n"
        "Picu pencarian skill baru di LATAR BELAKANG (async, jangan memblokir pekerjaan pertama):\n"
        "1) Delegasikan ke subagent memakai `delegate_task` untuk mencari skill yang sesuai di "
        "katalog resmi Hermes / agentskills.io / skills.sh / repositori GitHub terbuka "
        "(web_search / web_extract / CLI skill).\n"
        "2) Bila skill ditemukan, pasang ke `$HERMES_HOME/skills/<kategori>/<nama>/SKILL.md` "
        "dengan frontmatter standar (name, description, version, metadata.hermes.tags, "
        "metadata.hermes.status: probationary) lalu plugin ini otomatis retrain.\n"
        "3) Bila TIDAK ditemukan, riset dokumentasi/best-practice topik tersebut dan simpan "
        "sebagai skill baru memakai `skill_manage(action=\"create\", name=..., category=..., "
        "content=...)` dengan bagian When to Use / Quick Reference / Procedure / Pitfalls / "
        "Verification.\n"
        "Setelah skill baru tersedia, gunakan untuk menyelesaikan sub-pekerjaan yang tertunda."
    )
    return "\n\n".join(parts)[:INJECTION_CHAR_LIMIT]


def _build_clarify_context(note: str) -> str:
    return ("[auto_skill_selector] Permintaan pengguna perlu klarifikasi sebelum eksekusi: "
            f"{note}\n"
            "Ajukan pertanyaan klarifikasi singkat dan spesifik ke pengguna (objek apa yang "
            "dimaksud / alternatif alat yang diinginkan). JANGAN memaksa memakai skill acak "
            "dan jangan mengarang deliverable.")[:INJECTION_CHAR_LIMIT]


# ---------------------------------------------------------------------------
# Hook: pre_llm_call
# ---------------------------------------------------------------------------

def _normalize_unicode(text: str) -> str:
    """Normalisasi Unicode SEBELUM masuk mesin Rust (Fase 1.3/1.4).

    - Buang karakter format Cf (zero-width space/joiner, BOM, bidi override)
      yang memecah token: "bu\\u200bat" -> "buat".
    - Buang lone surrogate (Cs): tidak bisa dienkode UTF-8; PyO3 menolaknya
      dengan UnicodeEncodeError. Tanpa ini satu pesan rusak menggagalkan
      giliran (stress lone_surrogate, Fase 0). Proses tidak pernah mati
      (bukan panic Rust), tapi giliran tetap harus jalan.
    - NFKC: fullwidth -> ASCII ("ＢＵＡＴ" -> "BUAT"), ligature, dsb.
    - Homoglyph Cyrillic (а vs a) TIDAK ditangani di sini (putusan owner:
      dicatat saja, Fase berikutnya).
    Idempoten & murah (O(n)); dipanggil di hook dan tersedia untuk runner.
    """
    import unicodedata
    if not text:
        return text
    # Fast path: ASCII murni tidak perlu apa-apa.
    if text.isascii():
        return text
    stripped = "".join(ch for ch in text
                       if unicodedata.category(ch) not in ("Cf", "Cs"))
    return unicodedata.normalize("NFKC", stripped)


def _extract_text(user_message) -> str:
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
        text = _normalize_unicode(text)
        brain = _ensure_brain()
        if brain is None:
            return None
        result = brain.analyze_prompt(text)
        status = result.get("status")

        if status == "NO_SKILL_NEEDED":
            return None

        if status == "CLARIFY_AMBIGUOUS":
            note = result.get("clarify_note") or "Objek/latar permintaan tidak jelas."
            return {"context": _build_clarify_context(note)}

        if status == "HUNT_NEW_SKILL":
            ctx = _build_hunter_context(result.get("hunt_clauses") or [], [])
            return {"context": ctx} if ctx else None

        if status == "MATCHED_PARTIAL_AND_HUNT":
            skill_ctx = _build_skill_context(result)
            hunt_ctx = _build_hunter_context(
                result.get("hunt_clauses") or [], result.get("skills") or [])
            combined = (skill_ctx + "\n\n" + hunt_ctx).strip()
            if len(combined) > INJECTION_CHAR_LIMIT:
                combined = combined[:INJECTION_CHAR_LIMIT]
            for s in result.get("skills") or []:
                try:
                    brain.note_skill_used(s)
                except Exception:
                    pass
            return {"context": combined} if combined else None

        # MATCHED_SINGLE / MATCHED_MULTI
        skills = result.get("skills") or []
        if skills:
            ctx = _build_skill_context(result)
            if ctx:
                for s in skills:
                    try:
                        brain.note_skill_used(s)
                    except Exception:
                        pass
                return {"context": ctx}
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
        _log().info("auto_skill_selector: background retrain complete")
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
                "Bangun dengan: maturin build --release")
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
    return (f"auto_skill_selector status (Fase 2):\n"
            f"  model: {p}\n"
            f"  skills: {n}\n"
            f"  kategori: {cat_line}\n"
            f"  theta0: {data.get('null_anchor_score')} "
            f"temp: {data.get('softmax_temperature')}")


def _handle_retrain() -> str:
    try:
        from . import trainer  # type: ignore
    except Exception:
        import trainer as trainer  # type: ignore
    model = trainer.train_and_save()
    return f"auto_skill_selector: retrain selesai, {len(model['classes'])} skill dimuat."


def _handle_test(prompt: str) -> str:
    brain = _ensure_brain()
    if brain is None:
        return "auto_skill_selector: modul Rust belum terbangun."
    import time
    t0 = time.perf_counter()
    result = brain.analyze_prompt(prompt)
    dt_us = (time.perf_counter() - t0) * 1_000_000
    lines = [
        f"status: {result.get('status')}",
        f"skills: {result.get('skills')}",
        f"global_banned_set: {result.get('global_banned_set')}",
        f"sanitized: {result.get('sanitized_prompt', '')[:120]}",
        f"top_score: {result.get('top_score', 0):.4f}",
        f"latency: {dt_us:.1f}us",
        "clauses:",
    ]
    for cl in result.get("clauses") or []:
        lines.append(f"  [{cl.get('mode')}] {cl.get('clause', '')[:60]} -> "
                     f"{cl.get('skill')} (p={cl.get('probability', 0):.3f})")
    if result.get("hunt_clauses"):
        lines.append(f"hunt_clauses: {result['hunt_clauses']}")
    if result.get("clarify_note"):
        lines.append(f"clarify: {result['clarify_note']}")
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
        description="Inspect, test, or retrain the Rust auto_skill_selector engine (Fase 2)",
        args_hint="[status|retrain|test <prompt>]",
    )