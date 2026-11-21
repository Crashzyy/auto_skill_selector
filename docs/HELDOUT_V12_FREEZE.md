# Held-out v12 — FREEZE (Fase 3p)

- File: `tests/heldout_v12.json`
- 80 kasus S001–S080
- **SHA256: `a049524c0fea81eb7d5ed0adda41644b3c61259302d4e35da10e6e5ce8b5cfaf`**
- Dibekukan **sebelum** probe dan **sebelum** memuat daftar alias.
- 0 duplikat terhadap 596 prompt unik dari semua set (v2–v11, semua guard,
  NEG_CONV, NEG_CONV2, FMT_*); 0 duplikat internal; 0 expect ganda.
- Ekspektasi dari kaidah bahasa, bukan dari daftar delta 3o.

| Grup | N | Ekspektasi | Catatan |
|---|---|---|---|
| parafrase | 24 | MATCHED_SINGLE | ≥8 kategori skill, tanpa nama skill |
| kontrol | 12 | MATCHED_SINGLE | nama skill eksplisit, tanpa ban |
| negatif | 16 | NO_SKILL_NEEDED | percakapan pendek/panjang + informasional |
| polisemi | 8 | NO_SKILL_NEEDED | nama alat sebagai topik |
| typo | 8 | MATCHED_SINGLE | typo ringan |
| ellipsis | 6 | CLARIFY_AMBIGUOUS | kata ganti tanpa referen |
| H | 6 | HUNT_NEW_SKILL | tool baru memuat verba taksonomi v2 sebagai kata biasa |

v2–v11 + semua guard = dev set; v12 = held-out bersih satu-satunya.
Ekspektasi tidak diedit.
