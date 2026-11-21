# Laporan akhir Fase 3p

## Ringkasan

Mulai dari `dev@HEAD = 549f93d` (konfirmasi: benar; laporan 3o memang tidak
mencantumkan hash). `main = d1de873` tidak disentuh. Tidak ada merge,
force push, atau rewrite riwayat `dev`. Model terpin
`a6a14d6a…` dan taksonomi v2 `cdc001f4…` tidak berubah. Semua angka dari
binary hasil build ulang.

## Commit fase ini

| Commit | Branch | Isi |
|---|---|---|
| `91aee3e` | dev | `test: add held-out set v12` |
| `19e654e` | dev | `docs: freeze reconstructed alias map` |
| `38f98e2` | dev | `feat(lexicon): add single-category verb aliases` |
| `743b1c1` | dev | `docs: summarize final dev state` |
| `ffb2d97` | dev-clean | `feat(engine): replace router with staged six-step pipeline` |
| `24d1ff5` | dev-clean | `test: add benchmark and held-out suites` |
| `7b13fe8` | dev-clean | `docs: add audit and status reports` |
| `75fc7db` | dev-clean | `chore: add commit message lint` |

Semua pesan lewat `git commit -F` dan lolos lint. Audit riwayat `dev`
menemukan **99 dari 100 commit lama melanggar aturan baru**; tidak ada
riwayat yang diubah.

## Langkah 1 — v12

80 kasus, hash `a049524c0fea81eb7d5ed0adda41644b3c61259302d4e35da10e6e5ce8b5cfaf`.
Komposisi terverifikasi: parafrase 24, kontrol 12, negatif 16, polisemi 8,
typo 8, ellipsis 6, grup H 6. Nol duplikat dari 596 prompt, nol expect
ganda. Baseline tanpa alias: **38/80** (H 1/6, ellipsis 2/6, kontrol 9/12,
negatif 16/16, parafrase 7/24, polisemi 0/8, typo 3/8).

## Langkah 2 — Rekonstruksi

`docs/LEX_ALIASES_V2.json`, sha `e9e0d1a1…`: 91 pasangan, 86 di antaranya
baru (lima sudah ada di leksikon dasar). Rekonstruksi scratch menghasilkan
persis 86 alias baru dan angka yang sama dengan 3o: 14 kunci delta (13
benar, 4 netral pada 17 baris), v2 156/167, v6 30/41, v7 23/30, v8 17/30,
v9 16/30, v10 18/30, v11 27/36. Tidak ada selisih, jadi Langkah 3–5
dilanjutkan.

## Langkah 3 — Atribusi

14 kunci delta terverifikasi: **14 jalur (i) skor IDF naik**, 0 jalur
(ii) pengecualian `unknown_tool`, 0 jalur (iii) fuzzy/typo, 0 jalur (iv).
Jumlah 14 = total 14. Hipotesis 3o bahwa alias bekerja sebagai tambalan
kosakata pada deteksi `unknown_tool` **tidak didukung data baru**.

## Langkah 4 — Evaluasi v12 (out-of-sample)

Total **38/80 → 43/80**. I = 5 kasus (S002, S009, S015, S021 parafrase;
S025 kontrol), R = 0. Grup H tidak berubah (1/6), FP negatif tidak naik
(16/16). Parafrase 7/24 → 11/24 (+4), kontrol 9/12 → 10/12; grup lain
tetap. Semua kriteria sukses terpenuhi. v10 dan v11 total tetap 18/30 dan
27/36, sama dengan 3o.

Gerbang keras: diff-harness tidak ada delta "salah"; FMT_ADV_GUARD 7/14
per kasus; NEG_CONV 0/40; NEG_CONV2 4/5; v2 156/167; b35 35/35; negasi
6/6; guard 12/12; FMT_GUARD 10/10; 7/7 gerbang. p99 tiga run:
240.8, 240.8, 242.4 µs — median **240.8 µs**, rentang 240.8–242.4 µs,
naik 2.7% dari baseline, di bawah batas 10%.

## Langkah 5–6 — Keputusan dan penutupan

Karena semua kriteria lulus, perubahan leksikon di-commit sebagai
`38f98e2`. Build ulang dari commit itu menghasilkan angka yang identik
dengan scratch. `docs/STATUS_DEV.md` (`743b1c1`) merangkum metrik akhir,
artefak model, keterbatasan, eksperimen yang ditolak, dan kesiapan merge.

## Langkah 7 — Branch riwayat bersih

`dev-clean` dibuat dari `d1de873` dengan 4 commit logis. Commit pertama
`ffb2d97` terbukti bisa di-build. `git diff dev dev-clean` **kosong**
(trees identik). Keempat pesan lolos lint. Branch sudah di-push sebagai
`origin/dev-clean` tanpa force push; `main` dan `dev` tidak berubah.

## In-sample vs out-of-sample

- In-sample (dev): v2 156/167, b35 35/35, v3 43/52, v4 29/38, v5 15/40,
  v6 30/41, v7 23/30, v8 15/30, v9 16/30, guard 12/12, FMT_GUARD 10/10,
  FMT_ADV_GUARD 7/14.
- Out-of-sample (held-out terpakai): v10 18/30, v11 27/36, v12 43/80.
- Jumlah I+R = 5+0 = 5 = selisih total v12 (43−38), terverifikasi.

## Koreksi diri

1. Rekonstruksi awal menghasilkan 91 entri, bukan 86; selisihnya adalah
   lima alias yang memang sudah ada di leksikon dasar. Keduanya dicatat.
2. Atribusi awal saya memasukkan baris yang tidak berubah status dan
   menghitung 17, bukan 14; setelah memakai kunci delta harness, jumlah
   jalur sama dengan 14.
3. Saya tidak mengubah alias atau taksonomi setelah hasil, tidak menaikkan
   θ, tidak melonggarkan kriteria, dan tidak mengeksekusi merge.
4. Selama fase ini sha model pin dan hash set tetap.

## Status akhir

`dev = 743b1c1`, `dev-clean = 75fc7db`, `origin/dev-clean = 75fc7db`,
`main = d1de873`. Keduanya clean. **Berhenti.** Merge ke main menunggu
persetujuan.
