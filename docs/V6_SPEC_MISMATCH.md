# v6 — klasifikasi 13 kegagalan (Fase 3g Langkah 0)

## Headline

- **v6 = 28/41** pada binary build ulang `c98f3af` (evaluator asli, hash
  `7c7dac1a…` terverifikasi). Headline tidak diubah.
- File v6 beku **tidak diedit**. Tidak ada ekspektasi yang disetel.

Kategori:
- **engine gap** — ekspektasi sesuai desain, engine memang belum mampu
  (keterbatasan nyata).
- **spec mismatch** — ekspektasi bertentangan dengan desain yang berlaku.
- **noise sampel** — kalimat uji sendiri ambigu/ropic, ekspektasi tidak
  dapat dipertahankan secara tata bahasa.

## Tabel klasifikasi per kasus

| ID | Grup | Aktual → Exp | Klasifikasi | Alasan tata bahasa / mekanisme |
|---|---|---|---|---|
| X03 | informasional | CLARIFY → NO_SKILL | **engine gap** | "cara menghitung luas lingkaran itu gimana ya" = tanya prosedur, bukan minta artefak. Desain: NO_SKILL. Stage 0 tidak punya cue "cara menghitung" → lolos ke Stage 5, dbg 4.95 < θ₀ → CLARIFY. Keterbatasan daftar cue informasional, bukan salah ekspektasi. |
| X15 | alat-benar | HUNT → MATCHED | **engine gap** | "terjemahkan email ini ke bahasa Jerman": kata kerja artefak jelas (terjemahkan). Skill translation ada, tetapi "Jerman" tidak dikenal sebagai anchor bahasa → top 2.69 < θ₀. Gap leksikon bahasa, di luar cakupan Fase 3g. |
| X19 | polisemi | MATCHED → NO_SKILL | **engine gap** | "slide mikroskop di lab rusak" — `slide` adalah nomina fisik (preparat), bukan artefak presentasi. Engine tidak punya pembeda konteks → top 11.71 > θ₀. Gap polisemi (diakui, tidak dikerjakan). |
| X20 | polisemi | HUNT → NO_SKILL | **noise sampel** | "chart musik mingguan sudah keluar" — `chart` di sini bermakna tangga lagu, tetapi kalimatnya sangat elliptis tanpa konteks "tangga/urutan". Ekspektasi NO_SKILL masuk akal, namun sampelnya sendiri terlalu tipis untuk dijadikan penentu; engine memberi HUNT (top 6.82 < θ₀). Tidak dipakai sebagai bukti generalisasi. |
| X21 | polisemi | MATCHED → NO_SKILL | **engine gap** | "blender di dapur saya sudah rusak" — `blender` = peralatan dapur, konteks "dapur/rusak" eksplisit. Engine tetap aktifkan skill 3D (top 13.50). Gap polisemi yang jelas (sama W23/W25). |
| X23 | typo | HUNT → MATCHED | **engine gap** | "olh angka ini jadi grafik ya" — `olh` harusnya `olah`. P4c hanya mengoreksi token ≥6 huruf; `olh` (3 huruf) tidak masuk. Gap koreksi typo pendek, di luar cakupan. |
| X26 | negasi | HUNT → MATCHED | **engine gap** | "hindari pdf, kirim hasilnya sebagai docx": ban `pdf` benar; sisa klausa "sebagai docx" punya **penanda format `sebagai` + nama skill `docx`**. Engine tidak menjadikan `docx` anchor → top 6.65 < θ₀ → HUNT. Ini **target yang tepat untuk P-FMT** (Langkah 4). |
| X27 | negasi | NO_SKILL → MATCHED | **engine gap (jalur bypass; TIDAK terjangkau P-FMT)** | "jangan pakai slides, ringkasannya saja cukup": ban `slides` benar; sisa klausa "ringkasannya saja cukup" adalah ellipsis kata ganti + "cukup" — **tanpa penanda format dan tanpa nama skill**. Kena conversational bypass Stage 0 → NO_SKILL. P-FMT hanya bekerja bila ada penanda format + nama skill di klausa residual, jadi **tidak akan menyentuh X27**. |
| X28 | negasi | HUNT → MATCHED | **engine gap (P-FMT tidak terjangkau)** | "jangan gunakan infografik, cukup tabel biasa": ban `infografik` benar; sisa "cukup tabel biasa" memuat `tabel` (nama skill/canon) tetapi **tanpa penanda format** (`sebagai/dalam/jadi/as/in`). P-FMT mensyaratkan penanda format, jadi **X28 tidak akan berubah**. Perhatikan beda dengan X26 yang punya "sebagai docx". |
| X29 | negasi | HUNT → MATCHED | **engine gap** | "tanpa chart, sajikan angkanya dalam tabel": ban `chart` benar; sisa "sajikan angkanya dalam tabel" memuat penanda `dalam` + `tabel` — secara struktural mirip target P-FMT. Namun `tanpa` adalah cue lemah/opsional; kasus ini tetap gagal di baseline. Layak diamati apakah P-FMT menjangkau. |
| X31 | multi | MATCHED → MULTI | **engine gap** | "bersihkan teks artikel ini dan terjemahkan ke Prancis": dua artefak eksplisit, engine hanya activate satu (top 11.64). Gap multi-skill gate. |
| X32 | multi | MATCHED → MULTI | **engine gap** | "rangkum pdf ini dan buatkan infografisnya": dua artefak, engine satu (top 10.67). Gap multi-skill gate. |
| X35 | kontrol | HUNT → MATCHED | **engine gap** | "cek kode ini untuk bug dan perbaiki": permintaan debugging nyata, skill ada, tetapi top 5.35 < θ₀. Gap skor di bawah ambang (kelompok "skill benar < θ₀"). |

## Ringkasan

| Klasifikasi | ID | N |
|---|---|---|
| engine gap | X03, X15, X19, X21, X23, X26, X27, X28, X29, X31, X32, X35 | 12 |
| spec mismatch | — | 0 |
| noise sampel | X20 | 1 |

**Tidak ada spec mismatch di v6** — beda dengan v5 (W01–W10). Ekspektasi v6
memang ditulis dari prinsip sebelum probe, sehingga semuanya masih konsisten
dengan desain; yang gagal adalah kemampuan engine.

## Catatan X27 dan X28 (diminta khusus)

- **X27** gagal di **Stage 0 bypass** (sanitized "ringkasannya saja cukup" →
  conversational). P-FMT tidak menyentuh bypass.
- **X28** gagal di **Stage 5 below-θ₀**, tetapi klausa residualnya tidak punya
  penanda format. P-FMT mensyaratkan penanda format + nama skill yang tidak
  diban, jadi secara teori juga tidak menjangkau X28.
- Hanya **X26** (dan mungkin X29) yang secara struktural sesuai dengan
  mekanisme P-FMT. Ini dasar untuk uji dead-code Langkah 3: jika P-FMT hanya
  mengubah ≤2 kasus di kelompok A v7 dan nol di X27/X28, itu bukan perbaikan
  negasi umum — lihat keputusan penutup di laporan akhir.
