#!/usr/bin/env python3
"""Isolated measurement harness for Fase 3m (no edits to src/trainer/lexicon).

Creates a per-process HERMES_HOME data dir with a PINNED model copied from
/tmp/model_snapshot_3m/skill_model.json (read-only snapshot). Verifies sha256
before and after every run; aborts if the pinned model or the shared sandbox
model changed.

Usage:
  python tests/isolate_3m.py setup <name>     -> prints isolated HERMES_HOME path
  python tests/isolate_3m.py check <name>     -> verifies pins, prints status
  python tests/isolate_3m.py guard            -> verifies shared model unchanged
"""
import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

SNAPSHOT = Path("/tmp/model_snapshot_3m/skill_model.json")
SHARED = Path("/tmp/hermes-sandbox/plugin-data/auto_skill_selector/skill_model.json")
BASE = Path("/tmp/hermes-sandbox/iso-3m")
SHARED_BASELINE = {
    "sha256": "a6a14d6adf11a8c04f3bc6ef2b95659937913efed332c32d7b8d868b8ceadd3a",
    "mtime_display": "2026-11-21 12:15:57.304848773 +0000",
    "size": 2120902,
}

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def setup(name):
    if not SNAPSHOT.exists():
        raise SystemExit(f"snapshot missing: {SNAPSHOT}")
    root = BASE / name
    data = root / "plugin-data" / "auto_skill_selector"
    data.mkdir(parents=True, exist_ok=True)
    target = data / "skill_model.json"
    shutil.copyfile(SNAPSHOT, target)
    target.chmod(0o444)
    manifest = {
        "name": name,
        "model_sha256": sha(target),
        "snapshot_sha256": sha(SNAPSHOT),
        "source": str(SNAPSHOT),
    }
    (root / "model_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(str(root))
    print(json.dumps(manifest))

def check(name):
    root = BASE / name
    m = json.loads((root / "model_manifest.json").read_text())
    target = root / "plugin-data" / "auto_skill_selector" / "skill_model.json"
    ok = sha(target) == m["model_sha256"] == sha(SNAPSHOT)
    print(f"PINNED {name}: {'OK' if ok else 'MISMATCH'} sha={sha(target)}")
    if not ok:
        sys.exit(2)

def guard():
    st = SHARED.stat()
    cur = {"sha256": sha(SHARED), "mtime": st.st_mtime_ns, "size": st.st_size}
    ok = cur["sha256"] == SHARED_BASELINE["sha256"] and cur["size"] == SHARED_BASELINE["size"]
    print(f"SHARED {'UNCHANGED' if ok else 'CHANGED'}: {json.dumps(cur)}")
    if not ok:
        sys.exit(2)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cmd = sys.argv[1]
    if cmd == "setup": setup(sys.argv[2])
    elif cmd == "check": check(sys.argv[2])
    elif cmd == "guard": guard()
    else: raise SystemExit(f"unknown command {cmd}")
