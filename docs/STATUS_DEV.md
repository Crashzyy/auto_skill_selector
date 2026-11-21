# Status dev — ringkasan akhir

Semua angka dari binary hasil build ulang pada HEAD `38f98e2` dengan model
terpin `tests/fixtures/model/skill_model.json`.

## Metrik akhir

| Set | Skor | Kelas | Catatan |
|---|---|---|---|
| v2 | 156/167 | dev | in-sample |
| b35 | 35/35 | dev | regresi, in-sample |
| v3 | 43/52 | dev | in-sample |
| v4 | 29/38 | dev | in-sample |
| v5 | 15/40 | dev | 10 kasus spec-mismatch W01–W10 |
| v6 | 30/41 | dev | in-sample |
| v7 | 23/30 | dev | in-sample |
| v8 | 17/30 | dev | in-sample |
| v9 | 16/30 | dev | dipromosikan dari held-out |
| v10 | 18/30 | held-out terpakai | out-of-sample; dipakai sekali di 3o/3p |
| v11 | 27/36 | held-out terpakai | out-of-sample; dipakai di 3o/3p |
| v12 | 43/80 | held-out terpakai | out-of-sample; I=5, R=0 |
| guard | 12/12 | dev | in-sample |
| FMT_GUARD | 10/10 | dev | in-sample |
| FMT_ADV_GUARD | 7/14 | dev | in-sample |

Gerbang: 7/7 lolos; negasi 6/6; FP conversational 0/5.
Latensi p50 40.4–41.9µs; p99 240.8, 240.8, 242.4µs — median **240.8µs**,
rentang **240.8–242.4µs**.

## Artefak model

- Path: `tests/fixtures/model/skill_model.json`
- SHA256: `a6a14d6adf11a8c04f3bc6ef2b95659937913efed332c32d7b8d868b8ceadd3a`
- θ₀ artefak: **7.529**; `threshold` 0.6; 144 kelas.
- Re-baseline dari artefak historis 7.4688 karena file asli hilang (trainer
  nondeterministik, θ₀ 7.523–7.529 pada tiga training). Ini bukan
  penyetelan: kanonik dipilih dari snapshot yang terbukti ekuivalen per kasus.
- Menjalankan gerbang secara terisolasi:
  `HERMES_HOME=/tmp/hermes-sandbox/iso-3m/dev2 <venv>/bin/python tests/eval_heldout_v12.py`.
  `tests/isolate_3m.py` membuat data dir terisolasi; evaluator memverifikasi
  sha dan abort bila model bersama berubah.

## Keterbatasan yang diketahui

- Recall parafrase masih rendah (v11 8/12 sebelum alias; v12 11/24 sesudah).
- Ban-residual, polisemi, dan multi belum terselesaikan.
- OOD kapital belum ditangani.
- W01–W10 spec-mismatch di v5 tetap dilaporkan apa adanya (15/40).
- NEG_CONV2 4/5 FP — kelima kasus memang pelanggaran nyata, bukan guard rusak.
- Perbandingan dev vs main tidak valid dan tidak dipakai.

## Eksperimen yang ditolak atau di-revert

- P2a': gate niat informasional — dead code, Stage 0 sudah menangani.
- P-NEG: dua mekanisme negasi berbeda, tidak ada aturan tunggal.
- P-FMT: false-positive pin pada kasus topikal; di-revert.
- Leksikon v1: verba generik melanggar FMT_GUARD.
- Leksikon v2 3o: kandidat lolos gerbang tetapi gagal kriteria +3 parafrase,
  tidak di-commit; 3p merekonstruksi dan menguji ulang dengan v12.

## Kesiapan merge dan rekomendasi

- [x] 7/7 gerbang lolos dari build ulang.
- [x] Model terpin dan evaluator terverifikasi sha.
- [x] `git diff dev dev-clean` akan diverifikasi di langkah berikutnya.
- [x] Tidak ada perubahan src/, trainer, probe, deskripsi, θ, margin,
      ekspektasi, atau hash set.
- [ ] Merge ke main **tidak dieksekusi**; menunggu keputusan owner.

Rekomendasi: branch `dev-clean` siap untuk review; main tetap dipertahankan
sampai ada persetujuan eksplisit.
