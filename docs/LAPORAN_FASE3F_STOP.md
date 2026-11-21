# Fase 3f — STOP di Langkah 1 (diagnosis v6): negasi 0/4 bukan satu mekanisme

## State

- HEAD = **`383de5b`** (konfirmasi: **bukan `a6d0006`** — itu commit koreksi
  guard Fase 3e, dua commit lebih awal). `main = d1de873` utuh, clean.
- Binary di-build ulang dari `383de5b` (`BUILD-OK-383de5b`).
- θ₀ 7.4688, margin P1b, probe, deskripsi: tidak diubah; tidak ada merge.

## Langkah 0 — Pembukuan (SELESAI, commit `499246d`)

- Addendum `docs/DIAGNOSIS_V5_FASE3E.md`: **W14** masuk Grup 4
  (`CLARIFY`, dbg 5.53 < θ₀); **W30** tetap FAIL karena
  `expect_banned_contains: powerpoint` tapi ban set berisi `['powpoint']`.
  Total kegagalan v5 dari RUN aktual = **25**.
- `docs/V5_SPEC_MISMATCH.md`: v5 headline tetap **15/40**, dengan catatan
  terpisah 10 kasus (W01–W10) spec-mismatch — engine `NO_SKILL_NEEDED` benar
  menurut desain Stage 0. File v5 beku tidak diedit.

## Langkah 1 — Diagnosis v6 (read-only)

Sumber: `docs/HELDOUT_V6_BASELINE.txt`, 13 kegagalan dari 41 kasus (28/41).
Tabel per kasus (status aktual → ekspektasi, stage/mekanisme):

| ID | Grup | Aktual → Exp | Stage / Mekanisme |
|---|---|---|---|
| X03 | informasional | `CLARIFY_AMBIGUOUS` → NO_SKILL | Stage 0/5: dbg 4.95 < θ₀, top 0.00; "cara menghitung… gimana ya" masuk gray zone/CLARIFY |
| X15 | alat-benar | `HUNT_NEW_SKILL` → MATCHED | Stage 5: top 2.69, dbg 1.91; "terjemahkan… Jerman" tak cukup bobot → below_theta HUNT |
| X19 | polisemi | `MATCHED_SINGLE` → NO_SKILL | Stage 5: `slide` (alat) aktif, top 11.71 > θ₀; konteks mikroskop tak membedakan |
| X20 | polisemi | `HUNT_NEW_SKILL` → NO_SKILL | Stage 5: `chart` OOD-ish, top 6.82 < θ₀ → below_theta HUNT |
| X21 | polisemi | `MATCHED_SINGLE` → NO_SKILL | Stage 5: `blender` aktif, top 13.50 > θ₀; konteks dapur tak membedakan |
| X23 | typo | `HUNT_NEW_SKILL` → MATCHED | Stage 5: `olh` tak dikoreksi, top 6.84 < θ₀ → below_theta |
| X26 | negasi | `HUNT_NEW_SKILL` → MATCHED | Stage 2 ban `pdf` ✓; sisa "kirim hasilnya sebagai docx" top 6.65 < θ₀ → HUNT |
| X27 | negasi | `NO_SKILL_NEEDED` → MATCHED | Stage 2 ban `slides` ✓; sisa "ringkasannya saja cukup" kena Stage 0 bypass → NO_SKILL |
| X28 | negasi | `HUNT_NEW_SKILL` → MATCHED | Stage 2 ban `infografik` ✓; sisa "cukup tabel biasa" top 2.84 < θ₀ → HUNT |
| X29 | negasi | `HUNT_NEW_SKILL` → MATCHED | Stage 2 ban `chart` ✓; sisa "sajikan angkanya dalam tabel" top 2.60 < θ₀ → HUNT |
| X31 | multi | `MATCHED_SINGLE` → MULTI | Stage 5: top 11.64 > θ₀, dua artefak tak memicu multi gate |
| X32 | multi | `MATCHED_SINGLE` → MULTI | Stage 5: top 10.67 > θ₀, sama |
| X35 | kontrol | `HUNT_NEW_SKILL` → MATCHED | Stage 5: "cek kode… perbaiki" top 5.35 < θ₀ → below_theta |

### Fokus: negasi v6 0/4 vs v2 6/6

Keempat cue negasi **terdeteksi dan dibuang dengan benar** oleh Stage 2 sieve:

| ID | cue | `global_banned_set` | sisa klausa (sanitized) |
|---|---|---|---|
| X26 | `hindari pdf` | `['pdf']` | "kirim hasilnya sebagai docx" |
| X27 | `jangan pakai slides` | `['slides']` | "ringkasannya saja cukup" |
| X28 | `jangan gunakan infografik` | `['infografik']` | "cukup tabel biasa" |
| X29 | `tanpa chart` | `['chart']` | "sajikan angkanya dalam tabel" |

Jadi **bukan masalah deteksi ban / cakupan cue**. Beda v2 vs v6 terletak pada
**klausa positif sesudah ban**:

- v2 negasi 6/6 memakai artefak eksplisit + nama skill dikenal
  (mis. "jangan pakai excel, buatkan tabel penjualan" → B06; "Jangan pakai
  Excel. Tolong buat grafik…" → F03). Klausa sisa punya anchor skill kuat.
- v6 memakai kata ganti/ellipsis ("hasilnya", "ringkasannya saja cukup",
  "cukup tabel biasa", "sajikan angkanya dalam tabel") tanpa nama skill
  → skor jauh di bawah θ₀ (2.60–6.65) atau kena conversational bypass.

**Dua mekanisme berbeda**:
1. X26/X28/X29 — sisa klausa `below_theta` → `HUNT_NEW_SKILL` (Stage 5).
2. X27 — sisa klausa kena **conversational bypass** Stage 0 → `NO_SKILL_NEEDED`.

Sesuai perintah eksplisit: *"Jika 4 kegagalan itu BUKAN satu mekanisme, STOP
dan lapor sebelum kode."* → **BERHENTI di Langkah 1.**

## Konsekuensi

- P-NEG (Langkah 4) **tidak diimplementasi**. Generalisasi aturan ban tidak
  akan menyentuh kasus ini: ban sudah benar; yang salah adalah skor/bypass
  klausa residual, yang dilarang diubah (skor/θ₀/MNB/margin tidak boleh
  berubah) dan bukan objective P-NEG ("hanya menghapus kandidat").
- v7 tidak dibekukan; guard negasi tidak ditulis; tidak ada perubahan kode.
- Tidak ada ekspektasi set mana pun yang diedit.

## Koreksi diri

1. Saya sempat mengira W30 PASS karena statusnya `MATCHED_SINGLE`; evaluator
   asli juga mengekspektasikan ban `powerpoint`, jadi W30 tetap FAIL. Angka
   sementara 24 gagal saya buang; RUN aktual memberi **25** dan doc sudah
   dikoreksi di `499246d`.
2. Diagnosis v6 tidak dipaksa menjadi "satu mekanisme negasi" demi bisa
   melanjutkan ke kode. Dua jalur berbeda dilaporkan apa adanya.

## Yang dibutuhkan

Keputusan user: apakah P-NEG masih harus dijalankan sebagai eksperimen
kontrol (kemungkinan besar dead code / nol perubahan, seperti P2a' di 3e),
atau arah perbaikan dialihkan ke klausa residual (skor/bypass) — yang
memerlukan izin mengubah jalur selain "hanya menghapus kandidat".
**BERHENTI dan menunggu persetujuan.**
