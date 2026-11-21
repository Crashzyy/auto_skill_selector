# Fase 3h — STOP di Langkah 2 (false positive pin terkonfirmasi)

## Rekonsiliasi evaluator (Fase 3i Langkah 0)

Tabel lengkap A01–A14 pra/pasca (status, skill, PASS/FAIL):

| ID | Pra (dc429c9) | Pasca (db7ea9f) | Skor |
|---|---|---|---|
| A01 | HUNT `[]` FAIL | MATCHED `word-docx-reporting` FAIL | FAIL→FAIL |
| A02 | HUNT `[]` FAIL | MATCHED `powerpoint-slide-deck` FAIL | FAIL→FAIL |
| A03 | HUNT `[]` FAIL | MATCHED `meeting-notes-action-items` FAIL | FAIL→FAIL |
| A04 | HUNT `[]` FAIL | HUNT `[]` FAIL | FAIL→FAIL |
| A05 | HUNT `[]` **PASS** | MATCHED `boring-marketing-email-sequences` **FAIL** | **PASS→FAIL** |
| A06 | HUNT PASS | HUNT PASS | PASS |
| A07 | HUNT PASS | HUNT PASS | PASS |
| A08 | HUNT FAIL | MATCHED `word-docx-reporting` PASS | **FAIL→PASS** |
| A09 | HUNT FAIL | HUNT FAIL | FAIL (aspiratif — lihat addendum) |
| A10 | CLARIFY FAIL | MATCHED `tabular-pivot-cleaning` PASS | **FAIL→PASS** |
| A11 | MATCHED `word-docx-reporting` PASS | sama PASS | PASS |
| A12 | HUNT PASS | HUNT PASS | PASS |
| A13 | MATCHED `word-docx-reporting` PASS | sama PASS | PASS |
| A14 | MATCHED `mermaid-architecture-diagram` PASS | sama PASS | PASS |

**Skor dihitung ulang: pra 7/14, pasca 8/14.** Koreksi atas kalimat laporan
3h sebelumnya: "tabel menyiratkan pasca lebih buruk dari pra" **tidak tepat
bila diartikan sebagai skor**. Skor memang naik (+1: A08, A10), tetapi
kualitatif **lebih buruk** karena A05 berubah PASS→FAIL dan A01–A03 berubah
dari HUNT (benar secara perilaku, meski ekspektasinya FAIL) menjadi MATCHED
dengan skill yang tidak diminta. Kedua pernyataan kini dibedakan eksplisit.

### Addendum A09 (aspiratif)

A09 (`hindari pdf, tampilkan nilainya dalam bentuk tabel`) ditulis dengan
ekspektasi `MATCHED_SINGLE` dari prinsip "format sungguhan", tetapi engine
pra-P-FMT menghasilkan HUNT dan pasca-P-FMT juga HUNT (pin tidak aktif).
Ini adalah **ekspektasi aspiratif**, bukan regresi; A09 **dikeluarkan dari
gerbang** namun tetap dilaporkan. Hash guard tidak diubah.

## State

- HEAD = **`24cab64`** (konfirmasi: **bukan `db7ea9f`** — itu commit P-FMT,
  satu lebih awal; `db7ea9f^ = dc429c9`). `main = d1de873` utuh,
  θ₀ 7.4688, margin P1b, probe, deskripsi tidak diubah; tidak ada merge.
- Kedua binary (`db7ea9f` dan `dc429c9`) di-build ulang di worktree terpisah.
- Tidak ada kode engine yang diubah di Fase 3h.

## Langkah 1 — Audit aktivasi P-FMT (SELESAI)

Dokumen: `docs/AUDIT_PFMT_AKTIVASI.md`. 425 kasus dari v2/b35/v3–v7/guard.

- Aktivasi struktural (ban non-empty + marker + anchor): **11 kasus**.
- Delta status: **6 kasus** — 5 benar (X26, Y01, Y03, Y06, W33),
  **1 salah (v2 F05)**.
- F05: residual "... tolong **bikin** email ..." → marker `in` cocok sebagai
  substring pada "bikin " → pin `boring-marketing-email-sequences`,
  top 1.00, HUNT → MATCHED. Salah.

## Langkah 2 — FMT_ADV_GUARD → STOP

- `docs/FMT_ADV_GUARD.json`, 14 kasus, hash
  `17bbb97430d2ff92432a30bad25da90c10c3539e1d0b1531fe3b25da54733a05`,
  ekspektasi ditulis sebelum probe.
- Evaluator: `tests/eval_fmt_adv_guard.py`.
- Hasil di `db7ea9f`: **8/14**; di `dc429c9` (pre-P-FMT): **7/14**.

| ID | Pra (dc429c9) | Pasca (db7ea9f) | Penilaian |
|---|---|---|---|
| A01 | HUNT | MATCHED `word-docx-reporting` | **FALSE POSITIVE PIN** |
| A02 | HUNT | MATCHED `powerpoint-slide-deck` | **FALSE POSITIVE PIN** |
| A03 | HUNT | MATCHED `meeting-notes-action-items` | **FALSE POSITIVE PIN** |
| A05 | HUNT | MATCHED `boring-marketing-email-sequences` | **FALSE POSITIVE PIN** |
| A08 | HUNT | MATCHED `word-docx-reporting` | benar (format sungguhan) |
| A10 | CLARIFY | MATCHED `tabular-pivot-cleaning` | benar |
| A09 | HUNT | HUNT | netral (pin tidak aktif; ekspektasi saya aspiratif) |
| A04, A06, A07, A11–A14 | — | — | sesuai |

### Mekanisme false positive (dua kelemahan)

1. **Substring match pada marker pendek**: `lower.contains("in ")` membuat
   "bi**kin** " dan "bikin " terdeteksi sebagai penanda `in` (A05, dan F05
   di Langkah 1). Juga `as`/`into` berisiko sama.
2. **Tanpa syarat kedekatan (adjacency)**: helper hanya mengecek marker
   *ada di mana saja* dan token nama skill *ada di mana saja* residual.
   "aku lagi **dalam** rapat soal **word**" → `dalam` + `word` → pin
   `word-docx-reporting`, padahal `word` adalah topik pembicaraan, bukan
   format yang diminta (A01–A03).

Kedua kelemahan ini adalah konsekuensi langsung dari desain P-FMT Fase 3g
yang memakai `contains` untuk marker dan pencarian token global tanpa
hubungan sintaktik.

## STOP

Sesuai perintah eksplisit: *"False positive pin di Langkah 2 → STOP,
laporkan mekanismenya dan usulan penyempitan (jangan implementasi)."*
→ **BERHENTI sebelum Langkah 3 (pooled diagnosis) dan Langkah 4 (v8).**

## Usulan penyempitan (TIDAK diimplementasi)

1. Ganti `contains` dengan **pencocokan kata utuh** (token boundary) untuk
   semua marker, terutama `as`, `in`, `into` — menghilangkan "bikin" → `in`.
2. Minta **adjakensi langsung** marker ke token format (marker diikuti
   maximal 1–2 token sebelum nama skill), bukan keberadaan global.
3. Pastikan skill target benar-benar **objek permintaan**: ada kata kerja
   artefak (buat/kirim/tampilkan/show/present) sebelum marker, dan tidak ada
   konteks topical ("rapat soal", "diskusi tentang", "meeting about").
4. Ulangi audit Langkah 1 + adversarial guard setelah penyempitan; syarat
   lulus: A01–A03 & A05 kembali HUNT, A08/A10 tetap MATCHED, v7 Grup A
   tidak turun di bawah 5/8.

Semua perubahan di atas butuh **izin terpisah**; tidak ada yang dikerjakan.

## Koreksi diri

1. Audit Langkah 1 awal saya menghitung 34 "aktivasi" karena memakai
   `debug_sieve` pada prompt mentah dan lupa syarat `ban non-empty`;
   angka benar adalah **11** setelah filter yang tepat.
2. Saya tidak menutup false positive F05 dengan menyebutnya "netral karena
   expect_status None"; itu benar-benar perubahan status HUNT→MATCHED.
3. A09 saya tulis aspiratif (MATCHED) padahal baseline HUNT; dicatat netral,
   bukan dijadikan alasan untuk melonggarkan guard.

## Status akhir

`dev = origin/dev = 24cab64`, clean. Worktree `wt-prefmt` dibuang.
**BERHENTI dan menunggu persetujuan** untuk penyempitan P-FMT atau izin
melanjutkan Langkah 3–4 tanpa perubahan engine.
