# Aturan commit

Tujuan: riwayat yang terbaca seperti ditulis engineer, bukan transkrip proses kerja.

## Format

`type(scope): subject`

- type: feat, fix, perf, refactor, test, docs, build, chore, revert.
- scope opsional, satu kata nama modul: engine, lexicon, trainer, bench, tests, docs.
- Bahasa pesan: Inggris.
- Subject: imperatif ("add", "fix", "remove"; bukan "added" atau "adds"), huruf kecil, tanpa titik akhir, maksimal 60 karakter (batas keras 72), menyebut APA yang berubah.

## Dilarang di subject maupun body

- Label proses: "Fase", "Langkah", "Phase", "Step N", "Stage N" sebagai penanda kerja.
- ID pekerjaan atau kasus uji di subject: P1a, P2a', P-FMT, D3, HO14, V06, W33, X26, dan sejenisnya.
- Kata proses: STOP, gate, held-out, dev set, baseline (kecuali nama komponen kode).
- Angka metrik di subject (155/167, 43/52, p99 ...).
- Emoji, em dash, tanda panah, tanda seru, kurung penjelas panjang.
- Kata bergaya AI: comprehensive, robust, enhance, leverage, seamless, streamline, ensure, properly, various, significant, critical, overall, refine, address.
- Trailer atribusi: Co-Authored-By, "Generated with", tautan alat.

## Body (opsional)

- Hanya jika alasan tidak jelas dari diff. Satu baris kosong setelah subject.
- Prosa biasa, 1 sampai 3 kalimat pendek, wrap 72 karakter, maksimal 5 baris. Jelaskan MENGAPA, bukan daftar langkah.
- Tanpa tabel, tanpa bullet bertingkat, tanpa dump metrik. Satu angka boleh bila itu alasan perubahan (mis. perf).
- Rujukan kasus uji hanya di body, satu baris `Refs: ...`.

## Granularitas

- Satu perubahan logis per commit. Kode dan tesnya satu commit.
- Set uji baru: satu commit `test:`. Hasil satu fase: satu commit `docs:` di akhir, bukan per langkah.
- Dilarang commit yang tujuannya hanya mengisi hash commit lain ke dokumen. Hash tidak ditulis ke dokumen lewat commit sesudahnya; pakai `git describe` atau tag, atau sebut di laporan chat saja.
- Dilarang commit "perbaiki pesan commit sebelumnya". `git commit --amend` hanya untuk commit yang belum di-push.
- Tidak ada force push dan tidak ada rewrite riwayat yang sudah di-push.

## Contoh

Baik:

    fix(engine): treat "hindari X" as a ban cue
    test: add held-out set v11
    docs: record lexicon experiment result
    feat(lexicon): add single-category verb aliases
    revert: feat(lexicon): add verb aliases
    chore: add commit message lint

Hindari (ilustrasi gaya):

    Fase 3n STOP di Langkah D3 (alias terlalu luas; 2 delta "salah")
    P3b: hindari X = ban; Stage-0 tidak swallow ban cue → v2 152→155
    docs: koreksi guard sebelum kode (transkripsi, bukan setelan ke ID)
    ✨ Comprehensive improvements to robust skill selection

Cek sebelum commit: baca `git log -1` dan pastikan lolos scripts/commit-msg-lint.sh.
