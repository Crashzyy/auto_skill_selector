# P2a' Guard set — Fase 3e (SEBELUM kode)

- File: `docs/P2A_GUARD.json`
- Jumlah: **12 kasus** (G01–G12)
- **SHA256: `720066aaa43e400a74d93686e4ed1860ffaa42eb9d0245b4644ce2f611c24a28`**
- Ekspektasi ditulis **sebelum** probe engine dan sebelum kode P2a'.
- 0 duplikat terhadap v2/b35/v3/v4/v5 dan v6 (cek skrip).

## Prinsip ekspektasi

| Kelompok | ID | Aturan |
|---|---|---|
| (i) Permintaan alat sungguhan berbentuk pertanyaan | G01–G05 | Ada niat artefak ("bikinin", "convert") + kata tanya/alat baru → tetap `HUNT_NEW_SKILL` atau `MATCHED_SINGLE` (sesuai teks perintah), tidak boleh diredam gate informasional |
| (ii) Pertanyaan informasional murni | G06–G09 | Tanya/penjelasan tanpa niat artefak → `NO_SKILL_NEEDED` |
| (iii) Nama alat/skill + kata tanya | G10–G12 | Jalur MATCHED tidak berubah → `MATCHED_SINGLE` |

Guard ini dipakai sebagai gerbang: **tidak boleh ada PASS→FAIL** pasca-P2a'.
Ekspektasi tidak boleh diedit.
