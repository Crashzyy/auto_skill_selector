# Fase 3 — P5: Pengukuran `_ensure_brain` (tanpa optimasi)

Sesuai perintah: ukur saja, **jangan optimasi**.

- Metode: import hook dari plugin terpasang, panaskan `_import_brain()`,
  300 iterasi `_ensure_brain()` dengan model JSON dari disk (kondisi nyata),
  di venv sandbox dengan binary hasil build ulang.
- Hasil: **p50 46.20 ms · p95 56.05 ms · p99 61.71 ms**
  (min 33.10 ms, max 62.24 ms, mean 46.26 ms).
- Catatan: angka ini adalah overhead **per giliran hook**, bukan latensi
  `analyze_prompt` (yang tetap ~puluhan µs). Angka P5 tidak dioptimasi;
  variasi vs A4 (p50 ~33 ms) berasal dari kondisi pengukuran/model saat ini,
  bukan perubahan kode Fase 3. Tidak ada kode yang diubah untuk P5.
