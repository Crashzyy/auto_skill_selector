# Pembekuan Held-out Bersih v5 — Fase 3c

- File: `tests/heldout_v5.json`
- Jumlah kasus: **40**
- Dibuat: **sebelum** kode P2a dan **sebelum** probe engine (ekspektasi
  ditulis dari penalaran desain, bukan dari hasil RUN).
- Duplikat dengan v2 + b35 + v3 + v4: **0** (diverifikasi skrip normalisasi
  lowercase + strip).
- Expect ganda SINGLE/MULTI: **0**.
- Cakupan: OOD kapital (W19–W22), noise pola baru leet/ulang/redup
  (W26–W29), polisemi (W23–W25), typo nama skill + negasi (W30–W33),
  chitchat (W34–W36), kontrol skill-benar (W11–W18, W37–W40),
  pengetahuan umum untuk wordlist offline (W01–W10).

## Hash

```
SHA256(tests/heldout_v5.json) = a85a21a37167665c7b283a29fa9b4ae06e4a6a9eede299fa0e76998edd856140
```

Hash ini diverifikasi sebelum baseline (Langkah 2) dan sebelum evaluasi
pasca-P2a (Langkah 4). File v5 **tidak boleh diedit** setelah pembekuan.
v4 adalah **dev set** (kegagalannya dipakai merancang P2), bukan held-out;
ekspektasi v4 juga tidak diedit (termasuk V27).

## Catatan ekspektasi sengaja

- W01–W10 (pengetahuan umum: dijkstra, entropy, meteorologi, dll.) diberi
  `HUNT_NEW_SKILL`. Ini **sengaja menantang** P2a: jika wordlist kata umum
  terlalu agresif, HUNT yang sah ini bisa tertekan jadi NO_SKILL. Jika itu
  terjadi, itu PASS→FAIL di v5 → STOP otomatis.
- W31 (`jangan pakai exel`) memakai `exel` yang merupakan canon fuzzy — harus
  tetap ter-ban, tidak boleh terveto wordlist (pengecualian nama/canon).
- W32 (`tanpa wrod`) memakai `wrod` canon fuzzy — harus tetap no-ban.
- W30 (`powpoint`) typo nama skill — expect banned `powerpoint`, tetapi ini
  sudah diketahui gagal di v4/V27; sengaja dipertahankan sebagai pengingat
  bahwa P2a tidak boleh memperbaiki dengan menyetel v4.

## Status

- Dibekukan di commit ini (sebelum kode P2a).
- Baseline dijalankan sekali di 9e30de9 → `docs/HELDOUT_V5_BASELINE.txt`.
