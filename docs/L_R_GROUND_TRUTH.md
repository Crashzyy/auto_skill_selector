# Fase 3l Langkah 2 — Ukur ulang kelas R dengan ground truth

## Sumber target

Hanya kasus dengan **`expect_skills` eksplisit** yang dihitung. Di repo ini
hanya `tests/benchmark_35_labeled.json` yang memilikinya (**28 kasus**).
Field `target` di `benchmark_scenarios_v2.json` adalah tag skenario
(`S-1`, `H-2`, `M-6`, …), **bukan nama skill** — jadi tidak dipakai sebagai
ground truth. Semua set held-out (v3–v10) tidak punya `expect_skills`.

## Hasil

- **28 kasus ber-target eksplisit: semuanya MATCHED (lolos) di dev.**
- Jadi tabel R1–R4 dengan ground truth **kosong** (R1=0, R2=0, R3=0, R4=0),
  histogram gap tidak ada yang dihitung. Ini koreksi atas laporan 3k yang
  menginfer target dari top-1 dan menghasilkan R1 41/51 — angka itu
  **tidak dapat diverifikasi** dengan ground truth dan ditarik kembali.
- **16 kasus MATCHED-expect gagal tanpa `expect_skills`** dilaporkan
  terpisah sebagai **"target tak diketahui"** (tidak dihitung dalam R):
  v2 1, v3 1, v4 2, v5 2, v7 2, v8 1, v9 4, P2A_GUARD 1,
  v10 2 (skor saja; rincian per kasus v10 sengaja tidak dibuka).
- `expect_status` dari 16 kasus itu tetap gagal menurut evaluator asli;
  mekanismenya sudah didiagnosis di fase 3h–3k (bypass, ban-residual,
  polisemi, typo). Tidak ada yang diubah.

## Konsekuensi keputusan

Karena R dengan ground truth kosong, **tidak ada bukti kelas R dominan**
untuk memilih tuas kebijakan/leksikon. Langkah 3 (diagnosis kontrol) harus
berdiri sendiri; kalau juga tersebar tanpa mekanisme dominan → STOP
sesuai aturan.

## Koreksi diri

Saya sebelumnya (3k) menghitung R1 80.4% dengan target inferensi top-1;
metode itu secara struktural membuat R2/R3 = 0 dan R1 selalu benar.
Perintah 3l meminta ground truth; saya turuti dan menarik angka 3k,
bukan mempertahankannya demi kesimpulan sebelumnya.
