# Fase 3e — Laporan akhir (P2a' tidak diimplementasi: gate terbukti mati)

## State

- Mulai `dev@5a3bb57` (laporkan hash sebenarnya; itu commit STOP Fase 3d).
- `main = d1de873` utuh, θ₀ = 7.4688 tidak diubah, margin P1b 0.08 tidak
  diubah, tidak ada merge ke main.
- Komit Fase 3e: `1d9d810` (v6 freeze+baseline), `3a020ef` (diagnosis v5),
  `7829c74` (guard), `a6d0006` (koreksi guard sebelum kode).
- Semua angka di bawah dari binary hasil build ulang di `5a3bb57`/`a6d0006`.
- v2/v3/v4/v5/v6 = dev/held-out; **tidak ada ekspektasi yang diedit**
  (koreksi guard sebelum kode adalah transkripsi guard saya sendiri).

## Langkah 1 — v6 dibekukan & baseline

- `tests/heldout_v6.json`, **41 kasus** (X01–X41), SHA256
  `7c7dac1a5a4bfd61bced0787fc71b37da51ee148bb1b33208253566940853fc4`.
- 0 duplikat terhadap 320 prompt unik v2/b35/v3/v4/v5 (cek skrip), 0 expect
  ganda; ekspektasi ditulis dari prinsip sebelum probe.
- Freeze: `docs/HELDOUT_V6_FREEZE.md`; baseline sekali:
  `docs/HELDOUT_V6_BASELINE.txt` → **28/41**.
- Per grup: informasional 10/11, alat-benar 6/7, polisemi 0/3, typo 3/4,
  negasi 0/4, multi 2/4, kontrol 7/8.

## Langkah 2 — Diagnosis v5 (read-only)

Tabel lengkap `docs/DIAGNOSIS_V5_FASE3E.md`. Ringkasan 25 kegagalan:

| Grup | ID | Akar | Usulan (tidak dikerjakan) |
|---|---|---|---|
| Informational-query | W01–W10 (10) | Stage 0 conversational bypass → NO_SKILL, ekspektasi lama HUNT | Gate niat informasional (P2a') |
| OOD kapital | W20–W22 (3) | token kapital tak dikenal → top 0 | Sinyal ortografis |
| Polisemi | W23, W25 (2) | `blender` aktif top ≈13 > θ₀ | Domain-context |
| Skill benar < θ₀ | W15, W16, W31, W32, W33, W39 (6) | splitter + `csv` lemah, top 4–6 < θ₀ | Leksikon/splitter (bukan θ₀) |
| MULTI→SINGLE | W37, W40 (2) | multi gate tak menangkap artefak ke-2 | Multi-skill gate |

Prioritas usulan: (1) informational gate, (2) ortografi OOD, (3) polisemi,
(4) multi/sinonim — keputusan di user.

## Langkah 3 — Guard set

- `docs/P2A_GUARD.json`, 12 kasus, SHA256 akhir
  `720066aaa43e400a74d93686e4ed1860ffaa42eb9d0245b4644ce2f611c24a28`.
- (i) alat berbentuk tanya → HUNT/MATCHED; (ii) informational murni → NO_SKILL;
  (iii) MATCHED tidak berubah. Ekspektasi sebelum probe.
- Baseline **12/12**. Koreksi sebelum kode: ekspektasi (i) salah transkripsi
  HUNT-only (padahal perintah HUNT/MATCHED) dan G11/G12 memakai nama alat yang
  tidak match; keduanya diperbaiki sebelum P2a' — bukan setelan ke ID v2–v6.

## Langkah 4 — P2a': tidak diimplementasi (alasan teknis, bukan STOP administratif)

Saya **menulis** gate niat informasional di `src/lib.rs` (helper
`is_informational_intent` + pemanggilan di Stage 5 HUNT branch, setelah P1b,
tanpa menyentuh skor/θ₀/MNB/margin/MATCHED/CLARIFY). Build ulang sukses, lalu
saya ukur:

- Semua set identik dengan pra-change: v2 155/167, b35 35/35, negasi 6/6,
  guard 12/12, v3 43/52, v4 29/38, v5 15/40, **v6 28/41** (0 kasus berubah).
- Probe pembanding dua binary (pra vs pasca) pada 11+ bentuk tanya ID/EN
  dengan token OOD (`apa itu XYZTOOL`, `what is ZZZTOOL…`, `kenapa ZQX9 gagal`,
  `sejarah alat XYZ999`, dll.): **semua sudah `NO_SKILL_NEEDED` di binary pra**
  lewat Stage 0 *conversational bypass*.
- Artinya jalur HUNT yang disyaratkan P2a' **tidak pernah tercapai** untuk
  niat informasional pada mesin ini: gate itu akan menjadi **dead code**.
  Mencommitnya hanya agar ada "implementasi P2a'" akan menyesatkan.

Maka kode P2a' **saya revert** (`git checkout -- src/lib.rs`), binary dibangun
ulang dari `a6d0006`, dan ini dilaporkan jujur. Tidak ada commit kode Langkah 4.
Bukan pelanggaran "satu perubahan per commit" — tidak ada perubahan yang
bertahan.

Catatan mekanistik: ini juga menjelaskan Grup 1 diagnosis — ekspektasi v5
W01–W10 (HUNT) memang tidak tercapai, tetapi arah perbaikannya bukan menambah
gate baru (sudah ada di Stage 0), melainkan **ekspektasi v5 yang tidak sesuai
desain saat ini**. Ekspektasi v5 dilarang diedit, jadi saya tidak menyentuhnya;
v6 sudah menulis prinsip informasional → NO_SKILL dan 10/11 lolos.

## Langkah 5 — Evaluasi pra vs pasca

Tidak ada pasca-P2a' (kode direvert), jadi pra = pasca persis:

| Set | Pra | Pasca | Diff |
|---|---|---|---|
| v6 (out-of-sample) | 28/41 | 28/41 | tidak ada |
| v3 (dev) | 43/52 | 43/52 | tidak ada |
| v4 (dev) | 29/38 | 29/38 | tidak ada |
| v5 (dev) | 15/40 | 15/40 | tidak ada |
| v2 | 155/167 | 155/167 | tidak ada |
| b35 / negasi / guard | 35/35 / 6/6 / 12/12 | sama | tidak ada |

Tidak ada PASS→FAIL di mana pun. v6 split: informasional 10/11, alat-benar
6/7, polisemi 0/3, typo 3/4, negasi 0/4, multi 2/4, kontrol 7/8 — semua
angka baseline tidak berubah. Karena tidak ada intervensi yang bertahan,
"gain in-intent" tidak ada untuk dilaporkan.

## Gerbang & latensi (binary build ulang `a6d0006`)

- 7/7 gerbang PASS; b35 35/35; negasi 6/6; FP conversational 0/5.
- p99 3 run: 222.8µs, 214.8µs, 209.8µs → **median 214.8µs** (baseline
  3e ≈ 219.1µs; tidak naik).

## Koreksi diri

1. Evaluator ablasi Fase 3d dulu salah field; di sini saya pakai evaluator asli
   untuk semua set dan mencocokkan hash v3/v4/v5 sebelum menjalankan.
2. Saya sempat menulis dan meng-build P2a', lalu menemukan ia dead code;
   saya revert daripada mengklaim perbaikan. Ini bukan "perbaikan diam-diam".
3. Guard pertama saya salah transkrip (HUNT-only, bukan HUNT/MATCHED) dan
   memakai dua nama alat yang tidak match; dikoreksi **sebelum** kode dan
   hash guard diperbarui (720066aa…), bukan setelah melihat hasil P2a'.
4. Saya tidak menyetel θ₀, margin, probe, deskripsi, atau ekspektasi v3/v4/v5/v6
   untuk menaikkan angka. v5 tetap 15/40 apa adanya.

## Status akhir & BERHENTI

`dev = origin/dev = a6d0006`, `main = d1de873`, clean. Tidak ada merge.
Menunggu keputusan user: apakah P2a' harus tetap diimplementasi sebagai no-op
(kode tidak akan pernah mengubah hasil pada mesin ini), atau arah perbaikan
dialihkan ke Grup 2–5 dari tabel diagnosis (ortografi/polisemi/multi/sinonim).
