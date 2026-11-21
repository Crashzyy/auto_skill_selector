# Laporan Akhir Fase 3b — auto_skill_selector

Mulai dari `dev@5917645`. Semua angka dari binary hasil **build ulang**.
`main = d1de873` (hard lock) tidak disentuh. θ₀ = 7.4688 **tidak diubah**.

## Ringkasan metrik

| Metrik | Sebelum (5917645) | Sesudah |
|---|---|---|
| v2 | 152/167 | **155/167** |
| Regresi 35 | 35/35 | 35/35 |
| Negasi | 6/6 | 6/6 |
| 7 gerbang | 7/7 | 7/7 |
| Held-out v3 | 43/52 | 43/52 (tdk dijalankan ulang) |
| Held-out v4 (sekali, baru) | — | **29/38** |
| p50 / p99 | 41.5µs / 242.4µs | **38.2µs / 220.8µs** |

## Langkah 0 — rekonsiliasi held-out v3 (tanpa ubah kode)

- Output mentah: `docs/HELDOUT_V3_RESULT.txt` (diregenerasi ulang di **9e30de9**
  dengan binary build ulang; angka aktual **43/52**).
- **9 ID gagal sebenarnya di 9e30de9**: HO13, HO14, HO16, HO17, HO18, HO19,
  HO20, HO24, HO28 — **bukan** HO01–08/HO09–12 seperti draf lama, dan **bukan**
  HO36 (HO36 kini PASS lewat P3b). Status aktual tercantum di file hasil.
- Perubahan vs 5917645: **HO36 FAIL→PASS** (P3b), **HO14 PASS→FAIL** (efek
  samping P1b: `pakai tool aneh bikin laporan` → CLARIFY karena skor masuk zona
  abu). Net 43/52 tetap.
- 12 duplikat v2/b35: 8 PASS / 4 FAIL (HO13, HO16, HO18, HO24).
  **40 independen: 35 PASS / 5 FAIL** (HO14, HO17, HO19, HO20, HO28).
  Perkiraan 44/52 / independen 36/40 di permintaan **tidak sesuai RUN aktual**;
  dilaporkan apa adanya, tidak disetel.

## Langkah 1 — held-out v4

- 38 kasus, dibekukan sebelum kode: SHA256
  `a2c082fd5ab90eedd3e68712040262da88fd677652caf8aed77ea2e7b80902d8`.
- 0 duplikat dengan v2/b35/v3 (cek skrip), 0 expect ganda SINGLE/MULTI.
- Ekspektasi ditulis sebelum probe engine.

## Pekerjaan & diff per kasus

| Commit | Perubahan | Diff per kasus |
|---|---|---|
| `4e3e7ab` P3b | `hindari X` = ban; Stage-0 tidak swallow ban cue | HO36 FAIL→PASS (`hindari excel buat tabel` banned `[]`→`[excel,xls,xlsx]`). E10 dijaga (idiom `jangan...dulu` → NO_SKILL) |
| `a512d02` P4c | koreksi 1-edit kandidat-tunggal pasca-leet | H06/V22/V24 **tetap FAIL** (`penjalan` 7 kandidat → ambigu, ditolak; 4→u dilarang). k8s hunt utuh |
| `b4fd56b` P1a | fuzzy canon dipakai penuh (longest-preference) | `wrod`→`word` MATCHED; **G02 tetap 7.09** (fitur masuk tapi `active_n` MNB menyerap gain) |
| `bda31ad` P1b | zona abu CLARIFY margin 8%, only below_theta | G02/G04/G05 FAIL→PASS (→CLARIFY); v2 152→155 |
| `7851fd1` P2 | observasi saja, tanpa binary | penalti 0.5x tidak cukup balik K05; usulan ditulis |

## Tabel per kategori v2 (sebelum → sesudah)

| Kat | Sebelum | Sesudah | Δ |
|---|---|---|---|
| A | 14/14 | 14/14 | 0 |
| B | 27/29 | 27/29 | 0 |
| C | 7/7 | 7/7 | 0 |
| D | 16/17 | 16/17 | 0 |
| E | 20/20 | 20/20 | 0 |
| F | 7/8 | 7/8 | 0 |
| **G** | 8/12 | **11/12** | **+3** |
| H | 20/21 | 20/21 | 0 |
| I | 7/7 | 7/7 | 0 |
| J | 8/8 | 8/8 | 0 |
| K | 3/8 | 3/8 | 0 |
| L | 9/9 | 9/9 | 0 |
| M | 6/7 | 6/7 | 0 |

PASS→FAIL: **tidak ada**. Kenaikan hanya di G.

## Held-out v4 — 29/38 (dijalankan sekali, output mentah:
## `docs/HELDOUT_V4_RESULT.txt`)

9 kegagalan: V08 (expect MULTI, engine PARTIAL+HUNT), V15 & V25 (OOD kapital,
butuh P2 ortografi), V16 (polisemi food processor), V21–V24 (noise pola baru
belum tertangkap), V27 (`powpoint` typo → ban `powpoint`, ekspektasi
`powerpoint` terlalu spesifik). Tidak ada setelan untuk menaikkannya.

Catatan V25: `k8s cluster butuh konfigurasi` → NO_SKILL (skor 0, anchor tak
ada), tapi G12 `k8s dashboard` → HUNT (7.10, `unknown_tool`) tetap aman.

## 7 gerbang

| Gerbang | Hasil |
|---|---|
| 1 L2 normalization | PASS |
| 2 domain parity skew | PASS |
| 3 benchmark 35 | PASS (35/35) |
| 4 zero conversational FP | PASS (0/5) |
| 5 latency sub-ms | PASS (p99 220.8µs) |
| 6 live Hermes hook | PASS |
| 7 git production hygiene | PASS (main d1de873, dev==origin/dev) |

## Koreksi diri

1. **P3b sempat menurunkan v2 ke 151/167 (E 20→19)** karena `jangan buat
   laporan dulu, aku mau ngobrol aja` (E10) ikut kena strong-ban guard.
   STOP condition terpenuhi; saya perbaiki dengan eksklusi idiom delay
   `jangan...dulu`/reminder — aturan umum, bukan setelan per kasus — lalu
   v2 kembali 152. Dilaporkan transparan di commit `4e3e7ab`.
2. **Laporan Fase 3 lama salah sebut 9 ID gagal held-out v3**; dikoreksi di
   Langkah 0 dari RUN aktual, bukan dokumen.
3. **P1a tidak menaikkan G02** meski mekanismenya benar (`exel→excel` kini
   dipakai penuh, `wrod→word` terbukti). Penyebab: `active_n = sqrt(|active_keys|)`
   pada MNB menyerap gain BM25. Saya **tidak** menambah patch per kasus; G02
   diserahkan ke P1b (zona abu) yang menyelesaikannya secara kebijakan.
4. **P4c tidak menyelesaikan H06**: sesuai syarat "kandidat tunggal",
   `penjalan` punya 7 kandidat 1-edit → ditolak; 4→u dilarang. Gap jujur.
5. **P2 penalti 0.5x tidak saya terapkan** karena simulasi menunjukkan tidak
   cukup membalik polisemi dan berisiko menurunkan skill benar.

## Status akhir & STOP

- Semua commit di `dev`, `origin/dev` ter-sync; `main = d1de873` utuh.
- θ₀, probe, deskripsi, ekspektasi v2: tidak disetel. Tidak ada merge ke main.
- **BERHENTI.** Usulan P2 (wordlist tervendor, sinyal ortografi, domain-context)
  menunggu persetujuan.
