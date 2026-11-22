# Perbedaan korpus sandbox dan produksi

Sumber dibaca dari produksi tanpa modifikasi. Hash direktori skills produksi
di awal Fase 3s: `0027bf73e0f188e9cc47ec3084f311221a4c6f969f590058de16110adc4ac3b9`.
Hash plugin-data produksi: `e3b0c442...` (direktori kosong).

## Hitungan

| Kelompok | N |
|---|---|
| sandbox saja | 142 |
| produksi saja | 109 |
| irisan | 2 |
| deskripsi berbeda pada irisan | 2 |

Nama skill pada irisan: `claude-code`, `humanizer`. Keduanya memiliki deskripsi
berbeda antara sandbox dan produksi, sehingga hanya nama yang sama.

Daftar lengkap 142 nama sandbox-saja dan 109 nama produksi-saja disimpan di
`docs/CORPUS_DIFF.json` (dihasilkan dari pembacaan langsung, bukan perkiraan).
Model terpin memiliki 144 kelas, sesuai korpus sandbox. Hanya 2 dari 144 kelas
yang nama dan deskripsinya relevan dengan produksi (dan deskripsinya pun
berbeda).

## Dampak ke set uji

Set dengan `expect_skills`: b35 28/35, v2 3/167; sisanya "target tak
diketahui". Dari 31 kasus ber-label skill, **31** menunjuk ke skill
sandbox-saja, sehingga tidak ada satu pun kasus ber-target yang dapat
dievaluasi secara bermakna pada korpus produksi. Seluruh angka dev (termasuk
v2 156/167) terikat pada korpus sandbox 144 skill dan tidak mengukur sistem
produksi.

Implikasi untuk P3: subset restriksi kasus ber-expect_skills yang skill-nya
ada di produksi berisi **nol kasus**, sehingga ambang PASS→FAIL 5% tidak
dapat dihitung. Ini bukan lulus; ini ketiadaan bukti.
