#!/usr/bin/env python3
"""Fuzz + metamorphic + stress test untuk auto_skill_selector (Fase 2).

BELUM DIJALANKAN: dibuat tanpa akses ke binary/sandbox. Sesuaikan make_brain()
dengan cara _ensure_brain() di __init__.py membuat SkillBrain, lalu jalankan:

    HERMES_HOME=/tmp/hermes-sandbox python fuzz_metamorphic.py

Prinsip: panic="abort" di Rust berarti satu prompt jahat bisa mematikan SELURUH
proses gateway. Karena itu kasus stress dijalankan di SUBPROCESS: returncode
negatif/!=0 = proses mati = temuan kritis.
"""
import json, os, random, subprocess, sys, time

PLUGIN_DIR = os.environ.get("PLUGIN_DIR", "/tmp/hermes-sandbox/plugins/auto_skill_selector")
MODEL = os.path.join(os.environ.get("HERMES_HOME", "/tmp/hermes-sandbox"),
                     "plugin-data/auto_skill_selector/skill_model.json")
SCEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_scenarios_v2.json")
STATUSES = {"NO_SKILL_NEEDED", "MATCHED_SINGLE", "MATCHED_MULTI",
            "MATCHED_PARTIAL_AND_HUNT", "HUNT_NEW_SKILL", "CLARIFY_AMBIGUOUS"}


def _load_brain_module():
    """Samakan dengan __init__.py::_import_brain(): coba import modul dulu,
    lalu fallback memuat .so di PLUGIN_DIR lewat importlib (nama modul harus
    persis 'hermes_skill_brain' agar init PyO3 cocok)."""
    sys.path.insert(0, PLUGIN_DIR)
    try:
        import hermes_skill_brain as h
        return h
    except ImportError:
        pass
    import glob
    import importlib.util
    for so in glob.glob(os.path.join(PLUGIN_DIR, "*.so")) + glob.glob(os.path.join(PLUGIN_DIR, "*.pyd")):
        spec = importlib.util.spec_from_file_location("hermes_skill_brain", so)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise ImportError(f"hermes_skill_brain tidak ditemukan di {PLUGIN_DIR}")


def _ensure_brain():
    """Cermin __init__.py::_ensure_brain(): SkillBrain() + reload(model json)."""
    h = _load_brain_module()
    brain = h.SkillBrain()
    with open(MODEL, encoding="utf-8") as f:
        brain.reload(f.read())
    return brain


CHILD = r'''
import sys, json, os, glob, importlib.util
PLUGIN_DIR, MODEL = %r, %r
sys.path.insert(0, PLUGIN_DIR)
try:
    import hermes_skill_brain as h
except ImportError:
    h = None
    for so in glob.glob(os.path.join(PLUGIN_DIR, "*.so")):
        spec = importlib.util.spec_from_file_location("hermes_skill_brain", so)
        if spec and spec.loader:
            h = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(h)
            break
    if h is None:
        raise ImportError("hermes_skill_brain not found")
b = h.SkillBrain()          # sama dengan __init__.py::_ensure_brain
b.reload(open(MODEL, encoding="utf-8").read())
p = json.loads(sys.stdin.read())
sys.stdout.write(json.dumps(b.analyze_prompt(p), default=str))
''' % (PLUGIN_DIR, MODEL)


def run_isolated(prompt, timeout=10):
    """Return (ok, result_or_error, seconds). ok=False & 'CRASH' bila proses mati."""
    t = time.perf_counter()
    try:
        r = subprocess.run([sys.executable, "-c", CHILD], input=json.dumps(prompt, ensure_ascii=True),
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", time.perf_counter() - t
    dt = time.perf_counter() - t
    if r.returncode != 0:
        return False, f"CRASH rc={r.returncode} {r.stderr[-200:]}", dt
    return True, json.loads(r.stdout), dt


# ---------- 1) Stress / panic-safety (kandidat risiko panic=abort) ----------
def stress_cases():
    c = {}
    c["repeat_dan_20000"] = "ambil data " + "dan " * 20000 + "buat grafik"
    c["repeat_jangan_pakai_2000"] = "jangan pakai x " * 2000 + "buat grafik"
    c["commas_100k"] = "buat grafik" + "," * 100000
    c["one_token_1MB"] = "a" * 1_000_000
    c["nul_bytes"] = "buat\x00grafik\x00penjualan"
    c["turkish_dotted_I"] = "\u0130stanbul " * 100 + "buat grafik penjualan jangan pakai excel"
    c["german_sharp_s"] = "\u1e9e\u00df " * 200 + "ringkas pdf ini"
    c["combining_zalgo"] = "buat gra" + "\u0301\u0302\u0303" * 200 + "fik penjualan"
    c["emoji_zwj"] = "\U0001F468\u200D\U0001F469\u200D\U0001F467 " * 200 + "buat grafik"
    c["rtl_mixed"] = "\u202eبناء رسم بياني\u202c buat grafik penjualan"
    c["lone_surrogate"] = "buat grafik \ud800 penjualan"   # JSON ascii-escape; di Python str valid
    # Batas zona instruksi: head=80 char, tail=320 char, ambang 400 char.
    # Karakter multibyte (3-4 byte) tepat di batas -> uji slicing byte vs char.
    for ch, name in (("\u4e2d", "cjk3"), ("\U0001F600", "emoji4"), ("\u00e9", "latin2")):
        for n in (399, 400, 401):
            body = "buat grafik penjualan dari data ini "
            c[f"boundary_{name}_{n}"] = (body + ch * (n - len(body)))[:n]
        for off in (78, 79, 80, 81, 82):
            c[f"head80_{name}_{off}"] = ("x" * off) + ch + (" isi " * 90) + "ringkas jadi slide"
        for off in (318, 319, 320, 321, 322):
            c[f"tail320_{name}_{off}"] = ("data " * 120) + ("x" * (off - 20)) + ch + " buat grafik dari data di atas"
    return c


# Per putusan owner Fase 0: raw-Rust analyze_prompt pada lone surrogate
# diharapkan menaikkan UnicodeEncodeError (bukan panic / hang). Skenario ini
# adalah regression marker, bukan kegagalan — jangan dihitung sebagai BAD.
EXPECTED_FAIL = {"lone_surrogate"}

def run_stress():
    bad = 0
    for name, p in stress_cases().items():
        ok, res, dt = run_isolated(p)
        if name in EXPECTED_FAIL:
            flag = "OK*"  # expected non-zero exit, bukan crash tak terduga
            print(f"[stress] {flag} {name:34s} {dt*1000:8.1f} ms (diharapkan error)")
            continue
        flag = "OK " if ok and dt < 1.0 else "BAD"
        if flag == "BAD":
            bad += 1
        print(f"[stress] {flag} {name:34s} {dt*1000:8.1f} ms {'' if ok else res}")
    return bad


# ---------- 2) Invarian (harus selalu benar untuk semua prompt) ----------
def check_invariants(prompt, d):
    errs = []
    if d.get("status") not in STATUSES:
        errs.append(f"status tak dikenal {d.get('status')}")
    skills = list(d.get("skills") or [])
    banned = set(d.get("global_banned_set") or [])
    if d.get("status") in ("NO_SKILL_NEEDED", "CLARIFY_AMBIGUOUS") and skills:
        errs.append("status tanpa skill tapi skills tidak kosong")
    if len(d.get("clauses") or []) > 3:
        errs.append(">3 klausa")
    if banned & {s.lower() for s in skills}:
        errs.append("skill terlarang lolos ke hasil")
    if d.get("status") == "NO_SKILL_NEEDED" and d.get("hunt_clauses"):
        errs.append("NO_SKILL_NEEDED tapi ada hunt_clauses")
    return errs


# ---------- 3) Metamorfik: keputusan tidak boleh berubah ----------
POLITE = ["tolong ", "bisa tolong ", "mohon "]
TRANSFORMS = {
    "upper": lambda s: s.upper(),
    "lower": lambda s: s.lower(),
    "extra_ws": lambda s: s.replace(" ", "   "),
    "polite_prefix": lambda s: random.choice(POLITE) + s,
    "thanks_suffix": lambda s: s + " makasih ya",
    "emoji": lambda s: s + " \U0001F64F",
    "zero_width": lambda s: "\u200b".join(s[i:i+3] for i in range(0, len(s), 3)),
    "fullwidth": lambda s: "".join(chr(ord(c) + 0xFEE0) if "a" <= c <= "z" else c for c in s),
    "typo_1char": lambda s: _typo(s),
}
STRICT = {"upper", "lower", "extra_ws", "polite_prefix", "thanks_suffix", "emoji", "zero_width", "fullwidth"}


def _typo(s):
    ws = s.split(" ")
    idx = [i for i, w in enumerate(ws) if len(w) >= 5 and w.isalpha()]
    if not idx:
        return s
    i = random.choice(idx)
    w = ws[i]
    j = random.randrange(1, len(w) - 1)
    ws[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:] if j + 1 < len(w) - 1 else w[:j] + w[j + 1:]
    return " ".join(ws)


def run_metamorphic(cases, brain_call):
    ret = {k: [0, 0] for k in TRANSFORMS}
    for cs in cases:
        if cs.get("session") or "__PAYLOAD" in cs["prompt"]:
            continue
        base = brain_call(cs["prompt"])
        key0 = (base.get("status"), tuple(base.get("skills") or []))
        for name, fn in TRANSFORMS.items():
            random.seed(hash((cs["id"], name)) & 0xFFFF)
            d = brain_call(fn(cs["prompt"]))
            same = (d.get("status"), tuple(d.get("skills") or [])) == key0
            ret[name][0] += same
            ret[name][1] += 1
            if not same and name in STRICT:
                print(f"[meta] {name:13s} {cs['id']} {key0[0]} -> {d.get('status')}")
    for k, (a, b) in ret.items():
        print(f"[meta] retensi {k:14s} {a}/{b} = {a / max(b, 1):.1%}")


def _hook_normalize(text: str) -> str:
    """Cermin __init__.py::_normalize_unicode (Fase 1.3): buang Cf + NFKC.

    Runner/fuzz memakai ini agar mengukur jalur produksi (hook menormalkan
    SEBELUM Rust). Impor langsung dari plugin bila tersedia, fallback lokal.
    """
    try:
        sys.path.insert(0, PLUGIN_DIR)
        import importlib.util
        spec = importlib.util.spec_from_file_location("_ass_init", os.path.join(PLUGIN_DIR, "__init__.py"))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod._normalize_unicode(text)
    except Exception:
        pass
    import unicodedata
    if not text or text.isascii():
        return text
    return unicodedata.normalize("NFKC", "".join(c for c in text if unicodedata.category(c) != "Cf"))


def make_in_process_call():
    brain = _ensure_brain()
    def call(prompt):
        return brain.analyze_prompt(_hook_normalize(prompt))
    return call


def main():
    cases = json.load(open(SCEN, encoding="utf-8"))["cases"]
    print("== STRESS (subprocess, deteksi proses mati) ==")
    bad = run_stress()
    call = make_in_process_call()
    print("== INVARIAN + DETERMINISME ==")
    inv = 0
    for cs in cases:
        p = cs["prompt"].replace("__PAYLOAD_500__", ("kata data penjualan " * 170).strip())
        try:
            d1, d2 = call(p), call(p)
        except Exception as e:
            print(f"[inv] EXC {cs['id']}: {e}")
            inv += 1
            continue
        errs = check_invariants(p, d1)
        if d1.get("status") != d2.get("status") or d1.get("skills") != d2.get("skills"):
            errs.append("tidak deterministik")
        if errs:
            inv += 1
            print(f"[inv] {cs['id']}: {errs}")
    print("== METAMORFIK ==")
    run_metamorphic(cases, call)
    print(f"\nRINGKASAN: stress_bad={bad} invarian_gagal={inv}")
    sys.exit(1 if bad or inv else 0)


if __name__ == "__main__":
    main()
