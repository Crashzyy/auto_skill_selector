# Diagnosa pooled "skill benar < θ₀" — Fase 3j Langkah 3 (read-only)

Sumber: binary hasil revert `4e70dbf` (= perilaku `dc429c9`), 456 kasus dari
v2, b35, v3–v8, semua guard yang punya `expect_status`. Diambil semua kasus
ber-ekspektasi `MATCHED_*` yang menghasilkan `HUNT_NEW_SKILL`,
`CLARIFY_AMBIGUOUS`, atau `NO_SKILL_NEEDED`. **38 kasus**.

## Hitungan per mekanisme

| Mekanisme | N | ID |
|---|---|---|
| ban + klausa residual elliptis | **18** | W31, W32, W33, X26, X27, X28, X29, Y01, Y02, Y03, Y06, Z01, Z02, Z07, Z08, A08, A09, A10 |
| scoring di bawah θ₀ (umum) | 8 | F08, W15, X35, Y18, Y26, Z20, Z26, G03 |
| Stage-0 bypass / top=0 | 6 | B20, W14, W16, Y04, Y05, Z05 |
| token lemah / typo / bahasa | 5 | W39, X15, X23, Y19, Z21 |
| unknown_tool (OOD) | 1 | HO29 (`k8s`, top 10.76) |

Topik yang terlibat: **format/tool token 24**, numerik/tabel 9, translasi
5, code/debug 4, summarization 2. Kegagalan **tersebar** di banyak skill
(bukan terkonsentrasi pada 1–2 skill): tidak ada satu nama skill yang
mendominasi; yang sama adalah *bentuk kalimatnya* (ban + ellipsis, entitas
bahasa asing, angka tanpa konteks).

## Per kasus (ringkas: set:ID — skor — mekanisme)

- ban+ellipsis: v5:W31 4.92, W32 4.57, W33 5.72; v6:X26 6.66, X28 2.85,
  X29 2.61; v7:Y01 6.60, Y02 2.57, Y03 7.20, Y06 7.19; v8:Z01 6.49,
  Z02 6.95, Z07 2.57, Z08 6.80; guard:A08 6.55, A09 2.56, A10 7.04;
  v6:X27 6.01 (bypass).
- scoring umum: v2:F08 6.48; v5:W15 6.03; v6:X35 5.35; v7:Y18 4.44,
  Y26 5.38; v8:Z20 4.43, Z26 5.38; guard:G03 4.05.
- bypass/top=0: v2:B20, v5:W14, W16, v7:Y04, Y05, v8:Z05.
- token lemah: v5:W39 4.27, v6:X15 2.70, X23 6.84, v7:Y19 2.70, v8:Z21 2.70.
- unknown_tool: v3:HO29 10.76.

## Usulan untuk mekanisme terbesar (ban + residual elliptis, 18)

Masalahnya **bukan** θ₀: residual sesudah ban kehilangan anchor skill
("hasilnya sebagai docx", "cukup tabel biasa", "sajikan angkanya…"),
sehingga skor turun ke 2.5–7.2 sementara θ₀ = 7.4688. Menaikkan θ₀ tidak
membantu (justru menolak lebih banyak kasus benar), dan menurunkannya
berisiko membanjiri MATCHED dengan noise.

Yang perlu dibuka (dengan izin terpisah):
1. **Leksikon/splitter**: setelah sieve membuang cue ban, klausa residual
   harus tetap membawa objek format sebagai anchor. Perbaikan umum:
   **jangan membuang token deliverable/format saat mengekstrak ban** —
   catat sebagai anchor feature dengan bobot mention eksplisit, bukan pin
   1.0. Ini berbeda dari P-FMT: tidak memakai cue tata bahasa `sebagai`;
   hanya token format nyata (docx/tabel/spreadsheet) yang *memang ada* di
   residual dan tidak diban.
2. **Stage-0 bypass**: untuk kasus X27/Y05/Z05, prohibition sieve harus
   tetap diproses sebelum bypass (sudah ada `has_strong_ban_cue`), tetapi
   residual "ringkasannya saja cukup" tidak punya objek sama sekali — ini
   benar-benar ellipsis tanpa referen; ekspektasinya patut ditinjau ulang
   oleh user, bukan disetel diam-diam.

Argumen θ₀ tidak perlu disentuh: semua 38 kasus berada di bawah θ₀ karena
**fitur yang hilang** (anchor terbuang, token asing tak dikenal, atau ellipsis
tanpa objek), bukan karena ambang salah. θ₀ sudah lolos 7/7 gate dan
regresi 35/35. Mengubahnya adalah setelan kalibrasi, dilarang.

Tidak ada implementasi dari dokumen ini.
