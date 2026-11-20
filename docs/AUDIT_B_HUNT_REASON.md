# AUDIT B — Instrumentasi `hunt_reason` (tanpa ubah perilaku)

## Perubahan

Ditambahkan field `hunt_reason: String` ke `RoutingDecision` dan diekspos di
`to_py_dict()`. Nilai: `"unknown_tool"` | `"below_theta"` | `"no_match"`, atau
`""` bila tidak ada hunt. **Instrumen murni** — tidak masuk ke logika status,
skills, scoring, atau θ₀. Prioritas bila beberapa klausa hunt:
`unknown_tool > below_theta > no_match`.

Penempatan alasan:
- Klausa hunt normal (`_ =>` branch): `unknown_tool` bila detektor tool
  unknown aktif; `below_theta` bila ada kandidat tapi `top_score < θ₀`;
  `no_match` bila tidak ada kandidat ter-skor.
- Pin eksplisit tak dikenal & mixed-pin: `unknown_tool`.
- Fallback `any_directive` (hunt_clauses diisi dari clauses): `below_theta`
  bila `0 < top_score < threshold`, else `no_match`.

## Sebaran terukur (binary HEAD, θ₀ = 7.4688)

### Kasus G (12)
| ID | status | hunt_reason | top_score |
|---|---|---|---|
| G01 | HUNT_NEW_SKILL | below_theta | 4.69 |
| G02 | HUNT_NEW_SKILL | below_theta | 7.10 |
| G03 | MATCHED_SINGLE | — | 10.44 |
| G04 | HUNT_NEW_SKILL | below_theta | 7.02 |
| G05 | HUNT_NEW_SKILL | below_theta | 7.06 |
| G06 | MATCHED_SINGLE | — | 10.82 |
| G07 | HUNT_NEW_SKILL | **unknown_tool** | 6.86 |
| G08 | MATCHED_SINGLE | — | 9.84 |
| G09 | MATCHED_SINGLE | — | 10.65 |
| G10 | MATCHED_SINGLE | — | 8.06 |
| G11 | HUNT_NEW_SKILL | below_theta | 4.70 |
| G12 | HUNT_NEW_SKILL | **unknown_tool** | 10.73 |

**Sebaran G:** below_theta 5, unknown_tool 2, none 5.

### Kasus K (8)
| ID | status | hunt_reason | top_score |
|---|---|---|---|
| K01 | HUNT_NEW_SKILL | below_theta | 3.56 |
| K02 | MATCHED_SINGLE | — | 9.11 |
| K03 | NO_SKILL_NEEDED | — | 0.00 |
| K04 | MATCHED_PARTIAL_AND_HUNT | **unknown_tool** | 17.16 |
| K05 | MATCHED_SINGLE | — | 13.08 |
| K06 | MATCHED_SINGLE | — | 13.08 |
| K07 | MATCHED_SINGLE | — | 9.15 |
| K08 | HUNT_NEW_SKILL | below_theta | 4.74 |

**Sebaran K:** below_theta 2, unknown_tool 1, none 5.

Catatan: `no_match` tidak muncul di G/K — semua klausa hunt memiliki kandidat
ter-skor (masuk `below_theta`) atau memang unknown-tool. Field tetap tersedia
untuk kasus tanpa kandidat.

## Verifikasi tanpa-ubah-perilaku

- v2: **149/167** (identik dengan A4)
- regresi 35: **35/35**
- Status/skills per kasus tidak berubah; hanya field baru di dict.

Implikasi Fase 3 (dicatat, belum dikerjakan): 7 dari 9 hunt di G/K adalah
`below_theta`, bukan unknown-tool — ini dasar untuk memisahkan HUNT
`unknown_tool` dari fallback `below_theta` (butuh θ₀ terkalibrasi dari sumber
terpisah, bukan setelan per-kasus).
