# A1 — Verifikasi diff per-kasus v2: 8c64981 vs 5f85058

Tanpa ubah probe/θ₀/deskripsi/ekspektasi. Dua commit dibangun di worktree
terpisah (`/data/workspace/wt-8c64981`, `/data/workspace/wt-5f85058`), `.so`
masing-masing diekstrak dari wheel, lalu `benchmark_runner.run_v2()` dijalankan
dengan model sandbox yang sama (`skill_model.json`, θ₀ = 7.4688).

## Angka terverifikasi

| Commit | v2 | A | B | C | D | E | F | G | H | I | J | K | L | M |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `8c64981` (2.4) | 134/167 | 14/14 | 27/29 | 7/7 | 13/17 | 14/20 | **7/8** | 6/12 | **17/21** | 7/7 | 5/8 | 3/8 | 9/9 | 5/7 |
| `5f85058` (2.9a) | 145/167 | 14/14 | 27/29 | 7/7 | 16/17 | 18/20 | **6/8** | 7/12 | **17/21** | 7/7 | 8/8 | 3/8 | 9/9 | 6/7 |

## Regresi per-kasus (old PASS → new FAIL): 4 kasus

| Kasus | `8c64981` | `5f85058` | Penyebab |
|---|---|---|---|
| **F07** | MATCHED_SINGLE `pdf-extraction-manipulation` | CLARIFY_AMBIGUOUS | Vague-ask guard (2.7) kena `ini` pada "...ringkas isi halaman ini"; `isi`/`halaman` bukan DELIVERABLE_NOUNS, URL tidak dikecualikan |
| **E15** | NO_SKILL_NEEDED | CLARIFY_AMBIGUOUS | guard kena kata `bagus` pada "bikinan lokal kualitasnya bagus lho" (social, bukan tugas) |
| **E18** | NO_SKILL_NEEDED | CLARIFY_AMBIGUOUS | guard kena `that` pada "ok thanks, that's all" |
| **G12** | HUNT_NEW_SKILL | MATCHED_SINGLE `sql-bi-dashboard` | `fuzzy_known_tool("k8s")` menyubstitusi digit `8`→`a` → `kas` (known vocab), sehingga `k8s` dianggap tool dikenal |

Perbaikan umum (bukan per-kasus):
1. Vague-ask guard hanya menghasilkan CLARIFY bila ada action verb DAN tidak ada
   token URL/path/filename. J01/J06/J08 (bantu/make/buat) tetap CLARIFY; E15/E18
   (tanpa action verb) jatuh ke NO_SKILL; F07 (ada `ringkas` + URL) jatuh ke MATCHED.
2. `fuzzy_known_tool` tidak menyubstitusi posisi digit dengan huruf (digit bukan
   typo huruf). `k8s` tidak lagi salah menjadi `kas`.

Hasil setelah perbaikan pada `dev` (binary di-build ulang): **v2 149/167**,
E 20/20, F 7/8, G 8/12, J 8/8, regresi 35/35, J01/J06/J08 tetap CLARIFY.

## Catatan jujur F dan H

- **F 7/8 → 6/8**: penurunan SATU kasus nyata = **F07** (regresi guard, sudah
  diperbaiki → kembali 7/8). Bukan perubahan ekspektasi.
- **H 17/21 → 17/21**: TIDAK turun di kedua commit yang diukur. Laporan lanjutan
  Fase 2 menyebut "H 18/21" pada ringkasan sebelum 2.4 dan "17/21" di akhir;
  angka 18/21 itu berasal dari hitungan probe sementara pasca-patch 2.4 yang
  tidak muncul pada `run_v2()` commit mana pun. Status 4 kasus H yang FAIL
  (H05, H06, H08, H21) identik di kedua commit (NO_SKILL_NEEDED). Tidak ada
  regresi H yang perlu diperbaiki; koreksi dokumentasi dicatat di sini.
