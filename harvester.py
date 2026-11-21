"""auto_skill_selector — harvester.py (Fase 2, Master Prompt §3.1).

Harvester multi-katalog WAJIB (Zero Vendor Lock-In):
  1. Hermes Agent Official: Bundled + Optional Skills Catalog (checkout lokal
     ~/.hermes/hermes-agent/skills & optional-skills, atau tarball repo resmi).
  2. Anthropic/Claude: anthropics/skills, alirezarezvani/claude-skills.
  3. Registri terbuka: agentskills.io (spesifikasi + direktori) dan skills.sh
     (direktori; entri dipetakan ke repo GitHub sumbernya).
  4. Repo GitHub kurasi lintas domain: sickn33/agentic-awesome-skills,
     theneoai/awesome-skills, VoltAgent/awesome-agent-skills,
     bergside/awesome-design-skills, K-Dense-AI/scientific-agent-skills.

Anti rate-limit GitHub (60 req/jam REST): SATU tarball codeload per repo
(bukan REST /contents), di-cache ke disk; git clone --depth 1 --filter=blob:none
--sparse sebagai fallback. GITHUB_TOKEN opsional; harvester WAJIB sukses tanpa
token. Parser schema-agnostic: SKILL.md frontmatter (name/description/summary/
role), AGENTS.md, README.md, .cursorrules.
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import subprocess
import tarfile
import urllib.request
from collections import defaultdict
from pathlib import Path

_UA = "auto_skill_selector-harvester/3.0"

# ---------------------------------------------------------------------------
# Katalog wajib (Master Prompt §3.1)
# ---------------------------------------------------------------------------
CATALOG_REPOS: list[str] = [
    # Anthropic / Claude ecosystem
    "anthropics/skills",
    "alirezarezvani/claude-skills",
    # Curated multi-domain open GitHub
    "sickn33/agentic-awesome-skills",
    "theneoai/awesome-skills",
    "VoltAgent/awesome-agent-skills",
    "bergside/awesome-design-skills",
    "K-Dense-AI/scientific-agent-skills",
    # skills.sh ecosystem leaders (sumber direktori skills.sh)
    "vercel-labs/skills",
    "vercel-labs/agent-skills",
    "mattpocock/skills",
    "openai/skills",
]

# Repo resmi Hermes Agent (bundled + optional skills ada di dalamnya).
HERMES_REPO = "NousResearch/hermes-agent"

# Halaman registri terbuka yang dicatat sebagai sumber (bukan REST GitHub).
OPEN_REGISTRIES = [
    "https://agentskills.io/home",
    "https://skills.sh",
]


def _http_bytes(url: str, timeout: int = 90) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def _tarball_url(repo: str) -> str:
    return f"https://codeload.github.com/{repo}/tar.gz/HEAD"


def _cache_dir() -> Path:
    base = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / \
        "plugin-data" / "auto_skill_selector" / "harvest-cache"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _fetch_tarball(repo: str, cache_dir: Path) -> bytes | None:
    """1 request tarball per repo, cache disk. Fallback: sparse git clone."""
    cache_file = cache_dir / (re.sub(r"[^A-Za-z0-9._-]+", "_", repo) + ".tar.gz")
    if cache_file.exists() and cache_file.stat().st_size > 500:
        return cache_file.read_bytes()
    data = _http_bytes(_tarball_url(repo))
    if data and len(data) > 500:
        cache_file.write_bytes(data)
        return data
    # Fallback: sparse clone (tetap tanpa REST API).
    clone_dir = cache_dir / (re.sub(r"[^A-Za-z0-9._-]+", "_", repo) + ".git")
    if not clone_dir.exists():
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                 f"https://github.com/{repo}.git", str(clone_dir)],
                check=True, capture_output=True, timeout=180)
        except Exception:
            return None
    # Bundle the sparse checkout into a tarball in-memory for the same parser.
    try:
        out = subprocess.run(
            ["tar", "-czf", "-", "-C", str(clone_dir), "."],
            check=True, capture_output=True, timeout=120)
        if out.stdout and len(out.stdout) > 500:
            cache_file.write_bytes(out.stdout)
            return out.stdout
    except Exception:
        return None
    return None


_SKILL_FILENAMES = ("SKILL.md", "AGENTS.md", "DESIGN.md", "README.md", ".cursorrules")


def _extract_skills_from_tarball(repo: str, data: bytes) -> list[dict]:
    """Parser multi-format schema-agnostic: cari file skill di seluruh tree."""
    out: list[dict] = []
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                base = m.name.rsplit("/", 1)[-1]
                if base not in _SKILL_FILENAMES:
                    continue
                # README hanya dihitung bila berada di folder yang tampak
                # seperti skill (ada SKILL.md lain di repo yang sama nanti
                # didedup); batasi ukuran agar tidak menelan dokumentasi raksasa.
                if m.size > 400_000:
                    continue
                f = tf.extractfile(m)
                if not f:
                    continue
                try:
                    text = f.read().decode("utf-8", "replace")
                except Exception:
                    continue
                parts = m.name.split("/")
                slug = parts[-2] if len(parts) >= 2 else base
                out.append({"repo": repo, "path": m.name, "slug": slug,
                            "text": text, "format": base})
    except Exception:
        return out
    return out


def harvest_hermes_official(cache_dir: Path | None = None) -> list[dict]:
    """Bundled + Optional Skills Catalog Hermes.

    Prioritas: checkout lokal ~/.hermes/hermes-agent (read-only, tidak menulis
    apa pun ke produksi). Bila tidak ada, tarball repo resmi NousResearch.
    """
    cache_dir = cache_dir or _cache_dir()
    local = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "hermes-agent"
    out: list[dict] = []
    for catalog in ("skills", "optional-skills"):
        root = local / catalog
        if root.exists():
            for f in sorted(root.rglob("SKILL.md")):
                try:
                    text = f.read_text("utf-8", "replace")
                except Exception:
                    continue
                out.append({
                    "repo": f"hermes-agent/{catalog}",
                    "path": str(f.relative_to(local)),
                    "slug": f.parent.name,
                    "text": text,
                    "format": "SKILL.md",
                })
    if out:
        return out
    data = _fetch_tarball(HERMES_REPO, cache_dir)
    if not data:
        return []
    all_files = _extract_skills_from_tarball(HERMES_REPO, data)
    for item in all_files:
        p = item["path"]
        if "/skills/" in p or "/optional-skills/" in p:
            item["repo"] = "hermes-agent/" + ("optional-skills" if "/optional-skills/" in p else "skills")
            out.append(item)
    return out


def discover_community_skills(repos: list[str] | None = None,
                              cache_dir: Path | None = None) -> list[dict]:
    """Kumpulkan kandidat skill dari SEMUA katalog wajib (tanpa menulis)."""
    repos = repos or CATALOG_REPOS
    cache_dir = cache_dir or _cache_dir()
    seen: set[str] = set()
    out: list[dict] = []
    # 1. Hermes official (bundled + optional).
    for item in harvest_hermes_official(cache_dir):
        key = item["slug"].lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    # 2-4. GitHub catalogs via tarball.
    for repo in repos:
        data = _fetch_tarball(repo, cache_dir)
        if not data:
            continue
        for item in _extract_skills_from_tarball(repo, data):
            slug = re.sub(r"[^a-z0-9._-]+", "-", item["slug"].lower()).strip("-")
            if not slug or slug in seen:
                continue
            # README/AGENTS tanpa frontmatter skill: hanya ambil bila ada
            # indikasi kuat (frontmatter name/description atau heading skill).
            if item["format"] in ("README.md", "AGENTS.md"):
                head = item["text"][:800].lower()
                if not (head.startswith("---") or "name:" in head or "## when to use" in head):
                    continue
            seen.add(slug)
            item["slug"] = slug
            out.append(item)
    return out


def _feature_entropy(text: str) -> float:
    words = re.findall(r"[a-z]+", text.lower())
    if not words:
        return 0.0
    counts: dict[str, int] = defaultdict(int)
    for w in words:
        counts[w] += 1
    n = len(words)
    return -sum((c / n) * math.log(c / n) for c in counts.values())


def _quality_score(text: str) -> float:
    if not text or len(text) < 120:
        return 0.0
    score = math.log1p(len(text))
    if text.lstrip().startswith("---"):
        score += 2.0
    lower = text.lower()
    score += 0.5 * sum(s in lower for s in ("when to use", "## ", "description"))
    return score * (1.0 + 0.1 * _feature_entropy(text))


def harvest_and_ingest(repos: list[str] | None = None,
                       max_skills: int = 120,
                       per_pillar_quota: int = 12,
                       skills_root: Path | None = None) -> list[dict]:
    """Panen multi-katalog, kategorikan ke 9 pilar, isi kuota seimbang.

    Menulis ke <skills_root>/<pilar>/<slug>/SKILL.md dengan frontmatter standar
    + status probationary + source_repo. Skill inti 54 tidak pernah ditimpa.
    """
    if skills_root is None:
        from trainer import get_skills_root
        skills_root = get_skills_root()
    from trainer import infer_category
    import corpus_core

    candidates = discover_community_skills(repos)
    for c in candidates:
        c["_q"] = _quality_score(c["text"])
    candidates.sort(key=lambda c: c["_q"], reverse=True)

    core_slugs = {slug for skills in corpus_core.CORE_SKILLS.values()
                  for slug, *_ in skills}
    per_pillar: dict[str, int] = defaultdict(int)
    ingested: list[dict] = []
    for cand in candidates:
        if len(ingested) >= max_skills:
            break
        text = cand["text"]
        slug = cand["slug"]
        if slug in core_slugs:
            continue
        category = infer_category(slug, text[:600], text)
        if category == "general":
            continue
        if per_pillar[category] >= per_pillar_quota:
            continue
        dest = skills_root / category / slug
        if (dest / "SKILL.md").exists():
            per_pillar[category] += 1
            continue
        # Ekstrak deskripsi terbaik dari frontmatter bila ada.
        desc = ""
        m = re.search(r"^description:\s*[\"']?(.+?)[\"']?\s*$", text, re.MULTILINE)
        if m:
            desc = m.group(1)[:200]
        if not desc:
            for line in text.splitlines():
                st = line.strip()
                if st and not st.startswith(("#", "---", "name:", "version:")):
                    desc = st[:200]
                    break
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "SKILL.md").write_text(
            "---\n"
            f"name: {slug}\n"
            f'description: "{desc}"\n'
            "version: 1.0.0\n"
            "metadata:\n"
            "  hermes:\n"
            f"    tags: [{category}, github-harvested]\n"
            f"    source_repo: {cand['repo']}\n"
            "    status: probationary\n"
            "---\n\n"
            f"# {slug}\n\n"
            f"Sumber: di-harvest dari {cand['repo']} (multi-catalog Fase 2).\n\n"
            "## When to Use\n\n"
            f"{text[:3000]}\n",
            encoding="utf-8",
        )
        per_pillar[category] += 1
        ingested.append({"slug": slug, "category": category, "repo": cand["repo"]})
    return ingested


def harvest_report() -> dict:
    """Ringkasan sumber untuk laporan jujur (katalog mana yang berhasil)."""
    cache_dir = _cache_dir()
    report: dict = {"registries": OPEN_REGISTRIES, "catalogs": {}}
    hermes = harvest_hermes_official(cache_dir)
    report["catalogs"]["hermes-official"] = len(hermes)
    for repo in CATALOG_REPOS:
        data = _fetch_tarball(repo, cache_dir)
        n = len(_extract_skills_from_tarball(repo, data)) if data else 0
        report["catalogs"][repo] = n
    return report


if __name__ == "__main__":
    import sys
    if "--report" in sys.argv:
        rep = harvest_report()
        print(json.dumps(rep, indent=2))
    else:
        cands = discover_community_skills()
        for c in cands:
            c["_q"] = _quality_score(c["text"])
        print(f"Kandidat skill dari {len(CATALOG_REPOS)} katalog + Hermes official: {len(cands)}")
        for c in cands[:12]:
            print(f"  {c['repo']:42s} {c['slug']:30s} q={c['_q']:.1f}")