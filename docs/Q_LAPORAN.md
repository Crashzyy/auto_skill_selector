# Laporan akhir Fase 3q — validasi pra-merge

## Rekonsiliasi awal

- `dev@HEAD = 689618c` (konfirmasi: benar). `dev-clean = 324e768`,
  `main = d1de873`.
- Laporan 3p menyebut `dev=743b1c1` dan `dev-clean=75fc7db`: itu adalah HEAD
  **sebelum** commit laporan 3p. Selisihnya satu commit per branch,
  `docs: record phase results` (`689618c` di dev, `324e768` di dev-clean,
  cherry-pick dari commit yang sama). `git diff dev dev-clean` pada HEAD
  terbaru kedua branch **kosong**.
- Total commit `dev` = **108**; 94 commit sejak `d1de873`.
- `docs/STATUS_DEV.md` memiliki satu angka salah: v8 ditulis 15/30, padahal
  build ulang memberi **17/30**. Dikoreksi dalam commit `b082513`.

## Commit fase ini

| Commit | Branch | Isi |
|---|---|---|
| `b082513` | dev | koreksi skor v8 dan catatan hash |
| `1fe6e4d` | dev | `test: add conversational false-positive fixture` |
| `1226a6f` | dev | `docs: define cross-schema status mapping` |
| `4ccbea7` | dev | `docs: assess merge readiness` |
| `fffcdb0` | dev-clean | sinkronisasi laporan kesiapan |
| `73ca823` | dev-clean | sinkronisasi fixture dan status |

Semua pesan lewat `git commit -F` dan lolos lint.

## G1 — clone bersih

Build dari nol di direktori klon baru, venv baru, `HERMES_HOME` baru, model
dipasang dari fixture. Semua angka identik dengan workspace: v2 156/167,
v3 43/52, v4 29/38, v5 15/40, v6 30/41, v7 23/30, v8 17/30, v9 16/30,
v10 18/30, v11 27/36, v12 43/80, guard 12/12, FMT_GUARD 10/10,
FMT_ADV_GUARD 7/14. 7/7 gerbang lolos. p99 tiga run: **242.3, 249.3,
253.8 µs** — median **249.3 µs**, rentang 242.3–253.8 µs. **Lulus**;
dependensi Python dipakai ulang lewat `PYTHONPATH`, bukan instalasi jaringan.

## G2 — main native versus dev

`docs/MAIN_VS_DEV_MAPPING.md` ditulis sebelum perbandingan. Main berhasil
di-build, tetapi pelatihan model native main tidak selesai dalam batas waktu
tooling (lebih dari tujuh menit) dan dihentikan sebelum menulis model.
Langkah ini **dilewati dan dilaporkan**, tidak disubstitusi dengan model dev.
Tidak ada angka main native yang dikutip.

## G3 — NEG_LIVE

Fixture 150 kasus, sha `01d716b7…`, ekspektasi sebelum probe, nol duplikat.
Komposisi terverifikasi: percakapan 50, informasional 40, verba taksonomi
sebagai kata biasa 40, kalimat panjang 20.

Pra-alias **29/150 FP**, HEAD **31/150 FP**, selisih **+2**. Kriteria
(FP ≤ 2 dan selisih ≤ 0) **gagal dua-duanya**. Dua FP baru: `L101`
("rapikan" → tabular) dan `L102` ("agregasi" → tabular); `L119` juga
berubah dari NO_SKILL menjadi MATCHED. Blocker, tidak diperbaiki.

## G4 — Retrain

Pemicu default-on `on_skill_lifecycle` dan `on_subagent_stop` memanggil
`_spawn_retrain()` → `trainer.train_and_save()` → menimpa model di
`plugin-data` aktif. Perintah `/skill-brain retrain` dan CLI bersifat
opt-in. Direktori produksi ada tetapi kosong; tidak ada jalur pemasangan
model pin yang terdokumentasi. Tanpa model, hook mengembalikan brain kosong
dan memberi `HUNT_NEW_SKILL` pada prompt sah.

Satu retrain terisolasi menghasilkan θ₀ 7.5058 (pinned 7.529) tetapi
**0 perubahan status/skill** di seluruh suite. Blocker tetap berlaku karena
artefak dapat ditimpa dan jalur produksi tidak jelas.

## Keterbatasan

Polisemi 0/8, parafrase 11/24, held-out terpakai gabungan 88/146 (60%)
bersifat adversarial — bukan estimasi akurasi lalu lintas nyata. W01–W10
spec-mismatch dan NEG_CONV2 4/5 tetap dilaporkan apa adanya.

## Verdict dan perintah

**BELUM SIAP.** G1 lulus; G3 dan G4 blocker; G2 tidak menghasilkan data.
`docs/MERGE_READINESS.md` memuat perintah merge fast-forward, tag pra-merge
yang diusulkan, dan perintah rollback — **semuanya tidak dieksekusi**. Tidak
ada tag, push ke main, atau perubahan engine.

## Koreksi diri

1. Angka v8 di STATUS_DEV salah dan sudah dikoreksi.
2. Saya sempat lupa menyinkronkan tiga file ke dev-clean sehingga tree
   belum identik; dikoreksi dengan commit baru `73ca823`, bukan rewrite.
3. `lexicon_id_en.json` sempat termodifikasi di working tree saat pergantian
   branch; dikembalikan dari HEAD, bukan di-commit.
4. Tidak ada θ, margin, probe, deskripsi, ekspektasi, hash set, alias, atau
   src/ yang diubah; model pin tetap `a6a14d6a…`.

## Status akhir

`dev = 4ccbea7`, `dev-clean = 73ca823`, `main = d1de873`, keduanya clean,
`git diff dev dev-clean` kosong. **Berhenti.** Merge menunggu keputusan
setelah G3/G4 ditangani dalam mandat terpisah.
