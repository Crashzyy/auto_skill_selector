# Held-out Fase 3 — `tests/heldout_v3.json`

Dibuat **sebelum** menulis kode Fase 3 apa pun, dari probe skor independen
(bukan menyalin ekspektasi benchmark v2). Dipakai **hanya sekali** di gerbang
akhir. Jika gagal → laporkan, jangan disetel.

- Jumlah: **52 kasus**
- SHA256: `124dc7d7400200c5a4d265106b08b74542dd57a5a5dfcc9cd8935e49830e0c89`
- θ₀ referensi: 7.4688

## Komposisi

| Grup | IDs | Isi |
|---|---|---|
| Boundary atas θ₀ (match benar, 7.5–18) | HO01–HO08 | skor 7.50–18.21 |
| Boundary bawah θ₀ (weak ask) | HO09–HO12 | skor 3.01–5.02; terima CLARIFY atau HUNT |
| Hunt jelas (OOD) | HO13–HO15 | KNX, tool aneh, PLC/Modbus |
| Polisemi (konteks harus menekan skill salah) | HO16–HO22 | blender jus vs 3D, python ular vs script |
| Noise H (leet/repeat/redup/tanpa spasi) | HO23–HO29 | `expect_status_not NO_SKILL` (tidak mengunci status akhir) |
| Negasi/optionality | HO30–HO37 | tanpa ~ tidak masalah = no-ban; jangan/do-not = ban |
| Chitchat (harus NO_SKILL) | HO38–HO52 | haiii, makasiiih, hahaha, dll. |

Kasus **HO29** (`k8s dashboard`) memastikan digit `8` tidak dipetakan jadi `e`
saat normalisasi leet (G12 wajib tetap hunt).

## Aturan pembekuan

File dan hash ini dikunci di commit yang sama, sebelum commit P3 pertama.
Verifikasi akhir: `sha256sum tests/heldout_v3.json` harus sama persis.
