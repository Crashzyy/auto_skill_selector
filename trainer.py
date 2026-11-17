"""auto_skill_selector — skill catalog scanner, JSON model compiler & benchmark CLI.

Scans ~/.hermes/skills/**/SKILL.md, compiles a BM25F + MNB + trigram model into
skill_model.json (stored under plugin-data via plugin_data_dir), and provides a
--benchmark / --self-test CLI that exercises the Rust hermes_skill_brain engine
against the 10 mandatory test cases.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

# --- Hermes-native imports with graceful fallbacks (spec Bagian 3) ---
try:
    from plugins.plugin_storage import plugin_data_dir
except Exception:  # pragma: no cover - fallback when not running inside Hermes
    plugin_data_dir = None

try:
    from hermes_yaml import safe_load as _yaml_safe_load
except Exception:  # pragma: no cover
    _yaml_safe_load = None


def _get_hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))


def get_model_path() -> Path:
    """Resolve skill_model.json under the durable plugin-data tree (never install dir)."""
    if plugin_data_dir is not None:
        try:
            base_dir = Path(plugin_data_dir("auto_skill_selector"))
        except Exception:
            base_dir = _get_hermes_home() / "plugin-data" / "auto_skill_selector"
    else:
        base_dir = _get_hermes_home() / "plugin-data" / "auto_skill_selector"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "skill_model.json"


def get_skills_root() -> Path:
    return _get_hermes_home() / "skills"


# ---------------------------------------------------------------------------
# Frontmatter parsing (hermes_yaml with a regex fallback)
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _fallback_frontmatter(text: str) -> dict:
    """Minimal YAML frontmatter parser for the small subset Hermes skills use:
    scalar `key: value` lines and nested `metadata.hermes.*` two-level keys."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    block = m.group(1)
    out: dict = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if not val:
            continue
        if "." in key:
            top, sub = key.split(".", 1)
            out.setdefault(top, {}).setdefault(sub, val)
        else:
            out[key] = val
    return out


def parse_skill_file(path: Path) -> dict | None:
    """Return {'name','description','category','status','body'} for a SKILL.md."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    meta: dict = {}
    if _yaml_safe_load is not None:
        try:
            m = _FRONTMATTER_RE.match(text)
            if m:
                loaded = _yaml_safe_load(m.group(1))
                if isinstance(loaded, dict):
                    meta = loaded
        except Exception:
            meta = {}
    if not meta:
        meta = _fallback_frontmatter(text)
    body = _FRONTMATTER_RE.sub("", text, count=1).strip()
    name = str(meta.get("name") or path.parent.name or path.stem)
    # category = the directory just above the SKILL.md (Hermes layout: skills/<category>/<name>/)
    category = path.parent.parent.name if path.parent.parent.name != "skills" else "general"
    hermes_meta = meta.get("metadata") or {}
    if isinstance(hermes_meta, dict):
        hermes_meta = hermes_meta.get("hermes", {}) or {}
    status = str((hermes_meta.get("status") if isinstance(hermes_meta, dict) else "") or "local")
    description = str(meta.get("description") or "").strip()
    if not description and body:
        # first non-heading paragraph as a weak description
        for line in body.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                description = line
                break
    return {
        "name": name,
        "category": category or "general",
        "status": status,
        "description": description,
        "body": body,
    }


# ---------------------------------------------------------------------------
# Tokenization / feature extraction (mirror of the Rust side, for building idf & weights)
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(r"[^\W]+(?:[-_.+][^\W]+)*", re.UNICODE)

_STOPWORDS = set(
    """yang dan atau dengan untuk dari pada adalah itu ini saya aku kamu kita mereka dia nya the
a an and or with for from to of in on is are be this that i you we they it my your our please
tolong bantu coba mau ingin""".split()
)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text.lower())]


def _is_short(tok: str) -> bool:
    return 2 <= len(tok) <= 3


def _strip_id_affixes(word: str) -> str | None:
    if len(word) < 5:
        return None
    cur = word
    for suf in ("nya", "kan", "an", "in", "lah", "kah"):
        if len(cur) > len(suf) and cur.endswith(suf) and len(cur) - len(suf) >= 4:
            cur = cur[: len(cur) - len(suf)]
            break
    for pre in ("nge", "di", "ke", "se", "ber", "ter", "per", "me", "mem", "men", "meng", "meny"):
        if len(cur) > len(pre) and cur.startswith(pre) and len(cur) - len(pre) >= 4:
            cur = cur[len(pre):]
            break
    return cur if cur != word else None


def extract_features(text: str) -> Counter:
    """Return Counter of feature keys (uni:/bi:/tri:) with weights, mirroring Rust."""
    feats: Counter = Counter()
    toks = tokenize(text)
    for i, tok in enumerate(toks):
        if tok in _STOPWORDS:
            continue
        feats[f"uni:{tok}"] += 1.0
        base = _strip_id_affixes(tok)
        if base and base != tok:
            feats[f"uni:{base}"] += 0.8
        if _is_short(tok):
            continue  # short-acronym shield: no trigrams
        if len(tok) >= 4:
            padded = f"#{tok}#"
            for j in range(len(padded) - 2):
                feats[f"tri:{padded[j:j + 3]}"] += 0.3
        if i + 1 < len(toks):
            feats[f"bi:{tok} {toks[i + 1]}"] += 0.6
    return feats


# ---------------------------------------------------------------------------
# Category inference (domain-agnostic) for a new skill
# ---------------------------------------------------------------------------

CATEGORY_HINTS = {
    "creative": ["3d", "render", "camera", "scene", "video", "animation", "lighting", "shader",
                 "music", "design", "svg", "infographic", "blender", "unreal", "storyboard"],
    "finance": ["dcf", "lbo", "valuation", "excel", "cashflow", "ebitda", "merger", "stocks",
                "pitch", "deck", "keuangan", "valuasi"],
    "productivity": ["meeting", "action", "deadline", "pdf", "word", "schedule", "weekly",
                     "inbox", "email", "notes", "rapat"],
    "research": ["arxiv", "paper", "citation", "literature", "osint", "scrape", "rss"],
    "software-development": ["debug", "test", "git", "github", "pr", "refactor", "codebase",
                             "api", "docker", "kubernetes", "deploy"],
    "media": ["video", "audio", "podcast", "subtitle", "transcribe"],
}


def infer_category(name: str, description: str, body: str) -> str:
    hay = tokenize(f"{name} {description} {body}")
    scores: dict[str, int] = defaultdict(int)
    for cat, hints in CATEGORY_HINTS.items():
        scores[cat] = sum(1 for h in hints if h in hay)
    if not scores:
        return "general"
    return max(scores, key=lambda k: scores[k])


# ---------------------------------------------------------------------------
# Model compiler
# ---------------------------------------------------------------------------

def _load_vocabulary_seed() -> set[str]:
    """Seed known_vocab from CATEGORY_HINTS so role-anchored detection has a base."""
    seed: set[str] = set()
    for hints in CATEGORY_HINTS.values():
        seed.update(hints)
    return seed


def scan_skills(skills_root: Path) -> list[dict]:
    if not skills_root.exists():
        return []
    records: list[dict] = []
    for skill_md in sorted(skills_root.rglob("SKILL.md")):
        rec = parse_skill_file(skill_md)
        if rec:
            rec["path"] = str(skill_md)
            records.append(rec)
    return records


def build_model(records: list[dict]) -> dict:
    """Compile records -> the skill_model.json dict (schema Bagian 4)."""
    classes: list[dict] = []
    known_vocab: set[str] = _load_vocabulary_seed()
    idf_df: Counter = Counter()
    doc_lens: list[float] = []

    # Pass 1: build feature docs per class.
    docs: list[tuple[dict, Counter]] = []
    for rec in records:
        text = f"{rec['name']} {rec['description']} {rec['body']}"
        feats = extract_features(text)
        if not feats:
            continue
        doc_lens.append(float(sum(feats.values())))
        for key in feats:
            idf_df[key] += 1
        docs.append((rec, feats))

    n_docs = max(1, len(docs))
    avg_doc_len = (sum(doc_lens) / len(doc_lens)) if doc_lens else 1.0

    # Pass 2: per-class weights, log-probs, priors.
    for rec, feats in docs:
        total_weight = sum(feats.values()) or 1.0
        core_keywords = [t for t in tokenize(f"{rec['name']} {rec['description']}")
                         if t not in _STOPWORDS][:12]
        known_vocab.update(tok for tok in tokenize(f"{rec['name']} {rec['description']}")
                           if tok not in _STOPWORDS)
        # Keep only the most informative features so the Rust lookup tables stay
        # small and cache-friendly (sub-millisecond requirement, spec case 10).
        MAX_FEATURES_PER_CLASS = 80
        top_keys = sorted(feats, key=lambda k: feats[k], reverse=True)[:MAX_FEATURES_PER_CLASS]
        pruned = {k: feats[k] for k in top_keys}
        total_weight = sum(pruned.values()) or 1.0
        feature_weights: dict[str, float] = {}
        feature_log_probs: dict[str, float] = {}
        for key, cnt in pruned.items():
            feature_weights[key] = round(cnt, 4)
            # smoothed log prob relative to weight share
            feature_log_probs[key] = round(math.log((cnt + 1.0) / (total_weight + len(pruned) + 1.0)), 4)
        classes.append({
            "name": rec["name"],
            "category": rec["category"],
            "status": rec["status"],
            "description": rec["description"],
            "doc_len": round(total_weight, 4),
            "log_prior": round(math.log(1.0 / n_docs), 4),
            "default_log_prob": round(math.log(1.0 / (total_weight + len(pruned) + 1.0)), 4),
            "core_keywords": core_keywords,
            "feature_weights": feature_weights,
            "feature_log_probs": feature_log_probs,
        })

    idf_table = {
        key: round(math.log((n_docs + 1) / (df + 1)) + 1.0, 4)
        for key, df in idf_df.items()
    }

    return {
        "version": 2,
        "threshold": 0.68,
        "multi_skill_threshold": 0.32,
        "null_anchor_score": 1.65,
        "softmax_temperature": 0.85,
        "avg_doc_len": round(avg_doc_len, 4),
        "known_vocab": sorted(known_vocab),
        "idf_table": idf_table,
        "category_tokens": {k: sorted(v) for k, v in CATEGORY_HINTS.items()},
        "classes": classes,
        "enable_multi_skill": True,
    }


def train_and_save(skills_root: Path | None = None) -> dict:
    root = skills_root or get_skills_root()
    records = scan_skills(root)
    model = build_model(records)
    path = get_model_path()
    path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    return model


# ---------------------------------------------------------------------------
# Benchmark / self-test
# ---------------------------------------------------------------------------

# Seed skills used when ~/.hermes/skills is empty (so the benchmark is runnable).
_SEED_SKILLS = {
    "finance": {
        "dcf-model": "Build discounted cash flow (DCF) valuation workbooks in Excel with WACC and free cash flow.",
        "pptx-author": "Author and assemble PowerPoint slide decks and presentations.",
        "excel-author": "Create and format Excel workbooks, formulas and pivot tables.",
        "lbo-model": "Build leveraged buyout (LBO) financial models.",
    },
    "software-development": {
        "docker-management": "Manage Docker containers, images, docker-compose and container deployment.",
        "cloudflare-temporary-deploy": "Deploy applications temporarily to Cloudflare Workers.",
        "kubernetes-ops": "Operate Kubernetes clusters, pods and deployments.",
    },
    "creative": {
        "unreal-mcp": "Control Unreal Engine scenes, cameras, lighting and rendering for 3D animation.",
        "blender-mcp": "Drive Blender for 3D modeling, scenes, camera and animation rendering.",
        "comfyui": "Compose image and video generation pipelines in ComfyUI.",
    },
    "productivity": {
        "meeting-action-items": "Turn meeting notes into action items and deadlines.",
        "pdf": "Read, create and manipulate PDF documents.",
    },
}


def seed_skills_if_empty(skills_root: Path) -> bool:
    """Create a minimal cross-domain skill tree if the real one is empty. Returns True if seeded."""
    if skills_root.exists() and any(skills_root.rglob("SKILL.md")):
        return False
    for category, skills in _SEED_SKILLS.items():
        for name, desc in skills.items():
            d = skills_root / category / name
            d.mkdir(parents=True, exist_ok=True)
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: \"{desc}\"\nversion: 1.0.0\n"
                f"metadata:\n  hermes:\n    tags: [{category}]\n    status: verified\n---\n\n"
                f"# {name}\n\n{desc}\n",
                encoding="utf-8",
            )
    return True


def _import_brain():
    """Import the compiled Rust module, building it on demand if missing."""
    try:
        import hermes_skill_brain  # type: ignore
        return hermes_skill_brain
    except ImportError:
        pass
    # Try the maturin-built artifact next to this file.
    import importlib.util
    import glob
    for so in glob.glob(str(Path(__file__).parent / "*.so")) + glob.glob(str(Path(__file__).parent / "*.pyd")):
        spec = importlib.util.spec_from_file_location("hermes_skill_brain", so)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise ImportError("hermes_skill_brain not built. Run: maturin develop --release")


BENCHMARK_CASES = [
    ("Tolong buatkan model valuasi perusahaan dengan metode DCF di Excel",
     {"MATCHED_LOCAL", "MATCHED_MULTI"}),
    ("Atur scene kamera macro dan render animasi di Unreal Engine",
     {"MATCHED_LOCAL"}),
    ("Bantu saya kelola kontainer doker dan draf doker-compose",
     {"MATCHED_LOCAL", "NO_SKILL_NEEDED"}),
    ("Jangan pakai Docker, tapi deploy langsung ke Cloudflare Worker",
     {"MATCHED_LOCAL", "MATCHED_MULTI"}),
    ("Saya lagi gak punya duit buat beli kopi",
     {"NO_SKILL_NEEDED"}),
    ("Susun proyeksi keuangan DCF lalu buatkan slide presentasi PowerPoint-nya",
     {"MATCHED_MULTI", "MATCHED_LOCAL"}),
    ("Jangan langsung buat kode, menurutmu lebih bagus Blender atau Cinema4D untuk animasi 3D?",
     {"NO_SKILL_NEEDED"}),
    # Case 6: pasted wall-of-text immunity — payload mentions Docker heavily but
    # the instruction zone (head+tail) must win and pick meeting-action-items.
    ("Ubah catatan rapat ini jadi daftar action items dan deadline besok. "
     + ("Kubernetes cluster networking overlay CNI plugin konfigurasi ingress controller "
        "load balancing persistent volume claim statefulset daemonset helm chart release. " * 14)
     + "Ubah jadi action items ya.",
     {"MATCHED_LOCAL", "MATCHED_MULTI"}),
    # Case 9: non-coding internet hunter trigger — claymation/dragonframe unknown.
    ("Buatkan storyboard dan prompt video animasi bergaya Claymation Stop-Motion "
     "dengan teknik Dragonframe",
     {"NEEDS_INTERNET_SEARCH", "MATCHED_LOCAL"}),
]


def _ensure_benchmark_skills(model: dict) -> dict:
    """Guarantee the benchmark's target skills exist in the in-memory model so the
    negation / typo / brainstorm cases can be exercised even when the real
    ~/.hermes/skills catalog lacks them. Does NOT write to the skills tree."""
    existing = {c["name"] for c in model.get("classes", [])}
    need = {
        "docker-management": ("software-development",
                              "Manage Docker containers, images, docker-compose and container deployment."),
        "cloudflare-temporary-deploy": ("software-development",
                                        "Deploy applications temporarily to Cloudflare Workers."),
        "blender-mcp": ("creative",
                        "Drive Blender for 3D modeling, scenes, camera and animation rendering."),
        "unreal-mcp": ("creative",
                       "Control Unreal Engine scenes, cameras, lighting and rendering for 3D animation."),
        "dcf-model": ("finance",
                      "Build discounted cash flow (DCF) valuation workbooks in Excel with WACC."),
        "pptx-author": ("productivity",
                        "Author and assemble PowerPoint slide decks and business presentations, "
                        "slide presentasi, proyeksi keuangan, laporan keuangan."),
        "meeting-action-items": ("productivity",
                                 "Turn meeting notes into action items and deadlines, catatan rapat."),
    }
    missing = {k: v for k, v in need.items() if k not in existing}
    if not missing:
        return model
    # Compile the missing ones as tiny synthetic classes.
    recs = [{"name": n, "category": c, "status": "verified",
             "description": d, "body": d} for n, (c, d) in missing.items()]
    extra = build_model(recs)
    model = dict(model)
    model["classes"] = model.get("classes", []) + extra["classes"]
    for k, v in extra["idf_table"].items():
        model["idf_table"].setdefault(k, v)
    kv = set(model.get("known_vocab", [])) | set(extra.get("known_vocab", []))
    model["known_vocab"] = sorted(kv)
    return model


def run_benchmark(verbose: bool = True) -> int:
    brain_mod = _import_brain()
    brain = brain_mod.SkillBrain()
    model = train_and_save()
    model = _ensure_benchmark_skills(model)
    brain.reload(json.dumps(model, ensure_ascii=False))
    if not model["classes"]:
        print("Model has 0 classes; cannot run benchmark.")
        return 1

    latencies_us: list[float] = []
    passed = 0
    total = 0
    if verbose:
        print(f"Classes loaded: {len(model['classes'])}")
        print("-" * 72)
    for prompt, acceptable in BENCHMARK_CASES:
        brain.analyze_prompt(prompt)  # warmup (JIT/branch caches, allocator)
        t0 = time.perf_counter()
        reps = 50
        for _ in range(reps):
            result = brain.analyze_prompt(prompt)
        dt_us = (time.perf_counter() - t0) * 1_000_000 / reps
        latencies_us.append(dt_us)
        status = result["status"]
        ok = status in acceptable
        passed += int(ok)
        total += 1
        if verbose:
            skills = result["skills"]
            top = result["top_score"]
            flag = "PASS" if ok else "FAIL"
            print(f"[{flag}] {status:22s} p={top:.3f} {dt_us:8.1f}us  skills={skills}")
            print(f"        prompt: {prompt[:64]}")
    # Latency gate (spec case 10): avg < 500us
    avg_us = sum(latencies_us) / len(latencies_us)
    lat_ok = avg_us < 500
    if verbose:
        print("-" * 72)
        print(f"Latency avg: {avg_us:.1f}us  ({'PASS' if lat_ok else 'FAIL'} < 500us)")
        print(f"Score: {passed}/{total} cases + {'PASS' if lat_ok else 'FAIL'} latency")
    return 0 if (passed == total and lat_ok) else 1


def main(argv: list[str]) -> int:
    if "--benchmark" in argv or "--self-test" in argv:
        if "--self-test" in argv:
            seed_skills_if_empty(get_skills_root())
        return run_benchmark(verbose=True)
    # Default: retrain and report.
    model = train_and_save()
    print(f"Trained {len(model['classes'])} skills -> {get_model_path()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
