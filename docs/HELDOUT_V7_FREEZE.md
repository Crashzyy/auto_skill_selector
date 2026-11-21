# Held-out v7 — FREEZE (Fase 3g)

- File: `tests/heldout_v7.json`
- Jumlah: **30 kasus** (Y01–Y30)
- **SHA256: `b411991d705321f8a53e5b8e83228f78fd503bf107117da854402a0801905666`**
- Dibekukan sebelum probe engine dan sebelum kode P-FMT.
- 0 duplikat terhadap 361 prompt unik dari v2/b35/v3/v4/v5/v6 (cek skrip),
  0 duplikat internal, 0 expect ganda SINGLE/MULTI.
- Ekspektasi ditulis dari tata bahasa, bukan dari kegagalan v5/v6.

| Grup | N | ID | Prinsip |
|---|---|---|---|
| A | 8 | Y01–Y08 | cue ban + penanda format (`sebagai`, `dalam bentuk`, `sebagai`, `jadi`, `as`, `in`) + **nama skill lain** → skill itu harus match |
| B | 6 | Y09–Y14 | cue ban **tanpa** penanda format, sisa klausa elliptis → tetap tidak berubah |
| C | 12 | Y15–Y26 | kontrol skill-benar tanpa ban → `MATCHED_SINGLE` |
| D | 4 | Y27–Y30 | idiom bukan-ban (`jangan…dulu`, `jangan lupa`, `jangan sampai telat`, `bukan cuma…juga`) |

Status: v2–v6 = dev set; **v7 = held-out bersih**. Ekspektasi tidak boleh diedit.
