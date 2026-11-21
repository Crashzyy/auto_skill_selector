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


def validate(candidate: Path, active: Path, main_module, trainer) -> tuple[bool, str]:
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
    with tempfile.TemporaryDirectory(prefix="autoskill-retrain-") as tmp:
        staging_home = Path(tmp) / "home"
        staging_home.mkdir(parents=True)
        src_skills = Path(os.environ.get("HERMES_HOME", "")) / "skills"
        if src_skills.exists():
            import shutil
            shutil.copytree(src_skills, staging_home / "skills", dirs_exist_ok=True)
        old_home = os.environ.get("HERMES_HOME")
        os.environ["HERMES_HOME"] = str(staging_home)
        try:
            model = trainer.train_and_save()
            candidate = Path(trainer.get_model_path())
            ok, reason = validate(candidate, active, main_module, trainer)
            if not ok:
                return False, reason
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
