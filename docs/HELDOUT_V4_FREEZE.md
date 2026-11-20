# Held-out v4 — `tests/heldout_v4.json` (Fase 3b)

Dibuat **sebelum** kode Fase 3b apa pun (P3b/P4c/P1/P2). Ekspektasi ditulis
dulu, baru engine di-probe untuk observasi baseline (bukan penyesuaian).

- Jumlah: **38 kasus**
- SHA256: `a2c082fd5ab90eedd3e68712040262da88fd677652caf8aed77ea2e7b80902d8`
- θ₀ referensi: 7.4688 (tidak diubah)

## Pemeriksaan (skrip, sebelum tulis)

- **0 duplikat** dengan v2 + benchmark_35 + v3 (normalisasi: huruf/angka saja).
- **0 duplikat internal**.
- **0 expect ganda** `MATCHED_SINGLE`/`MATCHED_MULTI` dalam satu kasus.

## Komposisi

| Grup | IDs | Isi |
|---|---|---|
| Boundary atas θ₀ | V01–V08 | match benar, masing-masing SINGLE/MULTI tunggal |
| Boundary bawah | V09–V12 | weak ask → `CLARIFY_OR_HUNT` |
| OOD / kapital | V13–V15 | KNX, DMX512, ZBrush |
| Polisemi BARU | V16–V20 | food processor, kucing (bukan blender/python) |
| Noise leet/ulang/redup (kata beda) | V21–V25 | `tabelll`, `b1kinn`, `tabel-tabel`, `k8s` |
| Negasi/opsional | V26–V30 | hindari = ban, tanpa X pun tidak masalah = no-ban |
| Chitchat | V31–V38 | sapaan/terima kasih/tawa → NO_SKILL |

## Baseline engine (observasi, sebelum kode)

38 kasus di-probe: V21/V22/V24 masih NO_SKILL (target P4c),
V26/V29 ban excel sudah benar; V15/V16 masih perlu P2 observasi.
Tidak ada ekspektasi yang diubah setelah probe.

## Aturan pembekuan

Hash di atas diverifikasi saat evaluasi akhir Fase 3b (dijalankan sekali).
Jika berubah → lapor, jangan setel.
