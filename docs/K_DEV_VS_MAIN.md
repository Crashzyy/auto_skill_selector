# Fase 3k Langkah 1 — dev vs main (read-only)

Binary `main = d1de873` vs `dev = 8240e80`, keduanya di-build ulang dengan
venv sama. `tests/diff_harness.py` dijalankan dengan fixtures beku yang
disalin ke worktree main (main tidak punya fixtures/harness sendiri).
Kedua binary memuat model `skill_model.json` yang sama.

- Total kasus: **498** (v2, b35, v3–v9, semua guard).
- Delta status/skill: **379** — efek bersih Fase 2–3j (rewrite 6-stage,
  negation sieve, multi-skill, status rename `MATCHED_LOCAL`→`MATCHED_SINGLE`,
  dll). Output: `docs/K_DIFF_MAIN_VS_DEV.txt`.

## Skor per set (main → dev)

| Set | main | dev | n |
|---|---|---|---|
| b35 | 5 | **35** | 35 |
| v2 | 33 | **65**¹ | 167 |
| v3 | 18 | **31** | 52 |
| v4 | 11 | **25** | 38 |
| v5 | 5 | **16** | 40 |
| v6 | 14 | **28** | 41 |
| v7 | 7 | **20** | 30 |
| v8 | 8 | **15** | 30 |
| v9 | 0 | **15** | 30 |
| FMT_ADV_GUARD | 4 | **7** | 14 |
| FMT_GUARD | 5 | **10** | 10 |
| P2A_GUARD | 4 | **12** | 12 |

¹ Angka v2 di sini dari evaluator ad-hoc harness (hanya kasus dengan
`expect_status`, dan tanpa `check_case` penuh); **angka kanonik v2 = 155/167**
dari `benchmark_runner.py`. Angka ad-hoc tidak dipakai untuk kesimpulan gate.

Klasifikasi 379 delta dari output mentah (berdasarkan
`expect_status` OR): **benar 185, salah 20, netral 174**. Artinya
rewrite Fase 2–3j jauh lebih banyak memperbaiki daripada merusak;
20 delta "salah" terutama kasus yang tadinya NO_SKILL kini MATCHED pada
ekspektasi NO_SKILL — ini sudah tercatat di regresi guard Fase 3.

## Catatan held-out

- v5 5→16, v6 14→28, v7 7→20, v8 8→15, v9 0→15 — peningkatan besar
  di semua set yang dulunya held-out. Setelah dibedah, v5–v9 kini dev set.
- v10 (held-out baru) = 16/30, diukur terpisah di Langkah 4.
