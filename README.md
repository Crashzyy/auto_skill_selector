# auto_skill_selector

**Pemilih skill otonom untuk Hermes Agent.** Mesin Rust ini membaca setiap
prompt, menilai seluruh skill lokal, lalu memilihkan yang paling cocok.
Proyek ini masih **eksperimental** — belum dijamin bekerja baik pada pemakaian
nyata. Lihat [Keterbatasan](#keterbatasan).

> **Status: Alpha, eksperimental.** API, skema model, dan perilaku routing masih
> bisa berubah. Akurasi di luar kasus uji bawaan belum diverifikasi.

---

## Masalah yang ingin diselesaikan

Hermes Agent punya ratusan skill. Tanpa pemilih otomatis, pengguna harus menebak
skill mana yang sesuai lalu memanggilnya manual. Plugin ini mengambil alih
pekerjaan itu: membaca prompt, menilai seluruh kandidat, dan memilih yang terbaik.

Ada tiga keputusan yang dapat diambil, plus satu kondisi diam.

| Status | Arti |
|---|---|
| `MATCHED_LOCAL` | Satu skill lokal paling sesuai telah ditemukan |
| `MATCHED_MULTI` | Dua skill dirantai, mis. DCF di Excel lalu slide PowerPoint |
| `NEEDS_INTERNET_SEARCH` | Topik belum tersedia di lokal; didelegasikan ke subagent pencari |
| `NO_SKILL_NEEDED` | Pengguna sedang berdiskusi atau brainstorming; tidak ada skill yang diaktifkan |

## Cara kerja

Analisis berjalan lima lapis, semuanya di Rust.

1. **Pemisahan zona instruksional.** Prompt dipisah menjadi zona instruksi (200
   karakter awal plus 150 akhir, bobot penuh) dan zona payload (bobot 0,15,
   deduplikasi). Artikel sepanjang 5.000 kata yang ditempel tidak akan
   mendominasi perintah pendek di awal.
2. **Normalisasi morfologi.** Imbuhan Indonesia dipangkas: `menggunakan` menjadi
   `guna`, dan keduanya disimpan. Akronim pendek seperti `ui`, `3d`, `dcf` hanya
   menjadi unigram, tanpa trigram.
3. **Postur interaksi dan mesin negasi.** Frasa seperti "menurutmu" atau "jangan
   langsung buat kode" menghasilkan postur `conversational`. Negasi berbasis
   klausa membuat "Jangan pakai Docker, tapi deploy ke Cloudflare" mengecualikan
   Docker dan memilih Cloudflare.
4. **Skoring hibrida log-linear.** BM25F berbobot medan, Naive Bayes multinomial
   terkalibrasi, dan Dice-Sorensen trigram untuk ketahanan typo, lalu dikalikan
   afinitas domain dan momentum sesi.
5. **Softmax Top-5 Null-Anchor.** Probabilitas dihitung dari 5 kandidat teratas
   terhadap anchor nol. Baik 5 maupun 2.000 skill di disk, hasilnya tidak terdilusi.

## Bobot dokumen Zona S/A/B/C

Saat memindai `SKILL.md`, bobot fitur dokumen dihitung per zona.

| Zona | Bobot | Isi |
|---|---|---|
| **S** | 8.0 | Nama skill, slug folder, tags/keywords/triggers, judul H1 |
| **A** | 4.5 | Deskripsi, section "When to Use", sinonim dwibahasa |
| **B** | 2.5 | Heading lain, "Quick Reference"/"Procedure", nama perintah |
| **C** | 0.6 | Paragraf penjelasan, maks 80 baris di luar blok kode |

Total bobot tiap dokumen dinormalkan ke 100.0, sehingga SKILL.md pendek dan
panjang setara 1:1. Dari bobot inilah θ₀ (null_anchor_score) dikalibrasi
otomatis; nilai anchor selalu mengikuti skala skor aktual, apa pun jumlah skill
di disk.

## Performa

Benchmark bawaan lolos **10/10 kasus uji** dengan latensi rata-rata di bawah
500 mikrodetik per analisis. Di mesin pengembangan, hasil aktual berkisar
100–470 µs. Angka ini diukur pada katalog kecil (7 skill seed) dan **belum
diuji pada katalog besar atau beban kerja nyata**.

## Keterbatasan

- **Belum teruji di pemakaian nyata.** Yang diverifikasi hanyalah benchmark 10
  kasus, `plugins validate`, dan `plugins doctor`. Hook `pre_llm_call` belum
  diuji end-to-end di sesi Hermes hidup, jadi kualitas pemilihan skill pada
  prompt pengguna sungguhan masih belum diketahui.
- **Akurasi belum diverifikasi.** 10 kasus uji adalah sampel kecil yang
  ditulis sendiri; kinerja pada topik di luar kasus tersebut bisa jauh lebih
  buruk.
- **θ₀ (null_anchor_score) dikalibrasi ulang otomatis.** Parameter yang sama
  disebut `null_anchor` pada bagian Bobot dokumen. Nilai bawaan spesifikasi
  (1,65) diganti hasil kalibrasi dari sebaran skor lokal. Rumus dan ambangnya
  masih eksperimental dan bisa menghasilkan false positive/negative.
- **Katalog kosong saat build.** Model awal dibangun dari skill yang ada; pada
  katalog kosong, `avg_doc_len` dan θ₀ dihitung dari skill benchmark sintetis.

## Instalasi

```bash
# 1. Prasyarat: Rust (rustup) + Python 3.10+ + maturin
pip install maturin

# 2. Bangun mesin Rust
cd ~/.hermes/plugins/auto_skill_selector
maturin develop --release

# 3. Validasi lalu aktifkan
hermes plugins validate ~/.hermes/plugins/auto_skill_selector
hermes plugins enable auto_skill_selector
```

Detail varian `maturin build` tanpa venv ada di [`docs/CONTRACTS.md`](docs/CONTRACTS.md).

## Benchmark

```bash
python trainer.py --benchmark     # 10 kasus uji + gerbang latensi
python trainer.py --self-test     # seed skill contoh bila katalog kosong
python trainer.py                 # retrain saja
```

Kasus uji mencakup pencocokan dwibahasa, ketahanan typo, negasi majemuk, rantai
multi-skill, imunitas wall-of-text, bypass brainstorming, dan pemicu pencari
internet. Output diakhiri `Score: 10/10 cases + PASS latency`.

## Perintah slash

```
/skill-brain                 # status mesin & model
/skill-brain retrain         # pindai ulang skill, rebuild model
/skill-brain test <prompt>   # uji satu prompt, lihat probabilitasnya
```

## Struktur

```
auto_skill_selector/
├── Cargo.toml          # crate Rust cdylib (hermes_skill_brain)
├── pyproject.toml      # konfigurasi build Maturin
├── plugin.yaml         # manifest plugin Hermes
├── src/lib.rs          # mesin utama: PyO3 SkillBrain
├── __init__.py         # hook, slash command, retrain latar
├── trainer.py          # pemindai skill, compiler JSON, CLI benchmark
└── tests/              # verifikasi zona dan model
```

## Catatan desain

Mesin ini bebas-bias domain dan tidak menebak dari ekstensi file seperti `.py`
atau `.sql`. Pendekatannya lewat *role anchor* preposisi dan petunjuk ortografi,
ditopang graf konsep dwibahasa. Bidang kreatif, keuangan, dan produktivitas tetap
terdeteksi tanpa daftar kata kunci kaku per domain. Model sendiri tersimpan di
`plugin-data/`, bukan folder plugin, agar tahan terhadap `hermes plugins update`.

## Lisensi

MIT
