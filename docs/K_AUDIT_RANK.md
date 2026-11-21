# Fase 3k Langkah 2–3 — Audit rank/margin & konsentrasi skill

## Ketersediaan skor (syarat STOP terpenuhi)

`SkillBrain.debug_topk(probe, k, mode)` mengekspos per-skill `(name, score)`
dari `score_clause` tanpa gating — jadi **tidak ada STOP**. θ₀ internal
`null_anchor_score = 7.5308` (model pasca-revert). Mode 2 dipakai untuk
ranking penuh; skor gated diambil dari `analyze_prompt().top_score`.

## Populasi

Kasus ber-ekspektasi `MATCHED_*` di v2–v9 + guard yang menghasilkan
HUNT/CLARIFY/NO_SKILL, **dedupe by prompt**: **51 kasus**.

## Kelas (satu kasus satu kelas; prioritas R4 > R3 > R2 > R1)

| Kelas | Definisi | N | % |
|---|---|---|---|
| R4 | Stage-0 bypass / gated top_score = 0 | 10 | 19.6% |
| R3 | target di luar top-3 | 0 | 0% |
| R2 | target rank 2–3 | 0 | 0% |
| R1 | target = top-1 tetapi skor < θ₀ (atau decision-gate/ban menolak) | **41** | **80.4%** |

Per set: v2 (R4 1, R1 1), v3 (R1 1), v5 (R4 2, R1 5), v6 (R1 7),
v7 (R4 2, R1 7), v8 (R4 1, R1 7), v9 (R4 4, R1 9), FMT_ADV (R1 3),
P2A_GUARD (R1 1), b35 (0).

### Histogram R1 — selisih skor ke θ₀ (bucket 1.0)

| Selisih (θ₀ − score) | N |
|---|---|
| < 0 (skor > θ₀, tapi ditolak gate/ban) | 8 |
| 0 – 0.9 | 7 |
| 1 – 1.9 | 3 |
| 2 – 2.9 | 0 |
| 3 – 3.9 | 5 |
| 4 – 4.9 | 7 |
| 5 – 5.9 | 8 |
| ≥ 6 | 3 |

Catatan jujur: 8 kasus R1 memiliki skor *di atas* θ₀ tetapi tetap gagal
karena decision gate (ban/contradiction/gray-zone), bukan karena ambang.
15 kasus (8 + 7) berada dekat atau di atas θ₀ → tuas kebijakan decision
gate relevan; sisanya (23 kasus) benar-benar jauh di bawah θ₀ → tuas
leksikon/alias/fitur.

## Konsentrasi per skill target (bucket non-tumpang tindih)

| Skill target | N |
|---|---|
| tabular-pivot-cleaning | 9 |
| word-docx-reporting | 7 |
| excel-xlsx-automation | 6 |
| pdf-extraction-manipulation | 4 |
| boring-marketing-email-sequences | 4 |
| backend-api-code-review | 4 |
| sql-bi-dashboard | 3 |
| powerpoint-slide-deck | 3 |
| invoice-ledger-reconciliation | 3 |
| 8 skill lainnya (bucket `lainnya`) | 8 |

**Jumlah bucket = 9+7+6+4+4+4+3+3+3+8 = 51 = total kasus** (cek lolos).
Konsentrasi moderat pada skill format/tabular (tabular+word+excel = 22/51
= 43%), sisanya tersebar. Tidak ada satu skill yang mendominasi > 20%.

## Catatan metode

Target untuk kasus tanpa `expect_skills` diambil dari `analyze_prompt().skills`
bila ada, else top-1 `debug_topk`. Karena itu R2/R3 = 0 bukan bukti bahwa
target selalu benar di top-1 — ini adalah konsekuensi metode inferensi;
dinyatakan eksplisit agar tidak disalahartikan sebagai "ranking engine
sempurna".
