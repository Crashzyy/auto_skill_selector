# Fase 3j — Laporan akhir (P-FMT di-revert)

## State

- Mulai `dev@HEAD = 557407b` (konfirmasi: **bukan `10d372f`** — itu tiga
  commit lebih awal). `main = d1de873` utuh, θ₀ 7.4688, margin P1b, probe,
  deskripsi tidak diubah; tidak ada merge, tidak ada force push.
- Revert: `git revert db7ea9f` → **`4e70dbf`** (satu commit, `1 insertion,
  42 deletions` di `src/lib.rs`). Final `dev = 5016b28`, clean.
- Semua angka dari binary hasil build ulang. Tidak ada aturan ketiga,
  tidak ada penyempitan, tidak ada kode engine baru selain revert.

## Langkah 1 — Revert & gate utama

**Diff harness `revert` vs `dc429c9`: 468 kasus, 0 delta** —
`docs/DIFF_REVERT_VS_PREPFMT.txt`. Ini pembuktian kuat bahwa revert
mengembalikan perilaku persis pra-P-FMT.

Diff HEAD (`557407b`) → revert: 20 delta, **semuanya** dalam daftar
izin: F05, W33, X26, Y01, Y03, Y06, Z01, Z04, Z08, Z09–Z13, A01, A02,
A03, A05, A08, A10 — `docs/DIFF_HEAD_VS_REVERT.txt`. Tidak ada kasus
di luar daftar. Tidak ada STOP.

Penurunan yang diharapkan, terjadi semua:

| Set | HEAD (P-FMT) | Revert | Sesuai prediksi |
|---|---|---|---|
| v5 | 16/40 | **15/40** | ya |
| v6 | 29/41 | **28/41** | ya |
| v7 | 23/30 | **20/30** | ya |
| v8 | 17/30 | **15/30** | ya |
| FMT_ADV_GUARD | 8/14 | **7/14** | ya |

Gate lain: v2 **155/167**, b35 **35/35**, negasi **6/6**, guard **12/12**,
FMT_GUARD **10/10**, **7/7 gerbang PASS**, FP conv 0/5.
Latensi p99 3 run: 229.1 / 233.5 / 242.1µs → **median 233.5µs**;
baseline sebelum revert 224.0µs → +4.2%, di bawah batas +10%.

## Langkah 2 — Postmortem

`docs/PFMT_POSTMORTEM.md`: apa yang dicoba (3g implementasi, 3h audit+
adversarial, 3i penyempitan gagal, 3j revert), audit aktivasi **11 dari 425**,
tiga kelas false positive (marker substring `bikin`→`in`, tanpa adjakensi,
format vs topik). Klasifikasi mentah:
- **Z11 SALAH** — "I'm in a meeting about word": HUNT → MATCHED
  `meeting-notes-action-items`, top tepat **1.00** (pin), topik rapat.
- **Z04 SALAH** — "write the report as a pdf": MATCHED benar
  `pdf-extraction-manipulation` top 12.65 → MATCHED `geo-report` top 1.00.
Penyempitan (a)+(b): 10 delta, A03/Z11 masih salah, W33 hilang.
Kesimpulan struktural: cue tata bahasa tidak membedakan format dari topik,
dan pin bobot 1.0 melewati θ₀. Aset regresi dipertahankan; penyempitan
tidak disimpan sebagai kode.

## Langkah 3 — Diagnosis pooled (read-only)

`docs/DIAGNOSIS_POOLED_3J.md`: **38 kasus** MATCHED-expect tapi HUNT/
CLARIFY/NO_SKILL pasca-revert.

| Mekanisme | N |
|---|---|
| ban + klausa residual elliptis | **18** |
| scoring di bawah θ₀ (umum) | 8 |
| Stage-0 bypass / top=0 | 6 |
| token lemah / typo / bahasa | 5 |
| unknown_tool (OOD) | 1 |

Konsentrasi: format/tool token 24/38, numerik/tabel 9, translasi 5,
code/debug 4 — **tersebar di banyak skill**, bukan 1–2 skill dengan
deskripsi/probe lemah. Usulan mekanisme terbesar: perbaiki
**leksikon/splitter** supaya token deliverable/format tidak ikut terbuang
saat sieve menghapus cue ban; jadikan anchor feature berbobot mention,
**bukan** pin 1.0. θ₀ tidak perlu disentuh: yang hilang adalah fitur,
bukan ambang. Tidak diimplementasi.

## Langkah 4 — v9 beku & tabel lintas set

- v9: 30 kasus P01–P30, hash
  `9ae2a6d7b9b3eebbfc748f7e1e8339680e4c2485a5694435d70e6c57a3b927fa`,
  0 duplikat dari 456 prompt, ekspektasi sebelum probe, tanpa ban+format.
- Baseline pasca-revert: **15/30** — parafrase 2/10, ellipsis 3/5,
  typo 3/5, kontrol 7/10.

| Set | Skor | % | Kelas |
|---|---|---|---|
| v2 | 155/167 | 92.8% | in-sample (dev) |
| b35 | 35/35 | 100% | in-sample (regresi) |
| v3 | 43/52 | 82.7% | in-sample (dev) |
| v4 | 29/38 | 76.3% | in-sample (dev) |
| v5 | 15/40 | 37.5% | in-sample (dev; 10 spec-mismatch) |
| v6 | 28/41 | 68.3% | in-sample (dev) |
| v7 | 20/30 | 66.7% | in-sample (dev) |
| v8 | 15/30 | 50.0% | in-sample (dev) |
| guard / FMT_GUARD / FMT_ADV_GUARD | 12/12, 10/10, 7/14 | — | in-sample (guard) |
| **v9** | **15/30** | **50.0%** | **out-of-sample (held-out bersih)** |

Kesenjangan dev→held-out jelas: v2 92.8% vs v9 50.0%. Parafrase tanpa
nama skill 2/10 adalah inti gap-nya — ini yang harus disentuh berikutnya
(leksikon/splitter), bukan θ₀.

## Koreksi diri

1. Saya sempat menulis mekanisme "typo/alias" untuk HO29 padahal
   `hunt_reason = unknown_tool` dengan top 10.76; dikoreksi lewat
   klasifikasi ulang berdasarkan field aktual, bukan dugaan.
2. Diagnosis awal memakai bucket tumpang tindih (38 → 14/11/6/6/1);
   saya hitung ulang dengan prioritas eksplisit `top=0 → unknown_tool →
   ban → typo → general`, menghasilkan 18/8/6/5/1 yang dilaporkan.
3. Saya tidak menyetel ekspektasi v9 (parafrase 2/10 dan ellipsis 3/5
   rendah) agar laporan terlihat baik; itu hasil baseline apa adanya.
4. Tidak ada hash set mana pun yang diubah; θ₀/probe/deskripsi/margin
   utuh; revert adalah satu-satunya perubahan engine dan sudah
   diverifikasi 0 delta vs pra-P-FMT.

## Status akhir

`dev = origin/dev = 5016b28`, `main = d1de873`, clean. Worktree scratch
dibuang. **BERHENTI.** Semua lanjutan (leksikon/splitter, polisemi, multi,
OOD, P-FMT ulang) menunggu izin terpisah.
