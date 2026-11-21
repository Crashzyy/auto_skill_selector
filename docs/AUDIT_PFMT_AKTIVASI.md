# Fase 3h Langkah 1 — Audit aktivasi P-FMT (read-only)

Binary: `db7ea9f` (HEAD `24cab64`, kode identik) vs `db7ea9f^ = dc429c9`.
Keduanya di-build ulang. 425 kasus dari v2, b35, v3–v7, P2A_GUARD,
FMT_GUARD discan.

## Definisi aktivasi

`pfmt_format_anchor` aktif bila: **ban tidak kosong** + ada FORMAT_MARKER
(`sebagai`, `dalam bentuk`, `dalam`, `jadi`, `menjadi`, `as`, `in`, `into`)
+ token yang cocok dengan nama skill non-ban → pin dibuat (bobot 1.0).

Aktivasi struktural terdeteksi: **11 kasus**:

| Set/ID | Anchor | Status pra → pasca | Penilaian |
|---|---|---|---|
| b35 #4 | web-landing-design | MATCHED → MATCHED | netral (sudah benar) |
| b35 #5 | pdf-extraction-manipulation | MATCHED → MATCHED | netral |
| v2 B10 | powerpoint-slide-deck | MATCHED → MATCHED | netral |
| v4 V29 | pdf-extraction-manipulation | MATCHED → MATCHED | netral |
| v6 X26 | word-docx-reporting | HUNT → MATCHED | **benar** |
| v7 Y01 | word-docx-reporting | HUNT → MATCHED | **benar** |
| v7 Y03 | spreadsheet-modeling | CLARIFY → MATCHED | **benar** |
| v7 Y05 | write-swift | CLARIFY → CLARIFY | netral (anchor tak mengubah) |
| v7 Y06 | tabular-pivot-cleaning | CLARIFY → MATCHED | **benar** |
| v7 Y07 | mermaid-architecture-diagram | MATCHED → MATCHED | netral |
| v7 Y08 | word-docx-reporting | MATCHED → MATCHED | netral |

## Delta status aktual (6 kasus)

| Set/ID | Pra → Pasca | Penilaian |
|---|---|---|
| v6 X26 | HUNT → MATCHED (word-docx-reporting) | benar |
| v7 Y01 | HUNT → MATCHED (word-docx-reporting) | benar |
| v7 Y03 | CLARIFY → MATCHED (spreadsheet-modeling) | benar |
| v7 Y06 | CLARIFY → MATCHED (tabular-pivot-cleaning) | benar |
| v5 W33 | HUNT → MATCHED (imaging-data-commons) | benar |
| **v2 F05** | HUNT → MATCHED (boring-marketing-email-sequences) | **FALSE POSITIVE** |

## Temuan penting — false positive pin di v2 F05

`F05 = "Dari: Andi\nIsi: jangan pakai excel untuk laporan ini. __PAYLOAD_500__
tolong bikin email yang membosankan"`.

- Sieve residual: `"... tolong bikin email yang membosankan"`, ban `excel`.
- Marker yang memicu: **`in`** dari substring `"bikin "` — bukan penanda
  format. Kode memakai `lower.contains("in ")` (substring, bukan word-boundary),
  sehingga `bi**kin** ` salah terdeteksi sebagai penanda `in`.
- Anchor yang terpilih: `boring-marketing-email-sequences` (token `email`).
- Hasil: top_score tepat 1.00 = pin shortcut, status HUNT → MATCHED.
- Ini **bukan** perbaikan yang diminta; itu efek samping substring matching
  pada cue bahasa Inggris `in`.

Implikasi: mekanisme P-FMT lebih luas dari yang dilaporkan Fase 3g
(Fase 3g hanya menghitung per-set +3/+1/+1 dan tidak melihat delta F05 karena
F05 adalah kasus `expect_status: None` yang tidak dihitung sebagai PASS/FAIL
oleh evaluator v2).

## Rekap hitungan

- Aktivasi struktural: 11
- Dari aktivasi: benar 4, salah 0 (dalam 11), netral 7
- Delta status: 6 → benar 5, **salah 1 (F05)**
- Total kasus terpengaruh benar: 5, salah: 1.

Detail ini menjadi dasar FMT_ADV_GUARD (Langkah 2). Sesuai STOP otomatis,
false positive pin akan diverifikasi dengan guard adversarial sebelum
keputusan apa pun; tidak ada implementasi perbaikan di fase ini.
