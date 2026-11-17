# Kontrak API Hermes yang TERVERIFIKASI dari source lokal

Sumber: `/data/home/.hermes/hermes-agent/` (checkout git Hermes Agent).
Semua yang tertulis di sini sudah dibaca langsung dari kode, BUKAN tebakan.

## 1. plugin.yaml (manifest)
Dari `plugins/google_meet/plugin.yaml`:
```yaml
name: google_meet
version: 0.2.0
description: "..."
author: NousResearch
kind: standalone
platforms: [linux, macos]
provides_tools: [meet_join, ...]
provides_hooks: [on_session_end]
```
Field: `name`, `version`, `description`, `author`, `kind`, `platforms`,
`provides_tools`, `provides_hooks`. Gunakan skema ini.

## 2. `plugin_data_dir` (storage tahan `plugins update`)
`plugins/plugin_storage.py`:
```python
from plugins.plugin_storage import plugin_data_dir
root = plugin_data_dir("auto_skill_selector")  # -> <hermes_home>/plugin-data/auto_skill_selector/
# root.mkdir(parents=True, exist_ok=True) sudah dilakukan di dalamnya
```
Validasi nama: `^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$`, tanpa `..`.

## 3. `hermes_yaml` ADA di root repo
`hermes_yaml.py` -> `from hermes_yaml import safe_load`. (tetap sediakan fallback regex)

## 4. Hook `pre_llm_call` — return contract
Dari `agent/turn_context.py::_collect_pre_llm_call_context`:
- kwargs yang dikirim Hermes: `session_id, task_id, turn_id, user_message,
  conversation_history, is_first_turn, model, platform, parent_session_id, sender_id`
- return `{"context": "..."} ` -> diinjeksi ke pesan user (BUKAN system prompt)
- return `{"action":"block","message":"..."}` -> veto giliran (jangan dipakai di sini)
- return `None` / `""` -> tanpa injeksi
- Context oversized di-spill ke disk otomatis oleh Hermes.

## 5. ctx API di `register(ctx)`
- `ctx.register_hook(name, callback, *, hold_stream=False)`  (`hermes_cli/plugins_context.py:741`)
- `ctx.register_command(name, handler, description="", args_hint="")`  (`plugins_context.py:456`)
- `ctx.register_cli_command(...)`  (`plugins_context.py:442`) — untuk CLI `hermes`
- `ctx.register_tool(name, toolset, schema, handler, ...)`  (dipakai google_meet)
- Spec memakai `ctx.register_command(...)` -> VALID (ada di plugins_context).

## 6. Hooks yang kita pakai ADA
`on_skill_lifecycle`, `subagent_stop`, `pre_llm_call` terdaftar di
`hermes_cli/plugins.py` allowlist (baris 138-139). Terkonfirmasi.

## 7. `skill_manage` tool ADA
Dipakai di `acp_adapter/tools.py`. Signature: `skill_manage(action="create", name=..., category=..., content=...)`.

## 8. TIDAK ADA contoh plugin Rust/PyO3 bawaan
`find plugins -name Cargo.toml` -> kosong. Jadi kita PIONIR; PyO3 harus
dikonfigurasi hati-hati (maturin + abi3).

## 9. `skill_manage` menulis ke `~/.hermes/skills/<category>/<name>/SKILL.md`
(dikonfirmasi lewat docs & acp tools) — trainer memindai pola ini.
