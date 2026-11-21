# Fase 3l — STOP di Langkah 3 (kontrol gagal tersebar, tanpa mekanisme dominan)

## State

- HEAD = **`999409a`** (konfirmasi: **bukan `885bb8a`** — itu commit baseline
  v10, satu lebih awal). `main = d1de873`, clean saat mulai.
- θ₀ konseptual 7.4688, margin P1b, probe, deskripsi, engine: **tidak
  diubah**. Tidak ada merge/force push. Semua angka dari binary build ulang.
- Final `dev = 3b3d4b2`, clean.

## Insiden artefak model (jujur, penting)

Saat menjalankan `benchmark_runner.py` **main** di worktree, runner main
memanggil `t.train_and_save()` dan **menimpa model bersama**
`/tmp/hermes-sandbox/plugin-data/auto_skill_selector/skill_model.json`
(pukul 12:11). Model hasil overwrite punya `threshold 0.4477`,
`null_anchor_score 0.4278` — bukan kalibrasi dev. Akibatnya pengukuran
antara sempat melonjak (v7 25/30, v8 21/30, v9 24/30).

Saya deteksi lewat hash + field model, lalu **regenerasi model dari
`trainer.py` dev** (`train_and_save(calibrate=True)`), menghasilkan
`threshold 0.6`, `null_anchor_score 7.5054`. Setelah itu semua skor dev
kembali ke nilai Fase 3j: v2 155/167, v3 43/52, v4 29/38, v5 15/40,
v6 28/41, v7 20/30, v8 15/30, v9 15/40, v10 16/30, b35 35/35.
**θ₀ hasil training ulang = 7.5054, bukan 7.4688** — perintah melarang
mengubah θ₀ secara manual; saya tidak menyetelnya, hanya meregenerasi
artefak yang rusak. Ini dicatat sebagai keterbatasan, bukan hasil akhir
yang disembunyikan.

## Langkah 1 — Validasi dev vs main (evaluator asli)

Dokumen `docs/L_VALIDASI_MAIN.md`. Kedua binary build ulang; main wheel
0.1.0, dev 0.2.0; keduanya memuat model JSON yang sama (setelah
regenerasi). **Main tidak punya `lexicon_id_en.json`** (lexicon lama
di-embed), plus engine pra-rewrite → status `MATCHED_LOCAL`, tanpa
negation sieve/multi-skill.

Skor kanonik main → dev: b35 **4/35 → 35/35**, v2 **71/167 → 155/167**,
v3 21→43, v4 12→29, v5 5→15, v6 14→28, v7 7→20, v8 8→15, v3 0→15,
v10 0→16, guard 4→12, FMT_GUARD 5→10, FMT_ADV 4→7. Main 4/7 gate
(FAIL benchmark_35, conversational_fp, latency p99 2373.6µs).

**19 delta PASS→FAIL** menurut `expect_status` ORdirinci di dokumen; mayoritas adalah false-positive chitchat di dev ("oke siap" →
`sap-consultant`, "bye" → `lookdev`, dll), sisanya informational/polisemi/
multi. Tidak diperbaiki (dilarang).

## Langkah 2 — R dengan ground truth

`docs/L_R_GROUND_TRUTH.md`: hanya 28 kasus b35 punya `expect_skills`
eksplisit, **semuanya lolos** → tabel R1–R4 kosong; 16 kasus gagal
tanpa target dilaporkan terpisah sebagai "target tak diketahui" (rincian
v10 sengaja tidak dibuka). Angka R1 80.4% di Fase 3k **ditarik**
karena target diinfer dari top-1 (metode cacat).

## Langkah 3 — Diagnosis kontrol gagal (STOP)

10 kontrol gagal di v6–v9 (evaluator asli, bukan status-only):

| Kelompok | ID | N | Mekanisme |
|---|---|---|---|
| code/debug | X35, Y26, Z26, P28 | 4 | token lemah: `cek/perbaiki bug/kode` → `backend-api-code-review` top-1 ~3.5, gated ~5.35 < θ₀ |
| numerik/tabel | Y18, Z20, P23 | 3 | token lemah: `hitung/jumlahkan/omzet` → invoice/tabular ~2.9 |
| translasi | Y19, Z21, P30 | 3 | alias hilang: `terjemahkan/alihkan` → `boring-marketing-email-sequences` ~1.9 (bukan skill translasi) |

Bucket **4+3+3 = 10 = total** (cek lolos, non-tumpang tindih).
**Mekanisme terbesar 40% < 50%** → sesuai aturan: **STOP, laporkan,
jangan lanjut ke Langkah 4.**

Selain itu, ketiga kelompok adalah **keterbatasan leksikon/alias**
(kata kerja sehari-hari tidak terhubung ke skill yang tepat), bukan bug
satu mekanisme bersama yang bisa diperbaiki dengan satu aturan umum.
Perintah Langkah 3 menghendaki mekanisme dominan **dan** bug; syarat itu
tidak terpenuhi.

## Koreksi diri

1. Saya sempat mempercayai skor "melonjak" (v7 25/30) sebagai perbaikan;
   ternyata model bersama tertimpa oleh runner main. Saya deteksi via
   hash/field dan regenerasi, lalu melaporkan insiden daripada
   memakai angka itu.
2. Angka R1 3k ditarik karena inferensi target top-1 tidak dapat
   diverifikasi; ground truth hanya ada di b35 dan semuanya lolos.
3. Saya tidak membuka rincian per kasus v10; hanya skor pra 16/30 yang
   dipakai, sesuai instruksi.
4. Tidak ada ekspektasi, hash set, θ₀ manual, probe, deskripsi, margin,
   atau engine yang diubah; Langkah 4/5 tidak dijalankan.

## Status akhir

`dev = origin/dev = 3b3d4b2`, `main = d1de873`, clean.
Worktree main dibuang. **BERHENTI.** Perbaikan leksikon/alias dan
pembekuan artefak model menunggu izin terpisah.
