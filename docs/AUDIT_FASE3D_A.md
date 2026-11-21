# Fase 3d — Langkah A: Audit tanpa kode (laporan saja)

Semua angka dari binary hasil **build ulang**. HEAD = `18967f5` (konfirmasi:
`e384d73` adalah commit Langkah 2 Fase 3c, **bukan** HEAD; HEAD sebenarnya
`18967f5` = commit STOP Fase 3c). `dev = origin/dev = 18967f5`,
`main = d1de873` utuh. Tidak ada kode yang diubah untuk audit ini.

## A1 — HO14: diff probe `9e30de9` vs `5917645`

Kasus: `HO14 = "pakai tool aneh bikin laporan"`, ekspektasi `HUNT_NEW_SKILL`.

| Versi | debug_score | top_score | status | hunt_reason | hunt_clauses |
|---|---|---|---|---|---|
| `5917645` (pra-P1b) | 4.6778 | **7.0438** | `HUNT_NEW_SKILL` | `below_theta` | 1 |
| `18967f5` (≈`9e30de9`, pasca-P1b) | 4.6778 | **7.0438** | `CLARIFY_AMBIGUOUS` | `below_theta` | 0 |

**Mekanisme P1b** (konstanta `GRAY_ZONE_MARGIN = 0.08` di `src/lib.rs`):

- θ₀ internal = `7.4688`
- `gray_lo = θ₀ × (1 − 0.08) = 7.4688 × 0.92 = 6.871296`
- zona abu = `[6.8713, 7.4688)`
- `top_score = 7.0438` **masuk zona** → status `below_theta` diubah menjadi
  `CLARIFY_AMBIGUOUS`, `hunt_clauses` dikosongkan, `clarify_note` diisi.
- Skor/debug identik di kedua versi → ini **murni perubahan decision gate**,
  bukan perubahan skor/MNB/θ₀. DIaudit, **tidak diperbaiki** (perintah).

## A2 — Ablasi P1b: margin 0 vs 8%

Margin **sudah merupakan parameter** (`const GRAY_ZONE_MARGIN: f64`), jadi
ablasi dapat dilakukan tanpa mengubah kode di repo utama: worktree sementara
`/data/workspace/wt-ablate` dengan margin di-set `0.0`, di-build ulang; repo
utama tetap `0.08`. Keduanya dijalankan dengan evaluator asli.

| Set | margin 0 | margin 8% | Diff |
|---|---|---|---|
| v3 (held-out, 52) | **44/52** | **43/52** | HO10, HO11 HUNT→CLARIFY (tetap PASS), **HO14 PASS→FAIL** |
| v4 (dev, 38) | **29/38** | **29/38** | tidak ada |
| v5 (held-out, 40) | **15/40** | **15/40** | tidak ada |

Diff per kasus v3:

| ID | margin 0 | margin 8% | Ekspektasi |
|---|---|---|---|
| HO10 | `HUNT_NEW_SKILL` PASS | `CLARIFY_AMBIGUOUS` PASS | mengizinkan keduanya |
| HO11 | `HUNT_NEW_SKILL` PASS | `CLARIFY_AMBIGUOUS` PASS | mengizinkan keduanya |
| HO14 | `HUNT_NEW_SKILL` **PASS** | `CLARIFY_AMBIGUOUS` **FAIL** | hanya `HUNT_NEW_SKILL` |

Output mentah: `/tmp/hermes-sandbox/ablate*.txt` vs
`/tmp/hermes-sandbox/cur*.txt` (akan disalin ke `docs/` bila dibutuhkan).

**Tidak ada keputusan margin diambil dari ablasi ini** — sesuai perintah,
pilihan margin ada di user. Angka di atas hanya dilaporkan.

## Bersih

- Tidak ada kode repo yang diubah; worktree ablasi adalah artefak sementara
  (akan dihapus sebelum STOP).
- θ₀, probe, deskripsi, ekspektasi semua set: tidak disetel.
- Tidak ada merge ke main.
