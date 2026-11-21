# FMT_GUARD — Fase 3g (SEBELUM kode P-FMT)

- File: `docs/FMT_GUARD.json`
- 10 kasus, SHA256 `7f8f513bdc2b7cd21f393bdb53bc0cf640e8fff019c8971aaa0c735a1b3cf3d2`
- Ekspektasi ditulis sebelum probe engine dan sebelum kode P-FMT.

| Grup | ID | Aturan |
|---|---|---|
| penanda format tanpa ban | F01–F03 | jalur normal tidak boleh berubah → `MATCHED_SINGLE` |
| ban tanpa penanda | F04–F05 | tidak boleh berubah → `NO_SKILL_NEEDED` |
| penanda + nama skill yang DIBAN | F06–F07 | skill tetap terbuang → `NO_SKILL_NEEDED` |
| idiom delay / niat positif | F08–F10 | bukan ban → NO_SKILL / MATCHED sesuai niat |

Tidak boleh ada PASS→FAIL pasca-P-FMT. Ekspektasi tidak diedit.
