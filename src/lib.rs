//! hermes_skill_brain — Rust core engine for the Hermes `auto_skill_selector` plugin.
//!
//! FASE 2 — Strict 6-stage pipeline (Master Prompt §1, deterministic contract):
//!   [Stage 0] Conversational / Meta-Query Bypass       -> NO_SKILL_NEEDED
//!   [Stage 1] Explicit Skill Override & Pinning        -> pin (checked vs Stage 2)
//!   [Stage 2] GLOBAL Negation & Prohibition Sieve      -> GLOBAL_BANNED_SET + sanitized text
//!   [Stage 3] Multi-Clause & Multi-Job Splitter        -> max 3 sub-clauses
//!   [Stage 4] Per-Clause Dynamic Algorithm Selector    -> 4 adaptive modes
//!   [Stage 5] Decision Gate / Merge / Fallback         -> 6 official RoutingDecision states
//!
//! Scoring: BM25F 4-zone document weights (S 8.0 / A 4.5 / B 2.5 / C 0.6,
//! compiled by trainer.py), Multinomial Naive Bayes, category centroid cosine,
//! prompt Instruction zone 1.0x vs Payload zone 0.15x.
//!
//! Hard rules honoured here:
//!   * Never panic on user input (no unwrap() on externally-sourced data).
//!   * Stage 2 ALWAYS runs before Stage 3 (global ban applies to all clauses).
//!   * Banned skills get hard mask -inf and never appear in top-k/probabilities.
//!   * Latency: inverted index + capped payload tokens + instruction-only scan.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::sync::RwLock;

// ---------------------------------------------------------------------------
// Embedded bilingual lexicon (lexicon_id_en.json, built by lexicon_builder.py)
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize, Default)]
struct EmbeddedLexicon {
    #[serde(default)]
    slang_to_formal: HashMap<String, String>,
    #[serde(default)]
    en_to_id: HashMap<String, String>,
    #[serde(default)]
    id_to_en: HashMap<String, Vec<String>>,
}

static LEXICON_JSON: &str = include_str!("../lexicon_id_en.json");

struct Lexicon {
    slang: HashMap<String, String>,
    en_to_id: HashMap<String, String>,
    id_to_en: HashMap<String, Vec<String>>,
    /// Multi-word phrases (slang + concept pairs), longest-first for matching.
    phrases: Vec<(Vec<String>, Vec<String>)>,
}

impl Lexicon {
    fn load() -> Lexicon {
        let emb: EmbeddedLexicon = serde_json::from_str(LEXICON_JSON).unwrap_or_default();
        let mut phrases: Vec<(Vec<String>, Vec<String>)> = Vec::new();
        for (k, v) in emb.slang_to_formal.iter().chain(emb.en_to_id.iter()) {
            let ks: Vec<String> = k.split_whitespace().map(|s| s.to_string()).collect();
            if ks.len() >= 2 {
                let vs: Vec<String> = v.split_whitespace().map(|s| s.to_string()).collect();
                phrases.push((ks, vs));
            }
        }
        for (k, vs) in &emb.id_to_en {
            let ks: Vec<String> = k.split_whitespace().map(|s| s.to_string()).collect();
            if ks.len() >= 2 {
                phrases.push((ks, vs.clone()));
            }
        }
        phrases.sort_by(|a, b| b.0.len().cmp(&a.0.len()));
        Lexicon {
            slang: emb.slang_to_formal,
            en_to_id: emb.en_to_id,
            id_to_en: emb.id_to_en,
            phrases,
        }
    }
}

// ---------------------------------------------------------------------------
// Model schema (skill_model.json written by trainer.py)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SkillClass {
    pub name: String,
    #[serde(default)]
    pub category: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub doc_len: f64,
    #[serde(default)]
    pub log_prior: f64,
    #[serde(default)]
    pub default_log_prob: f64,
    #[serde(default)]
    pub core_keywords: Vec<String>,
    #[serde(default)]
    pub feature_weights: HashMap<String, f64>,
    #[serde(default)]
    pub feature_log_probs: HashMap<String, f64>,
    /// Synonym cluster tags used by the Stage-2 ban hard mask (e.g. excel, xlsx).
    #[serde(default)]
    pub ban_tags: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SkillModel {
    pub version: u32,
    pub threshold: f64,
    pub multi_skill_threshold: f64,
    pub null_anchor_score: f64,
    pub softmax_temperature: f64,
    pub avg_doc_len: f64,
    #[serde(default)]
    pub known_vocab: HashSet<String>,
    #[serde(default)]
    pub idf_table: HashMap<String, f64>,
    #[serde(default)]
    pub category_tokens: HashMap<String, Vec<String>>,
    /// Numeric centroid vectors per category for centroid-cosine (Stage 4).
    #[serde(default)]
    pub category_centroids: HashMap<String, HashMap<String, f64>>,
    #[serde(default)]
    pub classes: Vec<SkillClass>,
    #[serde(default)]
    pub enable_multi_skill: bool,
}

// --- BM25F constants (spec §1.3) ---
const K1: f64 = 1.2;
const B: f64 = 0.75;
const BIGRAM_BOOST: f64 = 2.5;

// Prompt zones (spec §1.3): instruction 1.0x, payload 0.15x.
// For long pastes the real instruction is usually a short request at the END
// (spec scenario 9). The instruction zone is therefore TAIL-dominant: the last
// ~320 chars at full weight, plus a small head window at reduced weight so a
// leading instruction is not lost entirely. Everything between is payload.
const INSTRUCTION_HEAD: usize = 80;
const INSTRUCTION_TAIL: usize = 320;
const HEAD_WEIGHT: f64 = 0.35;
const PAYLOAD_MIN_LEN: usize = 300;
const PAYLOAD_WEIGHT: f64 = 0.15;
const INSTRUCTION_WEIGHT: f64 = 1.0;
const PAYLOAD_MAX_TOKENS: usize = 25;

const MAX_CANDIDATES: usize = 5;
const HARD_MASK: f64 = f64::NEG_INFINITY;

// Mode weight tables (spec §1.3): (bm25f, mnb, centroid).
const MODE_WEIGHTS: [(f64, f64, f64); 4] = [
    (0.80, 0.15, 0.05), // 1 EXACT_LEXICAL_BM25F
    (0.25, 0.55, 0.20), // 2 SEMANTIC_CONCEPT_MNB
    (0.50, 0.30, 0.20), // 3 HYBRID_BALANCED
    (0.45, 0.35, 0.20), // 4 CONSTRAINT_FILTERED_RERANK
];
const MODE_NAMES: [&str; 4] = [
    "EXACT_LEXICAL_BM25F",
    "SEMANTIC_CONCEPT_MNB",
    "HYBRID_BALANCED",
    "CONSTRAINT_FILTERED_RERANK",
];

// Bilingual stopwords — never become features on their own.
const STOPWORDS: &[&str] = &[
    "yang", "dan", "atau", "dengan", "untuk", "dari", "pada", "adalah", "itu", "ini", "saya",
    "aku", "kamu", "kita", "mereka", "dia", "nya", "the", "a", "an", "and", "or", "with", "for",
    "from", "to", "of", "in", "on", "is", "are", "be", "this", "that", "i", "you", "we", "they",
    "it", "my", "your", "our", "please", "tolong", "bantu", "coba", "mau", "ingin", "ke", "di",
    "akan", "sudah", "bisa", "agar", "biar", "supaya", "sebuah", "para", "si", "pun", "lah",
    "tapi", "tetapi", "namun", "melainkan", "but", "however", "instead", "lantas", "habis",
    "setelah", "sesudah", "sebelum", "sambil", "seraya", "serta", "plus", "juga", "dan",
];

fn is_stopword(w: &str) -> bool {
    STOPWORDS.contains(&w)
}

// ---------------------------------------------------------------------------
// Stage 0 — conversational / meta-query detection
// ---------------------------------------------------------------------------

const GREETINGS: &[&str] = &[
    "halo", "hai", "hi", "hello", "hey", "pagi", "siang", "sore", "malam",
    "selamat pagi", "selamat siang", "selamat sore", "selamat malam", "apa kabar",
    "good morning", "good night", "how are you", "terima kasih", "makasih", "thanks",
    "thank you", "mantap", "keren", "bagus sekali", "wkwk", "haha", "hehe",
];

const CONVERSATIONAL_PHRASES: &[&str] = &[
    "menurutmu", "menurut kamu", "menurut anda", "apa pendapatmu", "apa pendapat kamu",
    "what do you think", "in your opinion", "lagi condong", "condong ke arah",
    "lebih bagus mana", "lebih baik mana", "apa bedanya", "apa perbedaan",
    "jelaskan pengertian", "jelaskan konsep", "jelaskan apa itu", "apa itu",
    "apa yang dimaksud", "kenapa ya", "mengapa ya", "why is", "what is the difference",
    "explain the concept", "let's brainstorm", "lets brainstorm", "brainstorming dulu",
    "kita diskusi", "bahas dulu", "diskusi dulu", "jangan langsung", "dont write code",
    "don't write code", "jangan buat kode", "lagi apa", "sedang apa", "bisa ngobrol",
    "mau ngobrol", "curhat", "how does", "how do", "ceritain dong", "ceritakan",
    "tren desain", "trend design", "menurut pendapat", "kira-kira", "kira kira",
];

/// Action verbs (ID + EN, incl. common affixed forms) — deliverable execution.
const ACTION_VERBS: &[&str] = &[
    "buat", "buatkan", "buatlah", "bikin", "bikinin", "buatin", "susun", "susunkan",
    "rancang", "rancangkan", "generate", "render", "konversi", "konversikan", "ubah",
    "ubahlah", "analisis", "analisa", "audit", "jalankan", "deploy", "setup", "edit",
    "perbaiki", "ekstrak", "ekstraksi", "hitung", "hitunglah", "simulasikan", "tulis",
    "tuliskan", "ringkas", "ringkaskan", "create", "build", "make", "convert", "fix",
    "extract", "write", "run", "automate", "optimize", "desain", "design", "ambil",
    "ambilkan",    "visualisasikan", "visualisasi", "gabung", "gabungkan", "pisah",
    "lakukan", "melakukan", "hitungin", "bikinlah", "jadikan", "jadikanlah",
    "pisahkan", "bersihkan", "bersihin", "rapikan", "rapihin", "benerin", "terjemah",
    "terjemahkan", "terjemahin", "pindai", "scan", "cetak", "print", "unduh", "download",
    "unggah", "upload", "kirim", "kirimkan", "kirimin", "cari", "carikan", "cariin",
    "telusuri", "teliti", "rekam", "rekamkan", "potong", "crop", "resize", "kompres",
    "compress", "tambahkan", "tambahin", "hapus", "hilangkan", "ilangin", "atur",
    "setting", "konfigurasikan", "instal", "install", "pasang", "bongkar", "refactor",
    "debug", "test", "uji", "dokumentasikan", "dokumentasi", "presentasikan", "susunlah",
    "hasilkan", "keluarkan", "export", "impor", "import", "sinkronkan", "sync",
    "jadwalkan", "jadwalin", "rencanakan", "evaluasi", "review", "tinjau", "periksa",
    "cek", "cekin", "validasi", "verifikasi", "rekonsiliasi", "hitungin", "gambarkan",
    "gambarin", "lukis", "animasikan", "animate", "editin", "sunting", "menyunting",
    "memindai", "mengekstrak", "merangkum", "mengonversi", "memvisualisasikan",
    "menulis", "menyusun", "membuat", "menghitung", "menganalisis", "menerjemahkan",
    "merender", "ngerender", "ngedit", "ngerekap", "rekap", "rekapan", "olah",
    "kelola", "manage", "monitor", "pantau", "pulihkan", "restore", "cadangkan",
    "backup", "amankan", "auditin", "strukturkan", "petakan", "plot", "plotkan",
    "grafikkan", "tabulasikan", "klasifikasikan", "kategorikan", "urutkan", "sort",
    "filter", "saring", "agregasikan", "join", "merge", "split", "bagikan", "share",
    "kirimkan", "drafkan", "draft", "finalkan", "selesaikan", "kerjakan", "garap",
    "eksekusi", "execute", "implementasikan", "terapkan", "bangun", "kembangkan",
    "memvisualisasikan", "memindai", "menyunting", "mengekstrak", "merangkum",
    "mengonversi", "menulis", "menyusun", "membuat", "menghitung", "menganalisis",
    "menerjemahkan", "merender", "mengelola", "memproses", "mengubah", "memotong",
    "menyusun", "memoles", "mengaudit", "menguji", "memeriksa", "memvalidasi",
];

/// Deliverable nouns — objects that imply an execution artifact.
const DELIVERABLE_NOUNS: &[&str] = &[
    "video", "animasi", "3d", "desain", "dokumen", "laporan", "slide", "salindia",
    "presentasi", "musik", "lagu", "komik", "infografis", "infografik", "strategi",
    "model", "jadwal", "aplikasi", "script", "skrip", "workflow", "storyboard",
    "render", "poster", "pdf", "csv", "xlsx", "excel", "docx", "word", "pptx",
    "powerpoint", "html", "web", "website", "situs", "dashboard", "dasbor", "grafik",
    "chart", "diagram", "bagan", "tabel", "data", "dataset", "database", "api",
    "kode", "code", "program", "bug", "fitur", "feature", "email", "surel", "surat",
    "memo", "notula", "notulen", "risalah", "artikel", "blog", "utas", "thread",
    "konten", "content", "kampanye", "campaign", "iklan", "seo", "terjemahan",
    "transkrip", "transkripsi", "siniar", "podcast", "audio", "rekaman", "suara",
    "voiceover", "lirik", "midi", "faktur", "invoice", "anggaran", "budget",
    "neraca", "valuasi", "dcf", "mece", "pitch", "dek", "deck", "wireframe",
    "mockup", "purwarupa", "logo", "brand", "merek", "tipografi", "palet", "banner",
    "spanduk", "ilustrasi", "komposisi", "aransemen", "subtitle", "takarir", "caption",
    "latar", "scene", "adegan", "karakter", "rig", "rigging", "keyframe", "mesh",
    "tekstur", "shader", "kamera", "lighting", "pencahayaan", "spektrogram", "midi",
    "jurnal", "makalah", "paper", "sitasi", "pustaka", "referensi", "paten", "survei",
    "kuesioner", "proposal", "abstrak", "hipotesis", "dataset", "pipeline", "etl",
    "kueri", "query", "sql", "skema", "schema", "kontainer", "container", "docker",
    "server", "peladen", "deploy", "deployment", "ci", "cd", "testing", "pengujian",
    "keamanan", "security", "audit", "checklist", "sop", "prosedur", "tenggat",
    "deadline", "agenda", "kalender", "formulir", "form", "template", "templat",
    "resume", "cv", "portofolio", "sertifikat", "kuitansi", "struk", "bon",
    "workbook", "spreadsheet", "lembar", "pivot", "kohort", "cohort", "funnel",
    "corong", "retensi", "metrik", "kpi", "okr", "swot", "tom", "tam", "sam", "som",
    "unit", "ekonomi", "pricing", "harga", "pasar", "market", "investor", "saham",
    "obligasi", "dividen", "anuitas", "rekonsiliasi", "laba", "rugi", "omzet",
    "arus", "kas", "cash", "flow", "wacc", "irr", "npv", "lbo", "merger", "akuisisi",
    "pajak", "tax", "gaji", "payroll", "penggajian", "neraca", "lajur", "anuitas",
    "mermaid", "excalidraw", "svg", "png", "jpg", "mp4", "mp3", "wav", "gif",
    "latex", "bibtex", "osint", "whois", "bioinformatika", "genom", "protein",
    "molekul", "simulasi", "eksperimen", "riset", "penelitian", "tinjauan",
    "literatur", "pustaka", "bibliometrik", "meta", "analisis", "flashcard",
    "kartu", "belajar", "hapal", "hafalan", "rangkuman", "ringkasan", "ikhtisar",
    "executive", "brief", "memo", "naskah", "pidato", "speech", "press", "release",
    "siaran", "pers", "headline", "judul", "hook", "copy", "copywriting",
    "lokalisasi", "localization", "dwibahasa", "bilingual", "suntingan", "edit",
    "koreksi", "proofread", "parafrase", "parafrasa", "tulisan", "draf", "draft",
];

fn has_action_verb(tokens: &[String]) -> bool {
    tokens.iter().any(|t| ACTION_VERBS.contains(&t.as_str()))
}

fn has_deliverable(tokens: &[String]) -> bool {
    tokens.iter().any(|t| DELIVERABLE_NOUNS.contains(&t.as_str()))
}

/// Stage 0: true when the prompt is pure conversation / meta-query with no
/// actionable deliverable. Explicit skill requests bypass this (checked first).
/// Strong conversational markers that override weak/ambiguous verb signals.
/// "menurutmu tren desain web..." is a discussion even though "desain" can be
/// a verb; only an UNAMBIGUOUS execution verb (buatkan, ekstrak, render...)
/// should pull such a prompt back into directive territory.
const STRONG_CONVERSATIONAL: &[&str] = &[
    "menurutmu", "menurut kamu", "menurut anda", "apa pendapatmu", "what do you think",
    "in your opinion", "lebih bagus mana", "lebih baik mana", "apa bedanya",
    "apa perbedaan", "jelaskan pengertian", "jelaskan konsep", "apa itu",
    "apa yang dimaksud", "what is the difference", "explain the concept",
    "let's brainstorm", "lets brainstorm", "kita diskusi", "bahas dulu",
    "diskusi dulu", "jangan langsung", "curhat", "lagi condong", "condong ke arah",
];

/// Unambiguous execution verbs (cannot be read as a plain noun in context).
const STRONG_ACTION_VERBS: &[&str] = &[
    "buat", "buatkan", "buatlah", "bikin", "bikinin", "buatin", "susun", "susunkan",
    "rancang", "generate", "render", "konversi", "konversikan", "ubah", "ekstrak",
    "ekstraksi", "hitung", "simulasikan", "tulis", "tuliskan", "ringkas", "create",
    "build", "make", "convert", "fix", "extract", "write", "run", "automate",
    "optimize", "ambil", "ambilkan", "visualisasikan", "gabung", "gabungkan",
    "bersihkan", "rapikan", "rapihin", "benerin", "terjemah", "terjemahkan",
    "pindai", "scan", "cetak", "unduh", "unggah", "kirim", "kirimkan", "cari",
    "carikan", "rekam", "potong", "kompres", "tambahkan", "hapus", "hilangkan",
    "atur", "instal", "install", "pasang", "refactor", "debug", "uji", "hasilkan",
    "export", "impor", "import", "jadwalkan", "rencanakan", "periksa", "cek",
    "validasi", "verifikasi", "rekonsiliasi", "gambarkan", "lukis", "animasikan",
    "sunting", "menyunting", "memindai", "mengekstrak", "merangkum", "mengonversi",
    "memvisualisasikan", "menulis", "menyusun", "membuat", "menghitung", "menerjemahkan",
    "merender", "olah", "kelola", "pulihkan", "cadangkan", "strukturkan", "petakan",
    "grafikkan", "tabulasikan", "klasifikasikan", "urutkan", "saring", "kerjakan",
    "garap", "eksekusi", "execute", "implementasikan", "terapkan", "bangun", "kembangkan",
    "deploy", "lakukan", "melakukan", "presentasikan", "dokumentasikan",
];

fn has_strong_action_verb(tokens: &[String]) -> bool {
    effective_action_verb(tokens, STRONG_ACTION_VERBS)
}

/// Negation / prepositional cues that neutralize a following verb for posture
/// detection: "jangan langsung buat kode" (negated) and "duit buat beli kopi"
/// ("buat" = untuk, prepositional) must NOT count as execution asks.
const VERB_NEUTRALIZERS: &[&str] = &[
    "jangan", "jgn", "tanpa", "hindari", "bukan", "tidak", "gak", "ga", "nggak",
    "enggak", "kagak", "gausah", "stop", "dilarang", "belum", "janganlah",
    "dont", "don't", "never", "avoid", "without", "not", "no",
];

/// Is there an execution verb that is NOT negated and NOT prepositional?
/// A verb is neutralized when a negation cue appears within the 3 preceding
/// tokens, or when "buat"/"bikin" is immediately followed by another verb
/// (prepositional "buat beli", "bikin pergi" = "untuk ...").
fn effective_action_verb(tokens: &[String], verb_set: &[&str]) -> bool {
    for (i, t) in tokens.iter().enumerate() {
        if !verb_set.contains(&t.as_str()) {
            continue;
        }
        // Negation window: any neutralizer in the 3 preceding tokens.
        let lo = i.saturating_sub(3);
        if tokens[lo..i].iter().any(|p| VERB_NEUTRALIZERS.contains(&p.as_str())) {
            continue;
        }
        // Prepositional "buat"/"bikin" + verb ("buat beli", "bikin pergi").
        if (t == "buat" || t == "bikin") {
            if let Some(next) = tokens.get(i + 1) {
                if ACTION_VERBS.contains(&next.as_str()) || STRONG_ACTION_VERBS.contains(&next.as_str()) {
                    continue;
                }
            }
        }
        return true;
    }
    false
}

fn is_conversational(lower: &str, tokens: &[String]) -> bool {
    // Pure greeting / very short social turn.
    if tokens.len() <= 4 && GREETINGS.iter().any(|g| lower.contains(g)) {
        return true;
    }
    // Venting / feelings without a deliverable ("lagi gak punya duit", "capek
    // banget", "aku sedih") — conversational even if "buat" appears as "untuk".
    const VENTING: &[&str] = &[
        "gak punya duit", "ga punya duit", "nggak punya uang", "capek banget",
        "capek sekali", "lagi sedih", "lagi capek", "lagi bete", "curhat",
        "bete banget", "pusing banget", "lelah sekali", "lagi galau",
    ];
    if VENTING.iter().any(|v| lower.contains(v)) && !effective_action_verb(tokens, STRONG_ACTION_VERBS) {
        return true;
    }
    let strong_conv = STRONG_CONVERSATIONAL.iter().any(|p| lower.contains(p));
    if strong_conv {
        // A strong discussion marker wins unless an un-negated execution verb
        // is present ("menurutmu bagus mana, buatkan X" -> directive; but
        // "jangan langsung buat kode, menurutmu..." -> discussion).
        return !has_strong_action_verb(tokens);
    }
    let conv_hit = CONVERSATIONAL_PHRASES.iter().any(|p| lower.contains(p));
    // Question-form meta queries without an execution verb ("what is ...?",
    // "jelaskan pengertian ...", "kenapa ...?") are conceptual, not tasks.
    let question_form = lower.trim_end().ends_with('?')
        && !effective_action_verb(tokens, ACTION_VERBS)
        && (lower.starts_with("what ") || lower.starts_with("why ")
            || lower.starts_with("how does") || lower.starts_with("how do")
            || lower.contains("apa itu") || lower.contains("apa yang dimaksud")
            || lower.contains("jelaskan") || lower.contains("kenapa")
            || lower.contains("mengapa") || lower.contains("menurutmu"));
    if !conv_hit && !question_form {
        // Greeting-led chit-chat without any action verb.
        if GREETINGS.iter().any(|g| lower.starts_with(g)) && !effective_action_verb(tokens, ACTION_VERBS) {
            return true;
        }
        return false;
    }
    // Conversational cue present: bypass only when there is no execution ask.
    !effective_action_verb(tokens, ACTION_VERBS)
}

// ---------------------------------------------------------------------------
// Stage 1 — explicit skill override & pinning
// ---------------------------------------------------------------------------

#[derive(Debug, Default)]
struct PinResult {
    /// Resolved skill names (exist in the model, legal candidates).
    resolved: Vec<String>,
    /// Count of explicit pin requests whose target does NOT exist in the
    /// model. The raw name is NEVER stored/echoed (prompt-injection vector,
    /// audit S-1/H-5) — only the fact that an unknown pin was requested.
    unknown_count: usize,
    /// Prompt text with pin trigger+name fragments removed (safe for scoring
    /// and for hunt clauses — unknown names never leak downstream).
    stripped_text: String,
}

/// Extract pinned skill names from "/skill <name>", "pakai skill <name>",
/// "gunakan skill <name>", "use skill <name>", "@skill <name>".
/// Multi-word triggers are matched on the token stream (so "pakai skill X"
/// anywhere in the sentence works, incl. after "lalu"). Bare "@slug" only at
/// message start; mid-sentence mentions and emails are never pins (A08/A09).
fn extract_pins(lower: &str, classes: &[SkillClass]) -> PinResult {
    let mut out = PinResult::default();
    let toks: Vec<&str> = lower.split_whitespace().collect();
    let clean_tok = |t: &str| -> String {
        t.trim_matches(|c: char| !c.is_alphanumeric() && c != '/' && c != '@' && c != '-' && c != '_').to_string()
    };
    let cleaned: Vec<String> = toks.iter().map(|t| clean_tok(t)).collect();
    let triggers: &[&[&str]] = &[
        &["pakai", "skill"], &["gunakan", "skill"], &["use", "skill"], &["with", "skill"],
        &["/skill"], &["@skill"],
    ];
    let mut candidates: Vec<String> = Vec::new();
    let mut consumed: Vec<bool> = vec![false; toks.len()];
    // Question guard: "jelaskan cara pakai skill di Hermes" / "I'm dealing
    // with skill issues" are NOT pin requests (audit A13/A14).
    let question_ctx = cleaned.iter().any(|t| matches!(t.as_str(),
        "cara" | "how" | "what" | "apa" | "jelaskan" | "explain" | "issues" | "issue" | "problems"))
        || lower.trim_end().ends_with('?');
    let mut i = 0usize;
    while i < cleaned.len() {
        let mut matched_len = 0usize;
        for trig in triggers {
            let n = trig.len();
            if i + n <= cleaned.len() && cleaned[i..i + n] == trig[..] {
                matched_len = n;
                break;
            }
        }
        if matched_len > 0 {
            let name_idx = i + matched_len;
            let next_clean = toks.get(name_idx)
                .map(|t| t.trim_matches(|c: char| !c.is_alphanumeric() && c != '-' && c != '_'))
                .unwrap_or("");
            // Natural-language continuation after the trigger ("pakai skill
            // di Hermes", "with skill issues"): prose, not a pin. Slash/@
            // forms stay explicit commands regardless.
            let is_slash = cleaned[i].starts_with('/') || cleaned[i].starts_with('@');
            let prose_continuation = next_clean.is_empty()
                || is_stopword(next_clean)
                || matches!(next_clean, "di" | "itu" | "ini" | "issues" | "issue" | "problems" | "yang");
            if !is_slash && (question_ctx || prose_continuation) {
                i += 1;
                continue;
            }
            for k in i..i + matched_len { consumed[k] = true; }
            if let Some(next) = toks.get(name_idx) {
                let cand = next.trim_matches(|c: char| !c.is_alphanumeric() && c != '-' && c != '_');
                let cand_clean = clean_tok(cand);
                let is_trigger = triggers.iter().any(|tr| tr.len() == 1 && tr[0] == cand_clean);
                if !cand.is_empty() && !is_trigger {
                    candidates.push(cand.to_string());
                    consumed[name_idx] = true;
                } else {
                    out.unknown_count += 1; // explicit pin with no usable name
                }
            } else {
                out.unknown_count += 1; // trailing trigger with nothing after
            }
            i += matched_len + 1;
            continue;
        }
        i += 1;
    }
    // Bare @mention at the START of the message is an explicit address to a
    // skill/bot. Known slug -> resolved pin; unknown -> unknown pin attempt
    // (hunt/clarify, never echoed). Mid-sentence mentions ("tag @budi") and
    // emails ("budi@gmail.com") are never pins (audit A02/A08/A09).
    if !consumed.first().copied().unwrap_or(true) {
        if let Some(first) = toks.first() {
            if let Some(stripped) = first.strip_prefix('@') {
                let cand = stripped.trim_matches(|c: char| !c.is_alphanumeric() && c != '-' && c != '_');
                if !cand.is_empty() && cand != "skill" {
                    if classes.iter().any(|c| c.name.to_lowercase() == cand) {
                        candidates.push(cand.to_string());
                    } else {
                        out.unknown_count += 1;
                    }
                    consumed[0] = true;
                }
            }
        }
    }
    // Resolve candidates against known classes (exact name/slug, CI).
    for p in candidates {
        let pl = p.to_lowercase();
        let mut found = false;
        for c in classes {
            if c.name.to_lowercase() == pl {
                if !out.resolved.contains(&c.name) {
                    out.resolved.push(c.name.clone());
                }
                found = true;
                break;
            }
        }
        if !found {
            out.unknown_count += 1; // name deliberately dropped, never echoed
        }
    }
    // Rebuild the working text without pin fragments (trigger + name).
    let kept: Vec<&str> = toks.iter().enumerate()
        .filter(|(i, _)| !consumed[*i])
        .map(|(_, t)| *t)
        .collect();
    out.stripped_text = kept.join(" ");
    out
}

// ---------------------------------------------------------------------------
// Stage 2 — GLOBAL negation & prohibition sieve (BEFORE splitting!)
// ---------------------------------------------------------------------------

/// Ban trigger phrases (ID & EN), longest-first. Matched on the lowercased
/// prompt with punctuation normalized to spaces.
const BAN_TRIGGERS: &[&str] = &[
    "jangan buat pakai", "jangan menggunakan", "jangan gunakan", "jangan pakai",
    "dilarang pakai", "dilarang menggunakan", "stop pakai", "ga usah pakai",
    "gausah pakai", "gausah pake", "gak mau pakai", "gak mau pake", "jgn pake",
    "jgn pakai", "jangan pake", "do not use", "don't use", "dont use", "never use",
    "not in", "instead of", "rather than", "without", "avoid", "except", "ban",
    "tanpa", "hindari", "selain", "kecuali", "bukan", "no",
];

/// Non-prohibition idioms: the cue word is part of a fixed expression, NOT a
/// ban ("jangan lupa" = reminder, "no worries" = reassurance, "no later than"
/// = deadline, "bukan itu" = correction, "no 1:" = numbering). General rule:
/// when the trigger is immediately followed by one of these continuation
/// words, the whole cue is skipped (no ban, no stripping of the target).
const TRIGGER_IDIOM_CONTINUATIONS: &[(&str, &[&str])] = &[
    ("jangan", &["lupa", "sampai", "khawatir", "ragu", "malu", "takut", "baper", "sedih", "marah"]),
    ("jgn", &["lupa", "sampai", "khawatir", "ragu"]),
    ("no", &["worries", "worry", "problem", "problemas", "later", "more", "longer",
             "1", "2", "3", "4", "5", "6", "7", "8", "9", "1:", "2:", "3:"]),
    ("bukan", &["itu", "ini", "saya", "aku", "gue", "gw", "kamu", "dia", "mereka",
                "maksudku", "maksudnya", "berarti", "artinya"]),
    ("not", &["only", "just", "yet", "sure", "really"]),
    ("tanpa", &["ribet", "rumit", "repot", "ribet-ribet"]),
];

/// Is the trigger at words[i..] actually a non-prohibition idiom?
fn is_trigger_idiom(words: &[&str], i: usize, tlen: usize) -> bool {
    let cue = words[i];
    for (trigger_cue, continuations) in TRIGGER_IDIOM_CONTINUATIONS {
        if cue == *trigger_cue {
            if let Some(next) = words.get(i + tlen) {
                let nc = clean_ban_target(next);
                if continuations.iter().any(|c| *c == nc) {
                    return true;
                }
                // "no <digit>" numbering ("no 1:", "no 2") — any pure number.
                if cue == "no" && !nc.is_empty() && nc.chars().all(|c| c.is_ascii_digit()) {
                    return true;
                }
            }
        }
    }
    false
}

/// Style words that follow a negation cue but are NOT tool bans
/// ("jgn kaku", "jangan ribet", "don't be stiff").
const STYLE_WORDS: &[&str] = &[
    "kaku", "ribet", "rumit", "njelimet", "lama", "lambat", "lelet", "lemot",
    "buruk", "jelek", "burik", "bose", "bosan", "formal", "kaku-kaku", "stiff",
    "boring", "slow", "complicated", "complex", "verbose", "panjang", "bertele",
    "tele", "ngawur", "asal", "random", "asal-asalan", "serius", "tegang",
    "mahal", "boros", "rugi", "boncos", "salah", "error", "rusak", "aneh",
    "berantakan", "acak", "ngaco", "kacau", "berlebihan", "lebay", "cringe",
];

/// Synonym clusters for ban expansion (spec §1.1). Banning any member bans the
/// whole cluster — EXCEPT the generic 'spreadsheet' family: banning "Excel"
/// specifically bans {excel, xlsx, xls} but NOT generic spreadsheet alternatives;
/// banning "spreadsheet"/"lembar sebar" bans the whole family.
const BAN_CLUSTERS: &[&[&str]] = &[
    &["excel", "xlsx", "xls"],
    &["spreadsheet", "lembar sebar", "google sheets", "sheets", "excel", "xlsx", "xls"],
    &["powerpoint", "pptx", "ppt"],
    &["word", "docx", "doc"],
    &["pdf"],
    &["docker", "kontainer", "container"],
    &["blender"],
    &["photoshop", "psd"],
    &["canva"],
    &["figma"],
    &["sql", "mysql", "postgres", "postgresql", "sqlite"],
    &["python"],
    &["javascript", "js", "typescript", "ts"],
    &["html", "web", "website"],
    &["csv"],
    &["json"],
    &["latex"],
    &["mermaid"],
    &["ffmpeg"],
    &["whisper"],
    &["midi"],
    &["suno"],
];

/// Tool/format vocabulary the sieve may ban (single tokens + phrases).
const TOOL_WORDS: &[&str] = &[
    "excel", "xlsx", "xls", "spreadsheet", "sheets", "powerpoint", "pptx", "ppt",
    "word", "docx", "doc", "pdf", "csv", "json", "html", "web", "website", "sql",
    "mysql", "postgres", "postgresql", "sqlite", "python", "javascript", "js",
    "typescript", "ts", "docker", "kontainer", "container", "kubernetes", "blender",
    "houdini", "unreal", "cinema4d", "photoshop", "psd", "canva", "figma",
    "excalidraw", "mermaid", "latex", "ffmpeg", "whisper", "midi", "suno",
    "audacity", "premiere", "after effects", "davinci", "capcut", "obs",
    "notion", "obsidian", "trello", "asana", "jira", "slack", "zoom", "meet",
    "teams", "gmail", "outlook", "thunderbird", "chrome", "firefox", "safari",
    "vscode", "vim", "emacs", "sublime", "react", "vue", "angular", "svelte",
    "nextjs", "next.js", "node", "nodejs", "deno", "bun", "rust", "go", "golang",
    "java", "kotlin", "swift", "php", "ruby", "rails", "django", "flask",
    "fastapi", "laravel", "spring", "nginx", "apache", "caddy", "aws", "gcp",
    "azure", "cloudflare", "vercel", "netlify", "heroku", "digitalocean",
    "supabase", "firebase", "mongodb", "redis", "elasticsearch", "kafka",
    "rabbitmq", "graphql", "rest", "grpc", "websocket", "oauth", "jwt",
    "terraform", "ansible", "jenkins", "github actions", "gitlab ci", "circleci",
    "pytest", "jest", "vitest", "cypress", "playwright", "selenium",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly", "tableau",
    "power bi", "powerbi", "looker", "metabase", "superset", "dbt", "airflow",
    "spark", "hadoop", "snowflake", "bigquery", "redshift", "databricks",
    "jupyter", "colab", "anaconda", "tensorflow", "pytorch", "keras",
    "scikit-learn", "sklearn", "xgboost", "lightgbm", "huggingface", "openai",
    "anthropic", "claude", "gemini", "llama", "mistral", "ollama", "langchain",
    "llamaindex", "autogen", "crewai", "comfyui", "stable diffusion", "midjourney",
    "dall-e", "dalle", "runway", "pika", "kling", "sora", "elevenlabs",
    "playht", "murf", "descript", "riverside", "zencastr", "squadcast",
    "spotify", "apple music", "soundcloud", "bandcamp", "distrokid",
    "mailchimp", "sendgrid", "twilio", "stripe", "paypal", "xendit", "midtrans",
    "shopify", "woocommerce", "magento", "wordpress", "webflow", "framer",
    "wix", "squarespace", "ghost", "substack", "medium", "linkedin", "twitter",
    "instagram", "tiktok", "youtube", "facebook", "whatsapp", "telegram",
    "discord", "reddit", "pinterest", "behance", "dribbble", "artstation",
    "sketchfab", "turbosquid", "cgtrader", "unity", "godot", "gamemaker",
    "rpg maker", "construct", "defold", "phaser", "pixi", "three.js", "threejs",
    "babylon", "aframe", "webgl", "opengl", "vulkan", "directx", "cuda",
    "opencl", "metal", "shader", "glsl", "hlsl", "arnold", "vray", "cycles",
    "eevee", "redshift", "octane", "keyshot", "zbrush", "substance", "mari",
    "nuke", "fusion", "flame", "houdini", "maya", "3ds max", "3dsmax", "modo",
    "lightwave", "sketchup", "rhino", "grasshopper", "fusion360", "solidworks",
    "autocad", "inventor", "catia", "creo", "freecad", "openscad", "tinkercad",
    "lembar sebar", "google sheets", "after effects", "power bi", "github actions",
    "gitlab ci", "stable diffusion", "apple music", "rpg maker", "3ds max",
];

#[derive(Debug, Default)]
struct SieveResult {
    banned: HashSet<String>,
    sanitized: String,
    /// Original ban phrases removed (for the case-#1 audit log).
    removed_fragments: Vec<String>,
}

fn normalize_for_match(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for ch in s.chars() {
        if ch.is_alphanumeric() || ch == '.' || ch == '-' || ch == '_' || ch == '\'' {
            out.push(ch.to_ascii_lowercase());
        } else {
            out.push(' ');
        }
    }
    // collapse spaces
    let mut prev_space = false;
    let mut collapsed = String::with_capacity(out.len());
    for ch in out.chars() {
        if ch == ' ' {
            if !prev_space {
                collapsed.push(' ');
            }
            prev_space = true;
        } else {
            collapsed.push(ch);
            prev_space = false;
        }
    }
    collapsed.trim().to_string()
}

/// Tokenize raw text into (word, byte_start, byte_end) keeping original case
/// and punctuation boundaries. Words are alphanumeric runs incl. . - _ '.
fn raw_word_spans(raw: &str) -> Vec<(String, usize, usize)> {
    let mut out = Vec::new();
    let mut start: Option<usize> = None;
    for (i, ch) in raw.char_indices() {
        let in_word = ch.is_alphanumeric() || ch == '.' || ch == '-' || ch == '_' || ch == '\'';
        if in_word {
            if start.is_none() {
                start = Some(i);
            }
        } else if let Some(s) = start.take() {
            out.push((raw[s..i].to_string(), s, i));
        }
    }
    if let Some(s) = start {
        out.push((raw[s..].to_string(), s, raw.len()));
    }
    out
}

/// Expand a banned term through the synonym clusters.
fn expand_ban(term: &str, banned: &mut HashSet<String>) {
    let tl = term.to_lowercase();
    banned.insert(tl.clone());
    // Generic spreadsheet family ban -> everything.
    let generic_spreadsheet = matches!(tl.as_str(), "spreadsheet" | "lembar sebar" | "sheets" | "google sheets");
    for cluster in BAN_CLUSTERS {
        if cluster.iter().any(|m| *m == tl) {
            for m in cluster.iter() {
                if generic_spreadsheet {
                    banned.insert(m.to_string());
                } else if *m == "spreadsheet" || *m == "lembar sebar" || *m == "google sheets" || *m == "sheets" {
                    // Specific Excel ban must not kill generic spreadsheet alternatives.
                    continue;
                } else {
                    banned.insert(m.to_string());
                }
            }
        }
    }
}

/// Strip punctuation attached to a ban TARGET token ("excel." -> "excel",
/// ".pdf" -> "pdf", "spreadsheet," -> "spreadsheet"). Keeps intra-word
/// - _ (e.g. google-sheets stays one token via hyphen) but removes leading/
/// trailing . , ; : ! ? ( ) " ' so cluster expansion & hard-mask match.
fn clean_ban_target(tok: &str) -> String {
    tok.trim_matches(|c: char| !c.is_alphanumeric() && c != '-' && c != '_')
        .to_lowercase()
}

/// Is this token a plausible ban target (tool/format), not a style word?
fn is_bannable_token(tok: &str) -> bool {
    let clean = clean_ban_target(tok);
    if clean.is_empty() || STYLE_WORDS.contains(&clean.as_str()) || is_stopword(&clean) {
        return false;
    }
    if TOOL_WORDS.contains(&clean.as_str()) {
        return true;
    }
    // File extensions (.pdf, .pptx, ...) and known format-ish tokens.
    if tok.starts_with('.') && clean.len() >= 2 {
        return true;
    }
    false
}

/// Stage 2: scan the WHOLE prompt for prohibition phrases, collect the global
/// banned set, and strip the prohibition fragments from the working text.
fn global_negation_sieve(raw: &str) -> SieveResult {
    let mut res = SieveResult::default();
    let spans = raw_word_spans(raw);
    let words: Vec<String> = spans.iter().map(|(w, _, _)| w.to_lowercase()).collect();
    let words_ref: Vec<&str> = words.iter().map(|s| s.as_str()).collect();

    // Track which word indices belong to a ban fragment so we can strip them.
    let mut banned_idx: Vec<bool> = vec![false; words.len()];

    let mut i = 0usize;
    while i < words_ref.len() {
        let mut matched_trigger: Option<(usize, &str)> = None;
        for trig in BAN_TRIGGERS {
            let tw: Vec<&str> = trig.split(' ').collect();
            if i + tw.len() <= words_ref.len() && words_ref[i..i + tw.len()] == tw[..] {
                matched_trigger = Some((tw.len(), trig));
                break;
            }
        }
        if let Some((tlen, trig)) = matched_trigger {
            // Non-prohibition idiom ("jangan lupa", "no worries", "no 1:",
            // "bukan itu"): skip the cue entirely — no ban, no stripping.
            if is_trigger_idiom(&words_ref, i, tlen) {
                i += tlen;
                continue;
            }
            // Weak/ambiguous cues ("no", "bukan", "not", "except", "selain",
            // "kecuali") require POSITIVE evidence: only known tools/formats
            // may be banned. The unknown-noun fallback ("tanpa Houdini")
            // applies to strong prohibition cues only — otherwise ordinary
            // nouns get over-banned ("no code comments", "bukan laporan").
            let first_cue = trig.split(' ').next().unwrap_or("");
            let weak_cue = matches!(first_cue, "no" | "bukan" | "not" | "except" | "selain" | "kecuali");
            // Collect ban targets after the trigger until a boundary.
            let mut j = i + tlen;
            let mut targets: Vec<String> = Vec::new();
            let mut last_target_end = j;
            while j < words_ref.len() && j < i + tlen + 8 {
                let w = words_ref[j];
                // Boundary: contrast pivot / clause connector / new verb clause.
                if matches!(w, "tapi" | "tetapi" | "namun" | "melainkan" | "sebaliknya"
                    | "but" | "however" | "instead" | "lalu" | "kemudian" | "terus"
                    | "then" | "and" | "dan" | "serta" | "plus" | "sambil" | "sekaligus"
                    | "untuk" | "buat" | "biar" | "agar" | "supaya" | "yang" | "ya"
                    | "saja" | "aja" | "dong" | "deh" | "nih" | "sih") {
                    break;
                }
                // "pakai"/"gunakan" after the cue is part of the prohibition
                // phrase itself ("jangan buat pakai X", "gausah pake X").
                if matches!(w, "pakai" | "pake" | "gunakan" | "make" | "use" | "using") {
                    j += 1;
                    continue;
                }
                if ACTION_VERBS.contains(&w) && !targets.is_empty() {
                    break;
                }
                // "atau"/"or" join multiple ban targets.
                if w == "atau" || w == "or" {
                    j += 1;
                    continue;
                }
                if is_bannable_token(w) {
                    let clean = clean_ban_target(w);
                    targets.push(clean.clone());
                    expand_ban(&clean, &mut res.banned);
                    last_target_end = j + 1;
                    j += 1;
                    continue;
                }
                // Unknown noun right after a STRONG trigger: treat as a tool
                // name too (e.g. "tanpa Houdini"), unless it's a style word.
                // Weak cues never reach here (positive evidence required).
                let wc = clean_ban_target(w);
                if !weak_cue && !wc.is_empty() && !STYLE_WORDS.contains(&wc.as_str()) && !is_stopword(&wc)
                    && wc.len() >= 3 && targets.len() < 3 && j == i + tlen
                {
                    targets.push(wc.clone());
                    expand_ban(&wc, &mut res.banned);
                    last_target_end = j + 1;
                    j += 1;
                    continue;
                }
                break;
            }
            if !targets.is_empty() {
                for k in i..last_target_end {
                    banned_idx[k] = true;
                }
                res.removed_fragments.push(words_ref[i..last_target_end].join(" "));
                i = last_target_end;
                continue;
            } else {
                // Style negation ("jgn kaku"): strip the cue + style word so it
                // cannot leak into scoring, but ban nothing.
                let mut k = i + tlen;
                let mut handled = false;
                while k < words_ref.len() && k < i + tlen + 3 {
                    if STYLE_WORDS.contains(&words_ref[k]) {
                        for x in i..=k {
                            banned_idx[x] = true;
                        }
                        res.removed_fragments.push(words_ref[i..=k].join(" "));
                        i = k + 1;
                        handled = true;
                        break;
                    }
                    k += 1;
                }
                if !handled {
                    // Negation cue with no recognizable target: strip the cue only.
                    for x in i..i + tlen {
                        banned_idx[x] = true;
                    }
                    i += tlen;
                }
                continue;
            }
        }
        i += 1;
    }

    // Rebuild sanitized text from the ORIGINAL raw spans, preserving casing and
    // inter-word punctuation (commas/semicolons) so Stage 3 can split on them.
    let kept_indices: Vec<usize> = (0..words_ref.len()).filter(|idx| !banned_idx[*idx]).collect();
    let mut sanitized = String::new();
    for &idx in &kept_indices {
        let (_w, s, e) = &spans[idx];
        sanitized.push_str(&raw[*s..*e]);
        if idx + 1 < spans.len() {
            let next_start = spans[idx + 1].1;
            if !banned_idx[idx + 1] {
                sanitized.push_str(&raw[*e..next_start]);
            } else {
                sanitized.push(' ');
            }
        }
    }
    res.sanitized = sanitized.trim().to_string();
    res
}

// ---------------------------------------------------------------------------
// Stage 3 — multi-clause & multi-job splitter (max 3)
// ---------------------------------------------------------------------------

const CLAUSE_CONNECTORS: &[&str] = &[
    "lalu", "kemudian", "terus", "habis itu", "setelah itu", "lantas", "dan juga",
    "sekaligus", "sambil", "plus", "then", "after that", "and then", "and also",
    "as well as", "followed by",
];

/// Split "1. foo 2. bar 3. baz" / "1) foo 2) bar" into segments (no regex dep).
fn regex_lite_numbered_split(text: &str) -> Vec<String> {
    let bytes = text.as_bytes();
    let mut starts: Vec<usize> = Vec::new();
    let mut i = 0usize;
    while i < bytes.len() {
        if bytes[i].is_ascii_digit() {
            let mut j = i;
            while j < bytes.len() && bytes[j].is_ascii_digit() { j += 1; }
            if j < bytes.len() && (bytes[j] == b'.' || bytes[j] == b')') {
                let at_start = i == 0 || bytes[i - 1].is_ascii_whitespace();
                let after_space = j + 1 >= bytes.len() || bytes[j + 1].is_ascii_whitespace();
                if at_start && after_space {
                    starts.push(i);
                }
            }
            i = j + 1;
        } else {
            i += 1;
        }
    }
    if starts.len() < 2 {
        return vec![text.to_string()];
    }
    let mut out = Vec::new();
    for (k, &s) in starts.iter().enumerate() {
        let e = if k + 1 < starts.len() { starts[k + 1] } else { text.len() };
        let seg = &text[s..e];
        // drop the "N." marker
        let dot = seg.find(|c: char| c == '.' || c == ')').map(|p| p + 1).unwrap_or(0);
        let body = seg[dot..].trim();
        if !body.is_empty() {
            out.push(body.to_string());
        }
    }
    out
}

/// Compound-noun guard: "laba dan rugi", "kelebihan dan kekurangan" are ONE
/// deliverable. If 'dan'/'and' joins two nouns (no action verb on either side
/// within the local window), do not split there.
const COMPOUND_PAIRS: &[(&str, &str)] = &[
    ("laba", "rugi"), ("kelebihan", "kekurangan"), ("pro", "kontra"),
    ("untung", "rugi"), ("debit", "kredit"), ("masuk", "keluar"),
    ("pemasukan", "pengeluaran"), ("pendapatan", "beban"), ("aset", "kewajiban"),
    ("harta", "utang"), ("siang", "malam"), ("pria", "wanita"),
    ("jual", "beli"), ("impor", "ekspor"), ("plus", "minus"),
    (" strengths", "weaknesses"), ("strengths", "weaknesses"), ("pros", "cons"),
    ("income", "expense"), ("assets", "liabilities"), ("debit", "credit"),
    ("untung", "buntung"), ("suka", "duka"), ("naik", "turun"),
];

fn is_compound_join(left: &[String], right: &[String]) -> bool {
    if left.is_empty() || right.is_empty() {
        return false;
    }
    let l = &left[left.len() - 1];
    let r = &right[0];
    for (a, b) in COMPOUND_PAIRS {
        if (l == a && r == b) || (l == b && r == a) {
            return true;
        }
    }
    // Both sides noun-only (no action verb anywhere near) -> single deliverable.
    let l_verb = left.iter().rev().take(3).any(|t| ACTION_VERBS.contains(&t.as_str()));
    let r_verb = right.iter().take(3).any(|t| ACTION_VERBS.contains(&t.as_str()));
    if !l_verb && !r_verb && DELIVERABLE_NOUNS.contains(&l.as_str()) && DELIVERABLE_NOUNS.contains(&r.as_str()) {
        return true;
    }
    false
}

/// Split sanitized text into <=3 sub-clauses. A split is only valid when each
/// segment carries its own action verb or distinct deliverable.
fn split_clauses(text: &str) -> Vec<String> {
    if text.trim().is_empty() {
        return vec![text.to_string()];
    }
    // Fast path: tanpa pemisah klausa (koma/titik-koma/connector/daftar nomor)
    // -> satu klausa. Cek substring dulu (murah); scan daftar nomor hanya
    // bila ada pola digit+titik yang berpotensi jadi penanda daftar.
    let has_sep = text.contains(',') || text.contains(';')
        || CLAUSE_CONNECTORS.iter().any(|c| text.contains(c))
        || (text.contains(". ") && regex_lite_numbered_split(text).len() > 1);
    if !has_sep {
        let n = normalize_for_match(text);
        return if n.is_empty() { vec![text.to_string()] } else { vec![n] };
    }
    // Strip a leading contrast pivot left over from the Stage-2 sieve.
    let text = {
        let t = text.trim();
        let mut s = t;
        for pivot in ["tapi ", "tetapi ", "namun ", "melainkan ", "but ", "however ", "instead "] {
            if let Some(rest) = s.strip_prefix(pivot) {
                s = rest;
                break;
            }
        }
        s
    };
    // STEP A0: numbered lists "1. ... 2. ... 3. ..." are hard boundaries.
    let numbered_re = regex_lite_numbered_split(text);
    let hard: Vec<String> = if numbered_re.len() > 1 {
        numbered_re
    } else {
        text.split(';').map(|s| s.to_string()).collect()
    };
    // STEP A: comma action-list splitting on the RAW text (commas are lost by
    // normalize_for_match, so handle them first). A comma split is kept when
    // the right side carries a job and the left side has a job OR an explicit
    // tool/deliverable object ("ambil data dari PDF, buat grafik, lalu susun slide").
    let mut comma_segments: Vec<String> = Vec::new();
    for seg in hard {
        let pieces: Vec<&str> = seg.split(',').map(|s| s.trim()).filter(|s| !s.is_empty()).collect();
        if pieces.len() <= 1 {
            let n = normalize_for_match(&seg);
            if !n.is_empty() { comma_segments.push(n); }
            continue;
        }
        let mut acc = String::new();
        // Precompute which pieces carry their own job.
        let piece_jobs: Vec<bool> = pieces.iter().map(|piece| {
            let pn = normalize_for_match(piece);
            let pt: Vec<String> = pn.split(' ').map(|s| s.to_string()).collect();
            has_action_verb(&pt) || has_deliverable(&pt)
        }).collect();
        for (pi, piece) in pieces.iter().enumerate() {
            let pn = normalize_for_match(piece);
            if pn.is_empty() { continue; }
            let piece_job = piece_jobs[pi];
            if acc.is_empty() {
                acc = pn;
                continue;
            }
            let at: Vec<String> = acc.split(' ').map(|s| s.to_string()).collect();
            let acc_job = has_action_verb(&at) || has_deliverable(&at) || has_explicit_tool(&at);
            // Split when the accumulator is a complete job AND this piece (or a
            // later piece) starts another job. Handles "ambil data dari PDF,
            // buat grafik tren, lalu susun slide" (3 jobs) while keeping
            // "buat laporan laba dan rugi" (single deliverable) intact.
            let other_job = piece_job || piece_jobs[pi + 1..].iter().any(|&j| j);
            if acc_job && other_job {
                comma_segments.push(acc);
                acc = pn;
            } else {
                acc = format!("{} {}", acc, pn);
            }
        }
        if !acc.is_empty() { comma_segments.push(acc); }
    }

    // STEP B: connector splitting on each normalized segment.
    let mut segments: Vec<String> = Vec::new();
    for seg in comma_segments {
        let mut parts: Vec<String> = vec![seg];
        for conn in CLAUSE_CONNECTORS {
            let needle = format!(" {} ", conn);
            let mut next: Vec<String> = Vec::new();
            for p in parts {
                let mut last = 0usize;
                let mut idx = 0usize;
                let mut found_any = false;
                while let Some(pos) = p[idx..].find(&needle) {
                    let abs = idx + pos;
                    let left = p[last..abs].trim().to_string();
                    let right_start = abs + needle.len();
                    let lt: Vec<String> = left.split(' ').map(|s| s.to_string()).collect();
                    let rt: Vec<String> = p[right_start..].split(' ').map(|s| s.to_string()).collect();
                    let left_job = has_action_verb(&lt) || has_deliverable(&lt);
                    let right_job = has_action_verb(&rt) || has_deliverable(&rt);
                    if !left.is_empty() && left_job && right_job && !is_compound_join(&lt, &rt) {
                        next.push(left);
                        found_any = true;
                        last = right_start;
                    }
                    idx = right_start;
                }
                let tail = p[last..].trim().to_string();
                if !found_any {
                    next.push(p);
                } else if !tail.is_empty() {
                    next.push(tail);
                }
            }
            parts = next.into_iter().filter(|p| !p.is_empty()).collect();
        }
        segments.extend(parts);
    }
    let cleaned = segments;

    // Validity filter: each clause must carry an action verb or a deliverable.
    // Merge fragments without a job into the previous clause.
    // Also merge quantity-spec fragments ("10 slide", "5 halaman", "3 poin")
    // into the previous clause — they specify the SAME deliverable, not a new
    // job (putusan owner I02; must not break D16 "laporan, grafik, dan slide").
    const QUANTITY_UNITS: &[&str] = &[
        "slide", "salindia", "halaman", "poin", "point", "points", "baris",
        "kolom", "paragraf", "kata", "menit", "detik", "lembar", "buah",
        "bab", "bagian", "grafik", "tabel", "gambar", "foto", "video",
    ];
    let is_quantity_spec = |ct: &[String]| -> bool {
        // Pure "<number> <unit> [tail words]" with NO action verb.
        if ct.len() < 2 || has_action_verb(ct) {
            return false;
        }
        let first = ct[0].trim_matches(|c: char| !c.is_ascii_digit());
        !first.is_empty() && first.chars().all(|c| c.is_ascii_digit())
            && QUANTITY_UNITS.contains(&ct[1].as_str())
    };
    let mut valid: Vec<String> = Vec::new();
    for c in cleaned {
        // Strip a leading clause connector left at the segment head.
        let mut c = c.as_str();
        for conn in ["lalu ", "kemudian ", "terus ", "lantas ", "then ", "after that ",
                     "and then ", "and also ", "as well as ", "followed by ", "habis itu ",
                     "setelah itu ", "dan juga ", "sekaligus ", "sambil ", "plus "] {
            if let Some(rest) = c.strip_prefix(conn) {
                c = rest;
                break;
            }
        }
        let c = c.to_string();
        let ct: Vec<String> = c.split(' ').map(|s| s.to_string()).collect();
        let has_job = has_action_verb(&ct) || has_deliverable(&ct);
        if !valid.is_empty() && is_quantity_spec(&ct) {
            if let Some(last) = valid.last_mut() {
                *last = format!("{} {}", last, c);
            }
        } else if has_job || valid.is_empty() {
            valid.push(c);
        } else if let Some(last) = valid.last_mut() {
            *last = format!("{} {}", last, c);
        }
    }
    if valid.is_empty() {
        valid.push(normalize_for_match(text));
    }

    // Cap at 3: merge same-domain extras, else keep the 3 highest-deliverable.
    if valid.len() > 3 {
        let mut scored: Vec<(usize, usize, String)> = valid.iter().enumerate().map(|(i, c)| {
            let ct: Vec<String> = c.split(' ').map(|s| s.to_string()).collect();
            let score = ct.iter().filter(|t| DELIVERABLE_NOUNS.contains(&t.as_str())).count() * 2
                + ct.iter().filter(|t| ACTION_VERBS.contains(&t.as_str())).count();
            (i, score, c.clone())
        }).collect();
        scored.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
        scored.truncate(3);
        scored.sort_by(|a, b| a.0.cmp(&b.0));
        valid = scored.into_iter().map(|(_, _, c)| c).collect();
    }
    valid
}

// ---------------------------------------------------------------------------
// Morphology: KPST stemmer + loanword transliteration (Lapis 1 & 4)
// ---------------------------------------------------------------------------

const ID_SUFFIXES: &[&str] = &["nya", "kan", "lah", "kah", "an", "i"];
const ID_PREFIXES: &[&str] = &[
    "meng", "meny", "men", "mem", "me", "peng", "peny", "pen", "pem", "pe",
    "ber", "ter", "di", "per", "se", "ke", "nge",
];

/// KPST elision candidates (kaidah KBBI): mengelola->kelola, menulis->tulis,
/// menyusun->susun, memindai->pindai, memotong->potong, mengubah->ubah.
/// Candidates are gated against known_vocab by the caller (gate-bearing
/// generator contract: pass the vocab in, never emit ungated stems).
fn kpst_candidates(word: &str, known: &HashSet<String>) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    if word.chars().count() < 5 {
        return out;
    }
    // (prefix, elided consonant, optional extra glide for peN- forms)
    let pairs: &[(&str, char)] = &[
        ("meng", 'k'), ("meny", 's'), ("men", 't'), ("mem", 'p'),
        ("peng", 'k'), ("peny", 's'), ("pen", 't'), ("pem", 'p'),
    ];
    for (pre, restored) in pairs {
        if let Some(rest) = word.strip_prefix(pre) {
            if rest.starts_with(['a', 'e', 'i', 'o', 'u']) {
                let elided = format!("{}{}", restored, rest);
                if elided.chars().count() >= 3 && known.contains(&elided) {
                    out.push(elided);
                }
                // merangkum -> rangkum: 'me' + 'rangkum' (r stays, no elision)
            }
            if rest.chars().count() >= 3 && known.contains(rest) {
                out.push(rest.to_string());
            }
        }
    }
    // me-/pe- + consonant-initial base (merangkum->rangkum, mesures->...).
    for pre in ["me", "pe"] {
        if let Some(rest) = word.strip_prefix(pre) {
            if rest.chars().count() >= 4 && known.contains(rest) && !out.contains(&rest.to_string()) {
                out.push(rest.to_string());
            }
        }
    }
    out
}

/// Strip one suffix then one prefix when the remainder stays plausible and
/// (for prefixes) the base is a known vocab word. Returns gated bases only.
fn strip_affixes(word: &str, known: &HashSet<String>) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    if word.chars().count() < 5 {
        return out;
    }
    // Suffix candidates: -kan / -i / -an / -nya / -lah / -kah. The stripped
    // form is only emitted when it is a known base OR a KPST-restored base.
    let mut suffix_forms: Vec<String> = vec![word.to_string()];
    for suf in ID_SUFFIXES {
        if word.len() > suf.len() + 2 && word.ends_with(suf) {
            let stripped = &word[..word.len() - suf.len()];
            if stripped.chars().count() >= 3 {
                suffix_forms.push(stripped.to_string());
            }
        }
    }
    for form in &suffix_forms {
        // Prefix pass with KPST restoration on the (possibly suffixed) form.
        for base in kpst_candidates(form, known) {
            if !out.contains(&base) {
                out.push(base);
            }
        }
        for pre in ID_PREFIXES {
            if form.len() > pre.len() + 2 && form.starts_with(pre) {
                let stripped = &form[pre.len()..];
                if stripped.chars().count() >= 3 && known.contains(stripped) && !out.contains(&stripped.to_string()) {
                    out.push(stripped.to_string());
                }
            }
        }
        if *form != word && known.contains(form) && !out.contains(form) {
            out.push(form.clone());
        }
    }
    out
}

/// Loanword transliteration shadow tokens (Lapis 4, Zero-RAM rules).
/// -isasi->-ization, -asi->-ation, -isi->-ition, -uksi->-uction,
/// -itas->-ity, -grafi->-graphy, -logi->-logy (+ reverse direction).
fn loanword_shadows(tok: &str) -> Vec<String> {
    let mut out = Vec::new();
    if tok.chars().count() < 6 {
        return out;
    }
    // Longest suffix first: -isasi before -asi; skip -isi when -isasi matched.
    let rules: &[(&str, &str)] = &[
        ("isasi", "ization"), ("isasi", "isation"),
        ("grafi", "graphy"), ("grafik", "graphic"),
        ("uksi", "uction"), ("itas", "ity"), ("logi", "logy"),
        ("asi", "ation"), ("isi", "ition"),
    ];
    let mut matched_isasi = false;
    for (id_suf, en_suf) in rules {
        if *id_suf == "isi" && matched_isasi {
            continue;
        }
        if let Some(stem) = tok.strip_suffix(id_suf) {
            if stem.chars().count() >= 3 {
                let shadow = format!("{}{}", stem, en_suf);
                if !out.contains(&shadow) {
                    out.push(shadow);
                }
                if *id_suf == "isasi" {
                    matched_isasi = true;
                }
            }
        }
    }
    let rev: &[(&str, &str)] = &[
        ("ization", "isasi"), ("isation", "isasi"), ("graphy", "grafi"),
        ("uction", "uksi"), ("ity", "itas"), ("logy", "logi"),
        ("ation", "asi"), ("ition", "isi"),
    ];
    for (en_suf, id_suf) in rev {
        if let Some(stem) = tok.strip_suffix(en_suf) {
            if stem.chars().count() >= 3 {
                out.push(format!("{}{}", stem, id_suf));
            }
        }
    }
    out
}

// ---------------------------------------------------------------------------
// Tokenization & feature extraction
// ---------------------------------------------------------------------------

fn tokenize(slice: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    let mut cur = String::new();
    for ch in slice.chars() {
        if ch.is_alphanumeric() || ch == '-' || ch == '_' || ch == '.' || ch == '+' {
            cur.push(ch.to_ascii_lowercase());
        } else if !cur.is_empty() {
            tokens.push(std::mem::take(&mut cur));
        }
    }
    if !cur.is_empty() {
        tokens.push(cur);
    }
    tokens
}

fn tokenize_capped(slice: &str, cap: usize) -> Vec<String> {
    let mut tokens: Vec<String> = Vec::with_capacity(cap.min(256));
    let mut seen: HashSet<String> = HashSet::new();
    let mut cur = String::new();
    for ch in slice.chars() {
        if ch.is_alphanumeric() || ch == '-' || ch == '_' || ch == '.' || ch == '+' {
            cur.push(ch.to_ascii_lowercase());
        } else if !cur.is_empty() {
            if seen.insert(cur.clone()) {
                tokens.push(std::mem::take(&mut cur));
                if tokens.len() >= cap {
                    return tokens;
                }
            } else {
                cur.clear();
            }
        }
    }
    if !cur.is_empty() && seen.insert(cur.clone()) {
        tokens.push(cur);
    }
    tokens
}

struct Zones {
    /// Full-weight instruction text (tail for long pastes, whole text for short).
    instruction: String,
    /// Reduced-weight leading window (long pastes only).
    head: String,
    payload: String,
}

fn split_zones(raw: &str) -> Zones {
    let total = raw.len();
    if total <= INSTRUCTION_HEAD + INSTRUCTION_TAIL {
        return Zones { instruction: raw.to_string(), head: String::new(), payload: String::new() };
    }
    // Tail window at char boundary.
    let tail_target = total.saturating_sub(INSTRUCTION_TAIL);
    let tail_start = (tail_target..=total)
        .find(|&i| raw.is_char_boundary(i))
        .unwrap_or(total);
    let tail = &raw[tail_start..];
    // Head window at char boundary.
    let head_end = (0..=INSTRUCTION_HEAD.min(total))
        .rev()
        .find(|&i| raw.is_char_boundary(i))
        .unwrap_or(0);
    let head = &raw[..head_end];
    if tail_start > head_end && tail_start - head_end > PAYLOAD_MIN_LEN {
        return Zones {
            instruction: tail.to_string(),
            head: head.to_string(),
            payload: raw[head_end..tail_start].to_string(),
        };
    }
    Zones { instruction: raw.to_string(), head: String::new(), payload: String::new() }
}

/// Apply slang normalization + multi-word phrase expansion to a token stream.
fn lexicon_normalize(tokens: &[String], lex: &Lexicon) -> Vec<String> {
    let mut out: Vec<String> = Vec::with_capacity(tokens.len());
    let mut i = 0usize;
    while i < tokens.len() {
        // Multi-word phrase match (longest first).
        let mut matched = false;
        for (phrase, repl) in &lex.phrases {
            let n = phrase.len();
            if i + n <= tokens.len() && tokens[i..i + n] == phrase[..] {
                out.extend(repl.iter().cloned());
                i += n;
                matched = true;
                break;
            }
        }
        if matched {
            continue;
        }
        let t = &tokens[i];
        if let Some(formal) = lex.slang.get(t) {
            if !formal.is_empty() {
                for w in formal.split(' ') {
                    out.push(w.to_string());
                }
            }
            // drop empty-mapped particles (dong/deh/nih)
        } else {
            out.push(t.clone());
        }
        i += 1;
    }
    out
}

#[derive(Debug, Default)]
struct Extracted {
    features: HashMap<String, f64>,
    active_keys: HashSet<String>,
    all_tokens: HashSet<String>,
    /// Normalized instruction tokens (for mode selection & ambiguity checks).
    norm_tokens: Vec<String>,
    slang_ratio: f64,
}

fn add_features(ex: &mut Extracted, tokens: &[String], weight: f64, dedup: bool,
                known: &HashSet<String>, lex: &Lexicon, bigram_boost: bool) {
    let mut seen: HashSet<String> = HashSet::new();
    for (i, tok) in tokens.iter().enumerate() {
        if is_stopword(tok) {
            continue;
        }
        let key_uni = format!("uni:{}", tok);
        if !(dedup && !seen.insert(key_uni.clone())) {
            *ex.features.entry(key_uni.clone()).or_insert(0.0) += weight;
            ex.active_keys.insert(key_uni);
        }
        ex.all_tokens.insert(tok.clone());

        // Morphology (gated): KPST + affix stripping.
        if tok.chars().count() >= 5 {
            for base in kpst_candidates(tok, known) {
                let key = format!("uni:{}", base);
                if !(dedup && !seen.insert(key.clone())) {
                    *ex.features.entry(key.clone()).or_insert(0.0) += weight * 0.9;
                    ex.active_keys.insert(key);
                }
            }
            for base in strip_affixes(tok, known) {
                if base == *tok {
                    continue;
                }
                let key = format!("uni:{}", base);
                if !(dedup && !seen.insert(key.clone())) {
                    *ex.features.entry(key.clone()).or_insert(0.0) += weight * 0.8;
                    ex.active_keys.insert(key);
                }
            }
        }
        // Loanword transliteration shadows (both directions).
        if tok.chars().count() >= 6 {
            for shadow in loanword_shadows(tok) {
                let key = format!("uni:{}", shadow);
                if !(dedup && !seen.insert(key.clone())) {
                    *ex.features.entry(key.clone()).or_insert(0.0) += weight * 0.7;
                    ex.active_keys.insert(key);
                }
            }
        }
        // Bilingual concept expansion (EN->ID and ID->EN single tokens).
        if let Some(idn) = lex.en_to_id.get(tok) {
            for w in idn.split(' ') {
                let key = format!("uni:{}", w);
                if !(dedup && !seen.insert(key.clone())) {
                    *ex.features.entry(key.clone()).or_insert(0.0) += weight * 0.7;
                    ex.active_keys.insert(key);
                }
            }
        }
        if let Some(ens) = lex.id_to_en.get(tok) {
            for en in ens.iter().take(3) {
                for w in en.split(' ') {
                    let key = format!("uni:{}", w);
                    if !(dedup && !seen.insert(key.clone())) {
                        *ex.features.entry(key.clone()).or_insert(0.0) += weight * 0.7;
                        ex.active_keys.insert(key);
                    }
                }
            }
        }
        // Bigram with next token (2.5x in Mode 1).
        if i + 1 < tokens.len() && !is_stopword(&tokens[i + 1]) {
            let key_bi = format!("bi:{} {}", tok, tokens[i + 1]);
            let bw = if bigram_boost { weight * BIGRAM_BOOST } else { weight * 0.6 };
            if !(dedup && !seen.insert(key_bi.clone())) {
                *ex.features.entry(key_bi.clone()).or_insert(0.0) += bw;
                ex.active_keys.insert(key_bi);
            }
        }
    }
}

fn extract_clause_features(clause: &str, known: &HashSet<String>, lex: &Lexicon,
                           bigram_boost: bool) -> Extracted {
    let mut ex = Extracted::default();
    let zones = split_zones(clause);
    let raw_instr = tokenize(&zones.instruction);
    // Slang ratio measured on raw instruction tokens (before normalization).
    let slang_hits = raw_instr.iter().filter(|t| lex.slang.contains_key(*t)).count();
    ex.slang_ratio = if raw_instr.is_empty() { 0.0 } else { slang_hits as f64 / raw_instr.len() as f64 };
    let instr = lexicon_normalize(&raw_instr, lex);
    ex.norm_tokens = instr.clone();
    add_features(&mut ex, &instr, INSTRUCTION_WEIGHT, false, known, lex, bigram_boost);
    // Reduced-weight leading window (long pastes): keeps a leading instruction
    // detectable without letting payload prose dominate.
    if !zones.head.is_empty() {
        let head_raw = tokenize(&zones.head);
        let head = lexicon_normalize(&head_raw, lex);
        add_features(&mut ex, &head, HEAD_WEIGHT, true, known, lex, false);
    }
    if !zones.payload.is_empty() {
        let payload_raw = tokenize_capped(&zones.payload, PAYLOAD_MAX_TOKENS);
        let payload = lexicon_normalize(&payload_raw, lex);
        add_features(&mut ex, &payload, PAYLOAD_WEIGHT, true, known, lex, false);
    }
    ex
}

// ---------------------------------------------------------------------------
// Stage 4 — dynamic algorithm selector (4 modes) + scoring
// ---------------------------------------------------------------------------

/// Explicit tool/extension cues that force Mode 1.
const EXPLICIT_TOOL_CUES: &[&str] = &[
    ".pdf", ".pptx", ".docx", ".xlsx", ".csv", ".html", ".mp4", ".mp3", ".wav",
    ".svg", ".png", ".jpg", ".json", ".sql", ".tex", ".md",
    "pdf", "pptx", "docx", "xlsx", "csv", "html", "sql", "blender", "ffmpeg",
    "infografis", "infografik", "mece", "mermaid", "excel", "powerpoint",
    "whisper", "midi", "latex", "docker", "react", "houdini", "unreal",
    "dcf", "lbo", "wacc", "irr", "npv", "seo", "osint", "whois", "arxiv",
    "comfyui", "manim", "suno", "figma", "canva", "photoshop", "premiere",
    "capcut", "davinci", "obs", "tableau", "powerbi", "metabase", "superset",
    "jupyter", "pandas", "numpy", "spark", "airflow", "dbt", "kubernetes",
    "terraform", "jenkins", "nginx", "postgres", "mysql", "mongodb", "redis",
];

fn has_explicit_tool(tokens: &[String]) -> bool {
    tokens.iter().any(|t| {
        EXPLICIT_TOOL_CUES.contains(&t.as_str())
            || (t.starts_with('.') && t.len() >= 3)
            || t.contains(".pdf") || t.contains(".pptx") || t.contains(".xlsx")
            || t.contains(".csv") || t.contains(".docx") || t.contains(".html")
    })
}

/// Deterministic mode selection per sub-clause (spec §1.3 table).
fn select_mode(ex: &Extracted, banned_nonempty: bool, has_substitution: bool) -> usize {
    if banned_nonempty || has_substitution {
        return 3; // CONSTRAINT_FILTERED_RERANK
    }
    let n = ex.norm_tokens.iter().filter(|t| !is_stopword(t)).count();
    if n <= 8 || has_explicit_tool(&ex.norm_tokens) {
        return 0; // EXACT_LEXICAL_BM25F
    }
    if !has_explicit_tool(&ex.norm_tokens) && (ex.slang_ratio >= 0.20 || n > 20) {
        return 1; // SEMANTIC_CONCEPT_MNB
    }
    2 // HYBRID_BALANCED
}

const SUBSTITUTION_CUES: &[&str] = &["pengganti", "alternatif", "instead of", "sebagai ganti", "ganti"];

#[derive(Debug, Clone)]
struct Scored {
    class_index: usize,
    score: f64,
}

fn idf(model: &SkillModel, key: &str) -> f64 {
    *model.idf_table.get(key).unwrap_or(&3.0)
}

/// Centroid cosine similarity between the clause feature bag and a category
/// centroid vector (both sparse maps). Returns 0..1.
fn centroid_cosine(ex: &Extracted, centroid: &HashMap<String, f64>) -> f64 {
    if centroid.is_empty() {
        return 0.0;
    }
    let mut dot = 0.0;
    let mut na = 0.0;
    for (k, w) in &ex.features {
        let ww = w * w;
        na += ww;
        if let Some(cw) = centroid.get(k) {
            dot += w * cw;
        }
    }
    let nb: f64 = centroid.values().map(|v| v * v).sum();
    if na <= 0.0 || nb <= 0.0 {
        return 0.0;
    }
    (dot / (na.sqrt() * nb.sqrt())).clamp(0.0, 1.0)
}

/// Score all classes for one clause under the selected mode. Banned classes
/// receive HARD_MASK (-inf) and are excluded from the candidate list entirely.
fn score_clause(
    model: &SkillModel,
    index: &HashMap<String, Vec<(usize, f64, f64)>>,
    ex: &Extracted,
    mode: usize,
    banned: &HashSet<String>,
) -> Vec<Scored> {
    let (w_bm, w_mnb, w_cent) = MODE_WEIGHTS[mode];
    let n_cls = model.classes.len();
    let mut bm25: Vec<f64> = vec![0.0; n_cls];
    let mut mnb: Vec<f64> = vec![0.0; n_cls];
    let mut matched: Vec<bool> = vec![false; n_cls];

    for (key, w) in &ex.features {
        if let Some(postings) = index.get(key) {
            let idf_v = if key.starts_with("uni:") || key.starts_with("bi:") {
                idf(model, key)
            } else {
                0.0
            };
            for &(ci, wcf, lp) in postings {
                matched[ci] = true;
                if idf_v != 0.0 {
                    let class = &model.classes[ci];
                    let norm = 1.0 - B + B * (class.doc_len / model.avg_doc_len.max(1.0));
                    bm25[ci] += w * idf_v * (wcf * (K1 + 1.0)) / (wcf + K1 * norm);
                }
                mnb[ci] += w * (lp - model.classes[ci].default_log_prob);
            }
        }
    }

    let active_n = (ex.active_keys.len().max(1) as f64).sqrt();
    let mut scored: Vec<Scored> = Vec::with_capacity(n_cls);
    for (ci, class) in model.classes.iter().enumerate() {
        // HARD MASK: banned skill or any ban-tag hit -> -inf, never a candidate.
        let name_l = class.name.to_lowercase();
        let is_banned = banned.iter().any(|b| {
            name_l == *b || name_l.contains(b.as_str())
                || class.ban_tags.iter().any(|t| t == b)
                || class.core_keywords.iter().take(4).any(|k| k == b)
        });
        if is_banned {
            continue; // hard mask: excluded from top-k entirely
        }
        if !matched[ci] {
            continue;
        }
        let cent = model.category_centroids.get(&class.category)
            .map(|c| centroid_cosine(ex, c))
            .unwrap_or(0.0);
        let mut combined = w_bm * bm25[ci] + w_mnb * (mnb[ci] / active_n) + w_cent * cent * 10.0;
        // Mode 1 (EXACT_LEXICAL_BM25F): prioritaskan exact match Zona S —
        // bonus kecil untuk overlap nama/ekstensi file (spec §1.3 aturan khusus).
        if mode == 0 {
            combined += 0.8 * zone_s_overlap(class, ex);
        }
        scored.push(Scored { class_index: ci, score: combined });
    }
    // Deterministic ordering: score desc; near-ties broken by Zone-S overlap
    // (name/alias exact hits), then by class index for full determinism.
    scored.sort_by(|a, b| {
        let diff = b.score - a.score;
        if diff.abs() > 1e-9 {
            return diff.partial_cmp(&0.0).unwrap_or(std::cmp::Ordering::Equal);
        }
        let sa = zone_s_overlap(&model.classes[a.class_index], ex);
        let sb = zone_s_overlap(&model.classes[b.class_index], ex);
        sb.partial_cmp(&sa).unwrap_or(std::cmp::Ordering::Equal)
            .then(a.class_index.cmp(&b.class_index))
    });
    scored
}

/// Zone-S overlap: prompt tokens hitting the class name/slug tokens, plus
/// explicit file-format affinity (a ".pdf" filename in the clause strongly
/// indicates the PDF skill). Used as a deterministic tie-breaker and a small
/// Mode-1 bonus (spec: prioritize exact Zone S match).
fn zone_s_overlap(class: &SkillClass, ex: &Extracted) -> f64 {
    let name_tokens: Vec<String> = class.name.to_lowercase()
        .split(|c: char| !c.is_alphanumeric())
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
        .collect();
    let mut hits = 0.0;
    for nt in &name_tokens {
        if nt.len() >= 3 && ex.all_tokens.contains(nt) {
            hits += 1.0;
        }
    }
    // File-extension affinity: token like "laporan_keuangan.pdf" -> "pdf".
    for tok in &ex.all_tokens {
        if let Some(pos) = tok.rfind('.') {
            let ext = &tok[pos + 1..];
            if ext.len() >= 2 && ext.len() <= 5 && name_tokens.iter().any(|nt| nt == ext) {
                hits += 2.0;
            }
        }
    }
    hits
}

/// Top-5 null-anchor softmax over the legal candidates of one clause.
fn softmax_topk(model: &SkillModel, scored: &[Scored]) -> Vec<(usize, f64)> {
    let k = scored.len().min(MAX_CANDIDATES);
    let top = &scored[..k];
    if top.is_empty() {
        return Vec::new();
    }
    let smax = top[0].score;
    if smax <= HARD_MASK / 2.0 || smax <= 0.0 {
        return Vec::new();
    }
    let tau = model.softmax_temperature.max(1e-6);
    let theta = model.null_anchor_score;
    let anchor_exp = ((theta - smax) / tau).exp();
    let mut denom = anchor_exp;
    let mut exps: Vec<(usize, f64)> = Vec::with_capacity(k);
    for s in top.iter() {
        let e = ((s.score - smax) / tau).exp();
        denom += e;
        exps.push((s.class_index, e));
    }
    exps.iter().map(|(ci, e)| (*ci, e / denom)).collect()
}

// ---------------------------------------------------------------------------
// Stage 5 — decision gate, merge & fallback (6 official states)
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize, Clone)]
pub struct ClauseResult {
    pub clause: String,
    pub mode: String,
    pub skill: Option<String>,
    pub probability: f64,
    pub top_score: f64,
}

#[derive(Debug, Serialize)]
pub struct RoutingDecision {
    pub status: String,
    pub skills: Vec<String>,
    pub probabilities: Vec<(String, f64)>,
    pub global_banned_set: Vec<String>,
    pub sanitized_prompt: String,
    pub clauses: Vec<ClauseResult>,
    pub hunt_clauses: Vec<String>,
    pub pinned: Vec<String>,
    pub clarify_note: String,
    pub threshold: f64,
    pub top_score: f64,
}

impl RoutingDecision {
    fn empty(status: &str, threshold: f64) -> RoutingDecision {
        RoutingDecision {
            status: status.into(),
            skills: Vec::new(),
            probabilities: Vec::new(),
            global_banned_set: Vec::new(),
            sanitized_prompt: String::new(),
            clauses: Vec::new(),
            hunt_clauses: Vec::new(),
            pinned: Vec::new(),
            clarify_note: String::new(),
            threshold,
            top_score: 0.0,
        }
    }
}

/// Ambiguity check (spec §1.4 state 6): action verb present but no concrete
/// object/deliverable and nothing attached ("tolong rapikan ini").
fn is_ambiguous_action(tokens: &[String]) -> bool {
    if !has_action_verb(tokens) {
        return false;
    }
    if has_deliverable(tokens) || has_explicit_tool(tokens) {
        return false;
    }
    // Only pronouns/particles/time words as objects -> ambiguous.
    const EMPTY_OBJECTS: &[&str] = &[
        "ini", "itu", "tersebut", "this", "that", "these", "those", "dong", "deh",
        "nih", "sih", "ya", "sekarang", "now", "please", "tolong", "sama", "dan",
        "and", "biar", "agar", "supaya", "yang", "yg", "saja", "aja", "dulu",
        "banget", "bgt", "sekali", "cepat", "cepet", "rapi", "bagus", "bener",
    ];
    let content: Vec<&String> = tokens.iter()
        .filter(|t| !is_stopword(t) && !ACTION_VERBS.contains(&t.as_str()))
        .collect();
    if content.is_empty() {
        return true;
    }
    content.iter().all(|t| EMPTY_OBJECTS.contains(&t.as_str()))
}

// ---------------------------------------------------------------------------
// PyO3 surface
// ---------------------------------------------------------------------------

#[pyclass(module = "hermes_skill_brain")]
pub struct SkillBrain {
    model: RwLock<SkillModel>,
    index: RwLock<HashMap<String, Vec<(usize, f64, f64)>>>,
    lexicon: Lexicon,
}

#[pymethods]
impl SkillBrain {
    #[new]
    fn new() -> Self {
        SkillBrain {
            model: RwLock::new(SkillModel::default()),
            index: RwLock::new(HashMap::new()),
            lexicon: Lexicon::load(),
        }
    }

    fn load_json(&self, json: &str) -> PyResult<bool> {
        let parsed: SkillModel = serde_json::from_str(json)
            .map_err(|e| PyValueError::new_err(format!("invalid skill model json: {e}")))?;
        let mut m = parsed;
        if m.threshold == 0.0 { m.threshold = 0.55; }
        if m.multi_skill_threshold == 0.0 { m.multi_skill_threshold = 0.30; }
        if m.null_anchor_score == 0.0 { m.null_anchor_score = 1.0; }
        if m.softmax_temperature == 0.0 { m.softmax_temperature = 0.85; }
        if m.avg_doc_len == 0.0 { m.avg_doc_len = 1.0; }
        let mut inv: HashMap<String, Vec<(usize, f64, f64)>> = HashMap::new();
        for (ci, class) in m.classes.iter().enumerate() {
            for (key, w) in &class.feature_weights {
                let lp = class.feature_log_probs.get(key).copied().unwrap_or(class.default_log_prob);
                inv.entry(key.clone()).or_default().push((ci, *w, lp));
            }
        }
        {
            let mut guard = self.model.write().map_err(|_| PyValueError::new_err("model lock poisoned"))?;
            *guard = m;
        }
        if let Ok(mut g) = self.index.write() {
            *g = inv;
        }
        Ok(true)
    }

    fn reload(&self, json: &str) -> PyResult<bool> {
        self.load_json(json)
    }

    #[pyo3(signature = (prompt))]
    fn analyze_prompt(&self, py: Python<'_>, prompt: &str) -> PyResult<PyObject> {
        let result = self.analyze_core(prompt);
        to_py_dict(py, &result)
    }

    #[pyo3(signature = (prompt))]
    fn analyze_status(&self, prompt: &str) -> PyResult<String> {
        Ok(self.analyze_core(prompt).status)
    }

    /// Expose the Stage-2 sieve for tests/audits (ban set + sanitized text).
    #[pyo3(signature = (prompt))]
    fn debug_sieve(&self, py: Python<'_>, prompt: &str) -> PyResult<PyObject> {
        let s = global_negation_sieve(prompt);
        let dict = PyDict::new_bound(py);
        let banned: Vec<String> = {
            let mut v: Vec<String> = s.banned.iter().cloned().collect();
            v.sort();
            v
        };
        dict.set_item("global_banned_set", banned)?;
        dict.set_item("sanitized_prompt", s.sanitized.clone())?;
        dict.set_item("removed_fragments", s.removed_fragments.clone())?;
        Ok(dict.into_any().unbind())
    }

    /// Expose the Stage-3 splitter for tests/audits.
    #[pyo3(signature = (prompt))]
    fn debug_split(&self, prompt: &str) -> PyResult<Vec<String>> {
        let s = global_negation_sieve(prompt);
        Ok(split_clauses(&s.sanitized))
    }

    /// Raw top-1 BM25F+MNB score for a probe, WITHOUT Stage-0 gating or ban
    /// masking. Used by trainer ROC calibration (negative probes must be
    /// scored on the same scale as positives).
    #[pyo3(signature = (probe))]
    fn debug_score(&self, probe: &str) -> PyResult<f64> {
        let model = match self.model.read() {
            Ok(g) => g,
            Err(_) => return Ok(0.0),
        };
        let index = match self.index.read() {
            Ok(g) => g,
            Err(_) => return Ok(0.0),
        };
        let ex = extract_clause_features(probe, &model.known_vocab, &self.lexicon, false);
        let empty_ban: HashSet<String> = HashSet::new();
        let scored = score_clause(&model, &index, &ex, 2, &empty_ban);
        Ok(scored.first().map(|s| s.score).unwrap_or(0.0))
    }

    /// Top-k (class_name, raw_score) for a probe under a fixed mode, no gating.
    /// Used by trainer diagnostics and parity measurement.
    #[pyo3(signature = (probe, k=5, mode=2))]
    fn debug_topk(&self, py: Python<'_>, probe: &str, k: usize, mode: usize) -> PyResult<PyObject> {
        let model = match self.model.read() {
            Ok(g) => g,
            Err(_) => return Ok(PyList::empty_bound(py).into_any().unbind()),
        };
        let index = match self.index.read() {
            Ok(g) => g,
            Err(_) => return Ok(PyList::empty_bound(py).into_any().unbind()),
        };
        let ex = extract_clause_features(probe, &model.known_vocab, &self.lexicon, mode == 0);
        let empty_ban: HashSet<String> = HashSet::new();
        let scored = score_clause(&model, &index, &ex, mode.min(3), &empty_ban);
        let out = PyList::empty_bound(py);
        for s in scored.iter().take(k) {
            let pair = PyDict::new_bound(py);
            pair.set_item("name", model.classes[s.class_index].name.clone())?;
            pair.set_item("score", s.score)?;
            out.append(pair)?;
        }
        Ok(out.into_any().unbind())
    }
}

impl SkillBrain {
    fn analyze_core(&self, prompt: &str) -> RoutingDecision {
        let model = match self.model.read() {
            Ok(g) => g,
            Err(_) => return RoutingDecision::empty("NO_SKILL_NEEDED", 0.55),
        };
        let index = match self.index.read() {
            Ok(g) => g,
            Err(_) => return RoutingDecision::empty("NO_SKILL_NEEDED", 0.55),
        };
        let threshold = model.threshold;
        let lex = &self.lexicon;

        // ---- Stage 1 (pins detected first; Stage 0 bypass skips pinned asks) ----
        // For long pastes, structural stages (pin/negation/split) operate on the
        // INSTRUCTION zone (head + tail) only — payload prose is data, not user
        // instructions, and scanning it end-to-end blows the latency budget
        // (spec scenario 9). Short prompts use the full text.
        let lower = prompt.to_lowercase();
        let z0 = split_zones(&lower);
        let has_payload = !z0.payload.is_empty();
        let structural_text: String = if has_payload {
            if z0.head.is_empty() {
                z0.instruction.clone()
            } else {
                format!("{} {}", z0.head, z0.instruction)
            }
        } else {
            lower.clone()
        };
        let pin_res = extract_pins(&structural_text, &model.classes);
        let pins = pin_res.resolved.clone();
        let has_explicit_pin = !pins.is_empty() || pin_res.unknown_count > 0;

        // ---- Stage 0: conversational / meta-query bypass ----
        let head_tokens = tokenize(&structural_text);
        if !has_explicit_pin && is_conversational(&structural_text, &head_tokens) {
            return RoutingDecision::empty("NO_SKILL_NEEDED", threshold);
        }

        // ---- Stage 2: GLOBAL negation sieve (BEFORE split) ----
        // On the original-cased instruction text so orthography is preserved.
        // When pins were detected, run the sieve on the PIN-STRIPPED text so
        // unknown pin names never leak into sanitized/hunt output (H-5).
        let sieve_source: String = if has_explicit_pin {
            pin_res.stripped_text.clone()
        } else if has_payload {
            let zr = split_zones(prompt);
            if zr.head.is_empty() { zr.instruction } else { format!("{} {}", zr.head, zr.instruction) }
        } else {
            prompt.to_string()
        };
        let sieve = global_negation_sieve(&sieve_source);
        let banned = sieve.banned.clone();
        let mut banned_sorted: Vec<String> = banned.iter().cloned().collect();
        banned_sorted.sort();

        // Pinned skills are checked against the ban set (spec Stage 1 note).
        let legal_pins: Vec<String> = pins.iter()
            .filter(|p| {
                let pl = p.to_lowercase();
                !banned.iter().any(|b| pl == *b || pl.contains(b.as_str()))
            })
            .cloned()
            .collect();
        let pin_conflict = !pins.is_empty() && legal_pins.is_empty();

        // ---- Unknown explicit pin (audit S-1/H-5): the requested skill does
        // not exist. NEVER echo the raw name (injection vector). Hunt for a
        // suitable skill when there is an actionable task; otherwise clarify.
        if pin_res.unknown_count > 0 && legal_pins.is_empty() && !pin_conflict {
            let stoks = tokenize(&sieve.sanitized);
            let snorm = lexicon_normalize(&stoks, lex);
            let actionable = has_action_verb(&snorm) || has_deliverable(&snorm)
                || has_action_verb(&stoks) || has_deliverable(&stoks);
            let mut d = RoutingDecision::empty(
                if actionable { "HUNT_NEW_SKILL" } else { "CLARIFY_AMBIGUOUS" }, threshold);
            d.global_banned_set = banned_sorted;
            d.sanitized_prompt = sieve.sanitized.clone();
            if actionable {
                d.hunt_clauses = vec![sieve.sanitized.clone()];
                d.clarify_note = "Skill yang diminta secara eksplisit tidak ditemukan di katalog lokal. Nama tidak diteruskan apa adanya; cari skill yang sesuai untuk pekerjaan ini.".into();
            } else {
                d.clarify_note = "Skill yang diminta secara eksplisit tidak ditemukan dan pekerjaannya belum jelas. Tanyakan skill/pekerjaan mana yang dimaksud.".into();
            }
            return d;
        }

        // ---- Contradiction check (spec state 6): the ONLY requested target is
        // banned, e.g. "buatkan workbook .xlsx tapi dilarang pakai excel/spreadsheet".
        let sanitized_tokens = tokenize(&sieve.sanitized);
        let sanitized_norm = lexicon_normalize(&sanitized_tokens, lex);
        let requested_targets_banned = !banned.is_empty() && {
            // Any explicit deliverable format in the sanitized text that maps
            // into the banned set means the ask contradicts its own constraint.
            sanitized_tokens.iter().any(|t| {
                let clean = clean_ban_target(t);
                banned.contains(&clean) || banned.contains(t)
            })
        };
        if requested_targets_banned || pin_conflict {
            let mut d = RoutingDecision::empty("CLARIFY_AMBIGUOUS", threshold);
            d.global_banned_set = banned_sorted;
            d.sanitized_prompt = sieve.sanitized.clone();
            d.pinned = pins.clone();
            d.clarify_note = "Kontradiksi: deliverable yang diminta termasuk alat/format yang dilarang. Tanyakan alternatif yang diinginkan pengguna.".into();
            return d;
        }

        // ---- Explicit pin shortcut (bypass scoring, spec scenario 8) ----
        if !legal_pins.is_empty() {
            // Mixed pins (some resolved, some unknown): keep the legal pin,
            // hunt for the missing one — never echo the unknown name (A12).
            let mixed = pin_res.unknown_count > 0;
            let mut d = RoutingDecision::empty(
                if mixed { "MATCHED_PARTIAL_AND_HUNT" } else { "MATCHED_SINGLE" }, threshold);
            d.skills = vec![legal_pins[0].clone()];
            d.probabilities = vec![(legal_pins[0].clone(), 1.0)];
            d.global_banned_set = banned_sorted;
            d.sanitized_prompt = sieve.sanitized.clone();
            d.pinned = legal_pins.clone();
            d.top_score = 1.0;
            d.clauses.push(ClauseResult {
                clause: sieve.sanitized.clone(),
                mode: "EXPLICIT_PIN".into(),
                skill: Some(legal_pins[0].clone()),
                probability: 1.0,
                top_score: 1.0,
            });
            if mixed {
                d.hunt_clauses = vec![sieve.sanitized.clone()];
                d.clarify_note = "Sebagian skill yang diminta eksplisit tidak ada di katalog lokal; cari skill untuk bagian pekerjaan yang belum tercakup.".into();
            }
            return d;
        }

        // ---- Stage 3: multi-clause split (max 3) ----
        let clauses = split_clauses(&sieve.sanitized);

        // ---- Ambiguity check on the whole ask (single-clause vague actions) ----
        if clauses.len() == 1 && is_ambiguous_action(&sanitized_norm) {
            let mut d = RoutingDecision::empty("CLARIFY_AMBIGUOUS", threshold);
            d.global_banned_set = banned_sorted;
            d.sanitized_prompt = sieve.sanitized.clone();
            d.clarify_note = "Permintaan aksi terlalu samar: objek/lampiran tidak jelas. Tanyakan apa yang perlu dikerjakan.".into();
            return d;
        }

        // ---- Stage 4: per-clause mode selection + scoring ----
        let has_substitution = SUBSTITUTION_CUES.iter().any(|c| lower.contains(c));
        let mut clause_results: Vec<ClauseResult> = Vec::new();
        let mut matched_skills: Vec<(String, f64)> = Vec::new();
        let mut hunt_clauses: Vec<String> = Vec::new();
        let mut any_directive = false;

        for clause in &clauses {
            let ex = extract_clause_features(clause, &model.known_vocab, lex, false);
            let mode = select_mode(&ex, !banned.is_empty(), has_substitution);
            // Mode 1 re-extracts with bigram boost (spec: prioritize bigram 2.5x).
            let ex = if mode == 0 {
                extract_clause_features(clause, &model.known_vocab, lex, true)
            } else {
                ex
            };
            let ct: Vec<String> = clause.split(' ').map(|s| s.to_string()).collect();
            if has_action_verb(&ct) || has_deliverable(&ct) {
                any_directive = true;
            }
            let scored = score_clause(&model, &index, &ex, mode, &banned);
            let probs = softmax_topk(&model, &scored);
            let top_score = scored.first().map(|s| s.score).unwrap_or(0.0);
            // Decision gate θ₀ (ROC-calibrated) operates on the RAW combined
            // score — scale-free, independent of softmax temperature. The
            // softmax probability is reported for ranking/confidence only.
            let theta0 = model.null_anchor_score;
            let best = scored.first().map(|s| (model.classes[s.class_index].name.clone(), s.score));
            let best_prob = probs.first().map(|(_, p)| *p).unwrap_or(0.0);
            // Unknown-tool detector: role-anchored tool names ("di Houdini",
            // "di SAP2000", "pakai Dragonframe") that no class knows -> hunt
            // this clause even if a generic local skill weakly matches.
            // ALL-CAPS format tokens (PDF, CSV) are exempt; only names with
            // lowercase letters (TitleCase) or digit-suffixed tool names qualify.
            let mut tool_candidates: Vec<String> = Vec::new();
            for (i, t) in ct.iter().enumerate() {
                if i > 0 && matches!(ct[i - 1].as_str(), "di" | "in" | "pakai" | "pake"
                    | "using" | "with" | "via" | "menggunakan" | "software" | "tool") {
                    tool_candidates.push(t.clone());
                }
            }
            let unknown_tool = tool_candidates.iter().any(|raw| {
                let tl = raw.trim_matches(|c: char| !c.is_alphanumeric()).to_lowercase();
                let has_lower = raw.chars().any(|c| c.is_lowercase());
                let has_digit_suffix = raw.chars().any(|c| c.is_ascii_digit())
                    && raw.chars().any(|c| c.is_alphabetic());
                if tl.len() < 3 || !(has_lower || has_digit_suffix)
                    || is_stopword(&tl) || DELIVERABLE_NOUNS.contains(&tl.as_str())
                    || model.known_vocab.contains(&tl) {
                    return false;
                }
                // Hanya periksa kandidat teratas (<=5): bila skill teratas
                // sudah mengenal tool ini, bukan unknown-tool hunt.
                !scored.iter().take(5).any(|s| {
                    let c = &model.classes[s.class_index];
                    c.name.to_lowercase().contains(&tl)
                        || c.core_keywords.iter().any(|k| k == &tl)
                })
            });
            match best {
                Some((name, _s)) if top_score >= theta0 && !unknown_tool => {
                    clause_results.push(ClauseResult {
                        clause: clause.clone(),
                        mode: MODE_NAMES[mode].into(),
                        skill: Some(name.clone()),
                        probability: best_prob,
                        top_score,
                    });
                    matched_skills.push((name, best_prob));
                }
                _ => {
                    clause_results.push(ClauseResult {
                        clause: clause.clone(),
                        mode: MODE_NAMES[mode].into(),
                        skill: None,
                        probability: best_prob,
                        top_score,
                    });
                    // Only hunt when the clause is a real action ask.
                    let cn = lexicon_normalize(&ct, lex);
                    if has_action_verb(&cn) || has_deliverable(&cn) || has_action_verb(&ct) || has_deliverable(&ct) {
                        hunt_clauses.push(clause.clone());
                    }
                }
            }
        }

        // ---- Stage 5: decision gate & merge ----
        // Deduplicate skills, preserve step order.
        let mut ordered: Vec<String> = Vec::new();
        let mut prob_map: Vec<(String, f64)> = Vec::new();
        for (name, p) in &matched_skills {
            if !ordered.contains(name) {
                ordered.push(name.clone());
                prob_map.push((name.clone(), *p));
            }
        }
        let top_score = clause_results.iter().map(|c| c.top_score).fold(0.0f64, f64::max);

        let mut d = RoutingDecision {
            status: String::new(),
            skills: ordered.clone(),
            probabilities: prob_map,
            global_banned_set: banned_sorted,
            sanitized_prompt: sieve.sanitized.clone(),
            clauses: clause_results,
            hunt_clauses: hunt_clauses.clone(),
            pinned: Vec::new(),
            clarify_note: String::new(),
            threshold,
            top_score,
        };

        let n_clauses = clauses.len();
        if !ordered.is_empty() && hunt_clauses.is_empty() {
            d.status = if ordered.len() >= 2 { "MATCHED_MULTI".into() } else { "MATCHED_SINGLE".into() };
        } else if !ordered.is_empty() && !hunt_clauses.is_empty() {
            d.status = "MATCHED_PARTIAL_AND_HUNT".into();
        } else if any_directive && n_clauses >= 1 {
            // Valid action ask but nothing legal passed theta0 (incl. all-banned).
            d.status = "HUNT_NEW_SKILL".into();
            if hunt_clauses.is_empty() {
                d.hunt_clauses = clauses.clone();
            }
        } else {
            d.status = "NO_SKILL_NEEDED".into();
            d.skills.clear();
            d.probabilities.clear();
        }
        d
    }
}

fn to_py_dict(py: Python<'_>, d: &RoutingDecision) -> PyResult<PyObject> {
    let dict = PyDict::new_bound(py);
    dict.set_item("status", d.status.clone())?;
    let skills = PyList::empty_bound(py);
    for s in &d.skills {
        skills.append(s)?;
    }
    dict.set_item("skills", &skills)?;
    let probs = PyDict::new_bound(py);
    for (name, p) in &d.probabilities {
        probs.set_item(name, *p)?;
    }
    dict.set_item("probabilities", &probs)?;
    let banned = PyList::empty_bound(py);
    for b in &d.global_banned_set {
        banned.append(b)?;
    }
    dict.set_item("global_banned_set", &banned)?;
    dict.set_item("sanitized_prompt", d.sanitized_prompt.clone())?;
    let clauses = PyList::empty_bound(py);
    for c in &d.clauses {
        let cd = PyDict::new_bound(py);
        cd.set_item("clause", c.clause.clone())?;
        cd.set_item("mode", c.mode.clone())?;
        cd.set_item("skill", c.skill.clone())?;
        cd.set_item("probability", c.probability)?;
        cd.set_item("top_score", c.top_score)?;
        clauses.append(cd)?;
    }
    dict.set_item("clauses", &clauses)?;
    let hunts = PyList::empty_bound(py);
    for h in &d.hunt_clauses {
        hunts.append(h)?;
    }
    dict.set_item("hunt_clauses", &hunts)?;
    let pinned = PyList::empty_bound(py);
    for p in &d.pinned {
        pinned.append(p)?;
    }
    dict.set_item("pinned", &pinned)?;
    dict.set_item("clarify_note", d.clarify_note.clone())?;
    dict.set_item("threshold", d.threshold)?;
    dict.set_item("top_score", d.top_score)?;
    Ok(dict.into_any().unbind())
}

#[pymodule]
fn hermes_skill_brain(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<SkillBrain>()?;
    m.add_function(wrap_pyfunction!(py_kpst_candidates, m)?)?;
    m.add_function(wrap_pyfunction!(py_loanword_shadows, m)?)?;
    m.add_function(wrap_pyfunction!(py_strip_affixes, m)?)?;
    Ok(())
}

#[pyfunction]
fn py_kpst_candidates(word: &str, known: Vec<String>) -> Vec<String> {
    let set: HashSet<String> = known.into_iter().collect();
    kpst_candidates(word, &set)
}

#[pyfunction]
fn py_loanword_shadows(tok: &str) -> Vec<String> {
    loanword_shadows(tok)
}

#[pyfunction]
fn py_strip_affixes(word: &str, known: Vec<String>) -> Vec<String> {
    let set: HashSet<String> = known.into_iter().collect();
    strip_affixes(word, &set)
}