# Validasi korpus produksi

## Ringkasan P1–P5

| Kriteria | Hasil | Angka |
|---|---|---|
| P1 CORPUS_DIFF | Lulus | irisan 2, sandbox-saja 142, produksi-saja 109 |
| P2 FP natural produksi | **Gagal** | 17/90 pada ketiga run (batas ≤6) |
| P3 delta 144→produksi | **Gagal** | 446 delta/run: 31 absent, 177 benar, 90 netral, **148 salah**; subset restriksi ber-label = 0 kasus |
| P4 first-run | Lulus | model terpasang dalam 2 s, keputusan 30/30 |
| P5 R2b/R3b/R7 + uji | **Gagal** | fixture NEG_CONV tidak ikut ke wheel; check FP dilewati |

Verdict **BELUM SIAP**.

## Detail determinisme

Tiga training korpus produksi (111 skill): durasi 1.59, 1.48, 1.44 s;
memori puncak ~92 MB; 111 kelas; θ₀ 1.5606, 1.5606, 1.5605; sha berbeda
(`cfcab79b…`, `8563e4de…`, `eaa0edf6…`). Keputusan identik di ketiga run
(0 kasus tidak stabil). Perubahan status/skill terhadap model 144: 446 kasus
per run, dengan klasifikasi 31 + 177 + 90 + 148 = 446 (terverifikasi).

## FP

NEG_LIVE per grup pada model produksi (setiap run): percakapan 7,
informasional 10, verba 30, panjang 4; natural 17/90. NEG_CONV 0/40.
Model 144 pada NEG_LIVE natural memberi 5/90.

## First-run

Dari klon `dev-clean` dengan wheel terpasang `--no-index --no-deps`,
`HERMES_HOME` berisi salinan 111 skill produksi dan plugin-data kosong:
hook awal pass-through (`None`), lifecycle memicu retrain, model terpasang
atomik dalam 2 detik, hook aktif, 30/30 keputusan contoh benar.
Dua bug pada implementasi hook pertama ditemukan dan diperbaiki: copytree
menghadapi symlink rusak, dan `os.replace` lintas filesystem.
Fixture `NEG_CONV` ternyata **tidak ikut ke wheel**, sehingga R2b tidak
dapat menjalankan pengecekan FP di produksi; ini gagal P5.

## Koreksi dan batasan

Perbandingan dev vs main menghasilkan 40 regresi dev (main benar, dev salah)
berdasarkan status; mayoritas FP pada kasus NO_SKILL.
Commit `0115131`/`ab39304` hanya mengisi hash — melanggar aturan
granularitas. Usulan squash `dev-clean` memerlukan force push dan tidak
dilakukan.
FP grup "verba sebagai kata biasa" 23/40 (57%) tetap menjadi keterbatasan
yang tidak diperbaiki (butuh mandat engine).

## Perintah merge (usulan, tidak dieksekusi)

    git checkout main
    git merge --ff-only dev-clean
    git tag -a pre-merge-fase3 -m "Pre-merge checkpoint" d1de873

Rollback:

    git revert --no-edit <merge-commit>
    git push origin main
