"""Open-GitHub Skill Harvester (Bagian 5 dari Zero-Bias Training Prompt).

Mengambil SKILL.md dari repositori komunitas terbuka di GitHub melalui GitHub
REST API (tanpa browser, tanpa camoufox/playwright — cukup HTTP + JSON). Dirancang
untuk 3-stage harvesting:
  Stage 1: baca indeks awesome-list (agentskills.io / awesome-* repo).
  Stage 2: telusuri file SKILL.md di repo komunitas.
  Stage 3: (di trainer) transpile ke ~/.hermes/skills/<kategori>/<slug>/SKILL.md.

Catatan jujur: GitHub API tanpa token dibatasi 60 request/jam. Untuk harvesting
skala besar, set env GITHUB_TOKEN.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.error

API = "https://api.github.com"
_UA = "auto_skill_selector-harvester/0.1"

# Repositori indeks komunitas yang dikenal menyimpan / mendaftar SKILL.md.
AWESOME_REPOS = [
    "sickn33/agentic-awesome-skills",
    "theneoai/awesome-skills",
    "VoltAgent/awesome-agent-skills",
    "bergside/awesome-design-skills",
    "K-Dense-AI/scientific-agent-skills",
    "anthropics/skills",
]


def _http(url: str, timeout: int = 20) -> tuple[int, str]:
    """GET sederhana; kembalikan (status, body). Tidak pernah raise ke caller."""
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA,
        "Accept": "application/vnd.github+json",
    })
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def _api(path: str) -> dict | list | None:
    status, body = _http(f"{API}{path}")
    if status != 200 or not body:
        return None
    try:
        return json.loads(body)
    except Exception:
        return None


def list_repo_skill_files(repo: str, limit: int = 200) -> list[dict]:
    """Stage 2: telusuri seluruh file SKILL.md di sebuah repo (rekursif).

    Mengembalikan list {path, download_url, repo} untuk tiap SKILL.md ditemukan.
    """
    tree = _api(f"/repos/{repo}/git/trees/HEAD?recursive=1")
    if not tree or "tree" not in tree:
        return []
    out: list[dict] = []
    for entry in tree["tree"]:
        if entry.get("type") != "blob":
            continue
        path = entry.get("path", "")
        if path.endswith("SKILL.md"):
            out.append({
                "repo": repo,
                "path": path,
                "download_url": f"https://raw.githubusercontent.com/{repo}/HEAD/{path}",
            })
            if len(out) >= limit:
                break
    return out


def fetch_skill_text(download_url: str) -> str | None:
    """Ambil isi mentah sebuah SKILL.md dari raw.githubusercontent."""
    status, body = _http(download_url)
    return body if status == 200 and body else None


def discover_community_skills(repos: list[str] | None = None,
                              per_repo_limit: int = 40) -> list[dict]:
    """Stage 1+2: kumpulkan kandidat SKILL.md dari beberapa repo komunitas.

    Mengembalikan list {repo, path, slug, download_url}. Tidak menulis ke disk.
    """
    repos = repos or AWESOME_REPOS
    seen: set[str] = set()
    out: list[dict] = []
    for repo in repos:
        for item in list_repo_skill_files(repo, limit=per_repo_limit):
            path = item["path"]
            # slug = nama folder induk SKILL.md (konvensi Hermes)
            parts = path.split("/")
            slug = parts[-2] if len(parts) >= 2 else path
            if slug in seen:
                continue
            seen.add(slug)
            out.append({
                "repo": item["repo"],
                "path": path,
                "slug": slug,
                "download_url": item["download_url"],
            })
    return out


def harvest_and_ingest(repos: list[str] | None = None,
                       max_skills: int = 12,
                       skills_root=None) -> list[dict]:
    """Stage 3: unduh, transpile ke layout Hermes, dan siap diretrain.

    Menulis ke <skills_root>/<kategori-inferred>/<slug>/SKILL.md. Mengembalikan
    daftar skill yang berhasil diambil. Kategori diinferensi trainer.infer_category.
    """
    if skills_root is None:
        from trainer import get_skills_root
        skills_root = get_skills_root()
    from trainer import infer_category, tokenize

    candidates = discover_community_skills(repos, per_repo_limit=max_skills * 3)
    ingested: list[dict] = []
    for cand in candidates:
        if len(ingested) >= max_skills:
            break
        text = fetch_skill_text(cand["download_url"])
        if not text or len(text) < 120:
            continue
        slug = re.sub(r"[^a-z0-9._-]+", "-", cand["slug"].lower()).strip("-")
        if not slug:
            continue
        category = infer_category(slug, text[:600], text)
        dest = skills_root / category / slug
        dest.mkdir(parents=True, exist_ok=True)
        frontmatter_tags = f"[{category}, github-harvested]"
        (dest / "SKILL.md").write_text(
            "---\n"
            f"name: {slug}\n"
            f'description: "{text.splitlines()[0][:160].strip()}"\n'
            "version: 1.0.0\n"
            "metadata:\n"
            "  hermes:\n"
            f"    tags: {frontmatter_tags}\n"
            f"    source_repo: {cand['repo']}\n"
            "    status: probationary\n"
            "---\n\n"
            f"# {slug}\n\n"
            "Sumber: di-harvest dari GitHub komunitas "
            f"({cand['repo']}).\n\n"
            "## When to Use\n\n"
            f"{text[:3000]}\n",
            encoding="utf-8",
        )
        ingested.append({"slug": slug, "category": category, "repo": cand["repo"]})
    return ingested


if __name__ == "__main__":
    skills = discover_community_skills(per_repo_limit=20)
    print(f"Menemukan {len(skills)} kandidat SKILL.md dari GitHub komunitas.")
    for s in skills[:10]:
        print(f"  {s['repo']:42s} {s['slug']}")
