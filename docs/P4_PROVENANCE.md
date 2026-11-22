# Audit asal prompt P4 (Fase 3s)

Pada Fase 3s, simulasi first-run memakai 30 prompt contoh:

- 15 "positif" dibuat secara ad-hoc di skrip sementara
  `/tmp/hermes-sandbox/s_sim30.py` dengan pola `pakai skill <nama>` dari
  15 nama produksi pertama. Skrip itu bukan fixture beku, tidak memiliki
  hash, dan tidak memiliki `expect_skills` eksplisit di artifacts repo.
- 15 "negatif" diambil dari 15 kasus pertama `docs/NEG_CONV.json`.

Kedua kelompok ditulis oleh agent selama Fase 3s, bukan oleh user, dan tidak
terdokumentasi sebelum evaluasi. Karena 15 positif bukan dari PROD_V1 atau
set beku lain, klaim P4 "30/30 benar" **tidak terverifikasi** sebagai bukti
kualitas; ia hanya membuktikan hook tidak inert dan jalur first-run bekerja.

Fase 3t akan mengulang first-run dengan prompt yang berasal dari PROD_V1.
