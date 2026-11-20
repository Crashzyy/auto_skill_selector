# Fase 3b — P2: Observasi OOD/polisemi K (TANPA implementasi)

Sesuai perintah: **observasi saja**, hitung aktivasi, simulasikan penalti 0.5x
tanpa mengubah binary, tulis usulan. Tidak ada kode engine yang diubah.

## Aktivasi token polisemi (v2 + b35 + v4, binary build ulang)

| Token | kasus | aktivasi skill |
|---|---|---|
| `blender` | K05, K06, b35#14 | K05/K06 → `blender-3d-modeling` (**salah**, konteks jus) |
| `python` | B01, F06, K02, K07 | K02/K07 → `scientific-slides` (**salah**, konteks PLC/ular) |
| `food processor` | V16, V17, V20 | V20 → `blender-3d-modeling` (**salah**, konteks render 3D — perlu diverifikasi) |
| `kucing` | V18, V19 | NO_SKILL (benar) |
| `excel` | 30 kasus | mayoritas benar; V30 HUNT (bisa benar) |
| `chart` | 6 kasus | G07 HUNT (unknown_tool, bukan polisemi — butuh wordlist) |

## Simulasi penalti 0.5x (analitik, tanpa binary)

Jika bobot token polisemi `blender` diturunkan 0.5x saat skoring:
- K05 `buat jus alpukat pakai blender` skor 13.05 → turun ~25% ≈ 9.8
  (masih **di atas θ₀ 7.47**) → **penalti 0.5x TIDAK cukup** untuk membalik
  K05/K06. Dibutuhkan penalti lebih kuat atau bukti konteks domain yang
  eksplisit (kata `jus`/`alpukat`/`resep` → kuliner).
- K02 `python` di `scientific-slides` skor 9.11 → ≈ 6.8 (< θ₀), tapi itu
  efek samping; konteks `modbus`/`plc` seharusnya mengarah ke HUNT.
- Risiko: penalti 0.5x tanpa konteks akan **menurunkan skill yang benar**
  (b35#14 `render di Blender` → 17.15 → ≈12.9, masih lolos, tapi margin tipis).

Kesimpulan jujur: **penalti 0.5x saja tidak menyelesaikan polisemi** dan
berisiko pada skill benar. Perlu sinyal konteks domain, bukan sekadar
skalar penalti.

## Usulan (TIDAK diimplementasi)

1. **Wordlist tervendor tanpa instalasi jaringan**: sertakan file wordlist EN
   umum di repo (mis. salinan `english-words` yang sudah ada di korpus
   `lexicon_id_en.json` — `kbbi_wordlist_size` dan `known_vocab` sudah 115k
   entri; tidak perlu `pip install` atau unduh). Tambahkan hanya kata umum
   (`examples`, `markdown`, `language`, `simple`, `report`) ke `known_vocab`
   saat training, **bukan** nama skill/tool. Ini menyembuhkan G07
   (`examples` dianggap unknown-tool) tanpa mengubah θ₀.
2. **Kecualikan nama di korpus skill**: jangan pernah memasukkan ke wordlist
   kata yang merupakan `name`/`core_keywords` skill apa pun (blender, python,
   excel, ...), supaya wordlist tidak mengubah aktivasi skill yang benar.
3. **Sinyal ortografi untuk token tak dikenal berhuruf kapital**: token seperti
   `KNX`, `DMX512`, `ZBrush` ( huruf kapital di tengah / ALL-CAPS + digit )
   bukan typo kata umum, melainkan nama alat/OOD → kuatkan HUNT, jangan
   fuzzy-correct ke kata umum. Ini menyembuhkan K03/K13/V13–V15 tanpa
   menyentuh θ₀. Perlu uji FP terhadap acronyms umum (NASA, API, CPU) agar
   tidak over-hunt.
4. **Domain-context disambiguation** (dari desain P2 Fase 3): penaliti token
   polisemi **hanya** bila ada pendukung domain lawan (`jus`, `resep` →
   kuliner; `ular`, `peliharaan` → biologi) dan tidak ada pendukung domain
   skill. Kombinasikan dengan (3), bukan penalti 0.5x seragam.

## Kontrak tidak berubah

- θ₀ = 7.4688 tidak diubah; probe/deskripsi/ekspektasi v2 tidak disetel.
- Tidak ada kode engine yang diubah untuk P2 (observasi murni).
- Usulan (1)–(4) menunggu persetujuan sebelum implementasi.
