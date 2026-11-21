# Pemetaan status main versus dev

Ditulis **sebelum** menjalankan perbandingan main native dengan dev.

## Tujuan

Skema status kedua engine berbeda (`main` memakai `MATCHED_LOCAL`,
`NO_SKILL_NEEDED`, dll.; `dev` memakai `MATCHED_SINGLE`, `MATCHED_MULTI`,
`CLARIFY_AMBIGUOUS`, dll.). Perbandingan tidak boleh memakai kesetaraan
status mentah.

## Normalisasi keputusan

| Status engine | Kelas keputusan |
|---|---|
| `MATCHED_LOCAL`, `MATCHED_SINGLE`, `MATCHED_MULTI`, `MATCHED_PARTIAL_AND_HUNT` | `memicu skill` |
| `HUNT_NEW_SKILL`, `CLARIFY_AMBIGUOUS`, `NO_SKILL_NEEDED` | `tidak memicu skill` |

`HUNT_NEW_SKILL` dan `CLARIFY_AMBIGUOUS` **tidak** dihitung sebagai memicu
skill: keduanya tidak mengembalikan skill yang sudah ada.

## Kecocokan skill

- Untuk kasus dengan `expect_skills` eksplisit (b35), bandingkan IDs skill
  yang dipilih dengan daftar ekspektasi. Normalisasi registrar skill sudah
  sama (nama skill dari model), jadi perbandingan langsung valid.
- Untuk kasus tanpa `expect_skills`, hanya kelas keputusan yang dibandingkan;
  tidak ada inferensi target dari top-1.

## Penilaian per kasus

| Main | Dev | Label |
|---|---|---|
| sesuai ekspektasi | sesuai ekspektasi | both correct |
| sesuai | tidak sesuai | regresi dev |
| tidak sesuai | sesuai | perbaikan dev |
| tidak sesuai | tidak sesuai | both wrong |

Evaluator asli tiap engine tetap dipakai untuk menentukan "sesuai";
pemetaan ini hanya untuk ringkasan lintas-skema. Tidak ada ambang
keputusan; laporan bersifat `report-only`.
