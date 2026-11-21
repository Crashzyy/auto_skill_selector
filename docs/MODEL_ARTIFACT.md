# MODEL_ARTIFACT — kanonik (Fase 3m)

## Artefak kanonik

- Path terpin: `tests/fixtures/model/skill_model.json` (chmod 444)
- **SHA256: `a6a14d6adf11a8c04f3bc6ef2b95659937913efed332c32d7b8d868b8ceadd3a`**
- Ukuran: 2.120.902 bytes
- θ₀ artefak (`null_anchor_score`): **7.529**
- `threshold`: 0.6; `calibration.theta0`: 7.529;
  `calibration.pos_min`: 12.5408, `pos_q1`: 15.512, `neg_max`: 4.4113,
  `neg_bound`: 4.8304; 144 kelas.
- Sumber: snapshot 0a dari path bersama
  `/tmp/hermes-sandbox/plugin-data/auto_skill_selector/skill_model.json`
  pada 2026-11-21 13:15:59 UTC (mtime asal 12:15:57 UTC).

Ini **bukan** penyetelan θ₀. θ₀ dilaporkan sebagai angka artefak + sha.
Angka historis 7.4688/7.5054 adalah nilai artefak lama yang tidak lagi
terdapat di sistem; pemilihan kanonik didasarkan bukti per kasus (Langkah 4),
bukan dekret.

## Status θ₀ historis (dari docs, bukan artefak yang tersedia)

| Nilai | Sumber | Bukti artefak |
|---|---|---|
| 7.4688 | laporan Fase 3b–3k | file asli tidak ditemukan; hanya teks docs |
| 7.5054 | regenerasi 3l | file tertimpa kemudian |
| 7.529 | artefak bersama 12:15:57 | **snapshot + sha di atas** |

## Determinisme trainer (Langkah 2)

- 3× di direktori terisolasi **tanpa korpus skill** → sha identik
  `8118e6ec…`, θ₀ 1.0 (kalibrasi tidak ada probe positif).
- 3× dengan 144 skill korpus → sha **berbeda-beda**:
  `82366527…` (θ₀ 7.523), `4fe91de2…` (7.5228), `3bfabf1a…` (7.5288).
- Simpulan: trainer **nondeterministik** pada kalibrasi penuh. Tidak ada
  `random.seed`/`shuffle` eksplisit; sumber paling mungkin adalah iterasi
  `set`/`dict` yang mengubah urutan penjumlahan floating-point saat
  agregasi fitur & probe kalibrasi (perbedaan θ₀ ≤ 0.006).
- Konsekuensi: **file model terpin dipakai sebagai sumber kebenaran**;
  `trainer.train_and_save` tidak dipakai untuk membuat baseline. Runner
  sudah diubah (default off, butuh `--allow-train`).

## Isolasi (Langkah 1)

- `tests/isolate_3m.py` membuat `HERMES_HOME` per proses dengan model pin.
- `tests/isolate_3m_guard.py` + evaluator memverifikasi sha model bersama
  dan abort bila berubah.
- `benchmark_runner.run()` tidak lagi memanggil `train_and_save` kecuali
  flag eksplisit `--allow-train`.
- Main tidak diedit: dijalankan dari salinan tmp dengan `HERMES_HOME`
  override. Verifikasi 7/7 gate + semua evaluator: sha **dan** mtime bersama
  identik sebelum/sesudah (`a6a14d6a…`, 12:15:57.304848773 UTC).

## Ekuivalensi per kasus (Langkah 4)

- 320 entri baseline docs (v2–v9 + guard) dibandingkan status + skill.
- 312 cocok; 8 beda, semuanya baseline **stale**:
  - 7 × `HELDOUT_V8_BASELINE_HEAD.txt` (Y01,Z01,Z08,Z09–Z13) berasal dari
    era P-FMT sebelum revert `db7ea9f`;
  - 1 × `FMT_GUARD_BASELINE.txt` F01 dari guard lama sebelum koreksi F01.
- Terhadap **run aktual pasca-revert** (pinned model): semua set cocok persis:
  v2 155/167, v3 43/52, v4 29/38, v5 15/40, v6 28/41, v7 20/30,
  v8 15/30, v9 15/40, v10 16/30, guard 12/12, FMT_GUARD 10/10,
  FMT_ADV 7/14; b35 35/35; 7/7 gate.
- Kasus zona abu lama `[6.871, 7.4688)` yang berubah dengan θ₀ 7.529:
  hanya 1 (X26, top 6.495) — sudah termasuk dalam grup stale di atas;
  tidak ada kasus baru yang berstatus CLARIFY akibat pergeseran θ₀.
- v10: hanya skor total 16/30 yang dipakai; rincian per kasus tidak dibuka.

Delta per kasus terhadap baseline aktuil = **0** → snapshot ditetapkan
kanonik sesuai aturan "re-baseline akibat kehilangan artefak".
