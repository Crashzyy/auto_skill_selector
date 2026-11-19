# auto_skill_selector

**Router skill otonom untuk Hermes Agent — Fase 2.** Mesin inti Rust + PyO3
(`hermes_skill_brain`) membaca setiap prompt pengguna melalui **pipeline
6 tahap deterministik**, lalu menyuntikkan skill lokal yang paling cocok ke
pesan user (bukan system prompt, prompt-cache aman), merantai multi-pekerjaan,
memicu pencarian skill baru secara async, atau diam saat pengguna hanya
mengobrol.

> Branch kerja: `dev`. Branch `main` = rilis stabil Fase 1 (tidak disentuh
> oleh pengembangan Fase 2). Seluruh pengujian berjalan di `HERMES_HOME`
> sandbox terpisah, bukan `~/.hermes` produksi.

---

## Pipeline 6 Tahap (kontrak deterministik, Master Prompt §1)

```text
User Prompt
  [Stage 0] Conversational / Meta-Query Bypass      -> NO_SKILL_NEEDED
  [Stage 1] Explicit Skill Override & Pinning       (/skill X, "pakai skill X", @X)
  [Stage 2] GLOBAL Negation & Prohibition Sieve     -> GLOBAL_BANNED_SET + teks bersih
            (WAJIB sebelum split; larangan berlaku global ke semua sub-klausa;
             hard mask -inf untuk skill & sinonim terlarang)
  [Stage 3] Multi-Clause & Multi-Job Splitter       -> maksimal 3 sub-klausa
            (guardrail anti over-split: "laporan laba dan rugi" tetap 1 klausa)
  [Stage 4] Per-Clause Dynamic Algorithm Selector   -> 4 mode adaptif:
            EXACT_LEXICAL_BM25F | SEMANTIC_CONCEPT_MNB | HYBRID_BALANCED |
            CONSTRAINT_FILTERED_RERANK
  [Stage 5] Decision Gate, Multi-Task Merge & Fallback
```

### 6 Status Keluaran (`RoutingDecision`)

| Status | Arti |
|---|---|
| `NO_SKILL_NEEDED` | Obrolan/sapaan/pertanyaan konsep murni tanpa deliverable |
| `MATCHED_SINGLE` | 1 pekerjaan, 1 skill sah lolos ambang ROC θ₀ |
| `MATCHED_MULTI` | 2–3 sub-klausa semua cocok; dedup, urutan step_1→step_2→step_3, injeksi < 10.000 karakter |
| `MATCHED_PARTIAL_AND_HUNT` | Sebagian cocok lokal + subagent pencari async untuk sisanya (tidak memblokir pekerjaan pertama) |
| `HUNT_NEW_SKILL` | Aksi valid tapi tak ada skill lokal lolos θ₀ (termasuk semua kandidat terlarang) |
| `CLARIFY_AMBIGUOUS` | Aksi samar tanpa objek, atau kontradiksi mutlak (mis. minta .xlsx tapi larang Excel) |

## Scoring (Stage 4)

* **BM25F 4 zona dokumen**: S (nama/alias) 8.0×, A (concept graph/deskripsi)
  4.5×, B (when-to-use/prosedur) 2.5×, C (body) 0.6× — dikompilasi `trainer.py`.
* **Multinomial Naive Bayes** + **centroid cosine** per kategori.
* **Zona prompt**: Instruction 1.0× vs Payload 0.15× (payload panjang: tail
  instruction dominan, head 0.35×, payload dedup capped 25 token).
* Bobot mode sesuai tabel §1.3 (0.80/0.15/0.05, 0.25/0.55/0.20,
  0.50/0.30/0.20, 0.45/0.35/0.20); bigram 2.5× di Mode 1.
* Keputusan gate memakai **θ₀ ROC scale-free** pada skor mentah; softmax
  Top-5 null-anchor hanya untuk keyakinan yang dilaporkan.

## Pelatihan Dwibahasa Mendalam (ID–EN)

`lexicon_builder.py` membangun `lexicon_id_en.json` (di-embed ke binary Rust
via `include_str!`, latensi tetap sub-milidetik):

1. **KBBI baku + glosarium Kemdikbud** (salindia, lembar sebar, siniar,
   rekonsiliasi, neraca lajur, anuitas, infografik, purwarupa, ...).
   Stemmer K-P-S-T deterministik di Rust: `memvisualisasikan→visualisasi`,
   `menyunting→sunting`, `mengonversi→konversi`, `memindai→pindai`,
   `menulis→tulis`, `mengekstrak→ekstrak`, `merangkum→rangkum` (gerbang
   known_vocab 114k+ kata KBBI mencegah stem palsu).
2. **Kamus konsep EN↔ID terkurasi**: 313 pasangan inti lintas 9 pilar.
3. **Gaul/singkatan chat**: 547 entri kurasi + 4.786 total dengan kamus-alay
   komunitas (bikinin→buatkan, rapihin→rapikan, pdfin→pdf, jgn→jangan,
   dek→pitch deck, ...).
4. **Transliterasi sufiks Zero-RAM** (aturan di Rust): -isasi→-ization,
   -asi→-ation, -isi→-ition, -uksi→-uction, -itas→-ity, -grafi→-graphy,
   -logi→-logy (dua arah).

## Korpus Multi-Katalog & 9 Pilar (54 skill inti)

`corpus_core.py` menanam **tepat 6 skill/pilar × 9 pilar = 54** skill inti.
`harvester.py` memanen katalog wajib **tanpa token GitHub** (tarball codeload
1 request/repo + cache disk, fallback sparse clone):

* Hermes Bundled + Optional Skills Catalog (199 skill)
* `anthropics/skills`, `alirezarezvani/claude-skills`
* registri terbuka agentskills.io & skills.sh (via repo sumbernya)
* `sickn33/agentic-awesome-skills`, `theneoai/awesome-skills`,
  `VoltAgent/awesome-agent-skills`, `bergside/awesome-design-skills`,
  `K-Dense-AI/scientific-agent-skills`, ekosistem skills.sh lainnya

**Anti-skew (§3.3):**
1. **Category-Stratified IDF** — kontribusi df_k/|C_k| per pilar; menambah
   dokumen di satu pilar tidak mengubah IDF pilar lain.
2. **Category Gain Equalization** — γ_k pada kontribusi IDF fitur khas pilar
   (fitur bersama lintas-domain netral), iteratif sampai CV ≤ 0.06;
   **L2 norm per kelas tetap 100.0 ± 0.01** pasca-pruning top-80.

## Gerbang Kelulusan (scorecard.json)

| # | Gerbang | Kriteria |
|---|---|---|
| 1 | L2 Weight Normalization | semua kelas L2 = 100.0 ± 0.01 |
| 2 | Domain Parity & Skew | parity ≥ 0.92 & CV ≤ 0.08 (54 inti); tetap ≥ 0.90 saat +10 skill ke 1 pilar |
| 3 | Benchmark 35 kasus | ≥ 34/35 DAN 6/6 kasus negasi global |
| 4 | Zero Conversational FP | 0/5 obrolan santai mengaktifkan skill |
| 5 | Latensi Rust | p50 < 200 µs, p99 < 500 µs (per-call, warmup) |
| 6 | Live Hermes Hook | ruamel.yaml di venv sandbox; `invoke_hook("pre_llm_call")` 6 skenario; `plugins validate` & `doctor` PASS |
| 7 | Git & Production Hygiene | push `origin/dev`; `main` tetap di commit rilis; `~/.hermes` produksi bersih |

## Menjalankan (sandbox, bukan produksi)

```bash
# 1. venv sandbox + dependensi dispatcher
python3.14 -m venv /tmp/hermes-sandbox/fase2-venv
/tmp/hermes-sandbox/fase2-venv/bin/pip install ruamel.yaml packaging loguru httpx requests

# 2. kamus + korpus inti + harvest multi-katalog
export HERMES_HOME=/tmp/hermes-sandbox
/tmp/hermes-sandbox/fase2-venv/bin/python lexicon_builder.py --force
/tmp/hermes-sandbox/fase2-venv/bin/python corpus_core.py
/tmp/hermes-sandbox/fase2-venv/bin/python -c "import harvester; harvester.harvest_and_ingest()"

# 3. build mesin Rust (PyO3 abi3 + extension-module)
export PYO3_PYTHON=/tmp/hermes-sandbox/fase2-venv/bin/python
maturin build --release
python -m zipfile -e target/wheels/*.whl target/wheel_extract/
cp target/wheel_extract/hermes_skill_brain/*.so .

# 4. train + benchmark 35 kasus + scorecard 7 gerbang
/tmp/hermes-sandbox/fase2-venv/bin/python benchmark_runner.py

# 5. pasang plugin ke sandbox & uji gateway hidup
cp __init__.py trainer.py harvester.py lexicon_builder.py corpus_core.py \
   benchmark_runner.py plugin.yaml pyproject.toml Cargo.toml \
   lexicon_id_en.json hermes_skill_brain.abi3.so $HERMES_HOME/plugins/auto_skill_selector/
hermes plugins validate $HERMES_HOME/plugins/auto_skill_selector
hermes plugins doctor auto_skill_selector
/tmp/hermes-sandbox/fase2-venv/bin/python tests/test_gateway_live.py
```

## Perintah slash

```
/skill-brain                 # status mesin & model
/skill-brain retrain         # pindai ulang skill, rebuild model
/skill-brain test <prompt>   # uji satu prompt: status, ban set, klausa, latensi
```

## Struktur

```
auto_skill_selector/
├── Cargo.toml               # crate Rust cdylib (hermes_skill_brain)
├── pyproject.toml           # konfigurasi build Maturin
├── plugin.yaml              # manifest plugin Hermes
├── src/lib.rs               # mesin 6-stage: PyO3 SkillBrain
├── __init__.py              # hook pre_llm_call, lifecycle, slash command
├── trainer.py               # scanner, compiler model, stratified IDF, kalibrasi ROC
├── lexicon_builder.py       # lexicon_id_en.json 4 lapisan (embed ke Rust)
├── corpus_core.py           # 54 skill inti (6/pilar × 9 pilar)
├── harvester.py             # multi-katalog tanpa token (tarball + cache)
├── benchmark_runner.py      # 35 kasus + scorecard 7 gerbang + uji stres
└── tests/
    ├── benchmark_35_labeled.json
    ├── test_gateway_live.py # invoke_hook dispatcher resmi + validate/doctor
    └── test_zones.py        # verifikasi zona S/A/B/C
```

## Keterbatasan jujur

* Korpus inti 54 adalah skill representatif terkurasi (bukan salinan verbatim
  katalog vendor); harvesting menambah kelas nyata di atasnya.
* `HUNT_NEW_SKILL`/`MATCHED_PARTIAL_AND_HUNT` menyuntikkan instruksi
  `delegate_task` ke pesan user — eksekusi subagent dilakukan oleh LLM agent,
  bukan oleh plugin (plugin tidak memanggil gateway secara rekursif).
* Deteksi unknown-tool berbasis role-anchor ("di Houdini") + ortografi;
  nama tool tanpa penanda bisa lolos sebagai match generik.
* Kalibrasi θ₀ memakai probe direktif per pilar; prompt di luar distribusi
  probe dapat memerlukan penyetelan ulang (retrain otomatis via
  `on_skill_lifecycle`).
* Model tersimpan di `plugin-data/`, bukan folder plugin, agar tahan
  terhadap `hermes plugins update`.

## Lisensi

MIT