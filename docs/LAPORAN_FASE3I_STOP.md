# Fase 3i — STOP di Langkah 3 (penyempitan (a)+(b) gagal)

## State

- HEAD = **`148f5b3`** saat mulai (konfirmasi: **bukan `24cab64`** — itu dua
  commit lebih awal; `148f5b3` = laporan STOP Fase 3h). Setelah commit
  docs (`8ed6e23`) dan v8 (`10d372f`), HEAD = `10d372f`.
- `main = d1de873` utuh; θ₀ 7.4688, margin P1b, probe, deskripsi tidak
  diubah; tidak ada merge; semua angka dari binary build ulang.
- **Penyempitan diuji di worktree scratch `wt-narrow` dan TIDAK di-commit**
  ke `dev`. Tidak ada perubahan engine di Fase 3i.

## Langkah 0 — Rekonsiliasi evaluator (SELESAI, commit `8ed6e23`)

Perhitungan ulang A01–A14 dari binary build ulang: **pra 7/14, pasca 8/14**.
Skor naik (+1: A08, A10 FAIL→PASS), tetapi kualitatif lebih buruk:
- A05 **PASS→FAIL** (HUNT → MATCHED `boring-marketing-email-sequences`);
- A01–A03 tetap FAIL, tapi berubah dari HUNT (perilaku benar) menjadi
  MATCHED dengan skill yang tidak diminta.

Koreksi laporan 3h: kalimat "pasca lebih buruk dari pra" **tidak tepat jika
diartikan sebagai skor**; dibedakan sekarang menjadi skor naik vs kualitas
perilaku turun. A09 dicatat **aspiratif**, dikeluarkan dari gerbang,
tetap dilaporkan; hash guard tidak diubah.

## Langkah 1 — v8 beku (SELESAI, commit `10d372f`)

- 30 kasus Z01–Z30, hash
  `6353018569eb681ad411c25ebcae75bde10de8e312d8f273f7c21af958fb8bf7`,
  0 duplikat dari 426 prompt (termasuk FMT_ADV_GUARD), 0 expect ganda.
- Baseline (binary build ulang):
  - **HEAD (`db7ea9f` kode) = 17/30** — A 5/8, B 1/8, C 7/10, D 4/4.
  - **pra-P-FMT (`dc429c9`) = 15/30** — A 3/8, B 1/8, C 7/10, D 4/4.
- Catatan jujur: grup B (1/8) bersifat aspiratif pada kedua binary — engine
  memang mem-pin skill topik; itu justru target deteksi false positive.

## Langkah 2 — Harness diferensial (SELESAI)

`tests/diff_harness.py`, 468 kasus. Pra-P-FMT → HEAD: **20 delta**:
{X26, Y01, Y03, Y06, W33, Z01, Z04, Z08, Z09, Z10, Z11, Z12, Z13,
A01, A02, A03, A05, A08, A10, F05}. Termasuk 5 false positive Grup B v8
(Z09–Z13) dan F05. Output: `docs/DIFF_PREPFMT_VS_HEAD.txt`.

## Langkah 3 — Penyempitan (a)+(b): GAGAL → STOP

Di worktree scratch, helper diubah:
- (a) marker dicocokkan **per token utuh** (`dalam bentuk` satu marker),
  menghilangkan substring `bikin`→`in`;
- (b) **adjakensi** marker→token skill, maksimal satu filler dari himpunan
  tertutup `{file, format, bentuk, berkas, a, an, the, sebuah}`.

Hasil diferensial pra-P-FMT → penyempitan: **10 delta**:
{X26, Y01, Y03, Y06, Z01, Z08, Z11, A03, A08, A10}.

### Dua kegagalan gate (keduanya memicu STOP)

1. **A03 masih false positive**: `"don't use excel, I'm in a meeting about
   word"` → residual `"I'm in a meeting about word"`; marker `in`, filler
   `a`, token `meeting` → pin `meeting-notes-action-items` (top 1.00).
   Ini adalah topik, bukan format yang diminta. (a)+(b) tidak cukup;
   memperbaikinya butuh **aturan ketiga** (dilarang).
2. **W33 hilang**: v5 turun **16/40 → 15/40** (W33 kembali HUNT), melanggar
   syarat "X26/Y01/Y03/Y06/W33 tidak boleh hilang".

Metrik penyempitan (scratch): v3 43/52, v4 29/38, v5 **15/40** (regresi),
v6 29/41, v7 23/30, v8 17/30; guard 12/12, FMT_GUARD 10/10,
FMT_ADV_GUARD **9/14** (A03 masih FAIL, A09 aspiratif); v2 155/167;
7/7 gate; p99 210.1µs. Tidak ada commit kode.

## Keputusan

Sesuai perintah: *"Jika A01–A03/A05 masih gagal setelah (a)+(b), atau salah
satu dari X26/Y01/Y03/Y06/W33 hilang: STOP, laporkan. Jangan tambah aturan
ketiga."* → **BERHENTI.**

Rekomendasi (TIDAK dijalankan): **git revert `db7ea9f`** — mengembalikan
P-FMT ke pra-state (`dc429c9`) adalah satu-satunya jalan yang saat ini
terbukti bebas false-positive pin A01–A03/A05/F05, dengan biaya kehilangan
5 perbaikan benar (X26, Y01, Y03, Y06, W33). Menjaga P-FMT apa adanya
berarti menerima false positive pada kalimat topical. Keputusan ada di user;
saya tidak mengeksekusi revert tanpa izin.

Langkah 4 (evaluasi final) dan Langkah 5 (diagnosis pooled) **tidak
dijalankan** karena STOP di Langkah 3.

## Koreksi diri

1. A09 saya tulis aspiratif di guard 3h; kini dicatat eksplisit dan
   dikeluarkan dari gerbang tanpa mengubah hash.
2. Saya awalnya mengira rekonsiliasi 7→8 berarti "pasca lebih buruk" itu
   salah hitung; ternyata skornya naik. Koreksi: yang memburuk adalah
   kualitas perilaku (A05, A01–A03), bukan angka agregat.
3. Ekspektasi Grup B v8 (1/8) aspiratif pada kedua binary; dilaporkan apa
   adanya, tidak disetel agar terlihat bagus.
4. Tidak ada ekspektasi, hash set, θ₀, probe, deskripsi, atau margin yang
   diubah; tidak ada kode engine yang di-commit di Fase 3i.

## Status akhir

`dev = origin/dev = 10d372f`, `main = d1de873`, clean.
Worktree scratch `wt-narrow` dan `wt-prefmt-i` dibuang. **BERHENTI.**
