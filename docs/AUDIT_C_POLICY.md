# AUDIT C — Putusan kebijakan user (B17/B20/B22/D04/E19)

Putusan user diterapkan apa adanya. Tidak ada probe/θ₀/deskripsi yang disetel
demi kasus; ekspektasi dikunci sesuai keputusan user (bukan sebaliknya).

| Kasus | Putusan user | Status/ban engine sebelum | Sesudah | Ekspektasi runner |
|---|---|---|---|---|
| **B17** | BUKAN ban | banned `[]` | banned `[]` | `expect_banned_excludes:["excel"]` (sudah ada) |
| **B20** | BAN | banned `['excel','xls','xlsx']` | sama | + `expect_banned_contains:["excel"]` |
| **B22** | BUKAN ban | banned `['excel','xls','xlsx']` ⚠ | banned `[]` ✓ | + `expect_banned_excludes:["excel"]` |
| **D04** | 1 atau 2 klausa diterima | 1 klausa | 1 klausa | `expect_clause_count:[1,2]` (sudah ada) |
| **E19** | NO_SKILL_NEEDED | NO_SKILL_NEEDED | sama | `expect_status:["NO_SKILL_NEEDED"]` (dipersempit) |

## Perbaikan engine untuk B22 (satu-satunya yang melanggar putusan)

Prompt: `tanpa excel pun tidak masalah, buat saja tabelnya`.
Sieve mem-parsing `tanpa` sebagai BAN_TRIGGER kuat → banned excel, HUNT.
Padahal `tanpa X pun tidak masalah` = **opsional**, bukan larangan.

Perbaikan umum (bukan per-kasus): optionality guard untuk cue `tanpa`/`without`
— bila dalam jendela 8 token setelah cue ada penanda pembatalan (`tidak/tak/
gak/... masalah|apa-apa`, `boleh`, `pun boleh`, `no problem`, `okay`), cue
di-skip (bukan ban, tidak di-strip).

**B20 tetap ban** karena memakai `jangan pakai` (bukan `tanpa`), tidak terkena
guard. Verifikasi negatif:
- `tanpa excel buat tabel` → masih banned excel ✓
- `jangan pakai excel` → masih banned excel ✓
- `without excel make a chart` → masih banned excel ✓
- `tanpa pakai makro buat laporan` → tidak banned (makro bukan format) ✓

## Verifikasi

- 5/5 kasus policy PASS di runner.
- v2 **149/167** (tidak berubah), regresi 35 **35/35**.
- Ekspektasi di-`commit` di `tests/benchmark_scenarios_v2.json` sehingga
  keputusan user menjadi kontrak permanen, bukan catatan sesi.
