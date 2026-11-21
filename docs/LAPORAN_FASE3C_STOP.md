# Laporan Fase 3c — STOP di Langkah 3 (P2a)

**Mulai:** `dev@9e30de9`. **Berhenti:** Langkah 3, sebelum kode P2a ditulis.
`main = d1de873` utuh; θ₀ = 7.4688 tidak diubah; tidak ada merge ke main.
Semua angka di bawah dari binary hasil **build ulang** di 9e30de9.

## Alasan STOP (sesuai perintah eksplisit)

Perintah Langkah 3: *"Sumber: kamus yang sudah ada di sistem/paket terpasang.
**Jika tidak ada sumber yang sah, STOP dan laporkan; jangan tulis wordlist besar
manual.**"*

Saya mencari kamus kata umum yang sah dan **tidak ada yang tersedia**:

| Sumber dicek | Hasil |
|---|---|
| `/usr/share/dict/` | ada direktori, **kosong** |
| `aspell dicts` / `/usr/share/hunspell` / `/usr/share/aspell` | tidak terpasang |
| Paket Python di venv sandbox (`wordfreq`, `wordninja`, `english_words`, `nltk`, `spacy`, `wordsegment`, `enchant`, …) | **semuanya tidak ada** |
| `/usr/share` (words/dict/ dic/wl) | tidak ada |
| Cargo registry (`…/target-lexicon-0.12.16`) | hanya tokenizer Rust, **bukan kamus kata** |
| Node global modules | tidak ada |

Satu-satunya kamus tervendor di repo adalah `lexicon_id_en.json` →
`known_vocab` (114.930 kata; sumber `kbbi-v6-wordlist` aryakdaniswara via
`lexicon_builder.py`, tervendor/offline). **Tapi kamus ini SUDAH dipakai engine**
di `src/lib.rs:2792` untuk mengecualikan token dari deteksi `unknown_tool`.
Memakainya ulang sebagai "wordlist kata umum P2a" adalah **no-op** — tidak
menghasilkan perilaku baru, tidak jujur disebut implementasi P2a.

Kata uji target (W01–W10: `dijkstra`, `entropy`, `serendipity`, …; W06 `SMTP`)
juga **tidak ada** di `known_vocab` KBBI, jadi kamus ini tidak bisa dijadikan
wordlist kata umum EN yang diminta desain P2a.

Maka: **tidak ada sumber wordlist kata umum yang sah → STOP, tidak menulis
wordlist manual, tidak mengubah kode engine.**

## Yang sudah selesai sebelum STOP

- **Langkah 0** (`ed30e05`): rerun held-out v3 di 9e30de9 → **43/52**.
  Rekonsiliasi: 9 ID gagal aktual = HO13, HO14, HO16, HO17, HO18, HO19, HO20,
  HO24, HO28. HO36 PASS (P3b), HO14 PASS→FAIL (efek samping P1b).
  12 duplikat 8 PASS/4 FAIL; independen **35/40** (perkiraan 44/52 & 36/40
  di permintaan tidak sesuai RUN aktual, dikoreksi jujur).
- **Langkah 1** (`ba7568e`): held-out v5 dibekukan, **40 kasus**, 0 duplikat
  dengan v2/b35/v3/v4 (cek skrip), 0 expect ganda, ekspektasi ditulis sebelum
  probe. SHA256 `a85a21a37167665c7b283a29fa9b4ae06e4a6a9eede299fa0e76998edd856140`
  (tercatat di `docs/HELDOUT_V5_FREEZE.md`).
- **Langkah 2** (`e384d73`): **baseline v5 = 15/40** di 9e30de9, output mentah
  `docs/HELDOUT_V5_BASELINE.txt`. 25 FAIL (W01–W10 HUNT umum, W14/16 CLARIFY,
  W15 HUNT CSV, W20–22 OOD kapital, W23/25 polisemi, W30–33 typo/negasi,
  W37/39/40 MULTI). Ini acuan STOP Langkah 4 — tidak tercapai karena STOP lebih
  awal di Langkah 3.

## Metrik "sebelum" (dari binary build ulang, 9e30de9)

| Metrik | Angka |
|---|---|
| v2 | **155/167** |
| Regresi b35 | **35/35** |
| Negasi | **6/6** |
| 7 gerbang | **7/7 PASS** |
| p50 / p99 | **42.0µs / 235.8µs** |
| Held-out v3 (aktual) | **43/52** |
| v4 (dev set) | **29/38** |
| Held-out v5 baseline | **15/40** |
| FP conversational | 0/5 |

## Tidak dikerjakan

- P2a: tidak diimplementasi (STOP — tanpa sumber wordlist sah).
- Sinyal ortografi KNX/DMX512, domain-context (V16/W23–W25), penalti 0.5x:
  tidak disentuh. Sisa kegagalan v5 (W20–W22 OOD kapital, W23/25 polisemi)
  **membenarkan** usulan itu, tetapi perintah mengecualikannya dari Fase 3c —
  saya hanya mencatat, tidak mengimplementasi.
- v4 tidak diedit (tetap dev set), v5 tidak diedit (hash beku).

## Koreksi diri

1. Perkiraan di permintaan (v3 ≈ 44/52, independen 36/40) **tidak sesuai RUN
   aktual**: 43/52 dan independen 35/40. Saya laporkan angka RUN, bukan angka
   perkiraan, dan mengoreksi draf laporan lewat commit `ed30e05`.
2. Saya **tidak** menyetel ekspektasi v5 yang sengaja menantang (W01–W10 HUNT,
   W30 typo `powpoint`), meski baseline v5 rendah (15/40) — itu desain uji,
   bukan target yang boleh dikejar.
3. Saya **tidak** memaksa P2a memakai `lexicon_id_en.json` hanya agar ada
   "implementasi": kamus itu sudah dipakai engine, jadi itu no-op dan akan
   menyesatkan. STOP jujur lebih baik daripada perubahan kosong.
4. HO14 yang muncul sebagai FAIL baru di v3 adalah efek samping P1b (zona
   abu) dari Fase 3b — bukan regresi Fase 3c; dicatat transparan di Langkah 0.

## Status & STOP

- `dev = origin/dev = e384d73` (clean). `main = d1de873` (hard lock utuh).
- θ₀, probe, deskripsi, ekspektasi v2: tidak disetel. Tidak ada merge ke main.
- **BERHENTI di Langkah 3.** Menunggu arahan: sumber wordlist kata umum yang
  sah (lokasi/file + lisensi) harus disediakan, atau perintah menentukan
  sumber lain, sebelum P2a boleh dilanjutkan.
