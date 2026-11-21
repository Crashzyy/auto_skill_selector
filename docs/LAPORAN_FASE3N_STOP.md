# Fase 3n — STOP di Langkah D3 (alias terlalu luas; 2 delta "salah")

## Ringkas hasil A–C

- **A1**: dari 19 FP 3l, hanya **5 reprodusibel** dengan model pin; 14 hilang
  (artefak model tertimpa). NEG_CONV2 berisi 5 varian topikal baru; tujuh
  kasus yang sudah ada di set lama **tidak** reprodusibel sebagai FP dengan
  model pin dan tidak dimasukkan. Lihat `docs/N_RECONCILIATION.md`.
- **A2**: AUC dikoreksi **0.8922** (bukan 0.9892 dari b35-ceiling), TPR
  71.0% / FPR 7.1% pada θ artefak 7.529. θ=5 naikkan TPR ke 81.0% tapi
  FPR 17.6% — tidak ada "gratis" kalibrasi.
- **A3**: docs dikoreksi (ceiling, invalid 3l/3m, v9 15/30).
- **B**: alias bersifat **runtime-only + rebuild**, tanpa retrain (dummy 0
  delta; "perbaiki"→debug = 3 benar). 10 kontrol: (i) 1, (ii) 9, (iii) 0.
- **C**: v11 36 kasus beku hash `d8263722…`, baseline **25/36**.

## D0–D3

- **D0** `docs/LEX_TAXONOMY.md` ditulis sebelum eksperimen, sha
  `fa85e3e6793ffb3460606bc1fd467d83ed1677ced74ab07fd01d52c9ac56d690`
  (72 kata, 12 kategori).
- **D1**: 95 alias ditambahkan ke `en_to_id` di worktree scratch, memetakan
  kata kerja umum ke kunci IDF yang sudah ada. Tanpa pin/bobot 1.0/boost,
  tanpa θ/MNB/margin/probe/deskripsi/ban/bypass.
- **D2**: bukan dead-code — 20 delta dari 564 kasus.
- **D3 klasifikasi**: benar 6, netral 16, **salah 2**:
  - `FMT_GUARD F02` HUNT→CLARIFY ("sajikan angkanya dalam bentuk tabel biasa")
    — alias "sajikan"→tabular mengubah status kontrol tanpa ban;
  - `FMT_GUARD F08` CLARIFY→MATCHED `infographic-design`
    ("jangan buat laporan dulu, aku cuma mau santai") — alias "buat"→design
    menembus idiom delay yang seharusnya NO_SKILL/CLARIFY.

## STOP

Aturan keras: *"Salah pada set dev mana pun: STOP."* → **BERHENTI.**
Tidak ada commit kode leksikon; worktree scratch dibuang. Tidak ada
penyempitan daftar alias (dilarang: "TIDAK DIKERJAKAN … penyempitan P-FMT",
dan aturan D tidak mengizinkan iterasi kedua tanpa izin). Tidak ada v11
pasca, tidak ada v10 pasca — keduanya tidak diukur karena eksperimen gagal
di gerbang dev sebelum evaluasi.

## Koreksi diri

1. Saya mengira pemetaan kategori→IDF seragam aman karena kata "umum";
   ternyata kata kerja sangat umum (`buat`, `sajikan`) justru menembus
   jalur tanpa ban dan idiom delay. Bukti: 2 delta salah di FMT_GUARD.
2. Saya tidak menyesuaikan daftar alias setelah melihat kegagalan (itu
   akan menjadi setelan per kasus), sesuai aturan STOP.
3. v11 dan v10 tetap tertutup; hanya baseline v11 25/36 dan pra v10 16/30
   yang dilaporkan, tanpa rincian v10.

## Status akhir

`dev = origin/dev = f0aac06`, `main = d1de873`, clean. Model kanonik sha
`a6a14d6a…` utuh. **BERHENTI.** Eksperimen leksikon berikutnya memerlukan
izin terpisah dengan desain yang lebih sempit (mis. hanya lemma teknis
ber-objek jelas, bukan verba generik).
