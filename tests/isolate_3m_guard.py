"""Shared-model immutability guard for Fase 3m (tests/ helper)."""
import hashlib
from pathlib import Path
SHARED = Path("/tmp/hermes-sandbox/plugin-data/auto_skill_selector/skill_model.json")
EXPECTED_SHA = "a6a14d6adf11a8c04f3bc6ef2b95659937913efed332c32d7b8d868b8ceadd3a"
def guard():
    if not SHARED.exists():
        raise SystemExit("shared model missing")
    h = hashlib.sha256(SHARED.read_bytes()).hexdigest()
    if h != EXPECTED_SHA:
        raise SystemExit(f"shared model changed: {h} != {EXPECTED_SHA}")
    return h
