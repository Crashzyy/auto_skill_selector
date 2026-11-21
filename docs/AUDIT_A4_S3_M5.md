# AUDIT A4 — S-3 (`note_skill_used`) & M-5 (overhead `_ensure_brain`)

## S-3 — Putusan: HAPUS panggilan `note_skill_used`

**Bukti:**
- Hook memanggil `brain.note_skill_used(s)` di 2 tempat (`__init__.py:338,350`,
  setelah patch: blok MATCHED_PARTIAL_AND_HUNT & MATCHED_SINGLE/MULTI).
- `SkillBrain` Fase 2 **tidak memiliki** metode itu (`src/lib.rs` pymethods:
  `reload`, `analyze_prompt`, `analyze_status`, `debug_*` saja). `git show
  41355ca:src/lib.rs` menunjukkan Fase 1 punya `note_skill_used` +
  `recent_skills: RwLock<HashSet>` + `SESSION_MOMENTUM = 0.45`; semuanya
  **sengaja dihapus** di Fase 2 (`analyze_prompt` kini hanya `(prompt)`).
- Jadi loop lama menelan `AttributeError` setiap giliran = dead code, dan
  memulihkannya akan **mengubah perilaku routing** (momentum sesi), yang
  dilarang pada fase verifikasi tanpa ubah engine/perilaku.

**Putusan:** hapus kedua loop `try: brain.note_skill_used(s) except: pass`.
Tidak ada fitur yang hilang (momentum sudah tidak ada sejak Fase 2). Tidak
ada perubahan skor/kontrak. Telah diterapkan di `__init__.py` + commit.

## M-5 — Overhead `_ensure_brain` per giliran (terukur)

Metode: 300 iterasi `hook._ensure_brain()` dengan `HERMES_HOME=/tmp/hermes-sandbox`,
modul di-import sekali (cache `_brain`), model JSON 2,121,095 byte.

| Komponen | p50 | p99 |
|---|---|---|
| `_ensure_brain()` penuh | **32.98 ms** | 44.41 ms |
| `_load_model_json()` | 0.66 ms | — |
| `SkillBrain()` construct | 2.09 ms | — |
| `brain.reload(js)` | 17.28 ms | — |

Sisa ±13 ms adalah parsing ~2.1 MB model JSON di dalam PyO3 `reload` (dict →
struktur Rust). Angka ini adalah **overhead hook per giliran**, bukan latensi
`analyze_prompt()` (sub-milidetik, lihat A2/A3: p50 42.8 µs). `import` modul
di-cache (`_brain` global), jadi tidak dihitung ulang tiap giliran.

Catatan jujur: ~33 ms/giliran bukan nol, dan seluruhnya berulang karena
`_ensure_brain()` membuat `SkillBrain()` baru + `reload` penuh tiap giliran.
Peluang optimasi (mis. cache brain singleton / reload hanya saat model berubah)
**sengaja tidak dikerjakan** di fase ini karena menyentuh perilaku hook;
dicatat untuk Fase 3 bila disetujui.

## Verifikasi setelah patch

- `pre_llm_call` tidak memanggil metode nonexistent lagi (grep: 0 referensi
  `note_skill_used` di `__init__.py` dan `src/lib.rs`).
- v2 / regresi / latensi tidak berubah (hook-only, engine tidak disentuh):
  v2 149/167, regresi 35/35.
