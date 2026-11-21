# P2a' Guard set — Fase 3e (SEBELUM kode)

- File: `docs/P2A_GUARD.json`
- Jumlah: **12 kasus** (G01–G12)
- **SHA256: `975197fe9cc3e7ceea6d15b6c89762542b9c440b8e2a85e93704f8bea3eca7cb`**
- Ekspektasi ditulis **sebelum** probe engine dan sebelum kode P2a'.
- 0 duplikat terhadap v2/b35/v3/v4/v5 dan v6 (cek skrip).

## Prinsip ekspektasi

| Kelompok | ID | Aturan |
|---|---|---|
| (i) Permintaan alat sungguhan berbentuk pertanyaan | G01–G05 | Ada niat artefak ("bikinin", "convert") + kata tanya/alat baru → tetap `HUNT_NEW_SKILL` (bukan diredam gate informasional) |
| (ii) Pertanyaan informasional murni | G06–G09 | Tanya/penjelasan tanpa niat artefak → `NO_SKILL_NEEDED` |
| (iii) Nama alat/skill + kata tanya | G10–G12 | Jalur MATCHED tidak berubah → `MATCHED_SINGLE` |

Guard ini dipakai sebagai gerbang: **tidak boleh ada PASS→FAIL** pasca-P2a'.
Ekspektasi tidak boleh diedit.
