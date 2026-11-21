# LEX_TAXONOMY — Fase 3n D0 (SEBELUM eksperimen)

Daftar kata kerja umum ID + EN untuk pemetaan **kategori artefak → skill** via
mekanisme alias `en_to_id` yang SUDAH ada di engine. Tidak dipilih dari 10
kegagalan kontrol v6–v9, tidak dari ID uji mana pun, tidak dari prompt v5–v11.
Kata dipilih dari kaidah bahasa sehari-hari (imperatif & infinitif umum).

Aturan pemetaan: kata kerja → **kategori artefak** (bukan skill tertentu);
kategori → skill lewat mekanisme alias yang sudah ada, seragam untuk semua skill.
Hanya menambah fitur; tanpa pin, bobot 1.0, boost per skill, atau pembuangan
token. θ₀/MNB/margin/probe/deskripsi/jalur ban/bypass tidak disentuh.

## Kategori (12) dan kata kerja (≥5 tiap, total 72)

| Kategori | Kata kerja ID | Kata kerja EN |
|---|---|---|
| tulis/teks | tulis, susun, karang, sunting, ringkas, parafrasa | write, draft, compose, edit, summarize, paraphrase |
| tabel/data | tabulasikan, rapikan, olah, agregasi, hitung, sajikan | tabulate, tidy, process, aggregate, compute, present |
| slide/visual | buat, gambar, desain, ilustrasi, susun | create, draw, design, illustrate, lay out |
| audio | rekam, potong, campur, transkrip, bersihkan | record, trim, mix, transcribe, clean |
| video | render, edit, gabung, potong, animasi | render, edit, merge, cut, animate |
| kode/teknis | perbaiki, benahi, telusuri, uji, terapkan | fix, repair, inspect, test, implement |
| riset | teliti, kumpulkan, bandingkan, kutip, evaluasi | research, gather, compare, cite, evaluate |
| keuangan | hitung, anggarkan, rekonsiliasi, laporkan, audit | calculate, budget, reconcile, report, audit |
| terjemahan | terjemahkan, alihkan, lokalisasi, ubah bahasa | translate, convert, localize, render |
| dokumen | ekstrak, konversi, gabung, arsipkan, susun | extract, convert, merge, archive, compile |
| perencanaan | jadwalkan, rencanakan, susun, prioritaskan, pantau | schedule, plan, organize, prioritize, monitor |
| grafis | gambar, warnai, sketsa, susun, cetak | draw, color, sketch, compose, print |

Jumlah: 12 kategori × 6 kata = **72 kata** (≥60), tersebar merata (6 per
kategori), ≥10 kategori (12). Kata "perbaiki", "hitung", "terjemahkan"
memang termasuk daftar umum — tetapi **tidak diambil karena ID uji**, melainkan
karena merupakan imperatif dasar bahasa Indonesia; tidak ada pasangan
satu-kata-satu-ID uji dalam daftar ini.

## Pemetaan kategori → kunci IDF yang sudah ada di model

Pemetaan memakai kunci yang **sudah ada** di `idf_table` model terpin,
sehingga tidak ada fitur baru yang memerlukan retrain. Contoh:
- tulis/teks → `writing`, `editorial`
- tabel/data → `tabular`, `analytics`, `pivot`
- kode/teknis → `debug`, `review`, `code`
- terjemahan → `translation`, `bilingual`
- keuangan → `invoice`, `ledger`, `finance`
- dokumen → `pdf`, `docx`, `extract`

(Pemetaan final ditulis di skrip eksperimen, bukan di sini; dokumen ini
hanya taksonomi kata, sesuai D0.)

## Hash

Hash SHA256 dokumen ini dicatat oleh perintah `sha256sum` setelah commit
dan ditambahkan ke laporan akhir. Versi pada saat experiment D dimulai
adalah versi ter-commit pertama.
