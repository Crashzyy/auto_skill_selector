# Fase 3 — P1: Zona abu di bawah θ₀ (DESAIN — belum ada kode)

> Status: **DESAIN SAJA**. Sesuai perintah, P1 ditulis di docs dulu, bukan
> kode. Implementasi menunggu keputusan. θ₀ = 7.4688 TIDAK diubah.

## 1. Masalah

Saat ini, klausa yang skornya di bawah θ₀ tetapi punya sinyal HUNT
(`hunt_reason = below_theta`) langsung menjadi `HUNT_NEW_SKILL`. Akibatnya:

| Kasus | status | hunt_reason | skor | ekspektasi |
|---|---|---|---|---|
| G02 `pakai exel buat tabel penjualan` | HUNT | below_theta | 7.09 | expect_hunt=false |
| G04 `buat laporan pakai warna biru dan font arial` | HUNT | below_theta | 7.02 | expect_hunt=false |
| G05 `write a report using simple language` | HUNT | below_theta | 7.06 | expect_hunt=false |

Ketiganya bukan benar-benar OOD; mereka adalah **match yang lemah** (skor
mendekati θ₀). Mengubahnya jadi HUNT adalah keputusan biner yang salah.

## 2. Desain: hasil zona abu = CLARIFY

Perkenalkan **zona abu** tepat di bawah θ₀:

```
score >= θ₀                     -> MATCHED (perilaku sekarang, tidak diubah)
θ₀·(1-m) <= score < θ₀          -> CLARIFY_AMBIGUOUS   (BARU)
score < θ₀·(1-m)                -> HUNT_NEW_SKILL / NO_SKILL (perilaku sekarang)
```

Artinya: untuk klausa dengan sinyal HUNT ber-`below_theta` yang skornya
**dekat** θ₀, jangan langsung HUNT dan jangan diam-diam NO_SKILL — minta
klarifikasi ke user. Ini memakai status `CLARIFY_AMBIGUOUS` yang sudah ada,
tanpa status baru, tanpa mengubah θ₀.

Margin `m` **TIDAK** diturunkan dari G02/G04/G05 (sesuai larangan). Ia
diturunkan dari **benchmark_35 + held-out**:

- benchmark_35: mayoritas directive asli skor 9–34 (median ~16); yang
  rendah tapi valid: #28=6.94, #11=7.95, #26=9.51, #27=8.22.
- held-out boundary match-benar: HO01=7.50, HO02=7.51, HO03=7.92,
  HO22=7.95, HO30=7.40, HO31=7.52, HO32=7.48, HO34=7.52.
- held-out hunt-benar: HO13=0.00, HO14=4.68, HO15=2.42, HO29=7.09
  (`k8s`, tapi `hunt_reason=unknown_tool`, bukan below_theta → tidak masuk zona).

Jarak aman antara match-terendah valid (~6.94) dan θ₀ (7.47) ≈ 0.53 ≈ 7%.
Namun HO29 (7.09) adalah hunt-benar dengan `below_theta`? TIDAK — ia
`unknown_tool`, jadi tidak terkena zona abu. Satu-satunya hunt-benar
`below_theta` di dekat θ₀ adalah G02/G04/G05 (7.02–7.09), yang justru
**ekspektasinya bukan hunt** — mendukung CLARIFY.

## 3. Sensitivitas margin 3 / 5 / 8 / 10%

"False-clarify" = kasus match-benar yang skornya masuk zona abu sehingga
berubah menjadi CLARIFY (padahal harusnya MATCHED).

| margin | zona abu (hanya untuk `below_theta`) | G02/G04/G05 ketangkap | match-benar terkena |
|---|---|---|---|
| 3% | [7.24, 7.47) | tidak (0/3) | 1/8 (HO30=7.40, negasi) |
| 5% | [7.10, 7.47) | tidak (0/3) — G02=7.09 < 7.10 | 1/8 (HO30) |
| 8% | [6.87, 7.47) | **ya (3/3)** | 1/8 (HO30) + reg35 #28=6.94 |
| 10% | [6.72, 7.47) | ya (3/3) | 1/8 + #28=6.94 + HO29=7.09* |

\* HO29 adalah `unknown_tool`, JADI tidak masuk zona abu (zona hanya untuk
`below_theta`), jadi aman juga di margin 10%.

Koreksi atas draf awal: margin 5% TIDAK menangkap G02/G04/G05 (G02=7.09
berada tepat di bawah batas 7.10). Margin minimal untuk menangkap ketiganya
adalah **8%**. Margins 3%/5% tidak menyelesaikan masalah yang dimaksud.

**Trade-off jujur:**
- margin 8% ([6.87, 7.47)) menangkap G02/G04/G05, dengan biaya reg35 #28
  (6.94, `/skill` pin — sebenarnya diproses Stage 1, jadi tidak terkena zona
  abu) dan HO30 (7.40, kasus negasi dengan ekspektasi ban, bukan status).
  Secara empiris tidak ada match-benar murni yang berubah jadi CLARIFY.
- G07 (6.86, `unknown_tool`) tidak pernah masuk zona abu di margin mana pun.

**Rekomendasi final: margin 8%**, diterapkan **hanya pada klausa dengan
`hunt_reason == below_theta`**. Ini menangkap G02/G04/G05 tanpa menyentuh
G07 (unknown_tool) maupun kasus MATCHED di atas θ₀. Jika setelah
implementasi ada kategori v2 turun atau gerbang gagal → BERHENTI dan lapor.

## 4. G07 — diagnosis terpisah (unknown_tool, bukan below_theta)

G07 `make a chart with examples in markdown`, skor 6.86,
`hunt_reason = unknown_tool` — BUKAN `below_theta`. Akar masalahnya: token
`examples` (kata Inggris umum) tidak ada di `known_vocab`, sehingga
unknown-tool detector mengira itu tool baru. Ini **bukan** masalah θ₀ dan
**bukan** zona abu.

Usulan perbaikan umum (masih desain, butuh persetujuan): perluas `known_vocab`
dengan wordlist Inggris umum (ini juga salah satu butir Fase 3), sehingga
`examples`, `markdown`, dll. tidak dianggap tool tak dikenal. Lakukan sebagai
perubahan terpisah dari zona abu, dan ukur dampaknya ke K/G serta regresi.

## 5. Kontrak yang tidak berubah

- θ₀ = 7.4688 (tidak diubah, tidak dikalibrasi ulang).
- Probe kalibrasi, deskripsi skill, ekspektasi v2: tidak disetel.
- Status MATCHED di atas θ₀: identik.
- `hunt_reason` tetap instrumentasi murni (tidak dipakai untuk mengubah
  status, hanya diagnostik).
- Jika implementasi nanti menurunkan satu kategori v2 atau menggagalkan
  gerbang: BERHENTI dan lapor (sesuai aturan keras).
