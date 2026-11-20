# Laporan Verifikasi A–C — sebelum Fase 3

HEAD final `530ec1a` (`dev == origin/dev`), `main == d1de873` (hard lock utuh).
Semua angka di bawah diukur dari binary hasil build ulang di HEAD ini.

## Ringkasan angka (final)

- **7/7 gerbang PASS** (scorecard.json ditulis ulang runner): L2 norm, parity,
  benchmark 35/35 (negasi 6/6), FP konversasional 0/5, latensi, live hook
  6/6 + validate + doctor, git hygiene.
- **v2 149/167** (naik dari 145 saat audit dimulai).
- **regresi 35/35**.
- **latensi p50 38.3 µs, p99 213.4 µs** (threshold <200 / <500).
- **fuzz Unicode generatif 5000 prompt: 0 gagal**; stress fast+slow 0 gagal.
- Per-category v2: A 14/14, B 27/29, C 7/7, D 16/17, E 20/20, F 7/8,
  G 8/12, H 17/21, I 7/7, J 8/8, K 3/8, L 9/9, M 6/7.

## A. Verifikasi (tanpa ubah probe/θ₀/deskripsi)

**A1** (`788f7ec`) — Diff per-case v2 `8c64981` vs `5f85058`:
- F 7/8→6/8 = regresi nyata **F07** (vague-ask guard kena `ini` pada URL+ringkas).
- E15/E18 (social) salah CLARIFY; G12 (`k8s`) salah dianggap known karena
  `fuzzy_known_tool` menyubstitusi digit `8`→`a` → `kas`.
- 4 regresi diperbaiki dengan 2 aturan umum: guard CLARIFY butuh action verb &
  bukan URL; fuzzy tidak substitusi digit→huruf. Hasil 149/167.
- **H tidak turun**: 17/21 di kedua commit. Angka "18/21" di laporan lama
  tidak muncul di `run_v2()` commit mana pun — dikoreksi jujur.

**A2** (`5eaacbd`) — 7 gerbang dijalankan ulang, scorecard.json diperbarui.

**A3** (`80772fb`) — Audit slicing byte-vs-char: 9 situs aman; **1 bug nyata**
`l[2..]` pada bullet `• ` (3 byte, memotong U+2022 → panic) diperbaiki dengan
`char_indices().nth(2)`. Fuzz Unicode 5000/0 ditambahkan ke
`test_stress_regression.py` (--unicode-fuzz, seed 20261120, batch/subprocess).

**A4** (`13e28a6`) — S-3: `note_skill_used` diputuskan **HAPUS** (metode
momentum sengaja hilang sejak Fase 2; loop try/except = dead code; memulihkan
akan mengubah perilaku — dilarang). M-5: `_ensure_brain()` **p50 33 ms /
p99 44 ms per giliran** (reload model 2.1 MB ≈ 17 ms); overhead hook, bukan
latensi `analyze_prompt`. Optimasi cache sengaja tidak dikerjakan.

## B. Instrumentasi (`2ba636a`)

`hunt_reason` (`unknown_tool|below_theta|no_match|""`) ditambahkan ke
`RoutingDecision`, diekspos via `to_py_dict`, **murni instrumentasi**. Sebaran:
- **G**: below_theta 5, unknown_tool 2, none 5.
- **K**: below_theta 2, unknown_tool 1, none 5.
- `no_match` tidak muncul (semua hunt punya kandidat ter-skor).
- 7 dari 9 hunt di G/K adalah `below_theta` → dasar pemisahan HUNT di Fase 3.

## C. Putusan kebijakan (`641d34d`)

B17 bukan ban ✓ · B20 ban ✓ · **B22 bukan ban** (perlu perbaikan:
`tanpa X pun tidak masalah`=k opsional → optionality guard umum untuk cue
`tanpa`/`without`; B20 memakai `jangan pakai`, tetap ban) · D04 1 klausa
(dalam [1,2]) ✓ · E19 NO_SKILL_NEEDED ✓. Ekspektasi dikunci di
`tests/benchmark_scenarios_v2.json`. 5/5 policy PASS.

## Gap yang tetap ada (jujur, tanpa setelan per-kasus)

- Skor di bawah θ₀ 7.47: F08, B08, D11, M04.
- OOD/polisemi: K02/K03/K05/K06/K07, G02/G04/G05 — butuh Fase 3.
- H 17/21 (H05/H06/H08/H21 tetap NO_SKILL_NEEDED).
- `_ensure_brain` ~33 ms/giliran (M-5) belum dioptimasi.

## Status

A–C selesai dan dilaporkan. **STOP** — Fase 3 menunggu persetujuan eksplisit.
Tidak ada probe/θ₀/deskripsi/ekspektasi yang disetel demi kasus tertentu
(kecuali mengunci putusan kebijakan yang memang diberikan user).

Dokumen pendukung: `docs/AUDIT_A1_V2_DIFF.md`, `AUDIT_A3_SLICING_UNICODE.md`,
`AUDIT_A4_S3_M5.md`, `AUDIT_B_HUNT_REASON.md`, `AUDIT_C_POLICY.md`.
