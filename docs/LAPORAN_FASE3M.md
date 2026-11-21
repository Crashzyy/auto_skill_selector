# Fase 3m — Laporan akhir (FONDASI PENGUKURAN)

## State

- HEAD = **`30ca38a`** saat mulai (konfirmasi: bukan `da1738d` — itu satu
  commit lebih awal, pengisi hash laporan 3l). `main = d1de873` tidak
  disentuh (kode maupun runner). Tidak ada merge/force push.
- Final `dev = <lihat commit terakhir>`, clean. Tidak ada perubahan `src/`,
  `trainer`, `lexicon`, `probe`, `deskripsi`, margin, atau ekspektasi.
- θ₀ dilaporkan sebagai **angka artefak + sha**: `7.529`,
  `a6a14d6adf11a8c04f3bc6ef2b95659937913efed332c32d7b8d868b8ceadd3a`,
  bukan lagi "7.4688 tidak diubah".

## 0a–0c — Snapshot & forensik

- Sandbox TZ **UTC** (`Etc/UTC`), `date -u 2026-11-21T13:15:59Z`.
- Path bersama `/tmp/hermes-sandbox/plugin-data/auto_skill_selector/skill_model.json`:
  sha `a6a14d6a…`, mtime **12:15:57.304848773 UTC**, 2.120.902 B,
  `threshold 0.6`, `null_anchor_score 7.529`, 144 kelas.
- Snapshot disalin ke `/tmp/model_snapshot_3m/skill_model.json`, chmod 444.
- **0b**: `HERMES_HOME` shell = `/data/home/.hermes` (produksi), tetapi
  direktori `plugin-data/auto_skill_selector/` produksi **kosong** — tidak
  ada model produksi terpisah. Gerbang 6 memakai `HERMES_HOME=/tmp/hermes-sandbox`.
  Jadi path bersama adalah sandbox uji, bukan model produksi. Tidak ada STOP.
- **0c**: mtime 12:15:57 UTC; tidak ada log `_retrain_worker`/
  `_handle_retrain` di jendela itu → **H2 (hook retrain) tidak didukung bukti**.
  Model memuat `calibration` (pos_min/pos_q1/neg_max/neg_bound/theta0),
  yang ditulis `trainer.calibrate_thresholds` (`trainer.py:825`) — dipakai
  oleh `train_and_save`. H1 (regenerasi 3l) dan H3 (nondeterminisme trainer)
  keduanya mungkin; 3× run di Langkah 2 membuktikan H3 nyata. Tidak
  menyimpulkan H1/H3 secara eksklusif tanpa bukti tambahan.

## Langkah 1 — Isolasi (commit `0026aa7`)

- `tests/isolate_3m.py` (setup/check/guard), `tests/isolate_3m_guard.py`.
- Semua evaluator + `diff_harness` memverifikasi sha model bersama dan abort.
- `benchmark_runner.run()`: `train_and_save` **default off**, hanya aktif
  dengan `--allow-train`; jika tidak, memuat model pinned.
- Main **tidak diedit**: dijalankan dari salinan tmp dengan override
  `HERMES_HOME`. (Catatan: commit `d1de873` tidak mengandung
  `benchmark_runner.py`; runner yang dipakai untuk skor main adalah evaluator
  kanonik dev yang dijalankan terhadap `.so` main dengan model pin — ini
  perbandingan engine yang adil, bukan "runner main".)
- Verifikasi: semua evaluator + 7 gerbang lolos; sha **dan** mtime bersama
  identik sebelum/sesudah (`a6a14d6a…`, 12:15:57).

## Langkah 2–5 — Determinisme & kanonik (commit `e759c90`)

- Trainer 3× tanpa korpus → sha identik, θ₀ 1.0 (tidak ada probe positif).
- Trainer 3× dengan 144 skill → **sha berbeda**, θ₀ 7.523 / 7.5228 / 7.5288.
  Sumber paling mungkin: iterasi `set`/`dict` mengubah urutan penjumlahan
  float saat agregasi & kalibrasi (θ₀ berbeda ≤ 0.006). Trainer dinyatakan
  **nondeterministik**; file model dipin sebagai sumber kebenaran.
- Artefak asli 7.4688 **tidak ditemukan** (git, /tmp, wheel, docs hanya
  angka, tanpa sha/file).
- Ekuivalensi per kasus: 320 entri baseline docs, 8 beda — semuanya
  baseline **stale** (7 dari era P-FMT sebelum revert, 1 guard lama).
  Terhadap run aktual pasca-revert dengan model pin: **delta 0** di semua
  set (v2 155/167, v3 43/52, v4 29/38, v5 15/40, v6 28/41, v7 20/30,
  v8 15/30, v9 15/40, v10 16/30, guard 12/12, FMT_GUARD 10/10,
  FMT_ADV 7/14, b35 35/35, 7/7 gate).
- Kanonik: snapshot `tests/fixtures/model/skill_model.json`, sha
  `a6a14d6a…`, θ₀ 7.529. Dicatat **"re-baseline akibat kehilangan artefak
  (7.4688→7.529)"** — bukan penyetelan.

## Langkah 6 — Validasi, NEG_CONV, AUC

### Dev vs main (model identik terpin)

Skor canonik main → dev: v3 21→43, v4 12→29, v5 5→15, v6 14→28,
v7 7→20, v8 8→15, v9 0→15, v10 0→16, guard 4→12, FMT_GUARD 5→10,
FMT_ADV 4→7. **19 kasus PASS→FAIL** main→dev, mayoritas false-positive
dev (chitchat "oke siap"→sap-consultant, polisemi "blender di dapur",
topik "meeting about word"→HUNT). Tidak diperbaiki.

### NEG_CONV

- `docs/NEG_CONV.json`, 40 kasus (sapaan/persetujuan/penutup/interjeksi/
  frasa 1–3 kata), hash `63d37614…`, ekspektasi NO_SKILL ditulis sebelum
  probe, 0 duplikat.
- Hasil: **main 0/40 FP, dev 0/40 FP**. Catatan jujur: saya sengaja
  tidak menyalin 19 prompt PASS→FAIL 3l, jadi NEG_CONV tidak menangkap
  FP chitchat yang lebih panjang ("oke siap", "bikinan lokal…") — itu
  tetap dilaporkan dari tabel 19 kasus di atas.

### Separabilitas (θ tidak disentuh)

- Positif: 28 kasus b35 ber-`expect_skills` (semua lolos).
  Negatif: 129 kasus NO_SKILL/HUNT + NEG_CONV.
- **AUC (rank) = 0.9892**.
- Tabel ambang (hanya tabel, bukan rekomendasi mengubah θ):

| θ | TPR | FPR |
|---|---|---|
| 5.0 | 96.4% | 10.1% |
| 6.9 | 96.4% | 3.9% |
| 7.529 (artefak) | 96.4% | 0.8% |
| 8.0 | 96.4% | 0.8% |
| 10.0 | 96.4% | 0.8% |

TPR sudah 96.4% pada θ artefak; **tidak ada ambang lain yang menaikkan
TPR +10pp tanpa FPR naik**.

### Tabel keputusan (3n)

| Syarat | Aktual | Cabang |
|---|---|---|
| FP dev > main ≥3/40 dari NEG_CONV + bisect satu commit | 0 vs 0 | tidak berlaku |
| AUC < 0.85 | 0.9892 | tidak berlaku |
| AUC ≥0.85 + ada θ dengan TPR +10pp tanpa FPR naik | AUC ≥0.85, **tidak ada θ tersebut** | tidak berlaku |

**Kesimpulan**: tidak ada cabang perubahan yang memenuhi syarat. θ bukan
hambatan (AUC 0.9892, TPR 96.4%, FPR 0.8%). Masalah dev terletak pada
**fitur/leksikon** untuk chitchat panjang dan polisemi, bukan ambang.
Sesuai aturan, tidak ada implementasi; menunggu izin terpisah untuk
eksperimen leksikon seragam (dengan NEG_CONV + FMT_ADV_GUARD sebagai
gerbang keras dan v11 baru sebagai ukuran).

## Koreksi diri

1. Angka dev-vs-main 3k/3l saya nyatakan tidak valid dan **tidak dikutip**
   sebagai bukti; perbandingan baru memakai model pin identik.
2. Saya awalnya salah hardcode `mtime_ns` di guard; dikoreksi menjadi
   sha+size untuk abort dan mtime dicatat manual di MODEL_ARTIFACT.
3. Saya awalnya menulis "main memuat model trainer dev" sebagai penyebab;
   dengan model pin identik, perbedaan ternyata dari **engine**, bukan model.
4. NEG_CONV 0/40 tidak saya gunakan untuk menyembunyikan 19 FP panjang;
   keduanya dilaporkan.
5. Tidak ada ekspektasi, hash set, θ₀ manual, probe, deskripsi, margin,
   atau engine yang diubah.

## Status akhir

`dev = origin/dev = <lihat commit terakhir>`, `main = d1de873`, clean.
Model bersama tidak berubah selama fase ini. **BERHENTI.**
