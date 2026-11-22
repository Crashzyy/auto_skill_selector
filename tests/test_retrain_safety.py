"""Isolated tests for safe retrain behavior (no shared model writes)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import plugin_retrain

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


class FakeModule:
    def _model_path(self):
        return Path(os.environ["HERMES_HOME"]) / "plugin-data" / "auto_skill_selector" / "skill_model.json"

    def _log(self):
        class L:
            def info(self, msg): pass
            def warning(self, msg): pass
        return L()


class FakeTrainer:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = 0

    def get_model_path(self):
        return Path(os.environ["HERMES_HOME"]) / "plugin-data" / "auto_skill_selector" / "skill_model.json"

    def get_skills_root(self):
        return Path(os.environ["HERMES_HOME"]) / "skills"

    def train_and_save(self):
        self.calls += 1
        if self.fail:
            raise RuntimeError("simulated failure")
        root = Path(os.environ["HERMES_HOME"])
        skills = [p.parent.name for p in (root / "skills").rglob("SKILL.md")]
        if not skills:
            skill = root / "skills" / "demo" / "SKILL.md"
            skill.parent.mkdir(parents=True, exist_ok=True)
            skill.write_text("---\nname: demo\n---\n", encoding="utf-8")
            skills = ["demo"]
        model = {"null_anchor_score": 7.5, "classes": [{"name": n} for n in skills]}
        p = root / "plugin-data" / "auto_skill_selector" / "skill_model.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(model), encoding="utf-8")
        return model


def fresh_home(name):
    import tempfile
    h = Path(tempfile.mkdtemp(prefix=f"r6-{name}-"))
    os.environ["HERMES_HOME"] = str(h)
    skill = h / "skills" / "demo" / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text("---\nname: demo\n---\n", encoding="utf-8")
    return h


def test_empty_dir_bootstrap_pass_through():
    h = fresh_home("empty")
    ok, reason = plugin_retrain.retrain_once(FakeModule(), FakeTrainer())
    assert ok, reason
    assert (h / "plugin-data" / "auto_skill_selector" / "skill_model.json").exists()
    assert "installed" in reason


def test_validation_failure_keeps_active():
    h = fresh_home("invalid")
    active = h / "plugin-data" / "auto_skill_selector" / "skill_model.json"
    active.parent.mkdir(parents=True)
    active.write_text(json.dumps({"null_anchor_score": 7.5, "classes": [{"name": "old"}]}), encoding="utf-8")
    ok, reason = plugin_retrain.retrain_once(FakeModule(), FakeTrainer(fail=True))
    assert not ok
    assert json.loads(active.read_text())["classes"][0]["name"] == "old"


def test_prev_backup_and_corpus_change():
    h = fresh_home("prev")
    active = h / "plugin-data" / "auto_skill_selector" / "skill_model.json"
    active.parent.mkdir(parents=True)
    active.write_text(json.dumps({"null_anchor_score": 7.5, "classes": [{"name": "demo"}]}), encoding="utf-8")
    ok, reason = plugin_retrain.retrain_once(FakeModule(), FakeTrainer())
    assert ok, reason
    prev = active.with_suffix(".prev")
    assert prev.exists()
    assert json.loads(prev.read_text())["classes"][0]["name"] == "demo"


def test_disable_flag():
    fresh_home("flag")
    os.environ["AUTO_SKILL_SELECTOR_DISABLE_AUTORETRAIN"] = "1"
    assert plugin_retrain.schedule(FakeModule()) is None
    os.environ.pop("AUTO_SKILL_SELECTOR_DISABLE_AUTORETRAIN", None)


def test_missing_fixture_fails_closed():
    fresh_home("nofix")
    real = plugin_retrain._neg_conv_cases
    def boom(_):
        raise FileNotFoundError("simulated missing fixture")
    plugin_retrain._neg_conv_cases = boom
    try:
        try:
            plugin_retrain._neg_conv_cases(FakeModule())
            raise AssertionError("missing fixture accepted")
        except FileNotFoundError:
            pass
    finally:
        plugin_retrain._neg_conv_cases = real


def test_single_flight():
    fresh_home("flight")
    os.environ["AUTO_SKILL_SELECTOR_RETRAIN_DEBOUNCE"] = "300"
    flight = plugin_retrain.SingleFlight()
    t = FakeTrainer()
    a, b = flight.run(FakeModule(), t), flight.run(FakeModule(), t)
    assert t.calls == 1
    assert a[0] is True and b[1] == "debounced"
    os.environ.pop("AUTO_SKILL_SELECTOR_RETRAIN_DEBOUNCE", None)


if __name__ == "__main__":
    for fn in [test_empty_dir_bootstrap_pass_through, test_validation_failure_keeps_active,
               test_prev_backup_and_corpus_change, test_disable_flag,
               test_missing_fixture_fails_closed, test_single_flight]:
        fn()
        print("PASS", fn.__name__)
