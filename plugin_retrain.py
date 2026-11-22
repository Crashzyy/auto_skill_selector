"""Safe background retraining for the skill-router plugin.

The engine and trainer stay untouched. This module wraps trainer.train_and_save
with an isolated staging directory, validation, atomic replacement, a
single-flight lock, debounce, and an opt-out switch.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from pathlib import Path

_DISABLE_FLAG = "AUTO_SKILL_SELECTOR_DISABLE_AUTORETRAIN"
_DEBOUNCE_ENV = "AUTO_SKILL_SELECTOR_RETRAIN_DEBOUNCE"
DEFAULT_DEBOUNCE_S = 30.0
_LOCK_NAME = "autoskill_retrain.lock"
SELF_RETRIEVAL_THRESHOLD = 0.9153
NEG_CONV_FP_LIMIT = 2


def disabled() -> bool:
    return os.environ.get(_DISABLE_FLAG, "").lower() in {"1", "true", "yes", "on"}


def debounce_seconds() -> float:
    try:
        return max(0.0, float(os.environ.get(_DEBOUNCE_ENV, DEFAULT_DEBOUNCE_S)))
    except ValueError:
        return DEFAULT_DEBOUNCE_S


def _model_path(main_module) -> Path:
    return Path(main_module._model_path())


def _skills_root(trainer) -> Path:
    return Path(trainer.get_skills_root())


def _skill_names(root: Path) -> set[str]:
    return {p.parent.name for p in root.rglob("SKILL.md")}


def corpus_hash(root: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    for p in sorted(root.rglob("SKILL.md")):
        h.update(str(p.relative_to(root)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def _neg_conv_cases(main_module) -> list:
    p = Path(__file__).resolve().parent / "tests" / "fixtures" / "neg_conv.json"
    if not p.exists():
        return []
    import json
    return json.loads(p.read_text(encoding="utf-8")).get("cases", [])


def validate_b(candidate: Path, active: Path, main_module, trainer) -> tuple[bool, str]:
    """Validation for a corpus that differs from the shipped model's corpus."""
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"unreadable: {exc}"
    classes = data.get("classes") or []
    root = _skills_root(trainer)
    expected = _skill_names(root)
    if not classes or {c.get("name") for c in classes} != expected:
        return False, "skill mismatch"
    theta = float(data.get("null_anchor_score", 0.0))
    if not (0 < theta < float("inf")):
        return False, "invalid theta"
    brain = main_module._import_brain()
    brain = brain.SkillBrain() if brain else None
    if brain is None:
        return False, "engine missing"
    brain.reload(json.dumps(data, ensure_ascii=False))
    ok = 0
    for p in root.rglob("SKILL.md"):
        lines = p.read_text(errors="ignore").splitlines()
        desc = next((ln.split(":", 1)[1].strip() for ln in lines
                     if ln.lower().startswith("description:")), "")
        r = brain.analyze_prompt(f"{p.parent.name} {desc[:160]}")
        ok += int(r["status"].startswith("MATCHED") and p.parent.name in r["skills"])
    rate = ok / max(1, len(expected))
    if rate < SELF_RETRIEVAL_THRESHOLD:
        return False, f"self-retrieval {rate:.4f}"
    import benchmark_runner  # type: ignore
    fp = 0
    for c in _neg_conv_cases(main_module):
        r = brain.analyze_prompt(benchmark_runner._hook_normalize(c["prompt"]))
        fp += int(r["status"] not in c["expect_status"])
    if fp > NEG_CONV_FP_LIMIT:
        return False, f"neg_conv fp {fp}"
    return True, f"validated {rate:.4f}"


def validate(candidate: Path, active: Path, main_module, trainer, corpus_changed: bool = False):
    if corpus_changed:
        return validate_b(candidate, active, main_module, trainer)
    return _validate_a(candidate, active, main_module, trainer)
def _validate_a(candidate: Path, active: Path, main_module, trainer) -> tuple[bool, str]:
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"unreadable: {exc}"
    classes = data.get("classes") or []
    if not classes:
        return False, "no classes"
    expected = _skill_names(_skills_root(trainer))
    got = {c.get("name") for c in classes}
    if got != expected:
        return False, f"skill mismatch: {len(got)} vs {len(expected)}"
    old_theta = None
    if active.exists():
        try:
            old_theta = float(json.loads(active.read_text(encoding="utf-8"))["null_anchor_score"])
        except Exception:
            old_theta = None
    theta = float(data.get("null_anchor_score", 0.0))
    if old_theta and abs(theta - old_theta) > 0.02 * abs(old_theta):
        return False, "theta drift"
    return True, "ok"


def retrain_once(main_module, trainer) -> tuple[bool, str]:
    active = _model_path(main_module)
    active.parent.mkdir(parents=True, exist_ok=True)
    lock = active.parent / _LOCK_NAME
    installed_root = Path(os.environ.get("HERMES_HOME", "")) / "skills"
    installed_hash = corpus_hash(installed_root) if installed_root.exists() else ""
    corpus_changed = False
    if active.exists():
        try:
            active_classes = {c.get("name") for c in
                              json.loads(active.read_text(encoding="utf-8"))["classes"]}
            installed_names = _skill_names(installed_root) if installed_root.exists() else set()
            corpus_changed = bool(installed_names) and active_classes != installed_names
        except Exception:
            corpus_changed = True
    with tempfile.TemporaryDirectory(prefix="autoskill-retrain-", dir=str(active.parent)) as tmp:
        staging_home = Path(tmp) / "home"
        staging_home.mkdir(parents=True)
        src_skills = Path(os.environ.get("HERMES_HOME", "")) / "skills"
        if src_skills.exists():
            import shutil
            shutil.copytree(src_skills, staging_home / "skills",
                            dirs_exist_ok=True, symlinks=True,
                            ignore=lambda d, names: [n for n in names
                                                     if (Path(d) / n).is_symlink()
                                                     and not (Path(d) / n).exists()])
        old_home = os.environ.get("HERMES_HOME")
        os.environ["HERMES_HOME"] = str(staging_home)
        try:
            model = trainer.train_and_save()
            candidate = Path(trainer.get_model_path())
            ok, reason = validate(candidate, active, main_module, trainer, corpus_changed)
            if not ok:
                return False, reason
            if active.exists():
                import shutil
                shutil.copyfile(active, active.with_suffix(".prev"))
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            with open(lock, "w", encoding="utf-8") as fh:
                fh.write(digest)
            os.replace(candidate, active)
            return True, f"installed {digest[:12]}"
        except Exception as exc:
            return False, f"error: {exc}"
        finally:
            if old_home is None:
                os.environ.pop("HERMES_HOME", None)
            else:
                os.environ["HERMES_HOME"] = old_home


class SingleFlight:
    def __init__(self):
        self._lock = threading.Lock()
        self._next = 0.0

    def run(self, main_module, trainer) -> tuple[bool, str]:
        now = time.monotonic()
        with self._lock:
            if now < self._next:
                return False, "debounced"
            self._next = now + debounce_seconds()
        return retrain_once(main_module, trainer)


_FLIGHT = SingleFlight()


def schedule(main_module) -> threading.Thread | None:
    if disabled():
        return None
    try:
        import trainer as trainer_module  # type: ignore
    except ImportError:
        return None

    def worker():
        ok, reason = _FLIGHT.run(main_module, trainer_module)
        (main_module._log().info if ok else main_module._log().warning)(
            f"auto_skill_selector: retrain {'complete' if ok else 'skipped'}: {reason}"
        )

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t
