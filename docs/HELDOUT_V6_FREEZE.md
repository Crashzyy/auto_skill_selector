# Held-out v6 — FREEZE (Fase 3e)

- File: `tests/heldout_v6.json`
- Jumlah kasus: **41** (X01–X41)
- **SHA256: `7c7dac1a5a4bfd61bced0787fc71b37da51ee148bb1b33208253566940853fc4`**
- Dibekukan **sebelum** probe engine dan sebelum kode P2a'.
- 0 duplikat persis terhadap 320 prompt unik dari v2 (167), b35 (35), v3 (52),
  v4 (38), v5 (40) — dicek dengan skrip normalisasi lowercase+strip.
- 0 duplikat internal; 0 pasangan dengan Jaccard token ≥ 0.70 terhadap set
  existing.
- 0 expect ganda SINGLE/MULTI: tiap kasus hanya satu status dalam
  `expect_status`.

## Prinsip penyusunan (bukan dari kegagalan v5)

| Kelompok | ID | N | Dasar ekspektasi |
|---|---|---|---|
| Informasional ID/EN, istilah teknis non-alat | X01–X11 | 11 | Pertanyaan/penjelasan tanpa niat artefak → `NO_SKILL_NEEDED` |
| Permintaan alat benar | X12–X18 | 7 | Ada kata kerja artefak (rangkai/ubah/bikin/hitung/buat) → `MATCHED_SINGLE` |
| Polisemi | X19–X21 | 3 | Kata `slide`/`chart`/`blender` dipakai bukan sebagai alat → `NO_SKILL_NEEDED` |
| Typo | X22–X25 | 4 | Typo ringan pada kata kerja artefak → `MATCHED_SINGLE` |
| Negasi | X26–X29 | 4 | Cue `hindari`/`jangan pakai`/`tanpa` memban alat → `MATCHED_SINGLE` |
| MULTI | X30–X33 | 4 | Dua artefak berurutan → `MATCHED_MULTI` |
| Kontrol skill-benar | X34–X41 | 8 | Delapan pilar domain, permintaan alat eksplisit → `MATCHED_SINGLE` |

Status data Fase 3e: v2/v3/v4/v5 **dev set**; **v6 = held-out bersih**.
Ekspektasi set mana pun tidak boleh diedit.
