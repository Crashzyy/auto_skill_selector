# Skenario Uji Fase 2: dipetakan ke arsitektur nyata (commit 8c12405)

Pengganti label seed lama: ROUTE -> MATCHED_*, NONE -> NO_SKILL_NEEDED, SEARCH -> HUNT_NEW_SKILL, CLARIFY -> CLARIFY_AMBIGUOUS.

## Berkas
- `benchmark_scenarios_v2.json`: sekitar 190 kasus dalam format benchmark Anda, ditambah kolom baru (lihat `_meta`).
- `fuzz_metamorphic.py`: stress panic-safety (subprocess), invarian, determinisme, uji metamorfik. Belum dijalankan; sesuaikan konstruktor `SkillBrain` lebih dulu.

## Hipotesis risiko baru (belum terbukti, perlu dijalankan)
| ID | Hipotesis | Kasus / alat |
|---|---|---|
| H-1 | Larangan di kepala paste panjang (di luar tail 320 char) lolos dari sieve, sehingga skill terlarang bisa aktif. Zona instruksi hanya tail, sedangkan head hanya bobot 0.35x. | F03 |
| H-2 | Instruksi di kepala paste panjang ("Buatkan grafik dari data berikut: [500 kata]") kalah oleh payload yang tail-dominant. | F02 |
| H-3 | Deteksi unknown-tool memicu false positive pada kata Inggris atau kata lowercase yang tak ada di `known_vocab` (leksikon KBBI/ID-centric): "using simple language", "in bullet points", "pakai font arial". Akibatnya klausa sah dipaksa hunt. | G04-G10 |
| H-4 | `panic="abort"` + manipulasi indeks pada karakter multibyte atau lowercase Unicode (İ, ß, kombinasi diakritik) bisa mematikan seluruh gateway, bukan hanya satu giliran. Cek apakah INSTRUCTION_HEAD/TAIL dan `raw_word_spans` bekerja pada byte atau char. | `stress_cases()`: boundary_*, head80_*, tail320_*, turkish_dotted_I |
| H-5 | Pin mentah yang tak dikenal masuk ke teks injeksi (S-1) bisa menjadi jalur prompt-injection: nama pin dikarang pengguna/pihak lain, lalu diperintahkan ke agent lewat `skill_view`. | A03, A04 |
| H-6 | Urutan langkah mengikuti urutan kemunculan klausa, bukan urutan logis. "Sebelum X, lakukan Y" membalik urutan. | D12, D13 |
| H-7 | Slang berbahaya di leksikon komunitas: `dek` (adik vs pitch deck), `no` (nomor vs larangan), `x`, `gan`. | I01-I03 |
| H-8 | Kalibrasi θ₀ dan benchmark dibuat sendiri, jadi 35/35 hanya mengukur kepatuhan spesifikasi. Perlu hold-out yang tidak dilihat siapa pun saat tuning. | lihat bagian Metodologi |

## Pemetaan ke temuan audit Anda
- S-1 (pin tak dikenal): A01-A04, A12
- S-2 (over-ban): B01-B05, B13-B15, B28, I03
- S-3 (momentum sesi): C05-C07 (butuh runner multi-turn `session`)
- S-4 (klausa ke-4 hilang): C01-C04 (`expect_note_dropped`)
- M-6 (slang komunitas): I01-I07

## Cakupan per stage
| Stage | Kasus |
|---|---|
| 1 Pin | A01-A14 |
| 0 Obrolan / bypass | E01-E20, L05-L09 |
| 2 Sieve/ban | B01-B29, F03-F06, I03, I05-I07 |
| 3 Splitter | C01-C04, D01-D17 |
| 4 Skor, mode, unknown-tool | F01-F08, G01-G12, H01-H21, M01-M07, K01-K08 |
| 5 Merge/status | D12-D13, K04, J01-J08 |
| Keamanan | A03-A04, L01-L04 + stress |

## Cara memakai
1. Tambahkan dukungan kolom baru di `check_case`: status sebagai list, `expect_status_not`, `expect_banned_excludes`, `expect_pinned_empty`, `expect_note_dropped`, `session`.
2. Jalankan sekali tanpa mengubah kode untuk mendapatkan baseline jujur. Kasus bertarget `S-*`, `H-*`, `M-6` kemungkinan banyak yang gagal.
3. Untuk kasus yang bertanda "putuskan kebijakan" (B17, B20, B22, D04, E19), putuskan perilaku yang diinginkan, kunci ekspektasinya, lalu jadikan regression test.
4. Jalankan `fuzz_metamorphic.py`. Prioritaskan temuan stress yang berujung CRASH (H-4).
5. Perbaiki mulai dari temuan keamanan dan crash (H-4, H-5, S-1), lalu S-2, S-4, H-1, H-3.

## Metodologi: menghindari overfit
- **Tiga set terpisah**: dev (35 kasus lama + v2, boleh dipakai tuning), hold-out (60-100 prompt ditulis orang lain atau diambil dari log nyata, tidak dilihat saat tuning), adversarial (fuzz).
- **Jangan ubah deskripsi skill atau probe kalibrasi demi lulus kasus tertentu.** Kalau θ₀ atau probe disetel berdasarkan kasus yang juga dites, angka jadi tidak bermakna. Probe kalibrasi (12) sebaiknya berbeda dari prompt benchmark.
- **Laporkan per kategori**, bukan satu angka total: typo, negasi, splitter, obrolan, OOD, keamanan. Rata-rata 100% bisa menutupi kategori yang rapuh.
- **Metrik wajib**: false-trigger rate pada obrolan (paling mahal), akurasi ban (leak dan over-ban dihitung terpisah), retensi metamorfik per transformasi, latensi p99 termasuk overhead `_ensure_brain` (M-5).
- **Log nyata**: setelah dipakai, kumpulkan prompt yang berakhir NO_SKILL/CLARIFY/HUNT lalu tinjau berkala untuk membuat kasus baru. Redaksi data pribadi dan rahasia (API key, token) sebelum disimpan.

## Skenario operasional (bukan prompt, perlu uji terpisah)
- Model JSON korup, kosong, atau lebih lama dari korpus
- `.so` hilang atau salah versi Python
- Dua skill bernama sama dari katalog berbeda; skill tanpa deskripsi; slug dengan karakter aneh
- Skill baru ditambahkan di tengah sesi sebelum retrain selesai
- Retrain bersamaan dengan prompt masuk (RwLock)
- Frontmatter YAML berbahaya atau SKILL.md 400 KB di harvest
- Deskripsi skill komunitas berisi instruksi tersembunyi (injection lewat katalog); sanitasi saat harvest, karena teks skill ikut masuk ke konteks injeksi (`_skill_summary`)
- Prompt multimodal (list bagian teks dan gambar), prompt dengan lampiran tanpa teks
