# Laporan akhir Fase 3s

## State

`dev@HEAD = 0115131`, `dev-clean = ab39304` (konfirmasi: benar; R_LAPORAN
menulis keduanya sebagai HEAD sebelum commit "hash final", yang benar secara
waktu). `git diff dev dev-clean` kosong. `main = d1de873` tidak disentuh.
Hash produksi awal = akhir: skills `0027bf73…`, plugin-data `e3b0c442…`
(kosong). Model terpin dan jalur bersama tidak berubah.

## Commit

| Commit | Isi |
|---|---|
| `dc40cdd` | validasi model terhadap korpus terpasang |
| `4116dc8` | uji validasi korpus + fixture + CORPUS_DIFF |
| `ec1b548` | sinkronisasi ke dev-clean |
| docs akhir | laporan validasi dan verdict |

## Langkah 0

`git show --stat 0115131/ab39304`: keduanya hanya mengubah baris hash di
`R_LAPORAN.md` — melanggar aturan granularitas. Seluruh 11 commit dev-clean
sejak main lolos lint, tetapi dua commit "isi hash" perlu squash; squash
membutuhkan force push dan **tidak dilakukan**. Dari 40 regresi dev vs main
native, 3r tidak merinci daftar; dihitung ulang: **40 kasus**, terutama FP
chitchat/polisemi/topik.

## Langkah 1

Irisan korpus sandbox 144 vs produksi 111 hanya **2** (`claude-code`,
`humanizer`, keduanya deskripsi berbeda); sandbox-saja 142, produksi-saja 109.
Dari 31 kasus ber-`expect_skills`, **31** menunjuk ke skill sandbox-saja.
Subset restriksi untuk P3 berisi nol kasus.

## Langkah 2

Tiga training produksi: durasi 1.59/1.48/1.44 s, RSS ~92 MB, 111 kelas,
θ₀ 1.5606/1.5606/1.5605, sha berbeda. Daya tahan keputusan: 0 kasus
tidak stabil. Delta terhadap model 144: 446 kasus/run — 31 by design,
177 benar, 90 netral, **148 salah** (jumlah 446 terverifikasi).
FP NEG_LIVE natural = 17/90 pada setiap run; NEG_CONV 0/40.

## Langkah 3

R2b (self-retrieval, ambang 91.53% dari ukuran 96.53% yang ditulis lebih
dulu), R3b, R7 (`.prev`), R8 (debounce 30 s > 2× durasi median 1.5 s)
diimplementasi. Dua bug pada hook pertama perbaikan: copytree gagal pada
symlink rusak dan `os.replace` lintas filesystem. Uji terisolasi: 5/5 lulus.
Namun fixture `NEG_CONV` tidak ikut ke wheel, sehingga pengecekan FP R2b
di produksi dilewati — P5 gagal.

## Langkah 4

Dari klon bersih, wheel offline terpasang. First-run: hook pass-through,
retrain, pasang atomik dalam **2 detik**, hook aktif, **30/30** keputusan
contoh benar. G1 diulang: semua evaluator identik, 7/7 gerbang; p99 tiga
run 254.8 µs (dari run tambahan), tidak ada regresi.

## Langkah 5 — verdict

P1 lulus, P2 **gagal** (17/90 > 6/90), P3 **gagal** (148 salah; subset nol),
P4 lulus, P5 **gagal** (fixture tidak di wheel). Verdict: **BELUM SIAP**.
Perintah merge/rollback tetap usulan, tidak dieksekusi.

## Koreksi diri

1. Dua implementasi hook pertama saya gagal pada kasus produksi nyata;
   diperbaiki setelah uji first-run, bukan dibiarkan.
2. Saya mengira fixture `NEG_CONV` ikut ke wheel; ternyata tidak, dan R2b
   secara diam-diam akan lolos dengan FP=0. Ini dilaporkan sebagai kegagalan.
3. Angka 148 "salah" tidak disembunyikan di balik 31 kasus by design.
4. Tidak ada ekspektasi, θ, margin, probe, deskripsi, alias, hash set,
   src/, trainer, atau model kanonik yang diubah; produksi hanya dibaca.

## Status akhir

`dev` dan `dev-clean` identik, clean, `main = d1de873`. **Berhenti.**
