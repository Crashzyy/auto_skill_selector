"""auto_skill_selector — trainer.py (Fase 2).

Scanner katalog skill + compiler model JSON untuk mesin Rust hermes_skill_brain.

Kontrak Fase 2 (Master Prompt §3.3 & §5):
  * Zona dokumen S/A/B/C (8.0 / 4.5 / 2.5 / 0.6) -> feature_weights.
  * Category-Stratified IDF: kontribusi 1/9 per pilar; penambahan dokumen di
    satu pilar TIDAK mengubah IDF pilar lain (uji stres +10 skill).
  * Pruning top-80 lalu normalisasi L2 per kelas ke 100.0 ± 0.01 (gerbang 1).
  * Category Gain Equalization: gain self-match antar pilar disetarakan
    (domain_parity_score >= 0.92, category_cv <= 0.08; gerbang 2).
  * θ₀ (null_anchor_score) dikalibrasi ROC dari skor self-match aktual mesin
    Rust (bukan tebakan skala), temperature softmax tetap.
  * ban_tags per kelas untuk hard-mask Stage 2 (klaster sinonim Excel dsb.).
  * Centroid kategori numerik untuk komponen centroid-cosine Stage 4.

Model disimpan di plugin-data (tahan `plugins update`), bukan di install dir.
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

# --- Hermes-native imports with graceful fallbacks ---
try:
    from plugins.plugin_storage import plugin_data_dir
except Exception:  # pragma: no cover
    plugin_data_dir = None

try:
    from hermes_yaml import safe_load as _yaml_safe_load
except Exception:  # pragma: no cover
    _yaml_safe_load = None


def _get_hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))


def get_model_path() -> Path:
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
# 9 Pilar Fase 2 (Master Prompt §3.2) — sumber kebenaran tunggal kategori.
# ---------------------------------------------------------------------------
PILLARS = [
    "data-analytics", "3d-video-animation", "audio-music-podcast",
    "design-ui-ux", "finance-business", "writing-editorial",
    "productivity-office", "research-science", "software-devops",
]
N_PILLARS = len(PILLARS)

# Pemetaan kategori lama / vendor -> pilar Fase 2 (inferensi memakai ini dulu).
_CATEGORY_ALIASES = {
    "data-analytics": "data-analytics", "data-science": "data-analytics",
    "analytics": "data-analytics", "bi": "data-analytics",
    "3d-animation": "3d-video-animation", "video-audio": "3d-video-animation",
    "3d-video-animation": "3d-video-animation", "media": "3d-video-animation",
    "animation": "3d-video-animation", "video": "3d-video-animation",
    "audio-music-podcast": "audio-music-podcast", "audio": "audio-music-podcast",
    "music": "audio-music-podcast", "podcast": "audio-music-podcast",
    "design": "design-ui-ux", "design-ui-ux": "design-ui-ux",
    "ui-ux": "design-ui-ux", "creative": "design-ui-ux",
    "finance": "finance-business", "finance-business": "finance-business",
    "business": "finance-business", "consulting": "finance-business",
    "writing": "writing-editorial", "writing-editorial": "writing-editorial",
    "editorial": "writing-editorial", "marketing": "writing-editorial",
    "productivity": "productivity-office", "productivity-office": "productivity-office",
    "office": "productivity-office", "operations": "productivity-office",
    "note-taking": "productivity-office", "email": "productivity-office",
    "research": "research-science", "research-science": "research-science",
    "science": "research-science", "osint": "research-science",
    "software-development": "software-devops", "software-devops": "software-devops",
    "devops": "software-devops", "web-development": "software-devops",
    "software": "software-devops", "web": "software-devops",
}

# Concept graph per pilar (EN + ID) untuk inferensi kategori & ekspansi Zona A.
PILLAR_CONCEPT_GRAPH: dict[str, dict[str, list[str]]] = {
    "data-analytics": {
        "en": ["sql", "bi", "dashboard", "pivot", "tabular", "cleaning", "forecasting",
               "forecast", "cohort", "funnel", "etl", "pipeline", "spreadsheet", "modeling",
               "dataset", "csv", "parquet", "pandas", "query", "eda", "chart", "plot",
               "visualization", "anomaly", "correlation", "regression", "kpi", "retention",
               "churn", "statistics", "metric", "tableau", "metabase", "superset", "dbt"],
        "id": ["analisis data", "olah data", "pembersihan data", "grafik", "visualisasi",
               "tren", "anomali", "korelasi", "regresi", "peramalan", "prediksi",
               "tabel pivot", "metrik", "statistik", "kueri", "dasbor", "lembar sebar"],
    },
    "3d-video-animation": {
        "en": ["blender", "3d", "modeling", "mesh", "rigging", "scene", "render", "shader",
               "video", "editing", "ffmpeg", "motion", "graphics", "subtitle", "captioning",
               "storyboard", "color", "grading", "keyframe", "compositing", "animation",
               "unreal", "houdini", "cinema4d", "vfx", "timeline", "mp4", "animatic"],
        "id": ["tiga dimensi", "adegan", "merender", "tekstur", "tulang karakter",
               "pencahayaan", "animasi", "gerak", "penyuntingan video", "takarir",
               "papan cerita", "gradasi warna", "bingkai kunci", "klip", "video"],
    },
    "audio-music-podcast": {
        "en": ["podcast", "production", "audio", "transcription", "whisper", "noise",
               "reduction", "mastering", "music", "composition", "midi", "voiceover",
               "tts", "stem", "separation", "mixing", "daw", "spectrogram", "waveform",
               "lyrics", "songwriting", "recording", "microphone", "equalizer", "reverb"],
        "id": ["siniar", "produksi siniar", "transkripsi audio", "pengurangan derau",
               "komposisi musik", "sulih suara", "pemisahan stem", "rekaman", "lagu",
               "lirik", "musik", "suara", "olah audio", "spektrogram", "buku audio"],
    },
    "design-ui-ux": {
        "en": ["infographic", "mermaid", "architecture", "diagram", "wireframe", "mockup",
               "brand", "identity", "typography", "landing", "web", "design", "accessibility",
               "audit", "ui", "ux", "prototype", "figma", "excalidraw", "svg", "poster",
               "palette", "layout", "grid", "icon", "logo", "illustration", "flowchart"],
        "id": ["infografis", "infografik", "diagram arsitektur", "diagram alur", "bagan",
               "kerangka kawat", "purwarupa", "identitas merek", "tipografi", "halaman arahan",
               "desain web", "audit aksesibilitas", "antarmuka", "palet warna", "tata letak",
               "ilustrasi", "poster", "komik", "sketsa"],
    },
    "finance-business": {
        "en": ["financial", "modeling", "dcf", "mece", "strategy", "memo", "pitch", "deck",
               "investor", "narrative", "invoice", "ledger", "reconciliation", "pricing",
               "unit", "economics", "market", "sizing", "valuation", "wacc", "irr", "npv",
               "lbo", "merger", "acquisition", "budget", "payroll", "tax", "equity",
               "dividend", "bond", "stock", "swot", "okr", "consulting", "mckinsey"],
        "id": ["pemodelan keuangan", "arus kas terdiskonto", "valuasi", "kerangka mece",
               "memo strategi", "dek pitch", "narasi investor", "faktur", "rekonsiliasi",
               "penetapan harga", "unit ekonomi", "ukuran pasar", "anggaran", "pajak",
               "neraca", "anuitas", "laba rugi", "saham", "obligasi", "dividen", "konsultansi"],
    },
    "writing-editorial": {
        "en": ["seo", "copywriting", "technical", "documentation", "pager", "executive",
               "brief", "social", "media", "campaign", "press", "release", "translation",
               "localization", "bilingual", "editing", "proofreading", "blog", "article",
               "newsletter", "content", "calendar", "hook", "headline", "rewrite",
               "paraphrase", "summarization", "tone", "humanize", "thread", "scriptwriting"],
        "id": ["penulisan seo", "naskah iklan", "dokumentasi teknis", "ringkasan eksekutif",
               "kampanye media sosial", "siaran pers", "penerjemahan", "lokalisasi",
               "dwibahasa", "penyuntingan", "koreksi baca", "artikel blog", "nawala",
               "kalender konten", "judul utama", "tulis ulang", "parafrase", "peringkasan",
               "utas", "konten", "tulisan", "draf"],
    },
    "productivity-office": {
        "en": ["pdf", "extraction", "manipulation", "ocr", "word", "docx", "reporting",
               "powerpoint", "pptx", "slide", "deck", "excel", "xlsx", "automation",
               "sop", "checklist", "meeting", "notes", "action", "items", "minutes",
               "deadline", "calendar", "email", "triage", "inbox", "template", "form",
               "merge", "documents", "conversion", "weekly", "review", "planning"],
        "id": ["ekstraksi pdf", "pindai", "dokumen word", "laporan", "salindia",
               "presentasi", "otomasi excel", "lembar sebar", "daftar periksa",
               "notula rapat", "risalah", "daftar tugas", "tenggat", "kalender",
               "pemilahan surel", "kotak masuk", "templat", "formulir", "gabung dokumen",
               "konversi berkas", "tinjauan mingguan", "perencanaan", "prosedur tetap"],
    },
    "research-science": {
        "en": ["literature", "review", "citation", "academic", "latex", "paper", "arxiv",
               "osint", "fact", "checking", "bioinformatics", "scientific", "data",
               "patent", "policy", "analysis", "survey", "design", "questionnaire",
               "bibliometric", "meta", "systematic", "peer", "journal", "genomics",
               "experiment", "simulation", "molecular", "protein", "clinical", "grant"],
        "id": ["tinjauan pustaka", "sitasi", "makalah akademik", "daftar pustaka",
               "cek fakta", "jejak digital", "bioinformatika", "analisis paten",
               "analisis kebijakan", "desain survei", "kuesioner", "bibliometrik",
               "meta analisis", "tinjauan sistematis", "telaah sejawat", "jurnal",
               "eksperimen", "simulasi", "proposal penelitian", "hibah", "kartu belajar"],
    },
    "software-devops": {
        "en": ["backend", "api", "code", "review", "frontend", "react", "html", "web",
               "app", "ci", "cd", "docker", "kubernetes", "database", "schema",
               "optimization", "security", "audit", "automated", "testing", "debugging",
               "unit", "test", "tdd", "refactoring", "deployment", "monitoring",
               "microservices", "rest", "graphql", "git", "pull", "request", "serverless",
               "cloudflare", "nginx", "rust", "python", "typescript", "pentest"],
        "id": ["api backend", "tinjauan kode", "aplikasi web", "kontainer", "skema basis data",
               "optimasi skema", "audit keamanan", "pengujian otomatis", "awakutu",
               "uji unit", "refaktorisasi", "penerapan", "pemantauan", "pencatatan log",
               "repositori", "pull request", "uji penetrasi", "kerentanan", "otentikasi",
               "skrip shell", "profil kinerja", "uji beban"],
    },
}

CATEGORY_HINTS = {
    pillar: [t.lower() for t in (g["en"] + g["id"])]
    for pillar, g in PILLAR_CONCEPT_GRAPH.items()
}

# Bigram kolokasi domain (bobot ekstra 2.5x, spec §1.3 Mode 1).
DOMAIN_BIGRAMS: dict[str, float] = {
    "pivot table": 2.5, "time series": 2.5, "ab testing": 2.5, "data cleaning": 2.5,
    "color grading": 2.5, "motion graphics": 2.5, "stem separation": 2.5,
    "noise reduction": 2.5, "design system": 2.5, "landing page": 2.5,
    "brand identity": 2.5, "financial model": 2.5, "pitch deck": 2.5,
    "issue tree": 2.5, "unit economics": 2.5, "market sizing": 2.5,
    "cash flow": 2.5, "action items": 2.5, "meeting notes": 2.5,
    "literature review": 2.5, "press release": 2.5, "content calendar": 2.5,
    "code review": 2.5, "security audit": 2.5, "database schema": 2.5,
    "neraca lajur": 2.5, "arus kas": 2.5, "laba rugi": 2.5, "lembar sebar": 2.5,
    "tinjauan pustaka": 2.5, "daftar tugas": 2.5, "diagram alur": 2.5,
}

# Klaster sinonim untuk ban_tags (harus selaras dengan BAN_CLUSTERS di Rust).
_BAN_TAG_CLUSTERS = {
    "excel": ["excel", "xlsx", "xls"],
    "spreadsheet": ["spreadsheet", "lembar sebar", "google sheets", "sheets", "excel", "xlsx", "xls"],
    "powerpoint": ["powerpoint", "pptx", "ppt"],
    "word": ["word", "docx", "doc"],
    "pdf": ["pdf"],
    "docker": ["docker", "kontainer", "container"],
    "blender": ["blender"],
    "sql": ["sql", "mysql", "postgres", "postgresql", "sqlite"],
    "html": ["html", "web", "website"],
    "csv": ["csv"],
    "latex": ["latex"],
    "mermaid": ["mermaid"],
    "ffmpeg": ["ffmpeg"],
    "whisper": ["whisper"],
    "midi": ["midi"],
}


def infer_category(name: str, description: str, body: str, folder_hint: str = "") -> str:
    """Inferensi pilar: alias folder dulu, lalu concept-graph scoring."""
    hint = _CATEGORY_ALIASES.get(folder_hint.lower().strip())
    if hint:
        return hint
    hay_tokens = set(tokenize(f"{name} {description} {body[:1500]}"))
    hay_text = f" {name} {description} {body[:1500]} ".lower()
    scores: dict[str, int] = {}
    for pillar, graph in PILLAR_CONCEPT_GRAPH.items():
        score = 0
        for term in graph["en"] + graph["id"]:
            term = term.lower()
            if " " in term:
                if term in hay_text:
                    score += 3
            elif term in hay_tokens:
                score += 1
        scores[pillar] = score
    if not scores or max(scores.values()) == 0:
        return "general"
    return max(scores, key=lambda k: scores[k])


# ---------------------------------------------------------------------------
# Frontmatter parsing (hermes_yaml with a regex fallback)
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _fallback_frontmatter(text: str) -> dict:
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
    name = ""
    for key in ("name", "id", "title"):
        val = meta.get(key)
        if isinstance(val, str) and val.strip():
            name = val.strip()
            break
    if not name:
        for line in body.splitlines():
            st = line.strip()
            if st.startswith("# ") and not st.startswith("## "):
                name = st.lstrip("#").strip()
                break
    if not name:
        name = path.parent.name or path.stem
    folder_cat = path.parent.parent.name if path.parent.parent.name != "skills" else ""
    hermes_meta = meta.get("metadata") or {}
    if isinstance(hermes_meta, dict):
        hermes_meta = hermes_meta.get("hermes", {}) or {}
    status = str((hermes_meta.get("status") if isinstance(hermes_meta, dict) else "") or "local")
    description = ""
    for key in ("description", "summary", "when_to_use", "role"):
        val = meta.get(key)
        if isinstance(val, str) and val.strip():
            description = val.strip()
            break
    if not description and body:
        for line in body.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                description = line
                break
    category = infer_category(name, description, body, folder_hint=folder_cat)
    return {
        "name": name,
        "category": category,
        "status": status,
        "description": description,
        "body": body,
        "_meta": meta,
        "_slug": path.parent.name,
        "_source_format": _detect_source_format(path, meta),
    }


def _detect_source_format(path: Path, meta: dict) -> str:
    fname = path.name.lower()
    if fname == "skill.md":
        return "hermes_skill_md"
    if fname == "agents.md":
        return "agents_md"
    if fname == "design.md":
        return "design_md"
    if fname == "readme.md":
        return "readme_md"
    if fname == ".cursorrules":
        return "cursor_rules_adapted"
    if isinstance(meta, dict) and ("globs" in meta or "allowed-tools" in meta):
        return "agentskills_io"
    return "markdown_adapted"


# ---------------------------------------------------------------------------
# Tokenization (mirror of the Rust side)
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(r"[^\W]+(?:[-_.+][^\W]+)*", re.UNICODE)

_STOPWORDS = set(
    """yang dan atau dengan untuk dari pada adalah itu ini saya aku kamu kita mereka dia nya the
a an and or with for from to of in on is are be this that i you we they it my your our please
tolong bantu coba mau ingin ke di akan sudah bisa agar biar supaya sebuah para si pun lah
tapi tetapi namun melainkan but however instead lantas habis setelah sesudah sebelum sambil
seraya serta plus juga""".split()
)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text.lower())]


# ---------------------------------------------------------------------------
# Zona S/A/B/C — pembobotan dokumen SKILL.md (BM25F W_{c,f})
# ---------------------------------------------------------------------------

ZONE_S_WEIGHT = 8.0
ZONE_A_WEIGHT = 4.5
ZONE_B_WEIGHT = 2.5
ZONE_C_WEIGHT = 0.6
ZONE_NORMALIZE_TOTAL = 100.0
ZONE_C_MAX_BODY_LINES = 80
MAX_FEATURES_PER_CLASS = 80

_ZONE_A_SECTIONS = ("when to use", "trigger", "triggers", "kapan digunakan")
_ZONE_B_SECTIONS = ("quick reference", "procedure", "prosedur", "commands", "perintah")


def _frontmatter_scalar_tags(meta: dict) -> list[str]:
    out: list[str] = []
    hermes = meta.get("metadata") or {}
    if isinstance(hermes, dict):
        hermes = hermes.get("hermes", {}) or {}
    for source in (meta, hermes):
        if not isinstance(source, dict):
            continue
        for key in ("tags", "keywords", "triggers", "trigger"):
            val = source.get(key)
            if isinstance(val, list):
                out.extend(str(v) for v in val)
            elif isinstance(val, str):
                out.append(val)
    return out


def _split_sections(body: str) -> tuple[list[tuple[str, list[str]]], list[str]]:
    sections: list[tuple[str, list[str]]] = []
    preamble: list[str] = []
    in_code = False
    current_heading = ""
    current_paras: list[str] = []
    buffer: list[str] = []

    def flush():
        if buffer:
            text = " ".join(b for b in buffer if b).strip()
            if text:
                if current_heading:
                    sections.append((current_heading, current_paras + [text]))
                else:
                    preamble.append(text)
            buffer.clear()

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if stripped.startswith("#"):
            flush()
            heading = stripped.lstrip("#").strip().lower()
            current_heading = heading
            sections.append((heading, []))
        else:
            buffer.append(stripped)
    flush()
    return sections, preamble


def zone_weights(rec: dict, lexicon: dict | None = None) -> dict[str, float]:
    """Feature weights berbobot Zona S/A/B/C, total L1 = 100.0 (pra-pruning).

    Ekspansi dwibahasa Zona A memakai lexicon_id_en (concept pairs + glosarium)
    sehingga skill EN dari katalog GitHub ikut terindeks padanan ID-nya.
    """
    meta = rec.get("_meta", {}) or {}
    slug = rec.get("_slug", "") or rec.get("name", "")

    s_texts: list[str] = [rec.get("name", ""), slug]
    s_texts.extend(_frontmatter_scalar_tags(meta))
    for line in rec.get("body", "").splitlines():
        st = line.strip()
        if st.startswith("# ") and not st.startswith("## "):
            s_texts.append(st.lstrip("#").strip())

    sections, preamble = _split_sections(rec.get("body", ""))
    a_texts: list[str] = [rec.get("description", "")]
    b_texts: list[str] = []
    c_texts: list[str] = list(preamble)
    for heading, paras in sections:
        is_a = any(h in heading for h in _ZONE_A_SECTIONS)
        is_b = any(h in heading for h in _ZONE_B_SECTIONS)
        if is_a:
            a_texts.extend(paras)
        elif is_b:
            b_texts.extend(paras)
        else:
            c_texts.extend(paras)
        if heading and not is_a:
            b_texts.append(heading)

    # Ekspansi dwibahasa Zona A (lexicon 4 lapisan).
    if lexicon:
        en_id = lexicon.get("en_to_id", {})
        id_en = lexicon.get("id_to_en", {})
        a_joined = " ".join(a_texts).lower()
        extra: list[str] = []
        for tok in set(tokenize(a_joined)):
            if tok in en_id:
                extra.append(en_id[tok])
            if tok in id_en:
                extra.extend(id_en[tok][:2])
        # Frasa konsep multi-kata.
        for pair in lexicon.get("concept_pairs", []):
            en, idn = pair["en"], pair["id"]
            if " " in en and en in a_joined:
                extra.append(idn)
            if " " in idn and idn in a_joined:
                extra.append(en)
        a_texts.extend(extra)

    c_text = " ".join(c_texts)
    c_lines = [l for l in c_text.splitlines() if l.strip()][:ZONE_C_MAX_BODY_LINES]
    c_text = "\n".join(c_lines)

    def zone_features(texts: list[str]) -> Counter:
        feats: Counter = Counter()
        for t in texts:
            feats.update(tokenize(t))
        return feats

    cS = zone_features(s_texts)
    cA = zone_features(a_texts)
    cB = zone_features(b_texts)
    cC = zone_features(c_text)

    raw_token: dict[str, float] = {}
    for zone_counter, w in ((cS, ZONE_S_WEIGHT), (cA, ZONE_A_WEIGHT),
                            (cB, ZONE_B_WEIGHT), (cC, ZONE_C_WEIGHT)):
        for tok, cnt in zone_counter.items():
            if tok in _STOPWORDS:
                continue
            raw_token[tok] = raw_token.get(tok, 0.0) + w * cnt

    if not raw_token:
        return {}

    # Kolokasi bigram domain: boost token penyusun + fitur bigram eksplisit.
    toks_ordered = list(raw_token.keys())
    for i in range(len(toks_ordered) - 1):
        bigram = f"{toks_ordered[i]} {toks_ordered[i + 1]}"
        if bigram in DOMAIN_BIGRAMS:
            raw_token[toks_ordered[i]] = raw_token.get(toks_ordered[i], 0.0) + DOMAIN_BIGRAMS[bigram]
            raw_token[toks_ordered[i + 1]] = raw_token.get(toks_ordered[i + 1], 0.0) + DOMAIN_BIGRAMS[bigram]

    # Turunkan fitur uni:/bi: (tanpa tri: — fuzzy trigram dihapus di Fase 2;
    # mesin Rust Fase 2 hanya memakai uni/bi sesuai kontrak BM25F 4 zona).
    derived: dict[str, float] = {}
    for tok, rw in raw_token.items():
        derived[f"uni:{tok}"] = derived.get(f"uni:{tok}", 0.0) + rw
    # Bigram dari urutan teks Zona S+A (nama & deskripsi) — kolokasi bermakna.
    sa_tokens: list[str] = []
    for t in s_texts + a_texts:
        sa_tokens.extend(tokenize(t))
    for i in range(len(sa_tokens) - 1):
        a, b = sa_tokens[i], sa_tokens[i + 1]
        if a in _STOPWORDS or b in _STOPWORDS:
            continue
        key = f"bi:{a} {b}"
        w = DOMAIN_BIGRAMS.get(f"{a} {b}", 0.6)
        derived[key] = derived.get(key, 0.0) + w * min(raw_token.get(a, 0.0), raw_token.get(b, 0.0)) * 0.15

    total_derived = sum(derived.values()) or 1.0
    scale = ZONE_NORMALIZE_TOTAL / total_derived
    return {key: w * scale for key, w in derived.items()}


# ---------------------------------------------------------------------------
# ban_tags per kelas (hard mask Stage 2)
# ---------------------------------------------------------------------------

def compute_ban_tags(rec: dict) -> list[str]:
    """Tag klaster sinonim yang dimiliki skill ini (nama/slug/deskripsi/tags).

    Skill excel-author -> {excel, xlsx, xls}; skill spreadsheet generik juga
    kena ban 'spreadsheet'. Dipakai Rust untuk hard-mask -inf.
    """
    meta = rec.get("_meta", {}) or {}
    hay = " ".join([
        rec.get("name", ""), rec.get("_slug", ""), rec.get("description", ""),
        " ".join(_frontmatter_scalar_tags(meta)),
    ]).lower()
    toks = set(tokenize(hay))
    tags: set[str] = set()
    for key, cluster in _BAN_TAG_CLUSTERS.items():
        if key in toks or any(m in toks for m in cluster if " " not in m):
            tags.update(cluster)
    # Frasa multi-kata (lembar sebar, google sheets).
    for key, cluster in _BAN_TAG_CLUSTERS.items():
        for m in cluster:
            if " " in m and m in hay:
                tags.update(cluster)
    return sorted(tags)


# ---------------------------------------------------------------------------
# Model compiler
# ---------------------------------------------------------------------------

def _load_lexicon() -> dict:
    try:
        import lexicon_builder as lb
        return lb.build_lexicon()
    except Exception:
        return {}


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


def _l2_normalize(weights: dict[str, float], target: float = ZONE_NORMALIZE_TOTAL) -> dict[str, float]:
    norm = math.sqrt(sum(v * v for v in weights.values())) or 1.0
    scale = target / norm
    return {k: v * scale for k, v in weights.items()}


def build_model(records: list[dict], lexicon: dict | None = None) -> dict:
    """Compile records -> skill_model.json (skema Fase 2)."""
    if lexicon is None:
        lexicon = _load_lexicon()
    classes: list[dict] = []
    known_vocab: set[str] = set(lexicon.get("known_vocab", []))
    for hints in CATEGORY_HINTS.values():
        for h in hints:
            known_vocab.update(w for w in h.split() if len(w) >= 3)

    # Pass 1: zona-weighted docs + pruning top-80 + L2 norm 100.0 (gerbang 1).
    docs: list[tuple[dict, dict[str, float]]] = []
    for rec in records:
        feats = zone_weights(rec, lexicon)
        if not feats:
            continue
        top_keys = sorted(feats, key=lambda k: feats[k], reverse=True)[:MAX_FEATURES_PER_CLASS]
        pruned = {k: feats[k] for k in top_keys}
        pruned = _l2_normalize(pruned, ZONE_NORMALIZE_TOTAL)
        docs.append((rec, pruned))

    n_docs = max(1, len(docs))
    avg_doc_len = ZONE_NORMALIZE_TOTAL  # semua kelas L2=100 -> doc_len seragam

    # Pass 2: log-probs MNB + prior + ban_tags.
    for rec, pruned in docs:
        total_weight = sum(pruned.values()) or 1.0
        core_keywords = [t for t in tokenize(f"{rec['name']} {rec['description']}")
                         if t not in _STOPWORDS][:12]
        known_vocab.update(tok for tok in tokenize(f"{rec['name']} {rec['description']}")
                           if tok not in _STOPWORDS and len(tok) >= 3)
        feature_weights = {k: round(v, 4) for k, v in pruned.items()}
        feature_log_probs = {
            k: round(math.log((v + 1.0) / (total_weight + len(pruned) + 1.0)), 4)
            for k, v in pruned.items()
        }
        classes.append({
            "name": rec["name"],
            "category": rec["category"],
            "status": rec["status"],
            "description": rec["description"],
            "doc_len": round(math.sqrt(sum(v * v for v in pruned.values())), 4),
            "log_prior": round(math.log(1.0 / n_docs), 4),
            "default_log_prob": round(math.log(1.0 / (total_weight + len(pruned) + 1.0)), 4),
            "core_keywords": core_keywords,
            "ban_tags": compute_ban_tags(rec),
            "feature_weights": feature_weights,
            "feature_log_probs": feature_log_probs,
        })

    # Category-Stratified IDF (spec §3.3 mekanisme 1):
    #   IDF_strat(f) = ln(1 + K / (0.5 + sum_k df_k(f)/|C_k|))
    # Kontribusi tiap pilar dibatasi 1 (df_k/|C_k| <= 1) dan skala 1/K sehingga
    # menambah dokumen di SATU pilar tidak mengubah IDF pilar lain.
    cat_sizes: Counter = Counter(c["category"] for c in classes)
    cats_present = [c for c in PILLARS if cat_sizes.get(c, 0) > 0]
    extra_cats = sorted(set(cat_sizes) - set(PILLARS))
    all_cats = cats_present + extra_cats
    K = max(1, len(all_cats))
    cat_key_df: dict[str, Counter] = defaultdict(Counter)
    for c in classes:
        for key in c["feature_weights"]:
            cat_key_df[key][c["category"]] += 1
    idf_table: dict[str, float] = {}
    for key, per_cat in cat_key_df.items():
        strat_sum = sum(cnt / max(1, cat_sizes[cat]) for cat, cnt in per_cat.items())
        idf_table[key] = round(math.log(1.0 + K / (0.5 + strat_sum)), 4)

    # Centroid kategori numerik (top fitur tf-idf per pilar) untuk cosine.
    category_centroids: dict[str, dict[str, float]] = {}
    cat_feat_sum: dict[str, Counter] = defaultdict(Counter)
    for c in classes:
        for key, w in c["feature_weights"].items():
            cat_feat_sum[c["category"]][key] += w
    for cat, feats in cat_feat_sum.items():
        scored = sorted(
            ((w * idf_table.get(k, 1.0), k) for k, w in feats.items()
             if k.startswith("uni:") and re.search(r"[a-z]", k)),
            reverse=True)
        top = scored[:40]
        norm = math.sqrt(sum(s * s for s, _ in top)) or 1.0
        category_centroids[cat] = {k: round(s / norm * 10.0, 4) for s, k in top}

    # category_tokens (kompatibilitas + domain affinity).
    category_tokens = {
        cat: sorted({k[4:] for k in category_centroids.get(cat, {})})[:25]
        for cat in all_cats
    }
    for pillar, terms in CATEGORY_HINTS.items():
        category_tokens.setdefault(pillar, sorted(set(terms))[:25])

    model = {
        "version": 3,
        "threshold": 0.55,
        "multi_skill_threshold": 0.30,
        "null_anchor_score": 1.0,
        "softmax_temperature": 0.85,
        "avg_doc_len": round(avg_doc_len, 4),
        "known_vocab": sorted(known_vocab),
        "idf_table": idf_table,
        "category_tokens": category_tokens,
        "category_centroids": category_centroids,
        "classes": classes,
        "enable_multi_skill": True,
        "pillar_counts": {c: cat_sizes.get(c, 0) for c in PILLARS},
    }
    return model


# ---------------------------------------------------------------------------
# θ₀ ROC calibration — diukur dari mesin Rust AKTUAL (bukan replika Python).
# ---------------------------------------------------------------------------

def _self_match_scores_rust(brain, classes: list[dict]) -> list[float]:
    """Skor top-1 mesin Rust untuk probe name+description tiap kelas."""
    out = []
    for c in classes:
        probe = f"{c['name']} {c['description']}"
        r = brain.analyze_prompt(probe)
        out.append(float(r.get("top_score", 0.0)))
    return out


def _raw_bm25_top(brain, probe: str) -> float:
    """Skor BM25F mentah top-1 (tanpa gating Stage 0) via debug_score."""
    try:
        return float(brain.debug_score(probe))
    except Exception:
        r = brain.analyze_prompt(probe)
        return float(r.get("top_score", 0.0))


# Probe direktif realistis per pilar (gaya prompt pengguna nyata, bukan
# self-match name+description yang terlalu panjang). Dipakai mengkalibrasi θ₀
# agar prompt nyata yang sah lolos, sementara obrolan tidak.
CALIBRATION_POS_PROBES = [
    "Buatkan query SQL untuk dasbor KPI penjualan bulanan",
    "Render scene karakter 3D di Blender dengan pencahayaan sinematik",
    "Produksi episode siniar baru dan mastering loudness rekaman",
    "Desain infografis ringkasan laporan tahunan dengan tipografi rapi",
    "Hitung valuasi perusahaan dengan metode DCF dan WACC",
    "Tulis artikel blog SEO tentang keamanan siber untuk pemula",
    "Gabungkan tiga berkas PDF kontrak ini jadi satu dokumen",
    "Cari makalah arXiv terbaru dan buat tinjauan pustaka",
    "Buatkan Dockerfile dan pipeline CI/CD untuk aplikasi React ini",
    "Bersihkan data CSV ini jadi tabel pivot yang rapi",
    "Susun notula rapat ini jadi daftar tugas dan tenggat",
    "Buatkan presentasi PowerPoint untuk rapat direksi besok",
]


def calibrate_thresholds(model: dict, brain) -> dict:
    """θ₀ + threshold dari probe direktif realistis & probe conversational.

    Positif: CALIBRATION_POS_PROBES (gaya prompt nyata lintas 9 pilar) diukur
    dengan debug_score (raw BM25F+MNB, tanpa gating Stage 0).
    Negatif: kalimat obrolan murni pada skala yang sama.
    θ₀ = neg_bound + 0.35 * (pos_min - neg_bound), dibatasi agar seluruh probe
    positif lolos; threshold probabilitas diturunkan dari posisi θ₀.
    """
    classes = model.get("classes", [])
    if not classes:
        return model
    pos_scores = [_raw_bm25_top(brain, p) for p in CALIBRATION_POS_PROBES]
    pos_scores = [s for s in pos_scores if s > 0]
    neg_prompts = [
        "menurutmu mana yang lebih bagus?",
        "kita diskusi dulu saja, jangan langsung eksekusi",
        "apa bedanya pendekatan A dan B menurut pendapatmu?",
        "what do you think is better here?",
        "let's brainstorm about the options",
        "halo, apa kabar hari ini?",
        "aku cuma mau curhat soal pekerjaan",
        "kenapa ya hasilnya bisa seperti itu?",
        "menurutmu tren desain web tahun ini lagi condong ke arah mana ya?",
        "jelaskan pengertian inflasi dan kenapa harga barang bisa naik terus",
    ]
    neg_scores = [_raw_bm25_top(brain, p) for p in neg_prompts]
    if not pos_scores:
        return model
    pos_sorted = sorted(pos_scores)
    pos_q1 = pos_sorted[max(0, len(pos_sorted) // 4)]
    pos_min = pos_sorted[0]
    neg_mean = sum(neg_scores) / len(neg_scores) if neg_scores else 0.0
    neg_std = math.sqrt(sum((x - neg_mean) ** 2 for x in neg_scores) / len(neg_scores)) if neg_scores else 0.0
    neg_bound = max(neg_scores) + 0.25 * neg_std if neg_scores else 0.0
    gap = max(0.05, pos_min - neg_bound)
    theta0 = neg_bound + 0.35 * gap
    theta0 = min(theta0, pos_min * 0.95)  # jamin probe positif terlemah lolos
    model["null_anchor_score"] = round(max(0.01, theta0), 4)
    # Threshold probabilitas (untuk pelaporan keyakinan): diturunkan dari
    # posisi θ₀ pada softmax Top-5. Keputusan gate sendiri memakai skor mentah
    # >= θ₀ (scale-free), bukan probabilitas.
    tau = model.get("softmax_temperature", 0.85) or 0.85
    p_q1 = 1.0 / (1.0 + math.exp((theta0 - pos_q1) / tau) + 0.5)
    model["threshold"] = round(max(0.30, min(0.85, p_q1 * 0.9)), 4)
    model["multi_skill_threshold"] = round(model["threshold"] * 0.6, 4)
    # Suhu softmax adaptif terhadap skala skor aktual agar probabilitas
    # bermakna (bukan 0/1 biner): tau ~ 18% dari pos_q1.
    model["softmax_temperature"] = round(max(0.5, pos_q1 * 0.18), 4)
    model["calibration"] = {
        "pos_min": round(pos_min, 4), "pos_q1": round(pos_q1, 4),
        "neg_max": round(max(neg_scores), 4) if neg_scores else 0.0,
        "neg_bound": round(neg_bound, 4),
        "theta0": model["null_anchor_score"], "threshold": model["threshold"],
    }
    return model


# ---------------------------------------------------------------------------
# Category Gain Equalization (spec §3.3 mekanisme 2) + metrik parity.
# ---------------------------------------------------------------------------

def _class_self_score_rust(brain, cls: dict) -> float:
    """Gain kelas = skor BM25F mentah kelas INI terhadap probe name+description.

    Diukur dengan debug_topk (mode HYBRID seragam) dan diambil skor kelas yang
    bersangkutan — bukan top-1 global — agar parity mengukur kekuatan sinyal
    tiap kelas secara adil antar pilar.
    """
    probe = f"{cls['name']} {cls['description']}"
    try:
        for entry in brain.debug_topk(probe, 60, 2):
            if entry["name"] == cls["name"]:
                return float(entry["score"])
        return 0.0
    except Exception:
        r = brain.analyze_prompt(probe)
        return float(r.get("top_score", 0.0))


def measure_parity(model: dict, brain) -> dict:
    """domain_parity_score = 1 - CV antar-rata-rata gain pilar; category_cv."""
    classes = model.get("classes", [])
    cat_scores: dict[str, list[float]] = defaultdict(list)
    for c in classes:
        s = _class_self_score_rust(brain, c)
        if s > 0:
            cat_scores[c.get("category", "general")].append(s)
    cat_avgs = {k: sum(v) / len(v) for k, v in cat_scores.items() if v}
    vals = list(cat_avgs.values())
    if len(vals) < 2:
        return {"domain_parity_score": None, "category_cv": None, "category_means": cat_avgs}
    mu = sum(vals) / len(vals)
    sigma = math.sqrt(sum((x - mu) ** 2 for x in vals) / len(vals))
    cv = sigma / mu if mu > 0 else 0.0
    return {
        "domain_parity_score": round(max(0.0, 1.0 - cv), 4),
        "category_cv": round(cv, 4),
        "category_means": {k: round(v, 4) for k, v in cat_avgs.items()},
    }


def apply_category_gain_equalization(model: dict, brain, max_rounds: int = 8) -> dict:
    """Samakan gain antar pilar via gamma_k pada KONTRIBUSI IDF per kategori.

    L2 norm 100.0 per kelas membuat penskalaan feature_weights langsung
    batal (renormalisasi mengembalikan bentuk semula). Maka gain disetarakan
    lewat idf_table: fitur milik kelas kategori k dikalikan gamma_k. Untuk
    fitur bersama antar pilar, gamma dirata-rata sehingga efeknya netral pada
    fitur lintas-domain dan fokus pada fitur khas pilar. Pilar lemah
    dinaikkan, pilar dominan diturunkan; bobot kelas & L2=100 tidak berubah
    (gerbang 1 tetap terjaga). Parity diukur ulang dengan mesin Rust aktual.
    """
    classes = model.get("classes", [])
    if not classes:
        return model
    base_idf = dict(model.get("idf_table", {}))
    key_cats: dict[str, set] = defaultdict(set)
    for c in classes:
        for key in c["feature_weights"]:
            key_cats[key].add(c.get("category", "general"))
    cumulative: dict[str, float] = {c.get("category", "general"): 1.0 for c in classes}
    for _ in range(max_rounds):
        parity = measure_parity(model, brain)
        cv = parity.get("category_cv")
        if cv is not None and cv <= 0.06:
            break
        means = parity.get("category_means", {})
        if len(means) < 2:
            break
        m_global = sorted(means.values())[len(means) // 2]
        if m_global <= 0:
            break
        gamma = {cat: max(0.55, min(1.8, m_global / val)) for cat, val in means.items()}
        for cat, g in gamma.items():
            cumulative[cat] = max(0.30, min(3.0, cumulative.get(cat, 1.0) * g))
        # Terapkan HANYA pada fitur khas pilar (dimiliki <=2 kategori) agar
        # fitur bersama lintas-domain tidak ikut terdistorsi.
        new_idf = {}
        for key, val in base_idf.items():
            cats = key_cats.get(key, set())
            if cats and len(cats) <= 2:
                g = sum(cumulative.get(cat, 1.0) for cat in cats) / len(cats)
            else:
                g = 1.0
            new_idf[key] = round(val * g, 4)
        model["idf_table"] = new_idf
        model["category_gain_gamma"] = {k: round(v, 4) for k, v in cumulative.items()}
        brain.reload(json.dumps(model, ensure_ascii=False))
    return model


def rebuild_idf_and_centroids(model: dict) -> dict:
    """Hitung ulang IDF stratified + centroid untuk korpus yang diubah (uji stres).

    Memakai rumus & skala yang SAMA dengan build_model agar perbandingan
    parity adil; kontribusi per pilar tetap df_k/|C_k| (anti-skew).
    """
    classes = model.get("classes", [])
    cat_sizes: Counter = Counter(c["category"] for c in classes)
    cats_present = [c for c in PILLARS if cat_sizes.get(c, 0) > 0]
    extra_cats = sorted(set(cat_sizes) - set(PILLARS))
    all_cats = cats_present + extra_cats
    K = max(1, len(all_cats))
    cat_key_df: dict[str, Counter] = defaultdict(Counter)
    for c in classes:
        for key in c["feature_weights"]:
            cat_key_df[key][c["category"]] += 1
    idf_table: dict[str, float] = {}
    for key, per_cat in cat_key_df.items():
        strat_sum = sum(cnt / max(1, cat_sizes[cat]) for cat, cnt in per_cat.items())
        idf_table[key] = round(math.log(1.0 + K / (0.5 + strat_sum)), 4)
    model["idf_table"] = idf_table
    cat_feat_sum: dict[str, Counter] = defaultdict(Counter)
    for c in classes:
        for key, w in c["feature_weights"].items():
            cat_feat_sum[c["category"]][key] += w
    category_centroids: dict[str, dict[str, float]] = {}
    for cat, feats in cat_feat_sum.items():
        scored = sorted(
            ((w * idf_table.get(k, 1.0), k) for k, w in feats.items()
             if k.startswith("uni:") and re.search(r"[a-z]", k)),
            reverse=True)
        top = scored[:40]
        norm = math.sqrt(sum(s * s for s, _ in top)) or 1.0
        category_centroids[cat] = {k: round(s / norm * 10.0, 4) for s, k in top}
    model["category_centroids"] = category_centroids
    model["category_tokens"] = {
        cat: sorted({k[4:] for k in category_centroids.get(cat, {})})[:25]
        for cat in all_cats
    }
    model["pillar_counts"] = {c: cat_sizes.get(c, 0) for c in PILLARS}
    return model


def _save_model(model: dict) -> None:
    get_model_path().write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")


def _import_brain():
    try:
        import hermes_skill_brain  # type: ignore
        return hermes_skill_brain
    except ImportError:
        pass
    import importlib.util
    import glob
    for so in glob.glob(str(Path(__file__).parent / "*.so")) + glob.glob(str(Path(__file__).parent / "*.pyd")):
        spec = importlib.util.spec_from_file_location("hermes_skill_brain", so)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise ImportError("hermes_skill_brain not built. Run: maturin build --release")


def train_and_save(skills_root: Path | None = None, calibrate: bool = True) -> dict:
    root = skills_root or get_skills_root()
    records = scan_skills(root)
    lexicon = _load_lexicon()
    model = build_model(records, lexicon)
    brain_mod = _import_brain()
    brain = brain_mod.SkillBrain()
    brain.reload(json.dumps(model, ensure_ascii=False))
    if calibrate and model["classes"]:
        model = apply_category_gain_equalization(model, brain)
        model = calibrate_thresholds(model, brain)
        brain.reload(json.dumps(model, ensure_ascii=False))
    _save_model(model)
    return model


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if "--benchmark" in argv or "--self-test" in argv:
        import benchmark_runner
        return benchmark_runner.run(verbose=True)
    model = train_and_save()
    counts = model.get("pillar_counts", {})
    print(f"Trained {len(model['classes'])} skills -> {get_model_path()}")
    print("Pilar:", {k: v for k, v in counts.items()})
    if "calibration" in model:
        print("Kalibrasi:", model["calibration"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))