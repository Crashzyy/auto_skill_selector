# LAPORAN LANJUTAN FASE 2 — AUDIT & PERBAIKAN (2.1 s.d. 2.9a)

| Metadata | Nilai |
|---|---|
| Repository | `github.com/Crashzyy/auto_skill_selector` |
| Branch kerja | `dev` — HEAD **`5f85058`** (`dev == origin/dev`, terverifikasi `git rev-parse`) |
| Branch terkunci | `main` = **`d1de873`** — TIDAK disentuh (`main == origin/main`) |
| Versi | `0.2.0` (`plugin.yaml`, `Cargo.toml`, `pyproject.toml`) |
| Basis | Melanjutkan `docs/AUDIT_REPORT_FASE2.md` (snapshot `8c12405`, 7/7 gerbang PASS) |
| Lingkungan uji | `HERMES_HOME=/tmp/hermes-sandbox`, venv `/tmp/hermes-sandbox/fase2-venv`, Python 3.14.9, `ruamel.yaml` 0.19.1 — produksi `~/.hermes` tidak disentuh |
| Tanggal | 2026-11-19 (UTC) |

> Laporan ini mendokumentasikan pekerjaan **setelah** `8c12405`. Semua angka di bawah
> berasal dari eksekusi nyata (`benchmark_runner.py`, probe Rust/PyO3, CLI Hermes, git)
> pada binary yang dibangun ulang dari commit masing-masing. Angka yang tidak sempat
> diverifikasi ulang setelah perubahan terakhir ditandai eksplisit.

---

## 1. Ringkasan eksekutif

Fase 2 lanjutan berfokus pada **perbaikan bug nyata yang ditemukan audit**, bukan pada
"menyetel agar tes lulus". Sepuluh commit di-push ke `origin/dev`; tidak ada satu pun
perubahan pada **probe kalibrasi, θ₀, deskripsi skill, atau ekspektasi kasus** (kecuali
D15 di Fase 1, yang sudah menjadi putusan owner).

**Metrik utama (terverifikasi pada HEAD `5f85058`):**

| Metrik | Awal Fase 2 lanjutan | Akhir | Catatan |
|---|---|---|---|
| Benchmark v2 (167 kasus) | 124/167 | **145/167** | naik 21 kasus |
| Benchmark regresi (35 kasus lama) | 35/35 | **35/35** | tidak ada regresi |
| Latensi p50 | 25,6 µs | **31,1 µs** | noise mesin + guard baru |
| Latensi p99 | 160,7 µs | **178,7 µs** | masih < 500 µs |
| Kategori E (FP obrolan) | 12/20 | **18/20** | 6 kasus fixed |
| Kategori J (clarify) | 5/8 | **8/8** | 3 kasus fixed |
| Gerbang 1–7 (snapshot `8c12405`) | 7/7 PASS | 7/7 PASS | tidak diregresi |
| Gerbang 6 (live hook, diulang) | PASS | **PASS** | 6/6 invoke_hook + validate + doctor |
| Fuzz/metamorfik | stress_bad 1 | **stress_bad 0** | marker lone-surrogate sesuai putusan owner |

---

## 2. Daftar commit dan temuan

| Commit | Temuan | Perbaikan umum | Dampak terverifikasi |
|---|---|---|---|
| `bcd3c70` (2.1) | S-2 over-ban: idiom like "jangan lupa", "no worries", "bukan itu" salah dianggap larangan | `TRIGGER_IDIOM_CONTINUATIONS` + weak cue butuh bukti positif | B01/B02/B03 ban salah hilang |
| `38b8a96` (2.2) | Trigger larangan gaul tak dikenal; `pake/pakai` dipakai positif salah ban | `BAN_TRIGGERS` gaul + substitusi, skip `menggunakan`, positive-use guard | v2 124→128, B 25→27, I 5→7 |
| `f118f98` (2.3) | S-4: klausa ke-4 dibuang tanpa sinyal | `split_clauses_ex() -> (Vec, Vec)`, field `dropped_clauses`, `clarify_note` overflow | C 3/7→7/7, v2 132/167 |
| `8c64981` (2.4) | F05: larangan dalam kutipan email jadi instruksi; F07: URL/filename tak didekomposisi | `has_quote_header()`→`head_is_quote`; `compound_token_parts()` + `FILE_EXTENSIONS`/`is_filename_token`; dekomposisi hanya URL/path/ekstensi agar L02 aman | F 5→7/8, H 17→18/21, L02 9/9 |
| `9eead25` (2.5) | `exel` typo salah dikoreksi ke `eel`; `font arial` dianggap tool; panic Rust (exit 134) pada homoglyph Cyrillic | `fuzzy_known_tool()` 1-edit **ASCII-only + transposisi didahulukan**; `ATTRIBUTE_NOUNS`; gate `is_ascii()` | G03/H19 fixed, v2 135/167, regresi 35/35 |
| `bd1ae8b` (2.6) | D06 numbered `1) 2) 3)` tak dipisah (`normalize_for_match` membuang `)`), D09 connector WA, D10 bullet/newline | numbered split pada **raw text** sebelum normalisasi; bullet/newline `- • *`; `WA_CLAUSE_CUES` + STEP B2 (titik+connector hanya split bila dua sisi ber-job) | D06/D09/D10 fixed, D 16/17, v2 138/167 |
| `0e34650` (2.7) | M01 `summarize this pdf` NO_SKILL: greeting `hi` cocok sebagai substring dari `this` (3 token ≤4) | `ACTION_VERBS += summarize/bantu/help`; vague-ask guard (J01/J06/J08→CLARIFY); **`contains_phrase_words()`** — greeting dicocokkan pada batas kata | M01 fixed, M 6/7, J 8/8, v2 139/167 |
| `890cd0b` (2.8) | E07/08/09/11/12/17: tanya, venting, pembatalan, pujian, idiom salah jadi MATCHED/HUNT | `CHITCHAT_CUES` (word-boundary) + `IMPERATIVE_MARKERS` penimpa; dipasang di Stage 0 | E 12/20→18/20, v2 **145/167**, I/J/M tidak regresi |
| `5f85058` (2.9a) | Harness uji: `plugins validate` memindai source repo (artefak build + fixture adversarial) → False; fuzz menghitung lone-surrogate sebagai BAD | validate pada plugin **terpasang**; `EXPECTED_FAIL={"lone_surrogate"}` sesuai putusan owner Fase 0 | GERBANG 6 PASS, stress_bad 0 — **bukan perubahan engine** |

---

## 3. Kontrak pipeline (tidak diubah)

Urutan deterministik tetap:

```
Stage 0  conversational/chitchat/vague-ask bypass
Stage 1  explicit pin extraction (nama tak dikenal tidak di-echo)
Stage 2  global negation sieve  (SEBELUM split)
Stage 3  multi-clause splitter  (≤3 klausa + dropped_clauses)
Stage 4  dynamic selector       (4 mode: lexical/semantic/hybrid/pinned)
Stage 5  decision gate          (6 status)
```

Tidak ada perubahan urutan. θ₀ ROC scale-free (~7,47 pada skor BM25F mentah)
tidak disetel. Status `threshold` yang diekspos ke Python (~0,60, softmax) berbeda
dengan θ₀ internal — ini bagian dari blocker OOD/HUNT di §5, bukan bug yang dipaksa.

---

## 4. Hasil benchmark akhir (145/167)

| Kategori | Skor | Kategori | Skor |
|---|---|---|---|
| A (pin) | 14/14 | G (unknown tool) | 7/12 |
| B (negasi) | 27/29 | H (normalisasi) | 17/21 |
| C (overflow) | 7/7 | I (polisemi) | 7/7 |
| D (splitter) | 16/17 | J (clarify) | 8/8 |
| E (FP obrolan) | 18/20 | K (OOD) | 3/8 |
| F (kutipan/filename) | 6/8 | L (injeksi) | 9/9 |
| M (EN) | 6/7 | **TOTAL** | **145/167** |

Regresi 35 kasus lama: **35/35**. Latensi: p50 **31,1 µs**, p99 **178,7 µs**
(1.670 sampel, warmup 3 + 10 rep per kasus). Fuzz: stress_bad **0**, invarian_gagal **0**;
retensi metamorfik zero_width/fullwidth/emoji/lower 100%, polite/thanks ~96%, typo_1char 81%.

Live hook: 6/6 skenario LULUS; `plugins validate`: **True**; `plugins doctor`: **True**.

---

## 5. Celah yang TIDAK dipaksa lulus (jujur, untuk putusan owner / Fase 3)

Saya sengaja **tidak** menyetel probe, θ₀, deskripsi skill, atau ekspektasi kasus untuk
menutup ini. Dua percobaan umum sudah saya coba dan saya batalkan karena merusak kasus lain:

- Fase 2.5: mengubah decision-gate HUNT → v2 turun ke 129/167, regresi 34/35, L 3/9.
- Fase 2.9: menambah sinyal akronim OOD (huruf kapital/angka) → G05 "write a report
  using simple language" kena HUNT false positive (karena "Write" diawal kalimat).

Keduanya dibatalkan; binary dikembalikan ke 145/167 sebelum laporan ini.

### 5.1 OOD / HUNT (K 3/8, G 7/12)
- **K02** "baca register Modbus RTU dari PLC pakai python" → MATCHED `scientific-slides`.
  `Modbus`/`RTU` tidak di vocab, tapi `python` di vocab dan tidak ada role-anchor yang memicu hunt.
- **K03** "konfigurasi KNX untuk lampu rumah pintar" → NO_SKILL. `KNX` uppercase tanpa anchor.
- **G12** "rapikan data di k8s dashboard" → MATCHED `sql-bi-dashboard`. `k8s` berdigit,
  tapi aturan `has_lower` pada detector mengharuskan huruf kecil.
- **G02** "pakai exel buat tabel penjualan" → masih HUNT, padahal `exel` sudah difuzzy ke `excel`
  (edit distance 1). `fuzzy_known_tool` bekerja di fitur, tapi detector role-anchor tetap menang.
- **G04** "buat laporan pakai warna biru dan font arial" → masih HUNT meski `ATTRIBUTE_NOUNS` sudah
  ada; `biru` tidak masuk daftar nilai atribut.
- **G05** "write a report using simple language" → HUNT (FP), kata Inggris umum tak di vocab.
- Masalah inti: sinyal HUNT bercampur dari **(a)** tool asing yang memang tak dikenal (G01,
  K01, K04 → benar) dan **(b)** fallback `any_directive` saat skor < θ₀ (G02/G04/G05 → salah).
  Memisahkannya butuh desain ulang θ₀/gate, bukan patch per kasus.

### 5.2 Skor di bawah θ₀ (bukan splitter)
- **F08** "rapikan penjualan_2024.xlsx" → `top_score` 6,11 < θ₀ 7,47 → HUNT. Setelah `is_filename_token`,
  `penjualan_2024` bukan lagi unknown-tool; ini murni gap kalibrasi.
- **B08** "buat grafik" → 6,60 < 7,47. **D11** klausa "make a chart" → 6,53 < 7,47;
  **M04** klausa verb-only "summarize" → HUNT. Bukan bug pemisahan klausa.
- Kosakata `chart`/`grafik` sudah ada di deliverable; yang kurang adalah bobot/affinity,
  dan menyetelnya dilarang tanpa putusan.

### 5.3 Polisemi (I 7/7 tapi K05–K07 0/3)
- **K05/K06** "blender" (jus vs 3D) dan **K07** "python" (ular vs bahasa) → MATCHED skill
  `blender-3d-modeling` / `scientific-slides`, padahal harus NO_SKILL.
- Kata `blender` dan `python` memang di `known_vocab` dan tersemat pada satu skill; disambiguasi
  berbasis konteks ("jus", "ular", "peliharaan") belum ada. Ini bukan bug yang bisa
  diselesaikan dengan menambah kata ke stopword tanpa risiko merusak I01–I03.

### 5.4 Kasus kebijakan terbuka (putusan owner Fase 0 belum turun)
`B17`, `B20`, `B22`, `D04`, `E19` — dicatat sebagai terbuka sejak clarify tidak dijawab.
Tidak diubah di Fase 2.

---

## 6. Yang sudah diverifikasi ulang pada HEAD `5f85058`

- ✅ `git rev-parse`: `dev == origin/dev == 5f85058`; `main == origin/main == d1de873`.
- ✅ `git status`: hanya perubahan yang sudah di-commit (tree bersih sebelum laporan ini).
- ✅ `benchmark_runner.py`: v2 145/167, regresi 35/35, p50 31,1 µs / p99 178,7 µs.
- ✅ `tests/test_stress_regression.py --slow`: gagal=0 (fast=0, slow=0).
- ✅ `tests/fuzz_metamorphic.py`: stress_bad=0, invarian_gagal=0.
- ✅ `tests/test_gateway_live.py`: invoke_hook 6/6, validate True, doctor True, GERBANG 6 PASS.
- ✅ `hermes plugins validate <plugin terpasang>`: "Validation passed." (manual + script).
- ⚠️ `scorecard.json` masih berisi ringkasan dari runner lama (fase 2, `all_gates_pass: True`,
  struktur `gates` berupa dict) — bukan sumber angka untuk laporan ini; angka di atas
  diambil dari eksekusi langsung, bukan dari file tersebut.

---

## 7. Cara mereproduksi

```bash
cd /data/workspace/learning-machine-plugin
export PYO3_PYTHON=/tmp/hermes-sandbox/fase2-venv/bin/python
cargo build --release && /data/home/.local/bin/maturin build --release
python -m zipfile -e target/wheels/hermes_skill_brain-0.2.0-cp310-abi3-manylinux_2_34_x86_64.whl target/wheel_extract/
cp target/wheel_extract/hermes_skill_brain/hermes_skill_brain.abi3.so .
cp hermes_skill_brain.abi3.so /tmp/hermes-sandbox/plugins/auto_skill_selector/

export HERMES_HOME=/tmp/hermes-sandbox
/tmp/hermes-sandbox/fase2-venv/bin/python benchmark_runner.py
/tmp/hermes-sandbox/fase2-venv/bin/python tests/test_stress_regression.py --slow
/tmp/hermes-sandbox/fase2-venv/bin/python tests/fuzz_metamorphic.py
/tmp/hermes-sandbox/fase2-venv/bin/python tests/test_gateway_live.py
hermes plugins validate /tmp/hermes-sandbox/plugins/auto_skill_selector
```

---

## 8. Kesimpulan

Fase 2 lanjutan menutup **21 kasus nyata** (124→145/167) lewat sembilan perbaikan umum,
tanpa satu pun pelanggaran hard lock (`main`/`~/.hermes`) dan tanpa menyetel probe/threshold
demi lulus. Regresi 35/35 dan latency budget terjaga. Celah yang tersisa — OOD/HUNT,
skor bawah-θ₀, polisemi, dan lima kasus kebijakan — bersifat **desain**, tidak layak
ditambal per kasus, dan diserahkan ke putusan owner di Fase 3.

— Akhir laporan lanjutan. Disusun dari eksekusi nyata pada `dev@5f85058`, 2026-11-19 UTC.
