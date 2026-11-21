# v5 — spec-mismatch W01–W10 (Fase 3f Langkah 0)

## Headline yang benar

- **v5 = 15/40** pada binary build ulang `383de5b` (evaluator asli,
  hash v5 `a85a21a3…` terverifikasi). Ini angka headline: tidak disembunyikan,
  tidak diganti angka "koreksi".
- Catatan terpisah: **10 dari 25 kegagalan (W01–W10) adalah spec-mismatch**,
  bukan kegagalan engine.

## Mengapa W01–W10 spec-mismatch

| ID | Ekspektasi v5 (beku) | Aktual engine | Penilaian |
|---|---|---|---|
| W01–W10 | `HUNT_NEW_SKILL` | `NO_SKILL_NEEDED` | **Engine benar menurut desain saat ini** |

Semua W01–W10 adalah pertanyaan informasional murni (definisi, perbandingan,
sejarah, cara kerja; ID + EN, istilah teknis non-alat). Stage 0
*conversational/informational bypass* sengaja mengarahkan bentuk tanya tanpa
niat artefak ke `NO_SKILL_NEEDED`. Fase 3e sudah membuktikan hal ini lewat
probe dua binary: 11+ variasi tanya dengan token OOD semuanya `NO_SKILL_NEEDED`
sebelum P2a' — itulah sebabnya P2a' direvert sebagai dead code.

Jadi ekspektasi lama W01–W10 (HUNT) bertentangan dengan desain yang berlaku.
Ekspektasi itu **tidak diedit** (v5 beku, hash `a85a21a3…`), dan tidak ada
perubahan engine yang dibuat untuk memenuannya.

## Konsekuensi pelaporan

- v5 tetap dilaporkan **15/40** di semua tabel (in-sample/dev).
- Di sampingnya dicatat: "10 kasus spec-mismatch (W01–W10) — engine NO_SKILL
  sesuai desain".
- v6 sudah menulis ekspektasi informasional → `NO_SKILL_NEEDED` dari prinsip,
  dan 10/11 lolos di baseline — bukti bahwa masalahnya ada di ekspektasi lama,
  bukan di engine.
- Tidak ada penyetelan ke ID mana pun; tidak adaθ₀/probe/deskripsi/margin
  yang diubah.
