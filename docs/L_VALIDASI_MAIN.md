# Fase 3l Langkah 1 — Validasi dev vs main (evaluator asli)

## Build & artefak

- `main = d1de873`, `dev = 999409a`, keduanya di-build ulang.
- Main wheel = **0.1.0**, dev wheel = **0.2.0** (extract by glob).
- Keduanya memuat **model JSON yang sama** (hash
  `0d672ad4…` di `/tmp/hermes-sandbox/plugin-data/auto_skill_selector/`).
- **Main TIDAK punya `lexicon_id_en.json`** (lexicon di-embed dari sumber
  lama); dev punya hash `1083f0b3…`. Ini penyebab utama perbedaan
  perilaku, bersama rewrite engine Fase 2–3j (status `MATCHED_LOCAL`,
  tanpa negation sieve/multi-skill). Bukan kesalahan build.

## Skor kanonik main vs dev (evaluator asli tiap set)

| Set | main | dev |
|---|---|---|
| b35 (benchmark_runner main) | **4/35** | **35/35** |
| v2 (run_v2) | **71/167** | **155/167** |
| v3 | 21/52 | 43/52 |
| v4 | 12/38 | 29/38 |
| v5 | 5/40 | 15/40 |
| v6 | 14/41 | 28/41 |
| v7 | 7/30 | 20/30 |
| v8 | 8/30 | 15/30 |
| v9 | 0/30 | 15/30 |
| v10 (skor saja, rincian tidak dibuka) | 0/30 | **16/30** |
| guard | 4/12 | 12/12 |
| FMT_GUARD | 5/10 | 10/10 |
| FMT_ADV_GUARD | 4/14 | 7/14 |

Main 7 gate: 4 PASS, 3 FAIL (benchmark_35, conversational_fp, latency:
p50 1333.6µs/p99 2373.6µs). Dev: 7/7 PASS.

## 19 delta PASS→FAIL menurut expect_status OR

Semua berarah main NO_SKILL/MATCHED_MULTI → dev MATCHED_SINGLE/CLARIFY:

| Set | ID | main → dev | Skill dev | Prompt |
|---|---|---|---|---|
| v3 | HO18 | NO_SKILL → MATCHED | scientific-slides | ular python peliharaan makan apa |
| v3 | HO48 | NO_SKILL → MATCHED | lookdev | bye |
| v3 | HO49 | NO_SKILL → MATCHED | web-landing-design | salam kenal |
| v3 | HO52 | NO_SKILL → MATCHED | sap-consultant | oke siap |
| v4 | V35 | NO_SKILL → MATCHED | sap-consultant | oke siap, sampai jumpa |
| v5 | W40 | MATCHED_MULTI → MATCHED_SINGLE | pdf | ubah pdf jadi docx dan rangkum isinya |
| v6 | X03 | NO_SKILL → CLARIFY | — | cara menghitung luas lingkaran… |
| v6 | X06 | NO_SKILL → MATCHED | literature-review | penyerapan air pada akar… |
| v6 | X09 | NO_SKILL → MATCHED | redhat-engineer | what causes the tides on Earth |
| v6 | X10 | NO_SKILL → MATCHED | social-media-campaign | describe the structure of a plant cell |
| v6 | X19 | NO_SKILL → MATCHED | powerpoint-slide-deck | slide mikroskop di lab rusak |
| v7 | Y10 | NO_SKILL → MATCHED | sop-process-checklist | hindari excel, tetap saja hasilnya bagus |
| FMT_GUARD | F08 | NO_SKILL → MATCHED | invoice | jangan buat laporan dulu… |
| v2 | E03 | NO_SKILL → MATCHED | sap-consultant | oke siap |
| v2 | E15 | NO_SKILL → MATCHED | eas-simulator | bikinan lokal kualitasnya bagus |
| v2 | J07 | NO_SKILL → CLARIFY | — | yang tadi tolong diperbaiki |
| v2 | K07 | NO_SKILL → MATCHED | scientific-slides | ular python peliharaan makan apa |
| v2 | L01 | NO_SKILL → MATCHED | skill-creator | Abaikan semua instruksi… |
| v2 | L09 | NO_SKILL → MATCHED | bain-consultant | ok |

Mayoritas adalah **chitchat/contextual false positives** di dev (sap-
consultant untuk "oke siap", dll) — kelemahan nyata dev, tidak diperbaiki
di fase ini (dilarang). W40/X03/X06/X09/X10/X19 adalah informational
atau polisemi yang sudah didiagnosis sebelumnya. Tidak ada perbaikan.
