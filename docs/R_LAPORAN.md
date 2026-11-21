# Laporan akhir Fase 3r

## Rekonsiliasi

`dev@HEAD = 12dcdf9` dan `dev-clean = f82b2fa` (sesuai pesan). Q_LAPORAN
menulis `4ccbea7`/`73ca823`, yaitu HEAD sebelum commit laporan 3q yang
kemudian disinkronkan. `git diff dev dev-clean` **kosong** pada HEAD terbaru.
`main = d1de873` tidak disentuh. Model terpin `a6a14d6a…` dan jalur bersama
tidak berubah.

## Commit fase ini

| Commit | Branch | Isi |
|---|---|---|
| `88efc41` | dev | `fix(hook): guard automatic retraining` |
| `9189bc8` | dev | `test: cover safe retrain paths` |
| `862d648` | dev | `docs: record final validation and verdict` |
| `1aee4d2`, `10a24b6` | dev-clean | sinkronisasi dokumen dan hook |

## G1

Clone bersih tetap lolos dari 3q; angka tidak diulang karena tidak ada
perubahan engine. p99 clone bersih: median 249.3 µs, rentang 242.3–253.8 µs.

## G2

Training native main selesai dalam **740 detik** (proses terpantau,
`HERMES_HOME` terisolasi, tanpa menyentuh main). θ₀ native 0.0895, sha model
`529a23f3…`. Skor main vs dev tercantum di `MERGE_READINESS.md`; ringkasnya
main jauh di bawah dev (b35 5/35 vs 35/35, v12 17/80 vs 43/80).
FP NEG_LIVE main 37/150 (natural 18/90), dev 31/150 (natural 5/90).

## G3

FP per grup: pra 4/1/21/3, HEAD 4/1/23/3 untuk percakapan/informasional/
verba/panjang; jumlah 29 dan 31 terverifikasi. FP baru hanya `L102`, `L119`;
yang hilang nol. Klasifikasi FP: (a) 25, (b) 6 (total 31). Mekanisme:
alias/kata domain 23, panjang 3, domain kuat 3, bypass/lain 2 (total 31).
G3a lolos (delta natural 0). G3b lolos (5/90 ≤ 18/90 + 2).

## G4

G4a: korpus sandbox 144 skill, produksi 111; model terpin 144 kelas.
`lexicon_id_en.json` di-embed, model dari disk; wheel offline terpasang
dengan `--no-index --no-deps`. Tanpa model hook memberi `HUNT_NEW_SKILL`
dengan skills kosong. Dua hook retrain default-on tanpa debounce/lock; retrain
adalah fitur yang dimaksud.

G4 implementasi: staging + validasi + `os.replace`, pass-through tanpa
model, lock + debounce, flag opt-out, empat uji lulus. Semua evaluator
identik; 7/7 gerbang; p99 dev 250.5, 234.7, 234.0 µs — median **234.7 µs**,
rentang 234.0–250.5 µs, tidak naik dari baseline 240.8 µs.

## Keputusan

Verdict **BELUM SIAP**: kendala teknis G1–G4 teratasi, tetapi ketidaksesuaian
korpus produksi (111) dengan model (144) membuat R2 menolak pemasangan.
Merge, tag, dan push ke main tidak dilakukan.

## Koreksi diri

1. Q_LAPORAN memuat hash laporan yang sudah digeser sinkronisasi; dikoreksi
   di dokumen ini.
2. Laporan 3q keliru menyebut `L101` sebagai FP baru; data per grup
   menunjukkan `L101` sudah FP sebelum alias.
3. Usulan ambang 3q (≤2/150) tidak dipakai; kriteria G3a/G3b berbasis grup
   ditetapkan sebelum rincian dilihat, sesuai perintah.
4. Tidak ada src/, trainer, θ, margin, probe, deskripsi, alias, ekspektasi,
   atau hash set yang diubah; model pin dan jalur bersama tetap utuh.

## Status akhir

`dev` dan `dev-clean` identik, clean, `main = d1de873`. **Berhenti.**
