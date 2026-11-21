# LEX_TAXONOMY_V2 — Fase 3o Langkah 1

Diturunkan dari `docs/LEX_TAXONOMY.md` (sha
`fa85e3e6793ffb3460606bc1fd467d83ed1677ced74ab07fd01d52c9ac56d690`)
dengan **dua aturan mekanis saja**, tanpa menambah verba baru:

- (a) hapus verba generik dari daftar tertutup: buat, buatkan, bikin,
  bikinkan, tolong, sajikan, tampilkan, kasih, berikan, jadikan, siapkan,
  lakukan, kerjakan, olah, make, create, show, give, do, prepare, generate.
- (b) hapus verba yang di taksonomi lama dipetakan ke lebih dari satu
  kategori.

Daftar (a) ditetapkan **setelah** eksperimen sebelumnya; motivasinya adalah
dua perubahan yang melanggar guard pada kasus F02 dan F08. Ini diakui
jujur: daftar itu tidak ditulis sebelum eksperimen sebelumnya. Tidak ada
verba yang dipilih atau disingkirkan berdasarkan hasil kasus lain.

## Hitungan (jujur)

Taksonomi lama mengandung **122 token** (bukan 72 seperti yang diklaim
sebelumnya; klaim itu salah menghitung frasa "lay out" dan "ubah bahasa"
sebagai satu token). Token unik: 105.

- Aturan (a) menghapus 4 token unik: `buat`, `create`, `olah`, `sajikan`.
- Aturan (b) menghapus 12 token unik yang muncul di >1 kategori:
  `audit`, `compose`, `convert`, `draw`, `edit`, `gabung`, `gambar`,
  `hitung`, `merge`, `potong`, `render`, `susun`.
- Gabungan (union): 16 token unik.
- **Token setelah aturan: 122 − 16 = 106** (dari 122 token awal).
- Alias yang akan dibuat: hanya token yang tersisa, dipetakan ke satu
  kunci IDF yang sudah ada di model terpin.

## Kategori setelah aturan

Semua 12 kategori masih memiliki minimal 3 token; tidak ada kategori kosong.

| Kategori | Token tersisa |
|---|---|
| tulis/teks | tulis, karang, sunting, ringkas, parafrasa, write, draft, summarize, paraphrase (9) |
| tabel/data | tabulasikan, rapikan, agregasi, tabulate, tidy, process, aggregate, compute, present (9) |
| slide/visual | desain, ilustrasi, design, illustrate, lay, out (6) |
| audio | rekam, campur, transkrip, bersihkan, record, trim, mix, transcribe, clean (9) |
| video | animasi, cut, animate (3) |
| kode/teknis | perbaiki, benahi, telusuri, uji, terapkan, fix, repair, inspect, test, implement (10) |
| riset | teliti, kumpulkan, bandingkan, kutip, evaluasi, research, gather, compare, cite, evaluate (10) |
| keuangan | anggarkan, rekonsiliasi, laporkan, calculate, budget, reconcile, report (7) |
| terjemahan | terjemahkan, alihkan, lokalisasi, ubah, bahasa, translate, localize (7) |
| dokumen | ekstrak, konversi, arsipkan, extract, archive, compile (6) |
| perencanaan | jadwalkan, rencanakan, prioritaskan, pantau, schedule, plan, organize, prioritize, monitor (9) |
| grafis | warnai, sketsa, cetak, color, sketch, print (6) |

Catatan: `lay`/`out` dan `ubah`/`bahasa` adalah potongan frasa lama; tetap
diperlakukan sebagai token sesuai aturan mekanis (b), bukan diperbaiki.

## Pemetaan kategori → kunci IDF

Memakai kunci yang sudah ada di `idf_table` model terpin, seragam untuk
semua skill, tanpa retrain:

- tulis/teks → `writing`
- tabel/data → `tabular`
- slide/visual → `design`
- audio → `transcription`
- video → `video`
- kode/teknis → `debug`
- riset → `research`
- keuangan → `invoice`
- terjemahan → `translation`
- dokumen → `extract`
- perencanaan → `planning`
- grafis → `visual`

## Hash

SHA256 dokumen ini: dicatat oleh perintah `sha256sum` saat commit dan
dilaporkan di laporan akhir. Hash versi ter-commit adalah yang berlaku
untuk eksperimen.
