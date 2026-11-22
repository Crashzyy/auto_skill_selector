# Fase 3t — keputusan

## Metrik utama (model produksi, rata-rata 3 run identik)

| Metrik | Nilai |
|---|---|
| PROD_V1 top-1 | 83/120 (69.2%) |
| PROD_V1 top-3 | 94/120 (78.3%) |
| Decision accuracy | 83/120 (69.2%) |
| FP natural NEG_LIVE | 14/90 |
| NEG_CONV | 0/40 |
| AUC (83 positif vs 190 negatif) | 0.9727 |
| R1/R2/R3/R4 | 77/12/22/9 = 120 |

Bahasa: ID 45/60 top-1, EN 11/20, MX 27/40. Tipe: P 42/60, E 41/60.
FP natural 14/90 tersebar: 2 skill teratas hanya 2+2 dari 14, tidak ada
konsentrasi ≥60% (Branch D tidak berlaku).
Efek alias: 0/120 perubahan pada PROD_V1; FP natural 14→14. Stabilitas: 0
kasus berbeda antar tiga run.

## Tabel ambang (skala produksi)

| θ' | TPR | FPR | FP natural/90 |
|---|---|---|---|
| 1.5606 (artefak) | 100.0% | 17.9% | 10 |
| 2.0 | 98.8% | 16.8% | 3 |
| 3.0 | 90.4% | 5.8% | 3 |
| 5.0 | 62.7% | 2.6% | 1 |

Pada θ'=2.0, FP natural 3/90 ≤6 dan TPR 98.8% ≥ 90% (batas cabang A).
**Branch A (kalibrasi)** berlaku: top-3 ≥70% dan ada ambang yang memenuhi.
Mandat berikutnya: kalibrasi θ per-korpus. Tidak diimplementasi di fase ini.

## Diagnosis θ₀ 1.56 vs 7.53

`trainer.calibrate_thresholds` memakai 12 probe positif tetap
(`CALIBRATION_POS_PROBES`) yang menyebut skill korpus sandbox: SQL/KPI,
Blender, siniar, infografis, DCF/WACC, SEO, PDF, arXiv, Dockerfile/React,
CSV/pivot, notula, PowerPoint — hampir semuanya absen di korpus produksi.
Skor positif produksi runtuh ke `pos_min` 1.643, sementara 10 probe negatif
bersifat umum tetap `neg_max` 3.025. Karena `neg_bound` (3.303) > `pos_min`,
`gap` di-clamp ke 0.05 dan θ₀ = 3.303+0.0175 = 3.32, lalu dibatasi
`min(theta0, pos_min*0.95)=1.56`. Model 144: pos_min 12.541, neg_bound 4.830,
θ₀ 7.529. Ini bukti kode+data, bukan dugaan.

## Step 4

Fixture `NEG_CONV` kini ikut di wheel (terverifikasi dalam zip),
`_neg_conv_cases` melempar `FileNotFoundError` bila tidak ada, sehingga R2b
fail-closed. Enam uji terisolasi lulus. 7/7 gerbang dan semua evaluator
identik. p99 3 run: 233.8 µs (dari pengukuran workspace); tidak naik.

## Verdict

**BELUM SIAP.** Decision accuracy PROD_V1 69.2% < 70% dan FP natural
14/90 > 6 pada θ artefak.Branch A memberi jalan kalibrasi θ per-korpus,
tetapi itu memerlukan mandat terpisah karena θ terkunci. Perintah merge,
tag, dan rollback tetap usulan saja.

P4 tidak terverifikasi pada 3s; first-run dengan prompt PROD_V1 belum
diulang karena kriteria sudah gagal lebih awal.
