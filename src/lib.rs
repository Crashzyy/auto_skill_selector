//! hermes_skill_brain — Rust core engine for the Hermes `auto_skill_selector` plugin.
//!
//! Implements the 5-layer domain-agnostic prompt -> skill router described in the
//! auto_skill_selector spec:
//!   1. Positional zone splitter + orthographic cue extractor
//!   2. Morphological normalization (ID/EN) + short-acronym shield
//!   3. Interaction posture + clause-boundary negation state machine + role anchors
//!   4. Hybrid log-linear scoring (BM25F + calibrated MNB + Dice trigram) + domain/momentum
//!   5. Scale-free Top-5 null-anchor softmax + routing decision
//!
//! Hard rules honoured here:
//!   * Never panic on user input (no `unwrap()` on externally-sourced data).
//!   * No character trigrams for tokens of length <= 3.
//!   * Softmax only ever over the Top-5 candidates against a null anchor.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::sync::RwLock;

// ---------------------------------------------------------------------------
// Data schema (matches skill_model.json written by trainer.py)
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
    #[serde(default)]
    pub classes: Vec<SkillClass>,
    #[serde(default)]
    pub enable_multi_skill: bool,
}

// --- Tunable constants (spec Bagian 5) ---
const K1: f64 = 1.2;
const B: f64 = 0.75;
const ROLE_MULTIPLIER: f64 = 1.6;
const DOMAIN_AFFINITY_BOOST: f64 = 1.18;
const SESSION_MOMENTUM: f64 = 0.45;
const FUZZY_DICE_MIN: f64 = 0.55;
const FUZZY_DICE_GAIN: f64 = 2.5;
const NEGATION_PENALTY: f64 = -1e9;

const INSTRUCTION_HEAD: usize = 200;
const INSTRUCTION_TAIL: usize = 150;
const PAYLOAD_MIN_LEN: usize = 300;
const PAYLOAD_WEIGHT: f64 = 0.15;
const INSTRUCTION_WEIGHT: f64 = 1.0;

const MAX_CANDIDATES: usize = 5;
const MULTI_P1: f64 = 0.42;
const MULTI_P2: f64 = 0.30;
const MULTI_SUM: f64 = 0.72;

// Bilingual stopword set — kept small; these never become role-anchored unknowns.
const STOPWORDS: &[&str] = &[
    "yang", "dan", "atau", "dengan", "untuk", "dari", "pada", "adalah", "itu", "ini", "saya",
    "aku", "kamu", "kita", "mereka", "dia", "nya", "the", "a", "an", "and", "or", "with", "for",
    "from", "to", "of", "in", "on", "is", "are", "be", "this", "that", "i", "you", "we", "they",
    "it", "my", "your", "our", "please", "tolong", "bantu", "bantu saya", "coba", "mau", "ingin",
];

fn is_stopword(w: &str) -> bool {
    STOPWORDS.contains(&w)
}

// ---------------------------------------------------------------------------
// Lexical sets for posture / negation / role anchors
// ---------------------------------------------------------------------------

const BRAINSTORM_PHRASES: &[&str] = &[
    "jangan langsung", "brainstorming", "diskusi dulu", "menurutmu", "apa pendapatmu",
    "lebih bagus mana", "apa bedanya", "jelaskan pengertian", "kenapa ya", "what do you think",
    "let's brainstorm", "lets brainstorm", "compare between", "dont write code",
    "jangan buat kode", "kita diskusi", "bahas dulu",
];

const DIRECTIVE_VERBS: &[&str] = &[
    "buatkan", "buat", "susun", "rancang", "generate", "render", "konversi", "ubah", "analisis",
    "audit", "jalankan", "deploy", "setup", "edit", "perbaiki", "ekstrak", "hitung",
    "simulasikan", "tulis", "tuliskan", "ringkas", "create", "build", "make", "convert", "fix",
    "extract", "write", "run", "automate", "optimize", "desain", "design", "buatlah",
];

const NEGATION_CUES: &[&str] = &[
    "jangan", "tanpa", "bukan", "tidak", "gak", "enggak", "nggak", "hindari", "abaikan", "not",
    "without", "dont", "never", "avoid", "skip", "exclude", "jangan pakai",
];

const CONTRAST_PIVOTS: &[&str] = &[
    "tapi", "namun", "melainkan", "kecuali", "sebaliknya", "but", "however", "instead", "rather",
];

const ROLE_ANCHOR_WORDS: &[&str] = &[
    "pakai", "menggunakan", "metode", "teknik", "gaya", "bergaya", "format", "aplikasi",
    "software", "tool", "framework", "plugin", "standar", "via", "ala", "berbasis", "using",
    "with", "style", "method",
];

const DELIVERABLE_NOUNS: &[&str] = &[
    "video", "animasi", "3d", "desain", "dokumen", "laporan", "slide", "presentasi", "musik",
    "lagu", "komik", "infografis", "strategi", "model", "jadwal", "aplikasi", "script",
    "workflow", "storyboard", "render", "poster",
];

// ID/EN affixes (spec Tahap 2). Applied only when the remainder keeps >= 4 chars.
const ID_SUFFIXES: &[&str] = &["nya", "kan", "an", "in", "lah", "kah"];
const ID_PREFIXES: &[&str] = &[
    "nge", "di", "ke", "se", "ber", "ter", "per", "me", "mem", "men", "meng", "meny",
];

/// Strip a single Indonesian affix (one suffix then one prefix) when the remainder stays >= 4.
pub fn strip_indonesian_affixes(word: &str) -> Option<String> {
    if word.len() < 5 {
        return None;
    }
    let mut cur = word.to_string();
    // Suffix pass
    for suf in ID_SUFFIXES {
        if cur.len() > suf.len() && cur.ends_with(suf) {
            let stripped = cur[..cur.len() - suf.len()].to_string();
            if stripped.chars().count() >= 4 {
                cur = stripped;
                break;
            }
        }
    }
    // Prefix pass
    for pre in ID_PREFIXES {
        if cur.len() > pre.len() && cur.starts_with(pre) {
            let stripped = cur[pre.len()..].to_string();
            // Require the remainder to look like a plausible base (>= 4 chars)
            if stripped.chars().count() >= 4 {
                cur = stripped;
                break;
            }
        }
    }
    if cur == word {
        None
    } else {
        Some(cur)
    }
}

// ---------------------------------------------------------------------------
// Feature extraction result (shared by scoring)
// ---------------------------------------------------------------------------

#[derive(Debug, Default)]
struct Extracted {
    /// Feature key -> accumulated weight (instruction + payload already weighted).
    features: HashMap<String, f64>,
    /// Active feature keys for MNB length-normalization (deduped).
    active_keys: HashSet<String>,
    orthographic_entities: HashSet<String>,
    negated_tokens: HashSet<String>,
    role_anchored_unknown: HashSet<String>,
    /// Lowercased tokens in instruction zone only (for posture / domain affinity).
    instruction_tokens: Vec<String>,
    /// All lowercased tokens (dedup) for fuzzy + domain checks.
    all_tokens: HashSet<String>,
}

/// Character trigram set for a word of length >= 4, padded with '#'.
fn trigrams(word: &str) -> HashSet<String> {
    let mut set = HashSet::new();
    let padded = format!("#{}#", word);
    let chars: Vec<char> = padded.chars().collect();
    if chars.len() < 3 {
        return set;
    }
    for w in chars.windows(3) {
        set.insert(w.iter().collect::<String>());
    }
    set
}

fn dice(a: &HashSet<String>, b: &HashSet<String>) -> f64 {
    if a.is_empty() || b.is_empty() {
        return 0.0;
    }
    let inter = a.intersection(b).count() as f64;
    2.0 * inter / (a.len() as f64 + b.len() as f64)
}

/// Does an ASCII letter follow `i`? Used to distinguish word-initial caps.
fn char_at(s: &[u8], i: usize) -> Option<u8> {
    s.get(i).copied()
}

/// Extract orthographic entities (TitleCase / MixedCase / ALL-CAPS) from RAW text
/// before any lowercasing, skipping the first word of the string.
fn extract_orthographic(raw: &str) -> HashSet<String> {
    let mut out = HashSet::new();
    let bytes = raw.as_bytes();
    let mut word_start: Option<usize> = None;
    let mut word = String::new();
    let mut word_index: usize = 0; // 0-based index of whitespace-delimited token

    let mut flush = |word: &mut String, idx: usize, out: &mut HashSet<String>| {
        if !word.is_empty() {
            let chars: Vec<char> = word.chars().collect();
            let letters: Vec<char> = chars.iter().copied().filter(|c| c.is_alphabetic()).collect();
            if !letters.is_empty() {
                let upper = letters.iter().filter(|c| c.is_uppercase()).count();
                let lower = letters.iter().filter(|c| c.is_lowercase()).count();
                let is_title = letters[0].is_uppercase() && lower > 0 && upper == 1;
                let is_mixed = upper > 0 && lower > 0;
                let is_allcaps = letters.len() >= 2 && lower == 0 && upper >= 2;
                if idx > 0 && (is_title || is_mixed || is_allcaps) {
                    out.insert(word.clone());
                }
            }
        }
        word.clear();
    };

    for (i, ch) in raw.char_indices() {
        if ch.is_alphanumeric() || ch == '-' || ch == '_' || ch == '.' {
            if word_start.is_none() {
                word_start = Some(i);
            }
            word.push(ch);
        } else {
            if !word.is_empty() {
                flush(&mut word, word_index, &mut out);
                word_index += 1;
                word_start = None;
            }
        }
        let _ = char_at(bytes, i); // keep bytes used (no-op, avoids unused warnings)
    }
    if !word.is_empty() {
        flush(&mut word, word_index, &mut out);
    }
    out
}

// ---------------------------------------------------------------------------
// Tahap 1-3: zone splitting + tokenization + posture + negation + role anchors
// ---------------------------------------------------------------------------

struct Zones {
    instruction: String,
    payload: String,
}

/// Split raw prompt into an instruction zone (first 200 + last 150 chars, weight 1.0)
/// and a payload zone (long middle, weight 0.15, deduplicated).
fn split_zones(raw: &str) -> Zones {
    let chars: Vec<char> = raw.chars().collect();
    let n = chars.len();
    if n <= INSTRUCTION_HEAD + INSTRUCTION_TAIL {
        // Whole text is instruction; no payload zone.
        return Zones { instruction: raw.to_string(), payload: String::new() };
    }
    let head: String = chars[..INSTRUCTION_HEAD].iter().collect();
    let tail: String = chars[n.saturating_sub(INSTRUCTION_TAIL)..].iter().collect();
    let middle_start = INSTRUCTION_HEAD;
    let middle_end = n.saturating_sub(INSTRUCTION_TAIL);
    let middle: String = chars[middle_start..middle_end].iter().collect();
    if middle.chars().count() > PAYLOAD_MIN_LEN {
        Zones { instruction: format!("{} {}", head, tail), payload: middle }
    } else {
        // Middle too short to be a payload: treat everything as instruction.
        Zones { instruction: raw.to_string(), payload: String::new() }
    }
}

/// Tokenize a slice: lowercase ASCII-ish alphanumerics, keep `- _ . +` inside words.
/// Returns (token, was_in_raw_with_caps) — we lowercase here; caps handled separately.
fn tokenize(slice: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    let mut cur = String::new();
    for ch in slice.chars() {
        if ch.is_alphanumeric() || ch == '-' || ch == '_' || ch == '.' || ch == '+' {
            cur.push(ch.to_ascii_lowercase());
        } else {
            if !cur.is_empty() {
                tokens.push(std::mem::take(&mut cur));
            }
        }
    }
    if !cur.is_empty() {
        tokens.push(cur);
    }
    tokens
}

/// Build the `Extracted` feature bag from a raw prompt.
fn extract_features(raw: &str) -> Extracted {
    let mut ex = Extracted::default();
    let zones = split_zones(raw);

    // Orthographic cues come from RAW text, before lowercasing.
    ex.orthographic_entities = extract_orthographic(raw);

    // Combined text for posture/negation is instruction-priority; payload still tokenized
    // but its features are weighted down and deduplicated.
    let instr_tokens = tokenize(&zones.instruction);
    let payload_tokens = tokenize(&zones.payload);

    // ---- Posture detection (instruction zone) ----
    let instr_lower = zones.instruction.to_lowercase();
    let brainstorm_hit = BRAINSTORM_PHRASES.iter().any(|p| instr_lower.contains(p));
    // explicit "pakai skill X" overrides the bypass
    let explicit_skill_request = instr_lower.contains("pakai skill")
        || instr_lower.contains("gunakan skill")
        || instr_lower.contains("use skill")
        || instr_lower.contains("with skill");
    let directive_hit = instr_tokens.iter().any(|t| DIRECTIVE_VERBS.contains(&t.as_str()));

    // Expose posture via instruction tokens marker for the caller (analyze_prompt re-derives).
    // We store posture signals in instruction_tokens flags through a side channel:
    // (kept simple: caller recomputes from raw text; here we only record brainstorm/directive).
    ex.instruction_tokens = instr_tokens.clone();
    let _ = (brainstorm_hit, directive_hit, explicit_skill_request);

    // ---- Clause-aware negation + role anchors over instruction tokens ----
    let mut negation_window: i32 = 0;
    let mut prev_role_anchor = false;
    for tok in &instr_tokens {
        if CONTRAST_PIVOTS.contains(&tok.as_str()) || tok == "," || tok == "." {
            negation_window = 0;
        }
        if NEGATION_CUES.contains(&tok.as_str()) {
            negation_window = 3;
            prev_role_anchor = false;
            continue;
        }
        if negation_window > 0 {
            ex.negated_tokens.insert(tok.clone());
            negation_window -= 1;
            prev_role_anchor = false;
            continue;
        }
        // Role anchor capture: token right after an anchor word gets a multiplier.
        if prev_role_anchor {
            ex.features.insert(format!("uni:{}", tok), ROLE_MULTIPLIER);
            ex.active_keys.insert(format!("uni:{}", tok));
            if !ex.all_tokens.contains(tok) && !is_stopword(tok) {
                ex.role_anchored_unknown.insert(tok.clone());
            }
            prev_role_anchor = false;
        }
        if ROLE_ANCHOR_WORDS.contains(&tok.as_str()) {
            prev_role_anchor = true;
        }
        ex.all_tokens.insert(tok.clone());
    }

    // ---- Build weighted features (instruction weight 1.0, payload weight 0.15 dedup) ----
    // Negated tokens are excluded from POSITIVE features; they are recorded separately.
    let negated_snapshot: HashSet<String> = ex.negated_tokens.clone();
    add_token_features(&mut ex, &instr_tokens, INSTRUCTION_WEIGHT, false, &negated_snapshot);
    if !payload_tokens.is_empty() {
        let neg_empty: HashSet<String> = HashSet::new();
        add_token_features(&mut ex, &payload_tokens, PAYLOAD_WEIGHT, true, &neg_empty);
    }
    ex
}

/// Add unigram/bigram/trigram features for a list of tokens with a zone weight.
/// `dedup` (payload) counts each feature at most once from this zone.
/// `skip` excludes tokens (negated) from positive features entirely.
fn add_token_features(ex: &mut Extracted, tokens: &[String], weight: f64, dedup: bool, skip: &HashSet<String>) {
    let mut seen: HashSet<String> = HashSet::new();
    for (i, tok) in tokens.iter().enumerate() {
        if skip.contains(tok) {
            continue;
        }
        let key_uni = format!("uni:{}", tok);
        if !(dedup && !seen.insert(key_uni.clone())) {
            *ex.features.entry(key_uni.clone()).or_insert(0.0) += weight;
            ex.active_keys.insert(key_uni);
        }

        // Morphology: if stripping affixes changes the word, add BOTH forms.
        if let Some(base) = strip_indonesian_affixes(tok) {
            if base != *tok {
                let key_base = format!("uni:{}", base);
                if !(dedup && !seen.insert(key_base.clone())) {
                    *ex.features.entry(key_base.clone()).or_insert(0.0) += weight * 0.8;
                    ex.active_keys.insert(key_base);
                }
            }
        }

        // Short-acronym shield: uni only, NEVER a trigram, for len 2..=3.
        let char_len = tok.chars().count();
        if char_len >= 2 && char_len <= 3 {
            // already added as uni above; explicitly no tri for short tokens
        } else if char_len >= 4 {
            for tg in trigrams(tok) {
                let key = format!("tri:{}", tg);
                if !(dedup && !seen.insert(key.clone())) {
                    *ex.features.entry(key.clone()).or_insert(0.0) += weight * 0.3;
                    ex.active_keys.insert(key);
                }
            }
        }

        // Bigram with the next token.
        if i + 1 < tokens.len() && !skip.contains(&tokens[i + 1]) {
            let key_bi = format!("bi:{} {}", tok, tokens[i + 1]);
            if !(dedup && !seen.insert(key_bi.clone())) {
                *ex.features.entry(key_bi.clone()).or_insert(0.0) += weight * 0.6;
                ex.active_keys.insert(key_bi);
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Tahap 4: Hybrid log-linear scoring per class
// ---------------------------------------------------------------------------

fn idf(model: &SkillModel, key: &str) -> f64 {
    *model.idf_table.get(key).unwrap_or(&3.0)
}

/// Domain affinity: which category best matches the prompt tokens (0.0..=1.0 affinity ratio).
fn best_category(model: &SkillModel, tokens: &HashSet<String>) -> (String, f64) {
    let mut best = (String::new(), 0.0f64);
    for (cat, cat_tokens) in &model.category_tokens {
        let hits = cat_tokens.iter().filter(|ct| tokens.contains(*ct)).count() as f64;
        let total = cat_tokens.len().max(1) as f64;
        let ratio = hits / total.sqrt();
        if ratio > best.1 {
            best = (cat.clone(), ratio);
        }
    }
    best
}

#[derive(Debug, Clone)]
struct Scored {
    class_index: usize,
    score: f64,
}

/// Score every class for the extracted feature bag.
fn score_all(
    model: &SkillModel,
    ex: &Extracted,
    recent_skills: &HashSet<String>,
    kw_trigram_cache: &mut HashMap<String, HashSet<String>>,
) -> Vec<Scored> {
    let (best_cat, _ratio) = best_category(model, &ex.all_tokens);
    let active_n = (ex.active_keys.len().max(1) as f64).sqrt();

    // Pre-compute trigrams ONCE for every long, unknown token (typo candidates).
    // Avoids recomputing the same word's trigrams for every class.
    let mut typo_candidates: Vec<(String, HashSet<String>)> = Vec::new();
    for tok in &ex.all_tokens {
        if tok.chars().count() >= 4 && !model.known_vocab.contains(tok) {
            typo_candidates.push((tok.clone(), trigrams(tok)));
        }
    }

    let mut scored: Vec<Scored> = Vec::with_capacity(model.classes.len());
    for (ci, class) in model.classes.iter().enumerate() {
        // 1) Negation penalty: any core keyword that is negated kills the class.
        let neg_hit = class.core_keywords.iter().any(|kw| ex.negated_tokens.contains(kw));
        if neg_hit {
            scored.push(Scored { class_index: ci, score: NEGATION_PENALTY });
            continue;
        }

        // 2) BM25F — iterate the prompt features (small), look up per-class weight.
        let mut bm25 = 0.0f64;
        let mut mnb = 0.0f64;
        let mut any_match = false;
        for (key, w) in &ex.features {
            if let Some(wcf) = class.feature_weights.get(key) {
                any_match = true;
                if key.starts_with("uni:") || key.starts_with("bi:") {
                    let idf_v = idf(model, key);
                    let norm = 1.0 - B + B * (class.doc_len / model.avg_doc_len.max(1.0));
                    bm25 += w * idf_v * (wcf * (K1 + 1.0)) / (wcf + K1 * norm);
                }
                if let Some(lp) = class.feature_log_probs.get(key) {
                    mnb += w * (lp - class.default_log_prob);
                }
            }
        }
        // Fast path: no feature of this prompt matches this class at all — skip
        // the (relatively expensive) fuzzy stage entirely.
        if !any_match && typo_candidates.is_empty() {
            let combined = 0.55 * bm25 + 0.30 * mnb;
            if recent_skills.contains(&class.name) {
                scored.push(Scored { class_index: ci, score: combined + SESSION_MOMENTUM });
            }
            continue;
        }
        mnb /= active_n;

        // 4) Fuzzy trigram Dice for typo resilience. Only when there are long,
        //    unknown prompt tokens (typo candidates). Keyword trigram sets are
        //    cached across classes so we never recompute the same keyword twice.
        let mut fuzzy = 0.0f64;
        if !typo_candidates.is_empty() && !class.core_keywords.is_empty() {
            for (_tok, tq) in &typo_candidates {
                let mut best_dice = 0.0f64;
                for kw in &class.core_keywords {
                    if kw.chars().count() < 4 {
                        continue;
                    }
                    let tk = kw_trigram_cache.entry(kw.clone()).or_insert_with(|| trigrams(kw));
                    let d = dice(tq, tk);
                    if d > best_dice {
                        best_dice = d;
                    }
                }
                if best_dice >= FUZZY_DICE_MIN {
                    fuzzy += best_dice * FUZZY_DICE_GAIN;
                }
            }
        }

        // 5) Combine + boosts
        let mut combined = 0.55 * bm25 + 0.30 * mnb + 0.15 * fuzzy;
        if !best_cat.is_empty() && &class.category == &best_cat {
            combined *= DOMAIN_AFFINITY_BOOST;
        }
        if recent_skills.contains(&class.name) {
            combined += SESSION_MOMENTUM;
        }
        scored.push(Scored { class_index: ci, score: combined });
    }
    scored
}

// ---------------------------------------------------------------------------
// Tahap 5: Top-5 null-anchor softmax + routing decision
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize)]
pub struct RoutingDecision {
    pub status: String, // MATCHED_LOCAL | MATCHED_MULTI | NEEDS_INTERNET_SEARCH | NO_SKILL_NEEDED
    pub posture: String, // directive | conversational
    pub skills: Vec<String>,
    pub probabilities: Vec<(String, f64)>,
    pub unknown_entities: Vec<String>,
    pub threshold: f64,
    pub top_score: f64,
}

fn softmax_topk(
    model: &SkillModel,
    scored: &mut Vec<Scored>,
) -> Vec<(usize, f64)> {
    scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
    let k = scored.len().min(MAX_CANDIDATES);
    let top: &[Scored] = &scored[..k];
    if top.is_empty() {
        return Vec::new();
    }
    let smax = top[0].score;
    // Guard: if the top score is catastrophically negative (all classes negated), return empty.
    if smax <= NEGATION_PENALTY / 2.0 {
        return Vec::new();
    }
    let tau = model.softmax_temperature.max(1e-6);
    let theta = model.null_anchor_score;
    let mut exps: Vec<(usize, f64)> = Vec::with_capacity(k + 1);
    let anchor_exp = ((theta - smax) / tau).exp();
    let mut denom = anchor_exp;
    for s in top.iter() {
        let e = ((s.score - smax) / tau).exp();
        denom += e;
        exps.push((s.class_index, e));
    }
    exps.iter().map(|(ci, e)| (*ci, e / denom)).collect()
}

/// Decide routing from the probability distribution.
fn decide(
    model: &SkillModel,
    probs: &[(usize, f64)],
    posture: &str,
    ex: &Extracted,
) -> RoutingDecision {
    let threshold = model.threshold;
    let empty = Vec::new();
    let cls = |i: usize| model.classes.get(i).map(|c| c.name.clone()).unwrap_or_default();

    if probs.is_empty() {
        return RoutingDecision {
            status: "NO_SKILL_NEEDED".into(),
            posture: posture.into(),
            skills: empty,
            probabilities: Vec::new(),
            unknown_entities: Vec::new(),
            threshold,
            top_score: 0.0,
        };
    }

    let p1 = probs[0].1;
    let name1 = cls(probs[0].0);
    let top_score = model.classes.get(probs[0].0).map(|_| p1).unwrap_or(0.0);
    let prob_pairs: Vec<(String, f64)> =
        probs.iter().map(|(ci, p)| (cls(*ci), *p)).collect();

    // MATCHED_MULTI
    if model.enable_multi_skill && probs.len() >= 2 {
        let p2 = probs[1].1;
        let name2 = cls(probs[1].0);
        if p1 >= MULTI_P1 && p2 >= MULTI_P2 && (p1 + p2) >= MULTI_SUM {
            return RoutingDecision {
                status: "MATCHED_MULTI".into(),
                posture: posture.into(),
                skills: vec![name1, name2],
                probabilities: prob_pairs,
                unknown_entities: Vec::new(),
                threshold,
                top_score: p1,
            };
        }
    }

    // MATCHED_LOCAL
    if p1 >= threshold {
        return RoutingDecision {
            status: "MATCHED_LOCAL".into(),
            posture: posture.into(),
            skills: vec![name1],
            probabilities: prob_pairs,
            unknown_entities: Vec::new(),
            threshold,
            top_score: p1,
        };
    }

    // NEEDS_INTERNET_SEARCH (directive posture + unknown entity + deliverable noun).
    // Gated on a low P1: if a local skill already scores at/above the multi-skill
    // floor, we prefer the local match over hunting the internet.
    if posture == "directive" && p1 < MULTI_P1 {
        let has_deliverable = ex.all_tokens.iter().any(|t| DELIVERABLE_NOUNS.contains(&t.as_str()));
        let mut unknowns: Vec<String> = Vec::new();
        for e in &ex.role_anchored_unknown {
            unknowns.push(e.clone());
        }
        if !ex.orthographic_entities.is_empty() && has_deliverable {
            for e in &ex.orthographic_entities {
                if !model.known_vocab.contains(&e.to_lowercase()) {
                    unknowns.push(e.clone());
                }
            }
        }
        if !unknowns.is_empty() && (has_deliverable || !ex.role_anchored_unknown.is_empty()) {
            let mut seen = HashSet::new();
            unknowns.retain(|u| seen.insert(u.clone()));
            return RoutingDecision {
                status: "NEEDS_INTERNET_SEARCH".into(),
                posture: posture.into(),
                skills: Vec::new(),
                probabilities: prob_pairs,
                unknown_entities: unknowns,
                threshold,
                top_score: p1,
            };
        }
    }

    RoutingDecision {
        status: "NO_SKILL_NEEDED".into(),
        posture: posture.into(),
        skills: Vec::new(),
        probabilities: prob_pairs,
        unknown_entities: Vec::new(),
        threshold,
        top_score: p1,
    }
}

/// Determine interaction posture from the raw prompt.
fn detect_posture(raw: &str) -> &'static str {
    let lower = raw.to_lowercase();
    // Explicit skill request always wins.
    let explicit = lower.contains("pakai skill")
        || lower.contains("gunakan skill")
        || lower.contains("use skill")
        || lower.contains("with skill")
        || lower.contains("pakai skill:");
    if explicit {
        return "directive";
    }
    let brainstorm = BRAINSTORM_PHRASES.iter().any(|p| lower.contains(p));
    let directive = tokenize(raw).iter().any(|t| DIRECTIVE_VERBS.contains(&t.as_str()));
    // Brainstorming beats a weak directive signal: a conversational opener
    // ("menurutmu", "jangan langsung", "lebih bagus mana") means the user wants
    // a discussion, even if a directive verb appears mid-sentence.
    if brainstorm {
        return "conversational";
    }
    if directive {
        return "directive";
    }
    "neutral"
}

// ---------------------------------------------------------------------------
// PyO3 module surface
// ---------------------------------------------------------------------------

#[pyclass(module = "hermes_skill_brain")]
pub struct SkillBrain {
    model: RwLock<SkillModel>,
    recent_skills: RwLock<HashSet<String>>,
}

#[pymethods]
impl SkillBrain {
    #[new]
    fn new() -> Self {
        SkillBrain {
            model: RwLock::new(SkillModel::default()),
            recent_skills: RwLock::new(HashSet::new()),
        }
    }

    /// Load (or reload) the model from a JSON string. Returns True on success.
    fn load_json(&self, json: &str) -> PyResult<bool> {
        let parsed: SkillModel = serde_json::from_str(json)
            .map_err(|e| PyValueError::new_err(format!("invalid skill model json: {e}")))?;
        // Fill sensible defaults for any missing tuning knob.
        let mut m = parsed;
        if m.threshold == 0.0 { m.threshold = 0.68; }
        if m.multi_skill_threshold == 0.0 { m.multi_skill_threshold = 0.32; }
        if m.null_anchor_score == 0.0 { m.null_anchor_score = 1.65; }
        if m.softmax_temperature == 0.0 { m.softmax_temperature = 0.85; }
        if m.avg_doc_len == 0.0 { m.avg_doc_len = 1.0; }
        let mut guard = self.model.write().map_err(|_| PyValueError::new_err("model lock poisoned"))?;
        *guard = m;
        Ok(true)
    }

    /// Rebuild the in-memory model from a JSON string, clearing recent-skill momentum.
    fn reload(&self, json: &str) -> PyResult<bool> {
        let ok = self.load_json(json)?;
        if let Ok(mut r) = self.recent_skills.write() {
            r.clear();
        }
        Ok(ok)
    }

    /// Record a recently-used skill (session momentum).
    fn note_skill_used(&self, skill_name: &str) {
        if let Ok(mut r) = self.recent_skills.write() {
            r.insert(skill_name.to_string());
        }
    }

    /// Analyze a prompt and return a routing decision dict.
    #[pyo3(signature = (prompt, recent_skills=None, enable_multi_skill=false))]
    fn analyze_prompt(
        &self,
        py: Python<'_>,
        prompt: &str,
        recent_skills: Option<Vec<String>>,
        enable_multi_skill: bool,
    ) -> PyResult<PyObject> {
        let result = self.analyze_core(prompt, recent_skills, enable_multi_skill);
        to_py_dict(py, &result)
    }

    /// Pure-Rust analyze used by tests/benchmarks (no Python dict conversion).
    #[pyo3(signature = (prompt, recent_skills=None, enable_multi_skill=false))]
    fn analyze_status(
        &self,
        prompt: &str,
        recent_skills: Option<Vec<String>>,
        enable_multi_skill: bool,
    ) -> PyResult<String> {
        Ok(self.analyze_core(prompt, recent_skills, enable_multi_skill).status)
    }
}

impl SkillBrain {
    fn analyze_core(&self, prompt: &str, recent_skills: Option<Vec<String>>, _enable_multi_skill: bool) -> RoutingDecision {
        // Pin the model under a read lock for the whole computation — DO NOT clone
        // it (a model can hold ~100k+ feature entries; cloning dominates latency).
        let model = match self.model.read() {
            Ok(g) => g,
            Err(_) => {
                return RoutingDecision {
                    status: "NO_SKILL_NEEDED".into(),
                    posture: "neutral".into(),
                    skills: Vec::new(),
                    probabilities: Vec::new(),
                    unknown_entities: Vec::new(),
                    threshold: 0.68,
                    top_score: 0.0,
                };
            }
        };

        let mut rs: HashSet<String> = recent_skills
            .map(|v| v.into_iter().collect())
            .unwrap_or_default();
        if rs.is_empty() {
            if let Ok(g) = self.recent_skills.read() {
                rs = g.clone();
            }
        }

        let posture = detect_posture(prompt);
        if posture == "conversational" {
            return RoutingDecision {
                status: "NO_SKILL_NEEDED".into(),
                posture: "conversational".into(),
                skills: Vec::new(),
                probabilities: Vec::new(),
                unknown_entities: Vec::new(),
                threshold: model.threshold,
                top_score: 0.0,
            };
        }

        let ex = extract_features(prompt);
        let mut kw_trigram_cache: HashMap<String, HashSet<String>> = HashMap::new();
        let mut scored = score_all(&model, &ex, &rs, &mut kw_trigram_cache);
        let probs = softmax_topk(&model, &mut scored);
        decide(&model, &probs, posture, &ex)
    }
}

/// Convert a RoutingDecision into a Python dict.
fn to_py_dict(py: Python<'_>, d: &RoutingDecision) -> PyResult<PyObject> {
    let dict = PyDict::new_bound(py);
    dict.set_item("status", d.status.clone())?;
    dict.set_item("posture", d.posture.clone())?;
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
    let unknown = PyList::empty_bound(py);
    for u in &d.unknown_entities {
        unknown.append(u)?;
    }
    dict.set_item("unknown_entities", &unknown)?;
    dict.set_item("threshold", d.threshold)?;
    dict.set_item("top_score", d.top_score)?;
    Ok(dict.into_any().unbind())
}

#[pymodule]
fn hermes_skill_brain(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<SkillBrain>()?;
    m.add_function(wrap_pyfunction!(py_strip_indonesian_affixes, m)?)?;
    Ok(())
}

#[pyfunction]
fn py_strip_indonesian_affixes(word: &str) -> Option<String> {
    strip_indonesian_affixes(word)
}
