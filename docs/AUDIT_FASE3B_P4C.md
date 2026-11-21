# Fase 3b — P4c: koreksi 1-edit pasca-leet (kandidat tunggal)

Sesuai perintah: setelah leet, coba koreksi 1-edit ke kosakata untuk token
campuran huruf+digit dengan panjang ≥6 huruf, **hanya jika kandidatnya tunggal**.
Tanpa 4→u. `k8s` tetap hunt.

## Implementasi

`unique_one_edit(&leeted, known)` di `src/lib.rs`: insert/delete/substitute/
transpose atas hasil leet; mengembalikan `Some` **hanya** jika tepat satu kandidat
ada di `known_vocab` (ambiguitas → `None`, tidak menebak). Dipanggil dari
`normalize_noise_token` setelah leet gagal, dengan syarat `changed && len>=6`.

## Hasil jujur (binary build ulang)

| Token | leet sah | 1-edit kandidat di vocab | Hasil |
|---|---|---|---|
| `penj4l4n` | `penjalan` | **7** (`penjualan`, `pejalan`, `penjajan`, …) | ambigu → ditolak |
| `tab3l` | `tabel` | sudah di vocab (leet cukup) | tidak perlu 1-edit |
| `k8s` | tidak ada digit sah | — | tetap unknown → HUNT |

- H06 / V22 / V24 **tidak naik** — `penjalan` butuh 4→u untuk jadi
  `penjualan`, yang **dilarang**; dan 7 kandidat 1-edit membuat koreksi
  kandidat-tunggal mustahil tanpa menebak. Ini gap yang disengaja, bukan
  setelan yang disesuaikan.
- v2 tetap **152/167**, tidak ada kategori turun.
- `k8s dashboard` → HUNT (G12/HO29/V25 aman).
- Tidak ada probe/θ₀/deskripsi/ekspektasi yang disetel.
