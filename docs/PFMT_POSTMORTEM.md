# PFMT_POSTMORTEM — Fase 3j Langkah 2

Keputusan user: **P-FMT di-revert** (`git revert db7ea9f` → `4e70dbf`), tanpa
aturan ketiga, tanpa penyempitan. Dokumen ini merangkum seluruh eksperimen.

## Apa yang dicoba

1. **Fase 3g** — P-FMT diimplementasi: jika ada ban, residual dengan penanda
   format + token nama skill non-ban dijadikan pin (bobot 1.0 = mention
   eksplisit). Uji scratch: v7 A 2/8→5/8, v5 +1, v6 +1, 7/7 gate, nol
   PASS→FAIL → di-commit `db7ea9f`.
2. **Fase 3h** — audit aktivasi + adversarial guard menemukan false-pin:
   marker `in` cocok sebagai substring pada "bikin ", dan marker + skill
   bisa berjauhan ("dalam rapat soal word"). STOP.
3. **Fase 3i** — penyempitan (a) word-boundary marker + (b) adjakensi
   (maks. satu filler tertutup) diuji di worktree: 10 delta, tapi A03 masih
   false-positive ("in a meeting" → `meeting-notes-action-items`) dan W33
   hilang (v5 16→15). STOP; aturan ketiga dilarang.
4. **Fase 3j** — revert.

## Audit aktivasi (Fase 3h)

425 kasus → **11 aktivasi** struktural (ban non-empty + marker + anchor),
6 perubahan status: 5 benar (X26, Y01, Y03, Y06, W33), 1 salah (v2 F05:
"bikin email" → pin `boring-marketing-email-sequences`).

Kelas false positive:
- **marker substring**: `in `/Si "bikin ", "bikinkan" (F05, A05);
- **tanpa adjakensi**: `dalam rapat soal word` → pin word (A01–A03);
- **format vs topik**: `meeting about word` → `meeting-notes-action-items`
  (A03, Z11 — marker `in` + determiner `a` + `meeting`);
- **pin menimpa skill benar**: Z04 `pdf-extraction-manipulation` → `geo-report`.

## Klasifikasi Z11 dan Z04 (dari output mentah, binary build ulang)

| ID | Prompt | pra-PFMT | P-FMT | Penilaian |
|---|---|---|---|---|
| Z11 | "don't use excel, I'm in a meeting about word usage" | HUNT `[]`, top 4.69 | MATCHED `meeting-notes-action-items`, **top 1.00** | **SALAH** — topik rapat, bukan permintaan format |
| Z04 | "don't use word, write the report as a pdf" | MATCHED `pdf-extraction-manipulation`, top 12.65 | MATCHED `geo-report`, **top 1.00** | **SALAH** — pin menggantikan skill yang sudah benar |

Keduanya bertanda top_score tepat 1.00 = pin shortcut, bukan skor organik.

## Hasil penyempitan (Fase 3i, tidak di-commit)

(a) marker per token utuh; (b) adjakensi marker→skill, filler tertutup
`{file, format, bentuk, berkas, a, an, the, sebuah}`. Hasil: **10 delta**
vs pra-PFMT: {X26, Y01, Y03, Y06, Z01, Z08, Z11, A03, A08, A10}.
A03 & Z11 masih berubah (salah), W33 hilang (v5 16→15). STOP.

Rekonstruksi (deskripsi, bukan kode): ganti `FORMAT_MARKERS` contains-check
dengan tokenisasi + pencocokan token utuh; tangani "dalam bentuk" sebagai
satu marker; untuk setiap posisi marker, terima kandidat pada `i+1` atau
`i+2` hanya bila `i+1` termasuk filler tertutup; cocokkan kandidat dengan
salah satu token nama skill; tolak yang banned. Helper tetap di module scope
(sebelum `impl SkillBrain`) — lihat catatan build E0425 di skill.

## Kesimpulan struktural

1. **Cue tata bahasa tidak membedakan format dari topik.** Kehadiran marker
   (`sebagai`, `dalam`, `as`, `in`) dan token nama skill dalam klausa yang
   sama bukan bukti hubungan argument-sintaktik. "dalam rapat soal word"
   dan "in a meeting" adalah konteks topikal.
2. **Pin bobot 1.0 melewati θ₀.** Begitu anchor dibuat, shortcut pin
   mengembalikan `MATCHED` dengan top 1.00 — mengabaikan bukti skor organik
   (Z04: 12.65 → 1.00) dan menimpa keputusan yang sudah benar.
3. Karena (1) dan (2) bersifat struktural, penyempitan tambahan apa pun
   (aturan ketiga: konteks topikal / kata kerja artefak) berisiko menjadi
   daftar per kasus; sesuai instruksi, tidak dikejar.

## Aset regresi yang dipertahankan

- `tests/heldout_v8.json` + `eval_heldout_v8.py` (hash `63530185…`)
- `docs/FMT_ADV_GUARD.json` + `tests/eval_fmt_adv_guard.py` (hash `17bbb974…`)
- `tests/diff_harness.py` + output diff (`DIFF_PREPFMT_VS_HEAD`,
  `DIFF_REVERT_VS_PREPFMT`, `DIFF_HEAD_VS_REVERT`)
- `docs/AUDIT_PFMT_AKTIVASI.md`, `docs/V6_SPEC_MISMATCH.md`

Penyempitan **tidak** disimpan sebagai kode; dideskripsikan cukup untuk
direkonstruksi bila izin diberikan kelak.
