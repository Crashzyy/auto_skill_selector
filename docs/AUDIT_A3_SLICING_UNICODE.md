# AUDIT A3 — Slicing byte vs char di `src/lib.rs` + fuzz Unicode generatif

## 1. Audit semua situs slicing / indexing string

Saya enumerasi setiap operasi `&s[a..b]`, `bytes[i]`, `as_bytes()`, `char_indices()`
di `src/lib.rs` dan menilai apakah bisa memotong di tengah char UTF-8 (panic
dengan `panic = "abort"`).

| Baris | Kode | Penilaian |
|---|---|---|
| 374-386 | `contains_phrase_words`: `bytes[i..i+p.len()]`, `bytes[i-1]`, `bytes[after]` | **AMAN** — perbandingan/indexing byte, bukan slicing `&str` |
| 509-522 | `cleaned[i..i+n] == trig[..]`, `cleaned[i]` | **AMAN** — `cleaned` = `Vec<String>`, indexing elemen |
| 858,949,962 | `words_ref[i.....]`, `words_ref[i..=k]` | **AMAN** — `Vec<String>` |
| 987-991 | `spans[idx]`, `spans[idx+1]` | **AMAN** — indexing vec |
| 1019-1027 | `bytes[i].is_ascii_digit()`, `bytes[i-1].is_ascii_whitespace()` | **AMAN** — digit/whitespace ASCII; `bytes[i-1]` dijaga `i>0` |
| 1049 | `seg[dot..]`, `dot` dari `seg.find(char)` | **AMAN** — `find` mengembalikan char boundary |
| 1133-1134 | `l.as_bytes()[0]`, `[1]`, dijaga `l.len()>2` | **AMAN** — index 0/1 ASCII digit/`.`/`)` |
| **1139** | `l[2..]` untuk bullet `- `, `* `, `• `, `1)`, `1.` | **BUG → DIPERBAIKI** — `• ` = 3 byte; `l[2..]` memotong di tengah U+2022 → panic. Diubah ke `char_indices().nth(2)` |
| 1205 | `p[idx..]`, `p[last..abs]`, `p[right_start..]` | **AMAN** — `idx`/`abs` dari `.find()` = char boundary; `right_start = abs + needle.len()` (needle ASCII) |
| 1400 | `word[..word.len()-suf.len()]` | **AMAN** — `suf` ASCII & `ends_with(suf)` menjamin boundary |
| 1555-1587 | head/tail window `raw[tail_start..]`, `raw[head_end..tail_start]` | **AMAN** — eksplisit `is_char_boundary()` |
| 1646-1682 | `fuzzy_known_tool`: `s[..i]`, `s[i+1..]`, `v[i]=c`, `v.insert(i,c)` | **AMAN** — `if !tok.is_ascii() { return None; }` di entry |
| 1815-1816,2035,2493-2495 | `tokens[i]`, `scored[..k]`, `ct[i-1]` | **AMAN** — `Vec`/slice indexing |

**Temuan:** tepat SATU slicing tidak aman (baris 1139, bullet `• `). Sudah
diperbaiki dengan `char_indices().nth(2)` (skip 2 **char**, bukan 2 byte).
Catatan: ini adalah bug panic nyata yang sebelumnya belum terpicu karena 5000+
prompt fuzz tidak punya bullet `•` di awal baris sebelum perbaikan ini.

## 2. Fuzz Unicode acak generatif (>=5000 prompt, subprocess)

Ditambahkan ke `tests/test_stress_regression.py`, layer `--unicode-fuzz`
(default 5000, seed 20261120, deterministik):

- Pool: ASCII + homoglyph Cyrillic/Greek (`аеорсхАЕОРСХαβγορπ`), fullwidth
  (`ＡＢＣ１２３（）`), Cf/zero-width (`\u200b\u200d\u200e\ufeff`), combining marks
  (`\u0301\u0308`), CJK, Arab, emoji.
- Generator mencampur 5 bentuk: polos, `1. … 2. …`, `• …`, URL+`ringkas`,
  `jangan pakai …; buat …` — menyerang semua situs slicing di atas.
- Eksekusi **batch 100 prompt per subprocess** (50 child untuk 5000). Rust
  `panic=abort` → satu panic membunuh child → `rc<0` terdeteksi; failing batch
  di-isolasi per-prompt via `fz.run_isolated`.
- Invarian per prompt: status ∈ STATUSES, klausa ≤ 3.

Hasil eksekusi nyata:

```
[ufuzz] selesai: 5000 prompt, gagal=0
RINGKASAN: gagal=0 (fast=0, slow=0, unicode_fuzz=0)
```

Stress FAST (jalur produksi) dan SLOW (raw-Rust subprocess) juga tetap 0 gagal.

## 3. Regresi & latensi pasca-perbaikan

- v2: **149/167** (tidak berubah dari A2)
- regresi 35: **35/35**
- latensi: **p50 42.8µs, p99 244.1µs** (threshold <200 / <500; variasi noise mesin)

Tidak ada probe / θ₀ / deskripsi / ekspektasi yang disetel.
