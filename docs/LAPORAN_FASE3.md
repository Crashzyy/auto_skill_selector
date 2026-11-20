# Laporan Akhir Fase 3 — auto_skill_selector

Mulai dari `dev@9a0a92d`; semua angka dari binary hasil **build ulang**.
`main = d1de873` (hard lock) tidak disentuh. θ₀ = 7.4688 **tidak diubah**.

## Ringkasan metrik

| Metrik | Sebelum (baseline 9a0a92d) | Sesudah |
|---|---|---|
| v2 | 149/167 | **152/167** |
| Regresi 35 | 35/35 | 35/35 |
| Negasi | 6/6 | 6/6 |
| 7 gerbang | 7/7 | 7/7 |
| Fuzz Unicode | 5000/0 gagal | 5000/0 gagal |
| Stress (fast+slow) | 0 gagal | 0 gagal |
| Fuzz metamorphic | stress_bad=0 | stress_bad=0 |
| p50 / p99 | 38.3µs / 213.4µs | **41.5µs / 242.4µs** |

## Tabel per kategori v2 (sebelum → sesudah)

| Kat | Sebelum | Sesudah | Δ |
|---|---|---|---|
| A | 14/14 | 14/14 | 0 |
| B | 27/29 | 27/29 | 0 |
| C | 7/7 | 7/7 | 0 |
| D | 16/17 | 16/17 | 0 |
| E | 20/20 | 20/20 | 0 |
| F | 7/8 | 7/8 | 0 |
| **G** | 8/12 | 8/12 | 0 |
| **H** | 17/21 | **20/21** | **+3** |
| I | 7/7 | 7/7 | 0 |
| J | 8/8 | 8/8 | 0 |
| K | 3/8 | 3/8 | 0 |
| L | 9/9 | 9/9 | 0 |
| M | 6/7 | 6/7 | 0 |

Tidak ada kategori yang turun. Kenaikan hanya di H.

## Diff per kasus (FAIL→PASS / PASS→FAIL)

| Kasus | Sebelum | Sesudah | Mekanisme |
|---|---|---|---|
| H05 | FAIL (0.00) | **PASS (7.88)** | segmentasi kosakata penuh |
| H08 | FAIL (0.00) | **PASS (7.76)** | ciut huruf berulang ≥3→1 |
| H21 | FAIL (6.40) | **PASS (13.58)** | reduplikasi digit-2 + hyphen |
| H06 | FAIL (0.00) | FAIL (4.20) | parsial; `penj4l4n`→`penjalan` bukan kosakata (4→a sesuai aturan) |

PASS→FAIL: **tidak ada**.

## Langkah 0 & urutan kerja

- **0a** Tag `baseline-fase2-final@530ec1a` dibuat & di-push; git hygiene refresh.
- **0b** Verifikasi kegagalan dari RUN: ada koreksi — **B22 sudah PASS** (AUDIT C),
  penggantinya **B26**. Daftar 18 aktual: B08 B26 D11 F08 G02 G04 G05 G07
  H05 H06 H08 H21 K02 K03 K05 K06 K07 M04.
- **0c** Held-out 52 kasus dibekukan SEBELUM kode P3, SHA256
  `124dc7d7…c89` (tdk diubah; diverifikasi saat evaluasi).
- **P3** Sudah diimplementasi di AUDIT C; diverifikasi: B22 no-ban, B20 ban,
  negasi 6/6. Tanpa kode baru.
- **P4** Normalisasi H: H05/H08/H21 PASS; H06 gap jujur. 2 commit terpisah.
- **P1** Desain zona abu (CLARIFY) ditulis di docs; **belum diimplementasi**
  (butuh keputusan). Rekomendasi margin 8%, hanya untuk `below_theta`.
- **P2** Desain OOD/polisemi K ditulis di docs; **belum diimplementasi**
  (menunggu persetujuan sesuai perintah).
- **P5** `_ensure_brain` diukur saja: p50 46.2ms / p99 61.7ms.

## Hasil held-out (dijalankan sekali di gerbang akhir)

**43/52 PASS.** 9 kegagalan, dikelompokkan:
- HO01–HO08 (8): engine return `MATCHED_SINGLE`, ekspektasi saya menulis
  `MATCHED_MULTI`. Ini **terlalu spesifik** di held-out saya — semua tetap
  match benar (bukan NO_SKILL/HUNT). Tidak saya ubah (hash dibekukan).
- HO09–HO12: weak ask → HUNT, bukan CLARIFY (P1 belum diimplementasi).
- HO13: `KNX` → NO_SKILL (butuh wordlist/penanganan OOD P2).
- HO16–HO20: polisemi blender/python (butuh P2).
- HO24/HO28: leet `penj4l4n` butuh 4→u (dilarang aturan).
- HO36: `hindari excel` banned=[] (masalah pre-existing AUDIT C).

Tidak ada perubahan/setelan untuk menaikkan angka ini.

## 7 gerbang (binary build ulang)

| Gerbang | Hasil |
|---|---|
| 1 L2 normalization | PASS |
| 2 domain parity skew | PASS |
| 3 benchmark 35 | PASS (35/35) |
| 4 zero conversational FP | PASS (0/5) |
| 5 latency sub-ms | PASS (p99 242µs) |
| 6 live Hermes hook | PASS |
| 7 git production hygiene | PASS (main d1de873, dev==origin/dev) |

Tambahan: fuzz metamorphic stress_bad=0; stress fast+slow 0; Unicode 5000/0;
tanpa panic.

## Koreksi diri (gaya A1)

1. **Daftar 18 kegagalan user keliru di satu titik**: B22 sudah PASS sejak
   AUDIT C; penggantinya B26. Saya verifikasi dari RUN, bukan dokumen.
2. **Draf awal desain P1 salah menghitung sensitivitas**: saya tulis margin 5%
   menangkap G02/G04/G05, padahal G02=7.09 < batas 7.10. Setelah dihitung
   ulang, yang menangkap ketiganya adalah margin **8%**. Dikoreksi di doc
   sebelum commit. Ini human-error saya, bukan bug engine.
3. **Evaluator held-out pertama saya salah**: `expect_status` multi-nilai
   dicek dengan AND (harusnya OR seperti `check_case`), membuat HO29
   (`k8s` → HUNT, yang **benar**) sempat tercatat FAIL. Diperbaiki; held-out
   final 43/52. File held-out tidak diubah (hash sama).
4. **H06 tidak dipaksa lulus**: `penj4l4n` menurut aturan leet (4→a) menjadi
   `penjalan` yang bukan kosakata. Memetakan 4→u akan melanggar aturan yang
   Anda berikan, jadi dilaporkan sebagai gap.
5. **Latensi naik** p99 213→242µs masih jauh di bawah 1ms; tidak ada
   optimasi yang dilakukan (P5 memang hanya mengukur).

## Status akhir & STOP

- `dev` = commit laporan ini; `origin/dev` = sama setelah push; `main = d1de873`.
- **BERHENTI.** P1 implementasi dan P2 implementasi menunggu persetujuan.
  Tidak ada merge ke main, tidak ada θ₀ yang diubah.
