# Ambang self-retrieval untuk R2b

Diukur **sekali** pada 2026-11-22, dari model terpin 144 kelas terhadap
korpus sandbox 144 skill. Probe: `<nama skill> <kalimat pertama deskripsi>`.
Keputusan benar bila status `MATCHED_*` dan nama skill muncul di `skills`.

- Hasil: **139/144 = 96.53%**.
- Ambang R2b = 96.53% − 5 poin persentase = **91.53%**.

Angka ini ditulis sebelum dipasang sebagai konstanta di modul hook. Ambang
hanya dipakai ketika korpus terpasang berbeda dari korpus model terkirim; bila
sama, R2 asli (golden b35 + guard) tetap dipakai.
