# Held-out v9 — FREEZE (Fase 3j, pasca-revert P-FMT)

- File: `tests/heldout_v9.json`
- 30 kasus P01–P30
- **SHA256: `9ae2a6d7b9b3eebbfc748f7e1e8339680e4c2485a5694435d70e6c57a3b927fa`**
- Dibekukan sebelum probe di binary pasca-revert.
- 0 duplikat terhadap 456 prompt unik dari semua set (v2–v8 + semua guard),
  0 duplikat internal, 0 expect ganda.
- Tanpa ban+format (sengaja, agar mengukur kemampuan inti tanpa efek P-FMT).

| Kelompok | N | ID | Ekspektasi dari tata bahasa |
|---|---|---|---|
| parafrase tanpa nama skill | 10 | P01–P10 | MATCHED_SINGLE |
| ellipsis / kata ganti | 5 | P11–P15 | CLARIFY_AMBIGUOUS |
| typo ringan | 5 | P16–P20 | MATCHED_SINGLE |
| kontrol skill-benar | 10 | P21–P30 | MATCHED_SINGLE |

v2–v8 + guards = dev set; **v9 = held-out bersih**. Ekspektasi tidak diedit.
