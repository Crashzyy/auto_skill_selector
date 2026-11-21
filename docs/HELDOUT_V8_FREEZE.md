# Held-out v8 — FREEZE (Fase 3i)

- File: `tests/heldout_v8.json`
- 30 kasus Z01–Z30
- **SHA256: `6353018569eb681ad411c25ebcae75bde10de8e312d8f273f7c21af958fb8bf7`**
- Dibekukan sebelum probe dan sebelum kode penyempitan P-FMT.
- 0 duplikat terhadap 426 prompt unik dari semua set termasuk
  FMT_ADV_GUARD (cek skrip), 0 duplikat internal, 0 expect ganda.
- Ekspektasi dari tata bahasa, bukan dari A01–A14.

| Grup | N | ID | Prinsip |
|---|---|---|---|
| A | 8 | Z01–Z08 | ban + penanda format sungguhan + skill lain; sengaja ada `bikinkan`/`buatkan` yang mengandung substring `in`/`as` |
| B | 8 | Z09–Z16 | ban + kata fungsi (`dalam`, `in`, `soal`, `tentang`) + skill sbg **topik**, bukan permintaan → tidak boleh di-pin |
| C | 10 | Z17–Z26 | kontrol skill-benar tanpa ban |
| D | 4 | Z27–Z30 | penanda format tanpa ban |

v2–v7, guard, FMT_GUARD, FMT_ADV_GUARD = dev set; **v8 = held-out bersih**.
