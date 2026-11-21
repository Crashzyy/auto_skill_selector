# Fase 3g — Laporan akhir

## State

- Mulai `dev@HEAD = c98f3af` (commit STOP Fase 3f). `main = d1de873` utuh,
  θ₀ 7.4688, margin P1b 0.08, probe, deskripsi tidak diubah; tidak ada merge.
- Semua angka dari binary hasil build ulang.
- Komit: `a99a9c4` (klasifikasi v6), `bca6a8a` (v7 freeze), `aad885a`+
  `be77fee`+`dc429c9` (guard + koreksi sebelum kode), `db7ea9f` (P-FMT).
- `dev = db7ea9f`, clean.

## Langkah 0 — Klasifikasi v6

`docs/V6_SPEC_MISMATCH.md`: 13 kegagalan v6 → **12 engine gap, 0 spec
mismatch, 1 noise sampel (X20)**. Headline v6 tetap **28/41**; file beku tidak
diedit. X27 = Stage-0 bypass (ellipsis tanpa penanda format), X28 = below-θ₀
tanpa penanda format — keduanya **tidak terjangkau P-FMT**; hanya X26 (dan
X29) yang struktural sesuai.

## Langkah 1 — v7 beku & baseline

- 30 kasus Y01–Y30, hash `b411991d705321f8a53e5b8e83228f78fd503bf107117da854402a0801905666`,
  0 duplikat dari 361 prompt existing, 0 expect ganda; ekspektasi sebelum probe.
- Komposisi A8/B6/C12/D4.
- Baseline: **20/30** — A 2/8, B 6/6, C 9/12, D 3/4.

## Langkah 2 — FMT_GUARD

- 10 kasus, hash akhir `fea04dbd860c2911c1fb8013fbd24a1d6ed55b5c15b8495113bdd0390a1d3ddd`,
  baseline **10/10** di binary unmodified.
- Koreksi guard sebelum kode: (1) ekspektasi aspiratif diganti invariant;
  (2) F01 "tanpa ban apa pun" mengandung cue `tanpa` yang sah membanned token
  `ban` → diganti; (3) F01 disetel ke baseline MATCHED. Bukan setelan ke ID uji.

## Langkah 3 — Uji dead-code (worktree scratch)

P-FMT diimplementasi di `/data/workspace/wt-pfmt` (tidak di-commit ke main
sampai diuji). Hasil: **bukan dead code** — v7 20→23, v5 15→16, v6 28→29,
v3/v4/v2 tidak berubah; guard 10/10; 7/7 gate; negasi 6/6. Worktree scratch
dibuang setelah commit.

## Langkah 4 — P-FMT (satu commit `db7ea9f`)

- Helper `pfmt_format_anchor`: cue grammar ID/EN (`sebagai`, `dalam bentuk`,
  `dalam`, `jadi`, `menjadi`, `as`, `in`, `into`) + token nama skill non-ban
  di klausa residual → dijadikan legal pin dengan **bobot eksplisit yang
  sudah ada** (1.0, shortcut pin).
- Hanya jika `banned` tidak kosong dan tidak ada pin eksplisit. Tidak
  menyentuh skor, θ₀, MNB, margin, jalur tanpa ban, atau bypass Stage 0.
- Daftar cue dari kaidah bahasa, bukan ID uji.

## Langkah 5 — Evaluasi (out-of-sample = v7)

| Set | Pra | Pasca | Diff per kasus |
|---|---|---|---|
| **v7 (held-out)** | **20/30** | **23/30** | **Y01, Y03, Y06** FAIL→PASS (semua Grup A) |
| v7 Grup A | 2/8 | **5/8** | +3 |
| v7 Grup B | 6/6 | 6/6 | tidak ada |
| v7 Grup C (kontrol) | 9/12 | 9/12 | tidak ada |
| v7 Grup D | 3/4 | 3/4 | tidak ada |
| v3 (dev) | 43/52 | 43/52 | tidak ada |
| v4 (dev) | 29/38 | 29/38 | tidak ada |
| v5 (dev) | 15/40 | 16/40 | W33 FAIL→PASS |
| v6 (dev) | 28/41 | 29/41 | X26 FAIL→PASS |
| v2 | 155/167 | 155/167 | tidak ada |
| b35 / negasi / guard / FMT_GUARD | 35/35 / 6/6 / 12/12 / 10/10 | sama | tidak ada |

**Tidak ada PASS→FAIL di mana pun.** Gain di v7 hanya di Grup A (target),
kontrol B/C/D utuh — ini in-intent, bukan bukti generalisasi untuk negasi
secara umum (X27/X28 memang tetap gagal, seperti diprediksi diagnosis v6).

## Gerbang & latensi (median 3 run, binary `db7ea9f`)

- 7/7 gerbang PASS; b35 35/35; negasi 6/6; FP conv 0/5.
- p99 3 run P-FMT: 227.8 / 217.6 / 222.6 µs → **median 222.6 µs**.
  Baseline 3 run: 227.6 / 224.0 / 216.3 µs → median 224.0 µs.
  Tidak naik (−1.4 µs), jauh di bawah batas +10%.

## Keputusan penutup (diminta)

Gain Grup A v7 = **3 kasus**, tepat di ambang. Tidak ada PASS→FAIL, kontrol
v7 B/C/D tidak turun, semua gerbang lolos. → **Rekomendasi: P-FMT boleh
dipertahankan**, dengan catatan: ini adalah perbaikan *sempit dan mekanistik*
(format-marker + skill mention), **bukan** perbaikan negasi umum. Sisa
kegagalan negasi (X27 bypass, X28 tanpa penanda) dan kelompok "skill benar
< θ₀" (X15/X23/X35, Y C 3 gagal) **tidak tersentuh** dan memerlukan izin
terpisah untuk kerja leksikon/splitter atau membuka probe/deskripsi.

## Koreksi diri

1. FMT_GUARD awal saya merah (4/10) karena ekspektasi aspiratif, bukan
   invariant; saya koreksi sebelum kode, bukan setelah melihat hasil P-FMT.
2. F01 dua kali salah: frasa "tanpa ban apa pun" memicu cue ban `tanpa`,
   lalu ekspektasinya masih HUNT padahal baseline MATCHED. Diperbaiki dan
   di-re-baseline di binary unmodified sebelum kode.
3. Saya tidak mengklaim P-FMT memperbaiki negasi v6 0/4: hanya X26 yang
   berubah; X27/X28 tetap gagal sesuai prediksi.
4. Tidak ada ekspektasi v3–v7, θ₀, probe, deskripsi, atau margin yang disetel.
   v5 headline tetap 15/40 pra → 16/40 pasca (pencapaian nyata, bukan
   penghapusan spec-mismatch W01–W10).

## Status akhir

`dev = origin/dev = db7ea9f`, `main = d1de873`, clean. Worktree scratch
dibuang. **BERHENTI.**
