# auto_skill_selector

Plugin Hermes Agent otonom **bebas-bias domain** yang memilih skill lokal paling
cocok untuk setiap prompt pengguna, atau tetap diam (`NO_SKILL_NEEDED`) saat
pengguna hanya ingin berdiskusi/brainstorming.

Inti mesinnya ditulis di **Rust** (`hermes_skill_brain`) agar analisis prompt
selesai dalam **< 500 mikrodetik**. Python (`__init__.py`, `trainer.py`) bertugas
sebagai perekat hook, pemindai katalog skill, dan benchmark.

## Cara kerja (5 lapis)

1. **Positional Zone Splitter + Orthographic Cue Extractor** — memisahkan instruksi
   (200 karakter awal + 150 akhir, bobot 1.0) dari teks tempelan (payload, bobot
   0.15, dedup), lalu menandai entitas Proper-Noun/akronim dari teks mentah.
2. **Morphological Normalization + Short-Acronym Shield** — memangkas imbuhan
   Indonesia/Inggris; token 2–3 huruf (mis. `3d`, `ui`, `dcf`) hanya jadi unigram,
   **tanpa** trigram.
3. **Interaction Posture + Negation State Machine** — mendeteksi brainstorming
   (langsung `NO_SKILL_NEEDED`), menangani negasi berbasis klausa, dan role anchor.
4. **Hybrid Log-Linear Scoring** — `BM25F` + `MNB terkalibrasi` + `Dice-Sorensen
   trigram`, dikalikan domain-affinity & session momentum.
5. **Top-5 Null-Anchor Softmax + Routing** — `MATCHED_MULTI`, `MATCHED_LOCAL`,
   `NEEDS_INTERNET_SEARCH`, atau `NO_SKILL_NEEDED`.

## Struktur

```
auto_skill_selector/
├── Cargo.toml          # crate Rust cdylib (hermes_skill_brain)
├── pyproject.toml      # konfigurasi build Maturin
├── plugin.yaml         # manifest plugin Hermes
├── src/lib.rs          # mesin utama Rust (PyO3 SkillBrain)
├── __init__.py         # registrasi hook, slash command, background retrain
└── trainer.py          # pemindai skill, JSON compiler, CLI benchmark
```

## Prasyarat

- Rust: `rustc >= 1.75` dan `cargo` (via `rustup`)
- Python `>= 3.10` dan `maturin >= 1.5,<2.0` (`pip install maturin`)
- `pdo`/`pyo3` diunduh otomatis oleh cargo

## Kompilasi

`maturin develop` mengharuskan ada **virtualenv aktif** (ia menginstal hasil build
langsung ke env tersebut):

```bash
cd ~/.hermes/plugins/auto_skill_selector
python -m venv .venv && source .venv/bin/activate   # wajib untuk `develop`
pip install maturin
maturin develop --release
```

Jika memakai Hermes yang berjalan di interpreter sistem/uv (tanpa venv), bangun
wheel lalu salin `.so`-nya ke folder plugin:

```bash
maturin build --release
python -m zipfile -e target/wheels/*.whl target/wheel_extract/
cp target/wheel_extract/hermes_skill_brain/*.so .
```

> **Catatan linker:** jika gagal dengan `unable to find library -lpython3.x`,
> arahkan PyO3 ke interpreter yang benar:
> ```bash
> export PYO3_PYTHON=$(python -c "import sys; print(sys.executable)")
> ```

## Validasi & pemeriksaan

```bash
hermes plugins validate ~/.hermes/plugins/auto_skill_selector
hermes plugins doctor auto_skill_selector
hermes plugins list          # pastikan muncul & enabled
hermes plugins enable auto_skill_selector
```

## Benchmark / self-test

```bash
cd ~/.hermes/plugins/auto_skill_selector
python trainer.py --benchmark      # jalankan 10 kasus uji wajib + gerbang latensi
python trainer.py --self-test      # seed skill contoh bila katalog kosong, lalu benchmark
python trainer.py                  # retrain saja (tanpa benchmark)
```

Output diakhiri dengan `Score: 10/10 cases + PASS latency`. Model tersimpan di
`~/.hermes/plugin-data/auto_skill_selector/skill_model.json` (**bukan** di folder
plugin, agar tahan terhadap `hermes plugins update`).

## Slash command

```
/skill-brain                 # status mesin & model
/skill-brain retrain         # pindai ulang skill & rebuild model
/skill-brain test <prompt>   # uji satu prompt, lihat status + probabilitas
```

## Hook yang dipasang

- `pre_llm_call` — menyuntikkan konteks skill terpilih / instruksi Internet Hunter.
- `on_skill_lifecycle` — memicu retrain + reload saat skill dibuat/diubah/dihapus.
- `subagent_stop` — memicu retrain setelah subagent Hunter selesai (di thread daemon).

## Lisensi

MIT
