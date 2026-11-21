# Held-out v10 — FREEZE (Fase 3k)

- File: `tests/heldout_v10.json`
- 30 kasus Q01–Q30
- **SHA256: `628bece6e31c6fcc56325a4a2d41d210b3a3d88002c51cdebe63b6a3ad8d11d4`**
- Dibekukan sebelum probe di `dev@8240e80` (pasca-revert P-FMT).
- 0 duplikat terhadap 486 prompt unik dari semua set (v2–v9 + semua guard),
  0 duplikat internal, 0 expect ganda.
- Tanpa ban+format, disusun dari tata bahasa.
- Ekspektasi sebelum probe.

| Kelompok | N | ID | Ekspektasi |
|---|---|---|---|
| parafrase tanpa nama skill | 10 | Q01–Q10 | MATCHED_SINGLE |
| kontrol skill-benar eksplisit tanpa ban | 10 | Q11–Q20 | MATCHED_SINGLE |
| ellipsis/kata ganti | 5 | Q21–Q25 | CLARIFY_AMBIGUOUS |
| typo ringan | 5 | Q26–Q30 | MATCHED_SINGLE |

Status data: v2–v8 dan semua guard = dev set; **v9 menjadi dev set** karena
kegagalannya sudah dibedah di Fase 3j; **v10 = held-out bersih**.
