# Fase 3 — P4: Normalisasi noise token H (H08 → H06 → H21 → H05)

## Diagnosis (dari binary build ulang, sebelum kode)

| Kasus | Prompt | Gerbang yang menghasilkan NO_SKILL | top_score |
|---|---|---|---|
| H05 | `buatkangrafikpenjualan` | Stage 0 bypass — 0 token dikenal, skor 0.00 | 0.00 |
| H06 | `b1kin gr4fik penj4l4n` | Stage 0 bypass — 0 token dikenal, skor 0.00 | 0.00 |
| H08 | `buaaaatkan grafiiiik penjualannn` | Stage 0 bypass — 0 token dikenal, skor 0.00 | 0.00 |
| H21 | `data-data penjualan tolong dibuat grafik2nya` | BUKAN bypass — below_theta (6.40 < 7.47) | 6.40 |

H05/H06/H08: `debug_score = 0.0` → tidak ada token yang cocok dengan kosakata,
bukan sekadar konversasional bypass. H21: skor 6.40 < θ₀.

## Perubahan (satu commit, gate-bearing generator)

`normalize_noise_token(tok, &known_vocab)` — sesuai pitfall skill
*rust-python-extension*: kandidat BARU hanya dikembalikan jika ada di
`known_vocab`; aturan tidak pernah menghasilkan non-kata. Token asli tetap
dipertahankan; bentuk kanonik ditambahkan sebagai feature unigram berbobot
penuh (1.0×). Tidak menyentuh logika ban/chitchat/pin.

- **H08** (ciut huruf berulang ≥3 → 1): `buaaaatkan`→`buat`,
  `grafiiiik`→`grafik`, `penjualannn`→`penjualan`. Run 1–2 dipertahankan
  (hindari merusak kata asli seperti `mau`).
- **H06** (leet 0→o 1→i 3→e 4→a 5→s 7→t; token campuran huruf+digit;
  hasil di kosakata): `b1kin`→`bikin`, `gr4fik`→`grafik`. **8/2/6/9 tidak
  pernah dipetakan**, jadi `k8s` (HO29/G12) tetap tidak dikenal → hunt.
- **H21** (reduplikasi digit 2, stem ≥4 huruf di kosakata; + hyphen
  reduplikasi): `grafik2nya`→`grafik`, `data-data`→`data`.
- **H05** (segmentasi kosakata penuh): DILEASE — butuh uji FP fuzz dulu.

## Hasil (binary build ulang)

| Kasus | Sebelum | Sesudah | top_score |
|---|---|---|---|
| H05 | FAIL | FAIL (gap) | 0.00 |
| H06 | FAIL | FAIL (parsial: 2/3 token pulih) | 4.20 |
| H08 | FAIL | **PASS** | 6.21 → 7.76 |
| H21 | FAIL | **PASS** | 6.40 → 13.58 |

- v2: **149 → 151/167**; H: 17 → 19/21. Tidak ada kategori turun.
- Regresi 35: **35/35** utuh.
- Jaga: `haiii`, `makasiiih`, `hahaha` → NO_SKILL (chitchat utuh);
  `k8s dashboard` tetap tidak ter-normalisasi jadi `kas`; B20 `jangan pakai
  excel` ban utuh; negasi 6/6 utuh.

## Gap jujur (tidak dipaksa)

- **H06**: `penj4l4n` menurut aturan leet yang ditentukan (4→a) menjadi
  `penjalan`, yang TIDAK ada di kosakata. Untuk mencapai `penjualan` harus
  memetakan 4→u, yang **melanggar aturan leet yang diberikan**. Tidak saya
  lakukan — dilaporkan sebagai gap, bukan disetel demi kasus.
- **H05**: segmentasi `buatkangrafikpenjualan` → `buat grafik penjualan`
  memerlukan segmentasi kosakata penuh; ditunda (opsional) sampai uji fuzz FP.
