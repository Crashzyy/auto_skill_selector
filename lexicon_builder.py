"""auto_skill_selector — lexicon_builder.py (Fase 2, Bagian 2).

Membangun `lexicon_id_en.json`: kamus dwibahasa 4 lapisan yang di-embed ke
binary Rust (include_str!) saat kompilasi agar latensi routing tetap <500 µs:

  Lapis 1  KBBI baku + glosarium resmi Kemdikbud (kata kerja aksi, nomina
           deliverable, istilah domain lintas 9 pilar). known_vocab diisi
           wordlist KBBI terbuka (cache) + seluruh basis glosarium.
  Lapis 2  Kamus konsep inti EN<->ID terkurasi lintas 9 pilar (>=250 pasangan).
  Lapis 3  Bahasa gaul / singkatan chat WA-Telegram-Jaksel (>=150 entri
           terverifikasi: kurasi manual + kamus-alay komunitas).
  Lapis 4  Aturan transliterasi sufiks serapan (Zero-RAM; aturan hidup di Rust,
           JSON hanya mendeklarasikan aturannya untuk audit).

Output ditulis ke repo (`lexicon_id_en.json`, sumber embed) dan ke plugin-data
(runtime). Semua unduhan via raw.githubusercontent / codeload tarball — bebas
kuota 60 req/jam GitHub REST API; gagal jaringan = fallback kurasi offline.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import tarfile
import urllib.request
from pathlib import Path

UA = "auto_skill_selector-lexicon/2.0"
_REPO_DIR = Path(__file__).resolve().parent
LEXICON_REPO_PATH = _REPO_DIR / "lexicon_id_en.json"

# ---------------------------------------------------------------------------
# Sumber terbuka (raw / tarball — bebas rate-limit REST API)
# ---------------------------------------------------------------------------
_SOURCES = {
    "kbbi_wordlist": (
        "https://codeload.github.com/aryakdaniswara/kbbi-v6-wordlist/tar.gz/refs/heads/main",
        "tarball",
        "kbbi-v6-wordlist-main/all_entries_v6.1.0.txt",
    ),
    "slang": (
        "https://raw.githubusercontent.com/nasalsabila/kamus-alay/master/colloquial-indonesian-lexicon.csv",
        "raw",
        None,
    ),
}

# ---------------------------------------------------------------------------
# Lapis 1 — KBBI baku & glosarium resmi (Kemdikbud/Pusat Bahasa).
# id_term -> padanan Inggris (multi-padanan diizinkan). Frasa multi-kata
# dicocokkan sebagai bigram/frasa oleh mesin.
# ---------------------------------------------------------------------------
KBBI_GLOSSARY: dict[str, list[str]] = {
    # --- istilah umum resmi ---
    "pranala": ["link", "hyperlink"], "antarmuka": ["interface", "ui"],
    "purwarupa": ["prototype", "mockup"], "purwarupa": ["prototype"],
    "pratinjau": ["preview"], "templat": ["template"], "berkas": ["file"],
    "peladen": ["server"], "peramban": ["browser"], "surel": ["email"],
    "salindia": ["slide", "slides", "presentation"], "lembar sebar": ["spreadsheet"],
    "infografik": ["infographic"], "infografis": ["infographic"],
    "siniar": ["podcast"], "penyuntingan": ["editing"], "sunting": ["edit"],
    "pindai": ["scan"], "pemindaian": ["scanning"], "transkripsi": ["transcription"],
    "rekonsiliasi": ["reconciliation"], "neraca lajur": ["worksheet", "trial balance"],
    "neraca": ["balance sheet"], "anuitas": ["annuity"], "audit": ["audit"],
    "katalog": ["catalog"], "tinjauan pustaka": ["literature review"],
    "daftar pustaka": ["bibliography", "references"], "sitasi": ["citation"],
    "notula": ["minutes", "meeting notes"], "risalah": ["minutes"],
    "tenggat": ["deadline"], "nawala": ["newsletter"], "laporan": ["report"],
    "labah rugi": ["profit and loss"], "laba rugi": ["profit and loss"],
    "arus kas": ["cash flow"], "penyusutan": ["depreciation"],
    "likuiditas": ["liquidity"], "solvabilitas": ["solvency"],
    "amortisasi": ["amortization"], "valuasi": ["valuation"],
    "saham": ["stock", "share"], "obligasi": ["bond"], "dividen": ["dividend"],
    "ekuitas": ["equity"], "utang": ["debt"], "piutang": ["receivable"],
    "kewajiban": ["liability", "obligation"], "pendapatan": ["revenue"],
    "beban": ["expense"], "modal": ["capital"], "anggaran": ["budget"],
    "faktur": ["invoice"], "tagihan": ["bill", "invoice"], "pajak": ["tax"],
    "gaji": ["salary", "payroll"], "neraca pembayaran": ["balance of payments"],
    "hipotesis": ["hypothesis"], "metodologi": ["methodology"],
    "abstrak": ["abstract"], "pustaka": ["reference", "library"],
    "variabel": ["variable"], "sampel": ["sample"], "populasi": ["population"],
    "korelasi": ["correlation"], "regresi": ["regression"],
    "peramalan": ["forecasting", "forecast"], "pencilan": ["outlier"],
    "kohort": ["cohort"], "retensi": ["retention"], "corong": ["funnel"],
    "dasbor": ["dashboard"], "kueri": ["query"], "tabel pivot": ["pivot table"],
    "pangkalan data": ["database"], "peranti lunak": ["software"],
    "peranti keras": ["hardware"], "luring": ["offline"], "daring": ["online"],
    "jaringan": ["network"], "sandi": ["cipher", "password"],
    "algoritma": ["algorithm"], "komputasi": ["computing"],
    "kontainer": ["container"], "penerapan": ["deployment"],
    "orkestrasi": ["orchestration"], "pengujian": ["testing"],
    "awakutu": ["debug", "debugging"], "galat": ["error"],
    "repositori": ["repository"], "cabang": ["branch"], "gabungan": ["merge"],
    "kerangka kerja": ["framework"], "pustaka kode": ["library"],
    "tipografi": ["typography"], "palet": ["palette"], "kisi": ["grid"],
    "tata letak": ["layout"], "aksesibilitas": ["accessibility"],
    "bagan": ["chart", "diagram"], "diagram alur": ["flowchart", "flow diagram"],
    "papan cerita": ["storyboard"], "bingkai kunci": ["keyframe"],
    "penggambaran": ["rendering"], "olah audio": ["audio processing"],
    "rekaman": ["recording"], "sulih suara": ["voiceover", "dubbing"],
    "takarir": ["subtitle", "caption"], "teks terjemahan": ["subtitle"],
    "komposisi": ["composition"], "aransemen": ["arrangement"],
    "penguasaan audio": ["mastering"], "pengurangan derau": ["noise reduction"],
    "pemisahan stem": ["stem separation"], "lirik": ["lyrics"],
    "penelitian": ["research"], "makalah": ["paper"], "jurnal": ["journal"],
    "paten": ["patent"], "kebijakan": ["policy"], "survei": ["survey"],
    "kuesioner": ["questionnaire"], "bioinformatika": ["bioinformatics"],
    "penyelidikan sumber terbuka": ["osint"], "jejak digital": ["digital footprint"],
    "uji tuntas": ["due diligence"], "lokalisasi": ["localization"],
    "penerjemahan": ["translation"], "penulisan teknis": ["technical writing"],
    "siaran pers": ["press release"], "kampanye": ["campaign"],
    "optimasi mesin pencari": ["seo"], "naskah iklan": ["copywriting"],
    "ringkasan eksekutif": ["executive brief"], "unit ekonomi": ["unit economics"],
    "ukuran pasar": ["market sizing"], "penetapan harga": ["pricing"],
    "arus kas terdiskonto": ["discounted cash flow", "dcf"],
    "PRESENTASI": ["presentation"], "presentasi": ["presentation", "pitch"],
    "wawancara": ["interview"], "rapat": ["meeting"], "jadwal": ["schedule"],
    "daftar periksa": ["checklist"], "prosedur tetap": ["sop"],
    "alur kerja": ["workflow"], "otomasi": ["automation"],
    "pemantauan": ["monitoring"], "pencadangan": ["backup"],
    "pemulihan": ["recovery"], "enkripsi": ["encryption"],
    "otentikasi": ["authentication"], "otorisasi": ["authorization"],
    "kerentanan": ["vulnerability"], "uji penetrasi": ["pentest"],
    "integrasi berkelanjutan": ["continuous integration", "ci"],
    "pengiriman berkelanjutan": ["continuous delivery", "cd"],
    "antarmuka pemrograman": ["api"], "layanan web": ["web service"],
    "halaman arahan": ["landing page"], "sistem desain": ["design system"],
    "identitas merek": ["brand identity"], "pemandu gaya": ["style guide"],
    "peta situs": ["sitemap"], "kerangka kawat": ["wireframe"],
    "pengalaman pengguna": ["user experience", "ux"],
    "antarmuka pengguna": ["user interface", "ui"],
    "kecerdasan bisnis": ["business intelligence", "bi"],
    "pembersihan data": ["data cleaning"], "pemodelan data": ["data modeling"],
    "gudang data": ["data warehouse"], "pipa data": ["data pipeline"],
    "ekstraksi transformasi pemuatan": ["etl"], "deret waktu": ["time series"],
    "pembelajaran mesin": ["machine learning"], "jaringan saraf": ["neural network"],
    "pengolahan bahasa alami": ["nlp"], "visi komputer": ["computer vision"],
}

# ---------------------------------------------------------------------------
# Lapis 2 — kamus konsep inti EN->ID terkurasi lintas 9 pilar (>=250 pasangan).
# ---------------------------------------------------------------------------
CORE_EN_ID: dict[str, str] = {
    # --- Pilar 1: Data Analytics & BI ---
    "spreadsheet": "lembar sebar", "workbook": "buku kerja", "ledger": "buku besar",
    "pivot table": "tabel pivot", "dashboard": "dasbor", "query": "kueri",
    "dataset": "dataset", "data cleaning": "pembersihan data", "etl": "etl",
    "data pipeline": "pipa data", "forecasting": "peramalan", "forecast": "peramalan",
    "time series": "deret waktu", "regression": "regresi", "correlation": "korelasi",
    "cohort": "kohort", "funnel": "corong", "retention": "retensi", "churn": "churn",
    "kpi": "kpi", "metric": "metrik", "outlier": "pencilan", "anomaly": "anomali",
    "statistics": "statistik", "visualization": "visualisasi", "chart": "grafik",
    "bar chart": "diagram batang", "line chart": "grafik garis", "heatmap": "peta panas",
    "business intelligence": "kecerdasan bisnis", "sql": "sql", "olap": "olap",
    "data warehouse": "gudang data", "aggregation": "agregasi", "join": "gabungan tabel",
    "trend": "tren", "distribution": "distribusi", "variance": "varians",
    "hypothesis testing": "uji hipotesis", "ab testing": "uji ab", "sampling": "pengambilan sampel",
    # --- Pilar 2: 3D, Video & Animation ---
    "3d modeling": "pemodelan 3d", "blender": "blender", "mesh": "mesh",
    "rigging": "rigging", "keyframe": "bingkai kunci", "rendering": "render",
    "shader": "shader", "texture": "tekstur", "sculpting": "sculpting",
    "compositing": "kompositing", "motion graphics": "grafis gerak",
    "video editing": "penyuntingan video", "ffmpeg": "ffmpeg", "color grading": "gradasi warna",
    "subtitle": "takarir", "captioning": "takarir", "storyboard": "papan cerita",
    "animatic": "animatik", "frame rate": "laju bingkai", "timeline": "linimasa",
    "stop motion": "stop motion", "claymation": "claymation", "vfx": "efek visual",
    "particle system": "sistem partikel", "camera": "kamera", "lighting": "pencahayaan",
    "unreal engine": "unreal", "houdini": "houdini", "cinema4d": "cinema4d",
    "uv mapping": "pemetaan uv", "topology": "topologi", "viewport": "viewport",
    # --- Pilar 3: Audio, Music & Podcast ---
    "podcast": "siniar", "podcast production": "produksi siniar",
    "audio transcription": "transkripsi audio", "whisper": "whisper",
    "noise reduction": "pengurangan derau", "mastering": "mastering",
    "mixing": "mixing", "stem separation": "pemisahan stem", "foh": "foh",
    "music composition": "komposisi musik", "midi": "midi", "voiceover": "sulih suara",
    "tts": "tts", "text to speech": "teks ke suara", "audio editing": "penyuntingan audio",
    "spectrogram": "spektrogram", "waveform": "bentuk gelombang", "daw": "daw",
    "synthesizer": "synthesizer", "lyrics": "lirik", "songwriting": "penulisan lagu",
    "jingle": "jingle", "sound design": "desain suara", "equalizer": "ekualiser",
    "compression": "kompresi audio", "reverb": "reverb", "sample rate": "laju sampel",
    "microphone": "mikrofon", "recording": "rekaman", "audiobook": "buku audio",
    # --- Pilar 4: Design, UI/UX & Diagrams ---
    "infographic": "infografis", "infographics": "infografis",
    "mermaid": "mermaid", "architecture diagram": "diagram arsitektur",
    "flowchart": "diagram alur", "wireframe": "kerangka kawat", "mockup": "purwarupa",
    "prototype": "purwarupa", "design system": "sistem desain",
    "brand identity": "identitas merek", "typography": "tipografi",
    "landing page": "halaman arahan", "web design": "desain web",
    "accessibility audit": "audit aksesibilitas", "accessibility": "aksesibilitas",
    "ui": "antarmuka", "ux": "pengalaman pengguna", "user research": "riset pengguna",
    "persona": "persona", "usability": "kebergunaan", "palette": "palet warna",
    "layout": "tata letak", "grid": "kisi", "icon": "ikon", "logo": "logo",
    "poster": "poster", "banner": "spanduk", "figma": "figma", "excalidraw": "excalidraw",
    "svg": "svg", "illustration": "ilustrasi", "comic": "komik",
    # --- Pilar 5: Finance, Business & Consulting ---
    "financial modeling": "pemodelan keuangan", "dcf": "dcf",
    "discounted cash flow": "arus kas terdiskonto", "mece": "mece",
    "issue tree": "pohon masalah", "strategy memo": "memo strategi",
    "pitch deck": "dek pitch", "investor narrative": "narasi investor",
    "invoice": "faktur", "reconciliation": "rekonsiliasi",
    "pricing": "penetapan harga", "unit economics": "unit ekonomi",
    "market sizing": "ukuran pasar", "tam": "tam", "sam": "sam", "som": "som",
    "valuation": "valuasi", "wacc": "wacc", "irr": "irr", "npv": "npv",
    "lbo": "lbo", "merger": "merger", "acquisition": "akuisisi",
    "balance sheet": "neraca", "income statement": "laporan laba rugi",
    "cash flow": "arus kas", "annuity": "anuitas", "depreciation": "penyusutan",
    "amortization": "amortisasi", "budget": "anggaran", "payroll": "penggajian",
    "tax": "pajak", "equity": "ekuitas", "dividend": "dividen", "bond": "obligasi",
    "stock": "saham", "burn rate": "laju bakar", "runway": "runway",
    "due diligence": "uji tuntas", "swot": "swot", "okr": "okr",
    "consulting": "konsultansi", "mckinsey": "mckinsey", "6-pager": "6-pager",
    # --- Pilar 6: Writing, Editorial & Marketing ---
    "seo copywriting": "penulisan seo", "copywriting": "penulisan naskah",
    "technical documentation": "dokumentasi teknis", "executive brief": "ringkasan eksekutif",
    "social media campaign": "kampanye media sosial", "press release": "siaran pers",
    "translation": "penerjemahan", "localization": "lokalisasi",
    "bilingual": "dwibahasa", "editing": "penyuntingan", "proofreading": "koreksi baca",
    "blog post": "artikel blog", "article": "artikel", "newsletter": "nawala",
    "content calendar": "kalender konten", "hook": "hook", "headline": "judul utama",
    "ghostwriting": "ghostwriting", "rewrite": "tulis ulang", "paraphrase": "parafrase",
    "summarization": "peringkasan", "tone": "nada tulisan", "style guide": "pemandu gaya",
    "humanize": "memanusiakan tulisan", "thread": "utas", "caption": "takarir",
    "scriptwriting": "penulisan naskah", "speech": "pidato", "resume": "resume",
    # --- Pilar 7: Productivity, Office & Operations ---
    "pdf extraction": "ekstraksi pdf", "pdf": "pdf", "ocr": "ocr",
    "word document": "dokumen word", "docx": "docx", "report generation": "pembuatan laporan",
    "powerpoint": "powerpoint", "pptx": "pptx", "slide deck": "dek salindia",
    "slides": "salindia", "presentation": "presentasi", "excel": "excel",
    "xlsx": "xlsx", "excel automation": "otomasi excel", "sop": "sop",
    "checklist": "daftar periksa", "meeting notes": "notula rapat",
    "action items": "daftar tugas", "minutes": "risalah", "deadline": "tenggat",
    "calendar": "kalender", "email triage": "pemilahan surel", "inbox": "kotak masuk",
    "template": "templat", "form": "formulir", "signature": "tanda tangan",
    "merge documents": "gabung dokumen", "split pdf": "pisah pdf",
    "file conversion": "konversi berkas", "batch rename": "ganti nama massal",
    "weekly review": "tinjauan mingguan", "planning": "perencanaan",
    "task management": "manajemen tugas", "reminder": "pengingat",
    # --- Pilar 8: Research, Science & OSINT ---
    "literature review": "tinjauan pustaka", "citation": "sitasi",
    "bibliometric": "bibliometrik", "meta-analysis": "meta analisis",
    "systematic review": "tinjauan sistematis", "latex": "latex",
    "academic paper": "makalah akademik", "arxiv": "arxiv", "journal": "jurnal",
    "peer review": "telaah sejawat", "osint": "osint", "fact-checking": "cek fakta",
    "whois": "whois", "bioinformatics": "bioinformatika", "genomics": "genomik",
    "patent analysis": "analisis paten", "policy analysis": "analisis kebijakan",
    "survey design": "desain survei", "questionnaire": "kuesioner",
    "experiment": "eksperimen", "dataset analysis": "analisis dataset",
    "scientific computing": "komputasi ilmiah", "simulation": "simulasi",
    "molecular": "molekuler", "protein": "protein", "clinical": "klinis",
    "statistics review": "tinjauan statistik", "grant": "hibah",
    "research proposal": "proposal penelitian", "flashcards": "kartu belajar",
    # --- Pilar 9: Software, Systems & DevOps ---
    "backend api": "api backend", "code review": "tinjauan kode",
    "frontend": "frontend", "react": "react", "html": "html", "web app": "aplikasi web",
    "ci/cd": "ci cd", "docker": "docker", "kubernetes": "kubernetes",
    "database schema": "skema basis data", "schema optimization": "optimasi skema",
    "security audit": "audit keamanan", "pentest": "uji penetrasi",
    "automated testing": "pengujian otomatis", "debugging": "awakutu",
    "unit test": "uji unit", "integration test": "uji integrasi", "tdd": "tdd",
    "refactoring": "refaktorisasi", "deployment": "penerapan", "monitoring": "pemantauan",
    "logging": "pencatatan log", "microservices": "microservices",
    "rest api": "api rest", "graphql": "graphql", "git": "git",
    "pull request": "pull request", "repository": "repositori",
    "container": "kontainer", "serverless": "serverless", "cloudflare": "cloudflare",
    "nginx": "nginx", "linux": "linux", "shell script": "skrip shell",
    "rust": "rust", "python": "python", "typescript": "typescript",
    "performance profiling": "profil kinerja", "load testing": "uji beban",
    "vulnerability": "kerentanan", "authentication": "otentikasi",
}

# ---------------------------------------------------------------------------
# Lapis 3 — gaul / singkatan chat / campur kode (kurasi terverifikasi >=150).
# Nilai = bentuk baku; frasa diperlakukan sebagai pemetaan token tunggal.
# ---------------------------------------------------------------------------
SLANG_CORE: dict[str, str] = {
    # kata kerja gaul
    "bikinin": "buatkan", "bikin": "buat", "buatin": "buatkan", "bikinan": "buatan",
    "rapihin": "rapikan", "beresin": "bereskan", "benerin": "perbaiki",
    "cekin": "periksa", "ngecek": "cek", "cek": "periksa",
    "rangkumin": "ringkas", "terjemahin": "terjemah", "editin": "sunting",
    "visualin": "visualisasi", "pdfin": "pdf", "excelin": "excel",
    "rekapan": "rekap", "ngerekap": "rekap", "garap": "kerjakan",
    "nggarap": "kerjakan", "oprek": "modifikasi", "ngoprek": "modifikasi",
    "kulik": "teliti", "bedah": "analisis", "peres": "ringkas",
    "ngoding": "menulis kode", "nyekrip": "menulis kode", "ngerender": "render",
    "ngedit": "sunting", "ngeprint": "cetak", "ngescan": "pindai",
    "upload": "unggah", "download": "unduh", "nyari": "cari", "cariin": "carikan",
    "kirimin": "kirimkan", "ambilin": "ambilkan", "susunin": "susunkan",
    "gambarin": "gambarkan", "desainin": "desainkan", "hitungin": "hitungkan",
    "analisiin": "analisis", "auditin": "audit", "testin": "uji",
    "deployin": "deploy", "setupin": "setup", "konversiin": "konversi",
    "gabungin": "gabungkan", "pisahin": "pisahkan", "kompresin": "kompres",
    "ubahin": "ubah", "tulisinn": "tuliskan", "bacain": "bacakan",
    "jelasin": "jelaskan", "kasih": "beri", "munculin": "munculkan",
    "ilangin": "hilangkan", "tambahin": "tambahkan", "kurangin": "kurangi",
    "bagusin": "baguskan", "jelekin": "jelekkan", "cepatin": "cepatkan",
    "lambatin": "lambatkan", "gedein": "besarkan", "kecilin": "kecilkan",
    "warnain": "warnai", "rapiin": "rapikan", "bersihin": "bersihkan",
    "berantakin": "berantakkan", "acak": "acak", "nyusun": "susun",
    "nyiapin": "siapkan", "siapin": "siapkan", "bantuin": "bantu",
    "kerjain": "kerjakan", "selesaiin": "selesaikan", "beres": "selesai",
    "nggak": "tidak", "ngga": "tidak", "gak": "tidak", "ga": "tidak",
    "gk": "tidak", "kagak": "tidak", "engga": "tidak", "enggak": "tidak",
    "jgn": "jangan", "jangan": "jangan", "gausah": "tidak usah",
    "gaperlu": "tidak perlu", "gapake": "tidak pakai", "gaboleh": "tidak boleh",
    # singkatan chat
    "yg": "yang", "dr": "dari", "dgn": "dengan", "dg": "dengan",
    "utk": "untuk", "unt": "untuk", "krn": "karena", "karna": "karena",
    "soalnya": "karena", "tp": "tetapi", "tapi": "tetapi", "tpi": "tetapi",
    "jd": "jadi", "jdi": "jadi", "sdh": "sudah", "udah": "sudah",
    "udh": "sudah", "blm": "belum", "belom": "belum", "bs": "bisa",
    "bisa": "bisa", "bsa": "bisa", "aja": "saja", "aj": "saja",
    "sm": "sama", "sma": "sama", "pd": "pada", "dsb": "dan sebagainya",
    "dll": "dan lain lain", "dsbnya": "dan sebagainya", "sy": "saya",
    "gue": "saya", "gw": "saya", "gua": "saya", "aku": "saya",
    "km": "kamu", "kmu": "kamu", "elo": "kamu", "lo": "kamu",
    "lu": "kamu", "dia": "dia", "mereka": "mereka", "bgt": "banget",
    "banget": "sangat", "bngt": "banget", "bener": "benar", "bner": "benar",
    "gmn": "bagaimana", "gimana": "bagaimana", "gmna": "bagaimana",
    "knp": "kenapa", "knapa": "kenapa", "dimana": "di mana", "dmn": "di mana",
    "kapan": "kapan", "kpn": "kapan", "berapa": "berapa", "brp": "berapa",
    "brapa": "berapa", "siapa": "siapa", "sap": "siapa", "apa": "apa",
    "ap": "apa", "mending": "lebih baik", "mendingan": "lebih baik",
    "bagusan": "lebih bagus", "kece": "bagus", "keren": "bagus",
    "cuan": "laba", "boncos": "rugi", "duit": "uang", "fulus": "uang",
    "lemot": "lambat", "lelet": "lambat", "ngelag": "terhenti",
    "burik": "buram", "njelimet": "rumit", "ribet": "rumit",
    "gampang": "mudah", "gmpng": "mudah", "susah": "sulit",
    "pake": "pakai", "pakek": "pakai", "make": "pakai", "nggakusah": "tidak usah",
    "gausah": "tidak usah", "pakenya": "pakainya", "doang": "saja",
    "dong": "", "deh": "", "nih": "", "sih": "", "ya": "", "yak": "",
    "yuk": "", "yu": "", "kuy": "", "pls": "tolong", "plis": "tolong",
    "tolongg": "tolong", "minta": "minta", "mintain": "minta",
    "pengen": "ingin", "pingin": "ingin", "mau": "mau", "mo": "mau",
    "mao": "mau", "bakal": "akan", "bakalan": "akan", "ntar": "nanti",
    "nanti": "nanti", "tar": "nanti", "skrg": "sekarang", "skg": "sekarang",
    "sbntr": "sebentar", "bentar": "sebentar", "lgsg": "langsung",
    "lgsung": "langsung", "langsng": "langsung", "bareng": "bersamaan",
    "sekalian": "sekaligus", "sambil": "sambil", "terus": "lalu",
    "abis": "setelah", "habis": "setelah", "abisitu": "setelah itu",
    "abis itu": "setelah itu", "habisitu": "setelah itu",
    # campur kode & istilah kerja Jaksel/WA
    "dek": "pitch deck", "ppt": "presentasi", "slide": "salindia",
    "meeting": "rapat", "miting": "rapat", "call": "panggilan",
    "report": "laporan", "repor": "laporan", "file": "berkas",
    "folder": "map", "attach": "lampiran", "attachment": "lampiran",
    "revisi": "revisi", "approve": "setujui", "acc": "setujui",
    "followup": "tindak lanjut", "follow up": "tindak lanjut",
    "urgent": "mendesak", "asap": "secepatnya", "eta": "estimasi",
    "deadline": "tenggat", "dedlen": "tenggat", "brief": "brief",
    "brainstorm": "diskusi", "brainstorming": "diskusi",
    "brainstor": "diskusi", "draft": "draf", "draf": "draf",
    "final": "final", "fix": "perbaiki", "error": "galat",
    "bug": "bug", "typo": "salah ketik", "format": "format",
    "layout": "tata letak", "font": "fonta", "warna": "warna",
    "gambar": "gambar", "foto": "foto", "vidio": "video",
    "vid": "video", "audio": "audio", "musik": "musik",
    "lagu": "lagu", "suara": "suara", "rekaman": "rekaman",
    "sosmed": "media sosial", "ig": "instagram", "fb": "facebook",
    "wa": "whatsapp", "tele": "telegram", "yt": "youtube",
    "linkedin": "linkedin", "twt": "twitter", "x": "twitter",
    "gpp": "tidak apa apa", "otw": "sedang menuju", "cmiiw": "koreksi jika salah",
    "fyi": "sekadar info", "imo": "menurut saya", "imho": "menurut saya",
    "tbh": "sejujurnya", "btw": "ngomong ngomong", "afaik": "setahu saya",
    "wkwk": "", "wkwkwk": "", "hehe": "", "haha": "", "xixi": "",
    "anjir": "", "anjay": "", "gokil": "luar biasa", "mantul": "mantap",
    "mantap": "bagus", "sip": "baik", "sippp": "baik", "oke": "baik",
    "ok": "baik", "okee": "baik", "yoi": "ya", "yups": "ya",
    "noted": "dicatat", "copy": "dimengerti", "roger": "dimengerti",
    "gas": "kerjakan", "gaskeun": "kerjakan", "sikat": "kerjakan",
    "hajar": "kerjakan", "lanjut": "lanjutkan", "skip": "lewati",
    "batal": "batalkan", "cancel": "batalkan", "rekap": "rekap",
    "notulen": "notula", "notulensi": "notula", "mom": "notula",
    "agenda": "agenda", "undangan": "undangan", "invite": "undangan",
    "jadwalin": "jadwalkan", "reschedule": "jadwal ulang",
    "invoice": "faktur", "kuitansi": "kuitansi", "bon": "bon",
    "struk": "struk", "budget": "anggaran", "cost": "biaya",
    "price": "harga", "harga": "harga", "diskon": "diskon",
    "promo": "promosi", "iklan": "iklan", "ads": "iklan",
    "campaign": "kampanye", "konten": "konten", "content": "konten",
    "caption": "takarir", "hashtag": "tagar", "mention": "sebutan",
    "engagement": "keterlibatan", "reach": "jangkauan", "impression": "tayangan",
    "konversi": "konversi", "leads": "prospek", "prospek": "prospek",
    "klien": "klien", "customer": "pelanggan", "user": "pengguna",
    "pengguna": "pengguna", "admin": "admin", "tim": "tim",
    "boss": "atasan", "bos": "atasan", "karyawan": "karyawan",
    "hrd": "hrd", "finance": "keuangan", "keuangan": "keuangan",
    "accounting": "akuntansi", "akunting": "akuntansi", "pajak": "pajak",
    "audit": "audit", "opname": "opname", "stock": "stok",
    "gudang": "gudang", "inventory": "inventaris", "asset": "aset",
    "aset": "aset", "profit": "laba", "loss": "rugi",
    "omzet": "omzet", "omset": "omzet", "revenue": "pendapatan",
    "margin": "margin", "modal": "modal", "investor": "investor",
    "pitch": "pitch", "pitching": "pitch", "valuasi": "valuasi",
    "saham": "saham", "dividen": "dividen", "portofolio": "portofolio",
    "dataset": "dataset", "data": "data", "database": "basis data",
    "db": "basis data", "server": "peladen", "hosting": "hosting",
    "domain": "domain", "website": "situs web", "web": "web",
    "landing": "halaman arahan", "homepage": "beranda", "app": "aplikasi",
    "aplikasi": "aplikasi", "apk": "aplikasi", "software": "peranti lunak",
    "hardware": "peranti keras", "laptop": "laptop", "komputer": "komputer",
    "hp": "ponsel", "handphone": "ponsel", "gadget": "gawai",
    "jaringan": "jaringan", "wifi": "wifi", "internet": "internet",
    "online": "daring", "offline": "luring", "cloud": "awan",
    "backup": "cadangan", "restore": "pulihkan", "sync": "sinkronisasi",
    "sinkron": "sinkronisasi", "export": "ekspor", "import": "impor",
    "convert": "konversi", "konvert": "konversi", "compress": "kompres",
    "extract": "ekstrak", "ekstrak": "ekstrak", "merge": "gabung",
    "split": "pisah", "crop": "potong", "resize": "ubah ukuran",
    "scan": "pindai", "scanner": "pemindai", "print": "cetak",
    "printer": "pencetak", "kertas": "kertas", "dokumen": "dokumen",
    "dok": "dokumen", "doc": "dokumen", "sheet": "lembar",
    "tabel": "tabel", "table": "tabel", "kolom": "kolom",
    "baris": "baris", "sel": "sel", "rumus": "rumus",
    "formula": "rumus", "fungsi": "fungsi", "grafik": "grafik",
    "chart": "grafik", "diagram": "diagram", "bagan": "bagan",
    "peta": "peta", "map": "peta", "lokasi": "lokasi",
    "alamat": "alamat", "kontak": "kontak", "nomor": "nomor",
    "no": "nomor", "telp": "telepon", "email": "surel",
    "surat": "surat", "suratmenyurat": "korespondensi", "memo": "memo",
    "pengumuman": "pengumuman", "edaran": "edaran", "kebijakan": "kebijakan",
    "aturan": "aturan", "sop": "sop", "prosedur": "prosedur",
    "checklist": "daftar periksa", "ceklis": "daftar periksa",
    "tugas": "tugas", "task": "tugas", "todo": "daftar tugas",
    "to-do": "daftar tugas", "target": "target", "goal": "tujuan",
    "kpi": "kpi", "okr": "okr", "milestone": "tonggak",
    "progress": "kemajuan", "status": "status", "update": "pembaruan",
    "lapor": "lapor", "laporan": "laporan", "evaluasi": "evaluasi",
    "review": "tinjauan", "tinjauan": "tinjauan", "revisian": "revisi",
    "feedback": "umpan balik", "masukan": "masukan", "saran": "saran",
    "kritik": "kritik", "pujian": "pujian", "komplain": "keluhan",
    "keluhan": "keluhan", "solusi": "solusi", "masalah": "masalah",
    "problem": "masalah", "issue": "masalah", "kendala": "kendala",
    "hambatan": "hambatan", "risiko": "risiko", "risk": "risiko",
    "mitigasi": "mitigasi", "rencana": "rencana", "plan": "rencana",
    "strategi": "strategi", "taktik": "taktik", "eksekusi": "eksekusi",
    "implementasi": "implementasi", "penerapan": "penerapan",
    "pengembangan": "pengembangan", "riset": "riset", "research": "riset",
    "penelitian": "penelitian", "studi": "studi", "analisis": "analisis",
    "analisa": "analisis", "analitik": "analitik", "insight": "wawasan",
    "wawasan": "wawasan", "kesimpulan": "kesimpulan", "rekomendasi": "rekomendasi",
    "saranin": "sarankan", "usul": "usul", "usulan": "usulan",
    "ide": "ide", "gagasan": "gagasan", "konsep": "konsep",
    "drafting": "penyusunan draf", "nyusun": "susun", "susun": "susun",
    "rapi": "rapi", "rapih": "rapi", "bersih": "bersih",
    "jelas": "jelas", "detail": "detail", "detil": "detail",
    "lengkap": "lengkap", "komplit": "lengkap", "singkat": "singkat",
    "padat": "padat", "ringkas": "ringkas", "panjang": "panjang",
    "pendek": "pendek", "cepat": "cepat", "cepet": "cepat",
    "slow": "lambat", "pelan": "pelan", "hati2": "hati hati",
    "urgentt": "mendesak", "penting": "penting", "prioritas": "prioritas",
    "prioritasin": "prioritaskan", "fokus": "fokus", "focus": "fokus",
}

# Lapis 4 — deklarasi aturan transliterasi (implementasi aturan ada di Rust,
# Zero-RAM: tidak menambah entri kamus per kata).
TRANSLIT_RULES = [
    {"id_suffix": "isasi", "en_suffix": "ization", "example": ["otomatisasi", "automation"]},
    {"id_suffix": "asi", "en_suffix": "ation", "example": ["dokumentasi", "documentation"]},
    {"id_suffix": "isi", "en_suffix": "ition", "example": ["komposisi", "composition"]},
    {"id_suffix": "uksi", "en_suffix": "uction", "example": ["produksi", "production"]},
    {"id_suffix": "itas", "en_suffix": "ity", "example": ["produktivitas", "productivity"]},
    {"id_suffix": "grafi", "en_suffix": "graphy", "example": ["tipografi", "typography"]},
    {"id_suffix": "grafik", "en_suffix": "graphic", "example": ["infografik", "infographic"]},
    {"id_suffix": "logi", "en_suffix": "logy", "example": ["metodologi", "methodology"]},
]


def _http_get(url: str, timeout: int = 30) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def _extract_tarball_member(url: str, member_suffix: str) -> str | None:
    data = _http_get(url)
    if not data:
        return None
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            for m in tf.getmembers():
                if m.name.endswith(member_suffix):
                    f = tf.extractfile(m)
                    return f.read().decode("utf-8", "replace") if f else None
    except Exception:
        return None
    return None


def _load_sources(cache_dir: Path) -> dict[str, str]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    out: dict[str, str] = {}
    for name, (url, kind, member) in _SOURCES.items():
        cache_file = cache_dir / f"{name}.cache"
        if cache_file.exists() and cache_file.stat().st_size > 100:
            out[name] = cache_file.read_text("utf-8", "replace")
            continue
        text: str | None = None
        if kind == "tarball":
            text = _extract_tarball_member(url, member)
        else:
            raw = _http_get(url)
            text = raw.decode("utf-8", "replace") if raw else None
        if text:
            cache_file.write_text(text, "utf-8")
            out[name] = text
    return out


def _parse_kbbi_wordlist(text: str) -> set[str]:
    words: set[str] = set()
    for line in text.splitlines():
        w = line.strip().lower()
        if not w or len(w) > 30 or " " in w or w.startswith("-") or w.endswith("-"):
            continue
        if re.fullmatch(r"[a-zA-Z]+", w):
            words.add(w)
    return words


def _parse_slang_csv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            slang = (row.get("slang") or "").strip().lower()
            formal = (row.get("formal") or "").strip().lower()
            if slang and formal and slang != formal and len(slang) <= 24:
                out.setdefault(slang, formal)
    except Exception:
        pass
    return out


def _get_plugin_data_dir() -> Path:
    try:
        from plugins.plugin_storage import plugin_data_dir
        base = Path(plugin_data_dir("auto_skill_selector"))
    except Exception:
        base = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / \
            "plugin-data" / "auto_skill_selector"
    base.mkdir(parents=True, exist_ok=True)
    return base


def build_lexicon(force: bool = False, write_repo: bool = True) -> dict:
    """Susun lexicon_id_en.json (4 lapisan). Return dict leksikon.

    known_vocab = wordlist KBBI (bila terunduh) + seluruh basis glosarium/kamus
    (selalu tersedia offline). slang_to_formal = kurasi inti (menang) + kamus
    komunitas. concept_pairs = >=250 pasangan EN<->ID lintas 9 pilar.
    """
    data_dir = _get_plugin_data_dir()
    cache_dir = data_dir / "lexicon-cache"
    out_path = data_dir / "lexicon_id_en.json"
    if out_path.exists() and not force and out_path.stat().st_size > 1000:
        try:
            lex = json.loads(out_path.read_text("utf-8"))
            if write_repo:
                LEXICON_REPO_PATH.write_text(
                    json.dumps(lex, ensure_ascii=False, separators=(",", ":")), "utf-8")
            return lex
        except Exception:
            pass

    sources = _load_sources(cache_dir)
    kbbi_words = _parse_kbbi_wordlist(sources.get("kbbi_wordlist", "")) \
        if sources.get("kbbi_wordlist") else set()

    # Lapis 3: kurasi inti menang atas kamus komunitas (mis. 'dek' -> pitch deck).
    slang = _parse_slang_csv(sources.get("slang", "")) if sources.get("slang") else {}
    slang.update(SLANG_CORE)
    slang = {k: v for k, v in slang.items() if v or k in SLANG_CORE}

    # Lapis 2: pasangan konsep EN->ID + balikannya (ID->EN multi-padanan).
    en_id = dict(CORE_EN_ID)
    id_en: dict[str, list[str]] = {}
    for idn, ens in KBBI_GLOSSARY.items():
        id_en.setdefault(idn.lower(), [])
        for e in ens:
            if e not in id_en[idn.lower()]:
                id_en[idn.lower()].append(e)
            en_id.setdefault(e, idn.lower())
    for en, idn in CORE_EN_ID.items():
        id_en.setdefault(idn, [])
        if en not in id_en[idn]:
            id_en[idn].append(en)

    # known_vocab: KBBI + semua kata dasar glosarium/kamus (gate KPST di Rust).
    vocab: set[str] = set(kbbi_words)
    for term in list(id_en.keys()) + list(en_id.keys()) + list(en_id.values()):
        for w in re.findall(r"[a-z]+", term.lower()):
            if len(w) >= 3:
                vocab.add(w)
    for v in slang.values():
        for w in re.findall(r"[a-z]+", v.lower()):
            if len(w) >= 3:
                vocab.add(w)

    concept_pairs = sorted(
        [{"en": en, "id": idn} for en, idn in CORE_EN_ID.items()],
        key=lambda p: p["en"])

    lexicon = {
        "version": 3,
        "layers": ["kbbi", "concept_en_id", "slang_chat", "translit_rules"],
        "known_vocab": sorted(vocab),
        "known_vocab_size": len(vocab),
        "kbbi_wordlist_size": len(kbbi_words),
        "slang_to_formal": dict(sorted(slang.items())),
        "slang_curated_count": len(SLANG_CORE),
        "concept_pairs": concept_pairs,
        "concept_pairs_count": len(concept_pairs),
        "kbbi_glossary": {k: v for k, v in sorted(KBBI_GLOSSARY.items())},
        "en_to_id": dict(sorted(en_id.items())),
        "id_to_en": {k: v for k, v in sorted(id_en.items())},
        "translit_rules": TRANSLIT_RULES,
    }
    js = json.dumps(lexicon, ensure_ascii=False, separators=(",", ":"))
    out_path.write_text(js, "utf-8")
    if write_repo:
        LEXICON_REPO_PATH.write_text(js, "utf-8")
    return lexicon


if __name__ == "__main__":
    import sys
    lx = build_lexicon(force="--force" in sys.argv)
    print(f"known_vocab:        {lx['known_vocab_size']} kata (KBBI wordlist: {lx['kbbi_wordlist_size']})")
    print(f"concept_pairs:      {lx['concept_pairs_count']} pasangan EN<->ID (target >=250)")
    print(f"slang curated:      {lx['slang_curated_count']} entri (target >=150)")
    print(f"slang total:        {len(lx['slang_to_formal'])} entri")
    print(f"kbbi_glossary:      {len(lx['kbbi_glossary'])} istilah baku")
    print(f"translit_rules:     {len(lx['translit_rules'])} aturan (diimplementasikan di Rust)")
    print(f"ditulis: {LEXICON_REPO_PATH}")