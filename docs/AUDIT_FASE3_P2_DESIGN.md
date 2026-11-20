# Fase 3 — P2: OOD / polisemi K (DESAIN — minta persetujuan sebelum kode)

> Status: **DESAIN SAJA**. Sesuai perintah P2, minta persetujuan dulu sebelum
> menulis kode. θ₀ = 7.4688 TIDAK diubah.

## 1. Data (dari binary build ulang)

| Kasus | Prompt | score | status sekarang | ekspektasi |
|---|---|---|---|---|
| K01 | `...protokol DMX512` | 3.56 | HUNT | HUNT ✓ |
| K02 | `baca register Modbus RTU dari PLC pakai python` | 9.11 | MATCHED `scientific-slides` | HUNT ✗ |
| K03 | `konfigurasi KNX untuk lampu rumah pintar` | 0.00 | NO_SKILL | HUNT ✗ |
| K04 | `...patung digital di ZBrush` | 17.15 | MATCHED+HUNT | MATCHED+HUNT ✓ |
| K05 | `buat jus alpukat pakai blender` | 13.05 | MATCHED `blender-3d-modeling` | NO_SKILL/CLARIFY ✗ |
| K06 | `resep jus alpukat pakai blender` | 13.05 | MATCHED `blender-3d-modeling` | NO_SKILL ✗ |
| K07 | `ular python peliharaan makan apa` | 9.15 | MATCHED `scientific-slides` | NO_SKILL ✗ |
| K08 | `harga bitcoin hari ini` | 4.74 | HUNT | NO_SKILL/HUNT ✓ |

K02/K05/K06/K07 skor **9–13, di atas θ₀** → ini **bukan** masalah θ₀ dan
bukan zona abu (P1). Mereka adalah **polisemi**: satu token (`blender`,
`python`, `modbus`) mengaktifkan skill yang salah karena skill itu memiliki
token yang sama, tanpa memeriksa apakah konteks kalimat mendukung domain skill.

K03 skor 0 → OOD murni (KNX tidak ada di kosakata), benar-benar butuh HUNT,
tapi Stage 0 menganggapnya konversasional? Tidak — skor 0 karena tidak ada
token dikenal. Ini masalah **vocabulary coverage**, bukan disambiguasi.

## 2. Pendekatan umum yang diusulkan

### 2a. Domain-context disambiguation (K02/K05/K06/K07)

Prinsip: **sebuah token polisemi hanya boleh menyumbang bobot ke skill jika
ada ≥1 token pendukung_domain di klausa yang sama**. Token pendukung adalah
kata yang secara semantik mengunci domain (mis. `jus`, `alpukat`, `resep` →
domain kuliner, bukan 3D; `ular`, `peliharaan`, `makan` → biologi, bukan
scripting; `modbus`, `plc`, `rtu`, `register` → otomasi industri, bukan
slide ilmiah).

Mekanisme umum (bukan daftar per-kasus):
1. Bangun **peta domain → kata kunci pendukung** dari korpus yang sudah ada
   (bukan dari ekspektasi kasus). Domain yang relevan: `kuliner`, `biologi`,
   `otomasi_industri`, `3d_modelling`, `programming`, `presentasi`.
2. Saat menghitung skor skill, untuk token polisemi `t` yang muncul di skill
   `S` dengan domain `D_s`, turunkan bobot `t` jika klausa mengandung
   pendukung domain `D_alt` yang bertentangan (`D_alt != D_s`) dan tidak ada
   pendukung `D_s`.
3. Ini **tidak** menyetel ekspektasi kasus; ia mengubah cara fitur dihitung
   secara umum. Harus diuji ke seluruh v2 + regresi; jika ada kategori turun
   → BERHENTI.

Risiko yang jujur: peta domain bisa salah mengklasifikasikan kata netral, dan
mengurangi skor skill yang sebenarnya benar. Karena itu mekanisme ini
sebaiknya diterapkan sebagai **penalti ringan (mis. 0.5× pada token polisemi
yang konteksnya bertentangan)**, bukan penghapusan total, dan diuji dulu
dalam mode observasi.

### 2b. Wordlist Inggris umum + istilah OOD (K03, G07, dan butir Fase 3)

Butir Fase 3: "Tambahkan wordlist Inggris umum ke `known_vocab` bila perlu,
bukan `ATTRIBUTE_NOUNS` per kasus."

- K03 `KNX`, G07 `examples`/`markdown`: kata/istilah ini tidak ada di
  `known_vocab`. Menambah **wordlist Inggris umum** (dari sumber eksternal,
  bukan dari kasus) akan mencegah `examples` dianggap unknown-tool (G07).
- `KNX` adalah **istilah domain smart-home yang memang harus memicu HUNT** — menambahkannya ke `known_vocab` akan merusak K03. Jadi
  wordlist Inggris umum harus **tidak** memasukkan akronim teknis seperti
  KNX/DMX512; itu justru sinyal OOD yang diinginkan.
- Sumber yang diusulkan: wordlist `/usr/share/dict/words` atau paket
  `wordfreq`/`english-words` (butuh persetujuan instalasi di venv sandbox).

## 3. Urutan & gerbang

1. Observasi dulu: hitung berapa token polisemi yang salah aktif di v2 saat
   ini, dan simulasi penalti 0.5× tanpa mengubah binary produksi.
2. Terapkan 2b (wordlist) sebagai commit terpisah dari 2a (domain).
3. Setiap commit: v2 penuh + regresi 35 + fuzz; BERHENTI jika ada kategori
   turun / gerbang gagal / butuh mengubah θ₀.

## 4. Yang TIDAK dilakukan

- θ₀, probe, deskripsi skill, ekspektasi v2: tidak disetel.
- Tidak menambah kata ke `ATTRIBUTE_NOUNS` per kasus.
- Tidak Menyetel ekspektasi K02/K05/K06/K07 agar lulus.
- Implementasi ditunda sampai user menyetujui desain ini.
