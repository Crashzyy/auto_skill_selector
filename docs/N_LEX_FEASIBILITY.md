# Fase 3n Langkah B — Kelayakan leksikon

## B1 — Peta konsumsi

| Komponen | Konsumsi `lexicon_id_en.json` | Catatan |
|---|---|---|
| Runtime engine `src/lib.rs` | `include_str!("../lexicon_id_en.json")` → `en_to_id`, `id_to_en`, slang | **compile-time embed**; perubahan alias butuh rebuild, **tanpa retrain** |
| Trainer `trainer.py` | `_load_lexicon()` → `known_vocab`, `en_to_id`, `id_to_en` saat `build_model` | hanya dipakai saat `train_and_save` (dilarang di fase ini) |
| Model terpin | sudah berisi idf/feature dari training lama | tidak berubah saat alias ditambah |

**Uji worktree scratch dengan model terpin:**
1. Alias dummy tak terpakai (`zzqqxx-unused-probe`) → rebuild → diff harness
   528 kasus: **0 delta** (benar).
2. Alias terpakai `en_to_id["perbaiki"]="debug"` → rebuild → **3 delta**,
   semuanya benar: X35, Y26, Z26 HUNT→MATCHED `automated-testing-debugging`.

Simpulan B1: **runtime-only + rebuild cukup; retrain TIDAK diperlukan.**
Model kanonik sha tetap `a6a14d6a…` (guard lolos).

## B2 — Klasifikasi 10 kontrol gagal v6–v9

| ID | Target | Kata kunci | Kelas | Catatan |
|---|---|---|---|---|
| X35 | backend-api-code-review | perbaiki | (ii) | "perbaiki" tidak di deskripsi; jembatan alias terbukti |
| Y26 | backend-api-code-review | perbaiki | (ii) | sama |
| Z26 | backend-api-code-review | perbaiki | (ii) | sama |
| P28 | backend-api-code-review | perbaiki/kesalahan | (ii) | sama |
| Y18 | invoice-ledger-reconciliation | hitung | (i) | "hitung anuitas" ada, tapi bobot lemah |
| Z20 | invoice-ledger-reconciliation | omzet | (ii) | tidak di deskripsi; jembatan alias "omzet"→"faktur" |
| P23 | tabular-pivot-cleaning | jumlahkan | (ii) | "agregasi" ada, kata kerja tidak; jembatan alias |
| Y19 | bilingual-translation | terjemahkan | (ii) | "penerjemahan" ada, verb tidak |
| Z21 | bilingual-translation | terjemahkan | (ii) | sama |
| P30 | bilingual-translation | alihkan | (ii) | sama |

Kelas (iii) — skill target tidak ada di 144 kelas: **0** (semua target ada:
`bilingual-translation` ada meski tidak terlihat di top-1).

Hitungan:
- (i) kata ada tapi bobot lemah: **1**
- (ii) celah leksikon, bisa dijembatani alias: **9**
- (iii) spec mismatch: **0**
- Total 10 = 1+9+0 (cek lolos, bucket non-tumpang tindih).

## B3 — Keputusan cabang

- Runtime-only **dan** 9/10 (≥50%) bisa dijembatani alias → **LANJUT ke C/D**.
- Tidak butuh retrain → tidak ada STOP.
- (iii) = 0 → tidak ada STOP.

Catatan jujur: 9 kasus (ii) baru **dibuktikan jembatan aliasnya** untuk
kelompok code/debug (3/4). Untuk numerik/translasi, jembatan masih
hipotesis berdasarkan struktur `en_to_id` → IDF key yang ada; akan diuji
di Langkah D, bukan dianggap sudah berhasil.
