# Diagnosis G3 dan G4

## G3 — FP menurut grup

`docs/NEG_LIVE.json`, 150 kasus: percakapan 50, informasional 40, verba
taksonomi 40, kalimat panjang 20.

| Grup | Pra-alias | HEAD | Delta |
|---|---|---|---|
| percakapan | 4 | 4 | 0 |
| informasional | 1 | 1 | 0 |
| verba taksonomi | 21 | 23 | +2 |
| panjang | 3 | 3 | 0 |
| **Total** | **29** | **31** | **+2** |

Jumlah per grup sama dengan total (29 dan 31). FP baru: `L102`
("agregasi" → `tabular-pivot-cleaning`, 8.98) dan `L119` ("transcribe"
→ `audio-transcription-whisper`, 8.15). FP yang hilang: **nol**, sehingga
2−0 = +2. Laporan 3q menyebut `L101` sebagai FP baru; itu salah — `L101`
sudah FP sebelum alias. Karena dua FP baru dan nol yang hilang, tidak ada
kasus "hilang yang tidak disebut".

Klasifikasi 31 FP HEAD tanpa mengubah ekspektasi:

| Kelas | N |
|---|---|
| (a) FP jelas | 25 |
| (b) ekspektasi diperdebatkan | 6 |

Mekanisme:

| Mekanisme | N |
|---|---|
| alias taksonomi / kata domain kuat | 23 |
| akumulasi kalimat panjang | 3 |
| kata domain kuat tanpa niat | 3 |
| bypass Stage 0 gagal / lain | 2 |

Jumlah 25+6 = 31 dan 23+3+3+2 = 31 (keduanya terverifikasi).
Usulan umum untuk mekanisme terbesar: jangan memberi bobot anchor hanya
karena kata kerja taksonomi hadir sebagai nomina/topik; ini memerlukan
perubahan engine dan **tidak diimplementasi** di fase ini.

Kriteria yang ditetapkan sebelum rincian dilihat:
- G3a grup natural (percakapan+informasional = 90): 5 → 5, delta **0** (lulus).
- G3b FP natural HEAD = **5/90**; batas jika main tidak tersedia = 4/90 →
  **gagal**.

## G4a — Korpus dan deploy

1. Sumber korpus: `HERMES_HOME/skills` (`trainer.get_skills_root`).
   Sandbox memiliki **144** `SKILL.md`, produksi
   `/data/home/.hermes/skills` memiliki **111**. Model terpin memiliki 144
   kelas. Daftar skill produksi **tidak cocok** dengan model terpin.
2. `lexicon_id_en.json` di-embed ke binary lewat `include_str!`; model dibaca
   dari disk. Wheel offline berisi `__init__.py`, `trainer.py`, dan `.so`;
   model tidak ikut terpasang. Instalasi `--no-index --no-deps` berhasil.
3. Tanpa model, `_ensure_brain()` mengembalikan brain tanpa muatan;
   prompt sah menghasilkan `HUNT_NEW_SKILL` dengan `skills=[]`, bukan
   pass-through.
4. `on_skill_lifecycle` dan `on_subagent_stop` memicu retrain pada setiap
   event, tanpa debounce, di thread daemon terpisah; dua event bersamaan
   bisa menulis model yang sama secara konkuren.
5. Retrain memang fitur yang dimaksud: skill baru harus dikenali. Solusinya
   bukan menonaktifkan, melainkan menulis atomik, validasi, fallback, dan
   single-flight.

## G4 — Implementasi

Perubahan hanya di `__init__.py` dan modul baru `plugin_retrain.py`:
- R1: trainer berjalan dengan `HERMES_HOME` sementara; model aktif diganti
  memakai `os.replace` hanya setelah validasi.
- R2: validasi membaca model, memeriksa jumlah kelas terhadap korpus,
  θ₀ dalam ±2%, dan gagal dengan aman tanpa mengganti model aktif.
- R3: tanpa model aktif, hook bersifat pass-through (`return None`) dan
  menjadwalkan bootstrap di latar belakang.
- R4: lock + debounce 30 detik (dapat diatur) menjamin satu trainer.
- R5: `AUTO_SKILL_SELECTOR_DISABLE_AUTORETRAIN=1` mematikan retrain;
  default tetap aktif.
- R6: empat uji terisolasi lulus: empty-dir bootstrap, validasi gagal,
  flag mati, dua pemicu bersamaan.

Gate: semua evaluator identik dengan sebelum perubahan; 7/7 gerbang lolos.
p99 tiga run: 250.5, 234.7, 234.0 µs — median **234.7 µs**, rentang
234.0–250.5 µs, tidak naik dari baseline 240.8 µs. Overhead hook tidak
diukur secara terpisah karena jalur keputusan tidak berubah kode.

## G2

Pelatihan native main dijalankan sebagai proses terpantau dengan data dir
terisolasi. Status pada penulisan dokumen ini masih berjalan; hasil akan
dicatat di laporan akhir. Model dev tidak dipakai sebagai substitusi.
