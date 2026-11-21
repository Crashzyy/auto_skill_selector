# FMT_GUARD — Fase 3g (SEBELUM kode P-FMT)

- File: `docs/FMT_GUARD.json`
- 10 kasus, SHA256 `fea04dbd860c2911c1fb8013fbd24a1d6ed55b5c15b8495113bdd0390a1d3ddd`
- Ekspektasi ditulis sebelum probe engine dan sebelum kode P-FMT.

| Grup | ID | Aturan |
|---|---|---|
| penanda format tanpa ban | F01–F03 | jalur normal tidak boleh berubah → `MATCHED_SINGLE` |
| ban tanpa penanda | F04–F05 | tidak boleh berubah → `NO_SKILL_NEEDED` |
| penanda + nama skill yang DIBAN | F06–F07 | skill tetap terbuang → `NO_SKILL_NEEDED` |
| idiom delay / niat positif | F08–F10 | bukan ban → NO_SKILL / MATCHED sesuai niat |

Tidak boleh ada PASS→FAIL pasca-P-FMT. Ekspektasi tidak diedit.
