# Held-out v11 — FREEZE (Fase 3n)

- File: `tests/heldout_v11.json`
- 36 kasus V01–V36
- **SHA256: `d8263722d6b0cb7873a68bdf3890834a60aeb8ddd55a573bebc9d45c7afee57e`**
- Dibekukan sebelum probe dan **sebelum eksperimen leksikon Langkah D**.
- 0 duplikat terhadap 560 prompt unik dari semua set termasuk v10, NEG_CONV,
  NEG_CONV2, FMT_ADV_GUARD; 0 duplikat internal; 0 expect ganda.
- Ekspektasi dari kaidah bahasa, bukan dari kegagalan v5–v10.

| Grup | N | ID | Ekspektasi |
|---|---|---|---|
| parafrase tanpa nama skill (≥6 kategori) | 12 | V01–V12 | MATCHED_SINGLE |
| kontrol eksplisit | 8 | V13–V20 | MATCHED_SINGLE |
| negatif (percakapan & informasional) | 8 | V21–V28 | NO_SKILL_NEEDED |
| polisemi | 4 | V29–V32 | NO_SKILL_NEEDED |
| typo ringan | 4 | V33–V36 | MATCHED_SINGLE |

v2–v9 + semua guard = dev set; v10 tertutup; **v11 = held-out bersih**.
Ekspektasi tidak diedit.
