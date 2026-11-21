# Fase 3k — Laporan akhir (READ-ONLY)

## State

- HEAD = **`8240e80`** (konfirmasi: **bukan `5016b28`** — itu tiga commit
  lebih awal). `main = d1de873`, `dev = origin/dev = 8240e80` saat mulai,
  clean. θ₀ 7.4688, margin P1b, probe, deskripsi, engine: **tidak diubah**.
  Tidak ada merge, tidak ada force push.
- Kedua binary (`d1de873` dan `8240e80`) di-build ulang dengan venv sama.
- Komit dokumen/fixture saja: `885bb8a` (v10). Final `dev = 885bb8a`.
- v9 **menjadi dev set** karena kegagalannya sudah dibedah di Fase 3j;
  v10 = held-out bersih.

## Langkah 1 — dev vs main

`docs/K_DEV_VS_MAIN.md`, output mentah `docs/K_DIFF_MAIN_VS_DEV.txt`.
498 kasus, **379 delta**; klasifikasi dari output mentah:
**benar 185, salah 20, netral 174**. Skor main→dev di semua set naik:
b35 5→35, v2 33→65¹, v3 18→31, v4 11→25, v5 5→16, v6 14→28,
v7 7→20, v8 8→15, v9 0→15, FMT_ADV 4→7, FMT_GUARD 5→10,
P2A_GUARD 4→12. (¹ angka ad-hoc harness; kanonik v2 = 155/167.)

Kesimpulan: efek bersih Fase 2–3j sangat positif dan **tidak ada indikasi
untuk merge lebih awal** — dev sudah jauh di depan main. Evaluasi kandidat
merge tetap butuh keputusan terpisah.

## Langkah 2 — Audit rank/margin

`docs/K_AUDIT_RANK.md`. Skor per skill **tersedia** (`debug_topk`),
jadi tidak ada STOP. 51 kasus MATCHED-expect gagal, dedupe.

| Kelas | N | % |
|---|---|---|
| R4 — bypass Stage 0 / top=0 | 10 | 19.6% |
| R3 — target luar top-3 | 0 | 0% |
| R2 — target rank 2–3 | 0 | 0% |
| R1 — target top-1 tapi skor < θ₀ / gate menolak | **41** | **80.4%** |

Histogram R1: 8 kasus skor > θ₀ tapi ditolak gate; 7 kasus gap 0–0.9;
3 kasus gap 1–1.9; 5 kasus gap 3–3.9; 7 kasus gap 4–4.9; 8 kasus gap
5–5.9; 3 kasus gap ≥ 6.

Metode disclosure: target untuk set tanpa `expect_skills` diinfer dari
`analyze_prompt().skills` atau top-1 `debug_topk`; maka R2/R3 = 0 adalah
konsekuensi metode, bukan bukti ranking engine sempurna.

## Langkah 3 — Konsentrasi per skill

Bucket **non-tumpang tindih**, jumlah = **51 = total kasus** (cek lolos):
tabular 9, word-docx 7, excel-xlsx 6, pdf 4, boring-marketing 4,
backend-api-review 4, sql 3, powerpoint 3, invoice 3, lainnya 8.
Konsentrasi moderat (tabular+word+excel 22/51 = 43%), tidak dominan
pada satu skill > 20%.

## Langkah 4 — v10 beku & baseline

- 30 kasus Q01–Q30, hash
  `628bece6e31c6fcc56325a4a2d41d210b3a3d88002c51cdebe63b6a3ad8d11d4`,
  0 duplikat dari 486 prompt, 0 expect ganda, ekspektasi sebelum probe.
- Baseline sekali di `8240e80`: **16/30** — parafrase 3/10, kontrol 7/10,
  ellipsis 3/5, typo 3/5.

### Tabel lintas set (in-sample vs out-of-sample)

| Set | Skor | % | Kelas |
|---|---|---|---|
| v2 | 155/167 | 92.8% | dev (in-sample) |
| b35 | 35/35 | 100% | dev (regresi) |
| v3 | 43/52 | 82.7% | dev |
| v4 | 29/38 | 76.3% | dev |
| v5 | 15/40 | 37.5% | dev (10 spec-mismatch) |
| v6 | 28/41 | 68.3% | dev |
| v7 | 20/30 | 66.7% | dev |
| v8 | 15/30 | 50.0% | dev |
| v9 | 15/30 | 50.0% | dev (baru dipromosikan) |
| guard / FMT_GUARD / FMT_ADV | 12/12, 10/10, 7/14 | — | dev (guard) |
| **v10** | **16/30** | **53.3%** | **held-out (out-of-sample)** |

Kesenjangan v2 92.8% vs v10 53.3% tetap besar; parafrase 3/10 inti gap-nya.

## Langkah 5 — Tabel keputusan

| Kondisi | Ambang | Aktual | Cabang? |
|---|---|---|---|
| R3 ≥ 50% → leksikon/alias/deskripsi | ≥ 50% | 0% | tidak |
| R1 ≥ 50% & gap kecil → kebijakan decision gate | ≥ 50% | **80.4%** (15/41 gap ≤ 0.9 atau negatif) | **YA** |
| R4 ≥ 30% → bypass Stage 0 | ≥ 30% | 19.6% | tidak |
| Tidak ada kelas ≥ 50% → bekukan engine + evaluasi merge | — | ada R1 ≥ 50% | tidak |

**Cabang terpilih: R1 — tuas kebijakan decision gate**, bukan θ₀.
Alasan: R1 80.4% dan 15 dari 41 kasus R1 berada di dekat/atas θ₀ (tolakan
gate/ban/gray-zone), sehingga menaikkan θ₀ justru akan menolak lebih banyak
kasus benar. Rekomendasi mekanisme: parameter **terpisah** seperti zona
CLARIFY (analog P1b), diukur dengan ablasi worktree — **bukan** mengubah
θ₀, probe, deskripsi, atau ekspektasi. Untuk 23 kasus R1 gap besar,
tuas leksikon/alias tetap diperlukan, tapi itu cabang kedua dan butuh
izin terpisah (dilarang di phase ini).

## Koreksi diri

1. Skor v2 dari harness ad-hoc (65) berbeda dengan kanonik (155/167);
   saya labeli jelas dan tidak memakainya untuk gate.
2. R1 awal saya hitung dengan `debug_topk(mode=2)` tanpa sadar mode itu
   mengabaikan ban, sehingga 8 kasus tampil "skor > θ₀ tapi gagal";
   saya pisahkan sebagai decision-gate rejects, bukan under-threshold.
3. Saya tidak menyetel ekspektasi v10 (parafrase 3/10 rendah) agar
   laporan terlihat bagus; itu baseline apa adanya.
4. Tidak ada engine, θ₀, probe, deskripsi, margin, atau hash set mana pun
   yang diubah; phase ini murni read-only + fixture baru.

## Status akhir

`dev = origin/dev = 885bb8a`, `main = d1de873`, clean. Worktree main
dibuang. **BERHENTI.** Semua implementasi (kebijakan decision gate,
leksikon/splitter, merge) menunggu izin terpisah.
