# Fase 3d — Laporan STOP di Langkah B3 (sumber wordlist tidak sah)

## Konfirmasi state (dari `git`, bukan dugaan)

- **HEAD sebenarnya = `18967f5`** (commit STOP Fase 3c), **bukan `e384d73`**
  (itu commit Langkah 2 Fase 3c, tiga commit lebih awal).
- Urutan: `e384d73` → `18967f5` (STOP) → `f59c679` (audit Langkah A Fase 3d).
- Saat ini `dev = origin/dev = f59c679`, `main = d1de873` (hard lock utuh), clean.
- Binary di-build ulang dari `18967f5` sebelum audit A (`BUILD-OK-18967f5`),
  dan dari `5917645` di worktree terpisah untuk perbandingan A1.
- θ₀ = 7.4688 tidak diubah. Tidak ada merge ke main.

## LANGKAH A — Audit tanpa kode (SELESAI,_commit `f59c679`)

Dokumen: `docs/AUDIT_FASE3D_A.md`; output mentah:
`docs/ABLATE_MARGIN0_{V3,V4,V5}.txt` vs `docs/MARGIN8_{V3,V4,V5}.txt`.

### A1 — HO14

`"pakai tool aneh bikin laporan"`, ekspektasi `HUNT_NEW_SKILL`.

| Versi | debug_score | top_score | status | hunt_reason | hunt_clauses |
|---|---|---|---|---|---|
| `5917645` | 4.6778 | 7.0438 | `HUNT_NEW_SKILL` | `below_theta` | 1 |
| `18967f5` | 4.6778 | 7.0438 | `CLARIFY_AMBIGUOUS` | `below_theta` | 0 |

Mekanisme P1b: `gray_lo = θ₀×(1−0.08) = 6.8713`; `7.0438 ∈ [6.8713, 7.4688)`
→ status `below_theta` diubah menjadi `CLARIFY_AMBIGUOUS`, `hunt_clauses`
dikosongkan. Skor identik → **murni decision gate**, bukan skor/MNB/θ₀.
Tidak diperbaiki (perintah: audit saja).

### A2 — Ablasi margin 0 vs 8%

Margin **sudah parameter** (`GRAY_ZONE_MARGIN: f64`), jadi ablasi tanpa ubah
kode repo utama (worktree `wt-ablate`, margin 0.0, di-build ulang).

| Set | margin 0 | margin 8% | Diff per kasus |
|---|---|---|---|
| v3 (dev) | **44/52** | **43/52** | HO10, HO11 HUNT→CLARIFY (masih PASS); **HO14 PASS→FAIL** |
| v4 (dev) | **29/38** | **29/38** | tidak ada |
| v5 (held-out) | **15/40** | **15/40** | tidak ada |

Tidak ada margin yang dipilih/disetel dari hasil ini — keputusan ada di user.

## LANGKAH B — Sumber wordlist (urutan ketat; **STOP di B3**)

### B1 — `vendor/wordlist_en.txt`

**Tidak ada** (bahkan direktori `vendor/` tidak ada). Tidak ada lisensi untuk
dicek.

### B2 — SEMUA key `lexicon_id_en.json` (bukan hanya `known_vocab`)

| Key | Isi sisi EN | Penilaian |
|---|---|---|
| `concept_pairs` (313) | `3d modeling`, `blender`, `python`, `excel`, `kubernetes`, `topology`, … | **nama tool/istilah domain**, bukan kata umum; sudah dipakai engine (`trainer.py:503`) |
| `kbbi_glossary` (178) | `abstract`, `algorithm`, `audit`, `budget`, … | glosarium **domain/konsep** Kemdikbud; sudah dipakai engine (`src/lib.rs:63`) |
| `en_to_id` (412) | gabungan `concept_pairs` + glosarium | **sudah dipakai engine** (`src/lib.rs:56,2017,2060`) |
| `id_to_en` (401) | kebalikannya | **sudah dipakai engine** (`src/lib.rs:63,2069`) |
| `known_vocab` (114.930) | KBBI + kata dasar dari semua lapis | **sudah dipakai engine** (`src/lib.rs:2792`) — sudah dibuktikan no-op di Fase 3c |
| `slang_to_formal` (4.786) | bahasa gaul ID | bukan kata umum EN; sudah dipakai engine |
| `translit_rules` (8) | aturan sufiks | bukan wordlist |

Dari 10 target P2a (W01–W10), hanya `topology` dan `smtp` yang muncul — keduanya
ada di `known_vocab` yang **sudah dipakai engine**. Kata umum target seperti
`dijkstra`, `entropy`, `serendipity`, `meteorologi`, `fotosintesis` **tidak ada**
di key mana pun. Jadi tidak ada sisi EN yang memenuhi syarat "kata umum + belum
dipakai engine".

**Lisensi**: tidak ada pernyataan lisensi eksplisit untuk `kbbi-v6-wordlist`,
`kamus-alay`, glosarium, atau kurasi sendiri di repo (tidak ada `LICENSE`, dan
`README.md`/`docs/` tidak mencantumkan lisensi sumber wordlist). Sumber tercatat
hanya URL di `lexicon_builder.py:37-47`. Syarat B2 "asal + lisensi jelas" tidak
terpenuhi.

### B3 — STOP

Sesuai perintah: *"Jika tidak ada: STOP, laporkan. Jangan tulis wordlist manual,
jangan lanjut ke Langkah C."* → **BERHENTI di sini**.

- Tidak ada kode P2a, tidak ada `docs/P2A_GUARD.md` (C0 tidak dijalankan).
- Tidak ada commit Langkah C/D.
- Tidak ada ekspektasi set mana pun yang diedit; tidak ada penyetelan ke ID
  v3/v4/v5; θ₀, probe, deskripsi, margin tidak diubah.
- Tidak ada merge ke main.

## Metrik pra-state (dari binary build ulang `18967f5`)

| Metrik | Angka |
|---|---|
| v2 | **155/167** |
| b35 regresi | **35/35** |
| Negasi | **6/6** |
| FP conversational | **0/5** |
| 7 gerbang | **7/7 PASS** |
| v3 (dev) | **43/52** |
| v4 (dev) | **29/38** |
| v5 (held-out) | **15/40** |
| Latensi p50 / p99 (median 4 run) | **38.2µs / 219.1µs** |
| Latensi p99 3 run berurutan | 221.3µs, 219.9µs, 214.6µs |

Step D (pra vs pasca P2a, split v5 target/non-target/kontrol) **tidak
dijalankan** karena P2a tidak pernah diimplementasi. Tidak ada angka pasca.

## Koreksi diri

1. Di awal kompresi, daftar todo masih menandakan A belum selesai; kenyataannya
   `f59c679` sudah meng-commit audit A. Saya verifikasi `git log` dan tidak
   mengulang kerja/commit ganda.
2. Percobaan pertama menghitung ablasi dengan evaluator tulisan sendiri memberi
   angka keliru (v3 38/52) karena saya mengambil `banned` dari field yang salah;
   saya buang angka itu dan memakai **evaluator asli** dari tiap worktree
   (44/52 vs 43/52).
3. Di Fase 3c saya menyimpulkan tidak ada kamus EN; di Fase 3d perintah meminta
   pemeriksaan **semua key** lexicon — saya lakukan dan menemukan key sisi EN,
   tetapi semua adalah istilah domain/nama tool yang sudah dikonsumsi engine.
   Kesimpulan STOP tetap sama, kini dengan bukti per-key, bukan perkiraan.
4. Saya **tidak** menulis wordlist kecil dari `concept_pairs` hanya agar
   Langkah B "lolos": itu bukan kata umum dan mengandung nama skill/tool yang
   secara eksplisit dilarang di C1.

## Yang dibutuhkan untuk melanjutkan

Sumber wordlist kata umum EN yang **offline/tervendor**, dengan **sumber + lisensi
tercatat**, dan **belum dipakai engine** (bukan `known_vocab`/`en_to_id`/
`id_to_en`/`concept_pairs`), atau keputusan eksplisit user yang mengganti syarat B. Sampai itu ada, **BERHENTI dan menunggu persetujuan**.
