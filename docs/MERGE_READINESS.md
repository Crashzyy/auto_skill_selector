# Kesiapan merge — pembaruan Fase 3r

## Ringkasan G1–G4

| Gerbang | Hasil | Angka kunci |
|---|---|---|
| G1 clone bersih | Lulus | semua evaluator identik; 7/7; p99 median 249.3 µs |
| G2 main native | Selesai | training 740 s; θ₀ 0.0895; b35 5/35; v2 79/167; NEG_LIVE 37/150 |
| G3a | Lulus | natural 5→5 dari 90, delta 0 |
| G3b | Lulus | dev 5/90 ≤ main 18/90 + 2 |
| G4 | Implementasi lolos | R1–R6; empat uji lulus; 7/7; p99 median 234.7 µs |

## G2 detail

Main native dilatih dengan trainer main di direktori terisolasi selama
740 detik. Skor main vs dev: v3 20/52 vs 43/52, v4 10/38 vs 29/38,
v5 3/40 vs 15/40, v6 10/41 vs 30/41, v7 7/30 vs 23/30, v8 1/30 vs 17/30,
v9 0/30 vs 16/30, v10 0/30 vs 18/30, v11 8/36 vs 27/36, v12 17/80 vs 43/80,
guard 3/12 vs 12/12, FMT_GUARD 5/10 vs 10/10, FMT_ADV 2/14 vs 7/14,
v2 79/167 vs 156/167, b35 5/35 vs 35/35.
FP NEG_LIVE per grup main: percakapan 12, informasional 6, verba 1,
panjang 18 (total 37); dev: 4, 1, 23, 3 (total 31).
Tidak ada ambang untuk perbandingan ini; keputusan ada di owner.

## G3 detail

FP natural (percakapan + informasional) pra-alias 5, HEAD 5, delta 0.
FP natural HEAD 5/90, main native 18/90 — batas main+2 terpenuhi.
Grup adversarial (verba, panjang) hanya dilaporkan: 21→23 dan 3→3.
Dua FP baru: `L102` dan `L119`; tidak ada FP yang hilang. Laporan 3q yang
menyebut `L101` sebagai FP baru tidak tepat.

## G4 detail

Hook sekarang: staging + `os.replace`, validasi jumlah kelas dan θ₀,
pass-through saat model tidak ada, lock + debounce 30 detik, dan flag
`AUTO_SKILL_SELECTOR_DISABLE_AUTORETRAIN`. Empat uji terisolasi lulus.

Audit G4a menemukan korpus produksi **111 skill**, sedangkan model terpin
memiliki **144 kelas**. R2 menolak pemasangan model yang tidak cocok dengan
korpus. Prosedur deploy saat ini belum bisa memasang model tervalidasi ke
produksi tanpa sinkronisasi korpus.

## Keterbatasan yang diterima

- Polisemi 0/8, parafrase 11/24.
- Held-out terpakai 88/146 (60%) dan bersifat adversarial, bukan perkiraan
  akurasi lalu lintas nyata.
- W01–W10 spec-mismatch dan NEG_CONV2 4/5 tetap dilaporkan apa adanya.

## Perintah merge (usulan, TIDAK dieksekusi)

    git checkout main
    git merge --ff-only dev-clean

Tag pra-merge yang diusulkan pada `d1de873`:

    git tag -a pre-merge-fase3 -m "Pre-merge checkpoint" d1de873

Rollback:

    git revert --no-edit <merge-commit>
    git push origin main

## Verdict

**BELUM SIAP.** Validasi korpus produksi (Fase 3s) menemukan FP natural
17/90 pada model produksi, 148 keputusan "salah" pada delta 144→produksi,
dan fixture NEG_CONV tidak ikut ke wheel. Selain itu korpus produksi hanya
beririsan 2 skill dengan korpus sandbox. Rincian di `docs/S_VALIDASI.md`.
Merge, tag, dan push ke main tidak dilakukan.
