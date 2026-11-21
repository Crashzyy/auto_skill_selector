# Kesiapan merge

## Status branch dan hash

- `dev = b082513` saat audit awal, lalu `1fe6e4d` (NEG_LIVE), `1226a6f`
  (pemetaan status). `dev-clean` mengikuti dengan commit sinkronisasi.
- `main = d1de873`, tidak disentuh. `git diff dev dev-clean` akan diverifikasi
  kosong setelah sinkronisasi akhir.
- Total commit `dev`: **108** saat awal fase (94 sejak `d1de873`).

## G1 — Clone bersih

Clone `origin/dev-clean` ke direktori baru, venv baru, `HERMES_HOME` baru,
model dipasang dari `tests/fixtures/model/skill_model.json`. Build dari nol.
Semua evaluator memberi angka identik dengan workspace: v3 43/52, v4 29/38,
v5 15/40, v6 30/41, v7 23/30, v8 17/30, v9 16/30, v10 18/30, v11 27/36,
v12 43/80, guard 12/12, FMT_GUARD 10/10, FMT_ADV_GUARD 7/14, v2 156/167.
7/7 gerbang lolos. p99 tiga run: 242.3, 249.3, 253.8 µs — median **249.3 µs**,
rentang **242.3–253.8 µs**. **Lulus** (dengan catatan: dependensi Python
dipakai ulang lewat `PYTHONPATH` dari venv sandbox; tidak ada instalasi
jaringan).

## G2 — Main native versus dev

Pemetaan status ditulis lebih dulu di `docs/MAIN_VS_DEV_MAPPING.md`.
Build main berhasil, tetapi pelatihan model native main dengan trainer main
tidak selesai dalam batas waktu tooling (lebih dari tujuh menit, proses
dihentikan sebelum menulis model). Sesuai instruksi, langkah ini **dilewati
dan dilaporkan**, bukan diganti dengan model dev. Tidak ada angka main
native yang dikutip; perbandingan 3k–3m juga tetap tidak valid.

## G3 — NEG_LIVE

`docs/NEG_LIVE.json`, 150 kasus, sha
`01d716b74b916db8a0498c6eaefdc675bea5ae53e109ed507fdef0ac06b4a8f7`,
ekspektasi ditulis sebelum probe, nol duplikat. Komposisi: percakapan 50,
informasional 40, verba taksonomi sebagai kata biasa 40, kalimat panjang 20.

Hasil: pra-alias **29/150 FP**, HEAD **31/150 FP**, selisih **+2**.
Kriteria: FP HEAD ≤ 2 dan FP HEAD − FP pra ≤ 0. **Keduanya gagal**.
Dua kasus baru yang menjadi FP: `L101` (rapikan → tabular) dan `L102`
(agregasi → tabular); `L119` juga berubah NO_SKILL→MATCHED. Ini **blocker**
dan tidak diperbaiki.

## G4 — Retrain dan jalur model

Pemicu otomatis:
- `on_skill_lifecycle` → `_spawn_retrain()` → `_retrain_worker()` →
  `trainer.train_and_save()`; terdaftar default di `register_hook`.
- `on_subagent_stop` → `_spawn_retrain()`; juga terdaftar default.
- `/skill-brain retrain` → `_handle_retrain()`; opt-in.
- CLI `trainer.py` → `train_and_save()`; opt-in.

Semua pemicu menulis ke `plugin-data/auto_skill_selector/skill_model.json`
milik `HERMES_HOME` aktif, sehingga dapat menimpa model terpin. Direktori
produksi `/data/home/.hermes/plugin-data/auto_skill_selector/` ada tetapi
**kosong**; tidak ada prosedur terdokumentasi untuk memasang model pin ke
produksi. Saat model tidak ada, `_ensure_brain()` mengembalikan brain tanpa
model dan memicu `HUNT_NEW_SKILL` untuk prompt sah.

Uji terisolasi: satu retrain menghasilkan θ₀ 7.5058 (pinned 7.529), tetapi
**0 perubahan status/skill** di seluruh suite. Nondeterminisme tidak
mengubah perilaku pada kasus yang diuji, namun artefaknya berubah.
**Blocker**: pemicu default-on dapat menimpa model tervalidasi, dan jalur
pemasangan model produksi tidak terdokumentasi.

## Keterbatasan yang diterima

- Polisemi 0/8 di v12; parafrase 11/24.
- Held-out terpakai gabungan 88/146 (60%) bersifat adversarial, bukan
  estimasi akurasi lalu lintas nyata.
- W01–W10 spec-mismatch di v5; NEG_CONV2 4/5 FP.

## Perintah merge (TIDAK dieksekusi)

Branch `dev-clean` berbasis `d1de873`, jadi merge ke main adalah fast-forward:

    git checkout main
    git merge --ff-only dev-clean

Tag pra-merge yang diusulkan pada `d1de873`:

    git tag -a pre-merge-fase3 -m "Pre-merge checkpoint" d1de873

Rollback (jika main sudah bergerak setelah merge):

    git revert --no-edit <merge-commit>
    git push origin main

Semua perintah di atas **hanya usulan**; tidak ada yang dijalankan.

## Verdict

**BELUM SIAP.** G1 lulus, tetapi G3 dan G4 menghasilkan blocker nyata:
alias menambah dua FP pada 150 kasus percakapan, dan hook default-on dapat
menimpa model tervalidasi tanpa jalur pemasangan produksi yang jelas.
G2 tidak menghasilkan data karena keterbatasan tooling, bukan karena main
gagal. Rekomendasi: selesaikan G3/G4 dalam mandat terpisah sebelum merge.
