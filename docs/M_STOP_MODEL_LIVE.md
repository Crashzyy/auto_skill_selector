# Fase 3m — STOP di Langkah 1a (model LIVE tertimpa)

## State

- HEAD = **`da1738d`** (konfirmasi: **bukan `b7e712b`** — itu dua commit
  lebih awal, commit pengisi hash laporan). `main = d1de873` tidak disentuh
  (kode maupun runner). `dev = origin/dev = da1738d`, clean saat mulai.
- θ₀ konseptual 7.4688, margin P1b, probe, deskripsi, ekspektasi: tidak
  diubah. Tidak ada merge/force push. Tidak ada perubahan `src/`,
  `trainer`, `lexicon`.

## 1a — Peta artefak & insiden LIVE

### Pembaca / penulis `skill_model.json`

| Komponen | Peran | Path / baris |
|---|---|---|
| `trainer.py` | **PENULIS** (`_save_model` → `get_model_path().write_text`) | `trainer.py:971-972`, `train_and_save:992-1004` |
| `trainer.py` CLI | memanggil `train_and_save()` | `trainer.py:1016` |
| runner dev `benchmark_runner.py` | **pembaca** di `run_v2` (`:181-183`); **penulis tak langsung** via `t.train_and_save(root)` di `:353` saat gerbang stress | `benchmark_runner.py:181,353` |
| runner main `d1de873` | sama: `:353` `t.train_and_save(root)` — tidak diedit sesuai instruksi | worktree main |
| hook Hermes live (gerbang 6) | `_ensure_brain()` → `brain.reload(js)` dari `plugin_data_dir` | `__init__.py:74,122` |
| hook retrain (background + manual) | **PENULIS** `trainer.train_and_save()` | `__init__.py:364` (`_retrain_worker`), `:446` (`_handle_retrain`) |
| evaluator tests/v3–v10/guard, diff_harness, fuzz, stress | pembaca via `t.get_model_path()` → `reload` | `tests/eval_*.py`, `tests/diff_harness.py:17`, `tests/fuzz_metamorphic.py:70`, `tests/test_stress_regression.py:43` |

Semua jalur menunjuk ke **satu file bersama**:
`/tmp/hermes-sandbox/plugin-data/auto_skill_selector/skill_model.json`
(LEBAR: `AUDIT_REPORT_FASE2.md` mendokumentasikan 2,12 MB / 144 kelas).

### Bukti overwrite

- Saat mulai fase ini: **mtime 2026-11-21 12:15:57**, **ukuran 2.120.902 B**,
  sha256 **`a6a14d6adf11a8c04f3bc6ef2b95659937913efed332c32d7b8d868b8ceadd3a`**,
  `threshold = 0.6`, `null_anchor_score = 7.529`, 144 kelas.
- Catatan Fase 3l: runner main menimpa model bersama pukul **12:11**
  (`threshold 0.4477`, `null_anchor 0.4278`); saya saat itu meregenerasi
  dengan `trainer.py` dev → `null_anchor 7.5054`.
- Kini file berubah lagi pada **12:15:57** menjadi `7.529` dengan hash baru.
  Jadi **model jalur LIVE berubah/tertimpa berulang kali** dalam jendela
  12:11–12:15, dan nilai θ₀ tidak stabil pada 7.4688.

## STOP

Perintah eksplisit: *"Cek hash dan mtime model di jalur LIVE di sekitar
12:11. **Jika model live berubah/tertimpa: STOP, lapor segera.**"*
→ **BERHENTI di Langkah 1a.** Tidak menjalankan 1b–1e, Langkah 2–5.
Tidak ada perbaikan, tidak ada regenerasi, tidak ada evaluasi lanjutan.

## Yang diperlukan sebelum lanjut

1. Keputusan penulisan model: runner/evaluator **dilarang** menimpa model
   live; tiap proses harus memakai `HERMES_HOME`/direktori data terisolasi
   (ini akan dikerjakan di 1e bila diizinkan lanjut).
2. Artefak kanonik θ₀ 7.4688 harus dipulihkan atau dinyatakan hilang dengan
   re-baseline yang disetujui — saya tidak memilihnya diam-diam.
3. Izinkan lanjut ke 1b (determinisme trainer) setelah (1)–(2).

## Koreksi diri

Saya tidak mengklaim angka dev/main apa pun di fase ini: semua angka
perbandingan 3k/3l sudah dinyatakan tidak valid oleh perintah, dan insiden
live ini menguatkan alasannya. Tidak ada ekspektasi, hash set, θ₀ manual,
probe, deskripsi, margin, atau engine yang saya ubah.

## Status akhir

`dev = origin/dev = da1738d`, `main = d1de873`, clean. **BERHENTI.**
