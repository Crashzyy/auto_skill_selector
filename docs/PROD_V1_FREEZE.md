# PROD_V1 — FREEZE (Fase 3t)

- File: `tests/prod_v1.json`
- 120 kasus PR001–PR120
- **SHA256: `6d550812b6aedc4ba36c4d3fc08efea6da810eea04ee2bfc0d45b6ea8fd06946`**
- Ekspektasi ditulis **sebelum** probe engine dan sebelum evaluasi apa pun.
- Sumber: 111 skill produksi dibaca dari `HERMES_HOME` produksi lalu
  disalin ke direktori terisolasi. Penulis melihat deskripsi produksi.
- Seleksi: 60 skill diambil secara acak dengan seed **20261122**, 20 dari
  tiap tersil panjang deskripsi (pendek ≤60, menengah ≤174, panjang >174).
- Per skill 2 prompt: P = parafrase tanpa nama skill/alat, E = menyebut
  alat/domain secara eksplisit. Keduanya dicek bebas n-gram 5 kata yang
  sama dengan deskripsi skill target.
- Bahasa: ID 60, EN 20, MX 40 (tag per kasus), tipe P 60 / E 60.
- Ekspektasi: `MATCHED_SINGLE` dengan `expect_skills` = skill target.
- Negatif memakai `docs/NEG_LIVE.json` (150) dan `docs/NEG_CONV.json` (40)
  yang sudah ada.
- 0 duplikat dengan semua set sebelumnya; 0 duplikat internal.

Karena penulis melihat deskripsi produksi, ini adalah **in-sample untuk
produksi**, bukan held-out generik. Hash produksi di awal fase:
`99c361b7c514d2897456a2345d35b0dbb79bb67c79aa7bf5b1a7b8841d4cc3f9`.
