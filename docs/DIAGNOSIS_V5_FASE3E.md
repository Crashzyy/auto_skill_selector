# Fase 3e Langkah 2 — Diagnosis v5 (read-only)

Sumber: binary hasil build ulang di `5a3bb57` (kode identik `9e30de9`).
25 kegagalan v5 (baseline 15/40), dikelompokkan per akar masalah.
`top` = top_score; `dbg` = debug_score. Tidak ada perbaikan yang diterapkan dari
tabel ini — semua usulan adalah prinsip umum, bukan setelan per kasus.

## Grup 1 — Informational-query HUNT (W01–W10)

| ID | Aktual → Ekspektasi | Mekanisme (skor/gerbang/stage) |
|---|---|---|
| W01 | `NO_SKILL_NEEDED` → HUNT | Stage 0/1: top 0.00, dbg 3.79 → conversational bypass/NO_SKILL, tidak masuk HUNT |
| W02 | `NO_SKILL_NEEDED` → HUNT | top 0.00, dbg 2.29 — sama |
| W03 | `NO_SKILL_NEEDED` → HUNT | top 0.00, dbg 0.00 — sama |
| W04 | `NO_SKILL_NEEDED` → HUNT | top 0.00, dbg 5.85 — sama |
| W05 | `NO_SKILL_NEEDED` → HUNT | top 4.40, dbg 2.96 →NO_SKILL lewat bypass, bukan skor ≥θ₀ |
| W06 | `NO_SKILL_NEEDED` → HUNT | top 0.00, dbg 0.00 — sama |
| W07 | `NO_SKILL_NEEDED` → HUNT | top 0.00, dbg 0.00 — sama |
| W08 | `NO_SKILL_NEEDED` → HUNT | top 0.00, dbg 0.00 — sama |
| W09 | `NO_SKILL_NEEDED` → HUNT | top 3.49, dbg 2.31 — sama |
| W10 | `NO_SKILL_NEEDED` → HUNT | top 6.49, dbg 4.18 — sama |

**Akar**: bentuk tanya/penjelasan memicu *conversational bypass* di Stage 0
sebelum decision gate; ekspektasi lama menganggap ini HUNT. **Usulan umum**:
gate niat informasional yang membedakan "tanya untuk penjelasan" vs "minta
artefak"—dikerjakan P2a' di Langkah 4 (HUNT/unknown-only, tidak menyentuh
MATCHED/CLARIFY). Catatan: ekspektasi v5 tidak diedit; arah P2a' diukur pada
v6 yang ekspektasinya ditulis dari prinsip (informasional → NO_SKILL).

## Grup 2 — OOD kapital / istilah tak dikenal (W20–W22)

| ID | Aktual → Ekspektasi | Mekanisme |
|---|---|---|
| W20 | `NO_SKILL_NEEDED` → HUNT | `DMX512` tak ada di kosakata → top 0.00 → NO_SKILL, bukan HUNT |
| W21 | `NO_SKILL_NEEDED` → HUNT | `BACnet` tak dikenal → top 0.00 |
| W22 | `NO_SKILL_NEEDED` → HUNT | `ZBrush` tak dikenal → top 0.00 |

**Akar**: token kapital OOD tidak menghasilkan sinyal HUNT. **Usulan umum**
(di luar cakupan Fase 3e): sinyal ortografis untuk token Capitalized tak
dikenal → HUNT. TIDAK diimplementasi (perintah: OOD kapital tidak dikerjakan).

## Grup 3 — Polisemi (W23, W25)

| ID | Aktual → Ekspektasi | Mekanisme |
|---|---|---|
| W23 | `MATCHED_SINGLE` → NO_SKILL | `blender` (alat 3D) aktif: top 13.09 > θ₀ → MATCHED, padahal konteks resep makanan |
| W25 | `MATCHED_SINGLE` → NO_SKILL | `blender` aktif: top 13.14 > θ₀ → MATCHED, konteks beli alat dapur |

**Akar**: token domain berpolisemi tanpa pembeda konteks. **Usulan umum**
(di luar cakupan): domain-context / companion-word signal. TIDAK diimplementasi.

## Grup 4 — Skill benar tapi skor di bawah θ₀ (W15, W16, W31, W32, W33, W39)

| ID | Aktual → Ekspektasi | Mekanisme |
|---|---|---|
| W15 | `HUNT_NEW_SKILL` (`below_theta`) → MATCHED | top 6.02, CSV tak cukup bobot → HUNT |
| W16 | `CLARIFY_AMBIGUOUS` → MATCHED | top 0.00, dbg 0.00 → Stage 0 bypass (terjemah) gagal match |
| W31 | `HUNT_NEW_SKILL` (`below_theta`) → MATCHED | top 4.91; klausa "olah data ini pakai csv" terpisah |
| W32 | `HUNT_NEW_SKILL` (`below_theta`) → MATCHED | top 4.57; klausa "pun aku bisa tulis laporan" |
| W33 | `HUNT_NEW_SKILL` (`below_theta`) → MATCHED | top 5.71; klausa "bikin tabel dari data ini" |
| W39 | `HUNT_NEW_SKILL` (`below_theta`) → MATCHED_MULTI | top 4.27; dua klausa terdeteksi tapi skor pertukaan rendah |

**Akar**: kombinasi (a) tokenizer "csv" lemah, (b) splitter memisah klausa
sehingga tiap klausa kehilangan konteks, (c) skor < θ₀. **Usulan umum**
(di luar cakupan P2a'): perluasan sinonim `csv`→tabel/spreadsheet (lexicon,
bukan θ₀) dan perbaikan splitting negasi. TIDAK diimplementasi — P2a' hanya
menyangkut jalur HUNT informasional.

## Grup 5 — MULTI yang terdeteksi sebagai SINGLE (W37, W40)

| ID | Aktual → Ekspektasi | Mekanisme |
|---|---|---|
| W37 | `MATCHED_SINGLE` → MULTI | top 19.62 > θ₀; dua artefak (analisis + grafik) tidak memicu multi gate |
| W40 | `MATCHED_SINGLE` → MULTI | top 10.85 > θ₀; "ubah pdf jadi docx" + "rangkum" dianggap satu skill |

**Akar**: decision gate multi-skill tidak menangkap pasangan artefak kedua
ketika skor pertama dominan. **Usulan umum** (di luar cakupan): penyesuaian
multi-skill gate berbasis jumlah artefak. TIDAK diimplementasi.

## Prioritas usulan (untuk diputuskan user, bukan dikerjakan sekarang)

1. Gate niat informasional (P2a') — langsung ditangani Langkah 4, karena tidak
   mengubah skor/θ₀ dan punya guard set.
2. Sinyal ortografis OOD kapital (W20–W22).
3. Domain-context untuk polisemi (W23/W25).
4. Multi-skill gate + sinonim csv (W15/W31/W37/W40) — paling invasif.

## Koreksi kategori lama

Ekspektasi W01–W10 adalah HUNT (v5), tetapi desain v6 menulis
informasional → NO_SKILL_NEEDED. Itu **bukan edit ekspektasi**; v5 dibekukan
dan tetap dilaporkan apa adanya (25/40 gagal). v6 adalah held-out baru dengan
prinsip berbeda. Tidak ada penyetelan ke ID mana pun.
