"""Verifikasi Zona S/A/B/C pada trainer.py (Fase 2, lingkungan sandbox).

Membuktikan:
  1. Bobot Zona S (name/tags/H1) > Zona B (heading/prosedur).
  2. Total L1 feature_weights per skill dinormalkan ke 100.0 (pra-pruning).
  3. SKILL.md pendek dan panjang menghasilkan skala setara (1:1).
  4. Pasca-pruning top-80 + L2 normalize, norm L2 = 100.0 (gerbang 1).

Jalankan dari root repo:
  HERMES_HOME=/tmp/hermes-sandbox python tests/test_zones.py
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trainer import zone_weights, ZONE_NORMALIZE_TOTAL, _l2_normalize, MAX_FEATURES_PER_CLASS


def _rec(name, slug, desc, body, meta=None):
    return {"name": name, "_slug": slug, "description": desc, "body": body,
            "_meta": meta or {}}


# --- Uji 1: bobot zona S > B ---
rec = _rec(
    name="Docker Management",
    slug="docker-management",
    desc="Manage Docker containers and deployment.",
    body=(
        "# Docker Management\n"
        "## When to Use\n"
        "Use when you need to run containers.\n"
        "## Procedure\n"
        "docker run -d myimage\n"
        "This tool helps orchestrate container workloads and services."
    ),
    meta={"metadata": {"hermes": {"tags": ["docker", "container"]}}},
)
w = zone_weights(rec)
total = sum(w.values())
uni = {k: v for k, v in w.items() if k.startswith("uni:")}
w_docker = uni.get("uni:docker", 0.0)
w_procedure = uni.get("uni:procedure", 0.0)
print(f"Total bobot L1 dokumen = {total:.4f}  (target {ZONE_NORMALIZE_TOTAL})")
print(f"W(docker)  [Zona S+A+C] = {w_docker:.4f}")
print(f"W(procedure)[Zona B]   = {w_procedure:.4f}")
assert abs(total - ZONE_NORMALIZE_TOTAL) < 0.5, f"normalisasi L1 gagal: {total}"
assert w_docker > w_procedure, "Zona S harus > Zona B"

# --- Uji 2: SKILL.md pendek vs panjang setara 1:1 ---
short = _rec("Valuation", "valuation", "Build DCF valuation in Excel.",
             "# Valuation\nBuild a discounted cash flow model.")
long_body = ("# Valuation\nBuild a discounted cash flow model.\n"
             + ("Additional explanatory paragraph about valuation methodology. " * 60))
long = _rec("Valuation", "valuation", "Build DCF valuation in Excel.", long_body)
ts, tl = sum(zone_weights(short).values()), sum(zone_weights(long).values())
print(f"Total pendek={ts:.2f}  panjang={tl:.2f}  (rasio {ts/tl:.3f})")
assert abs(ts - tl) < 1.0, "pendek & panjang harus setara"

# --- Uji 3: pruning top-80 + L2 normalize = 100.0 (gerbang 1) ---
feats = zone_weights(long)
top = sorted(feats, key=lambda k: feats[k], reverse=True)[:MAX_FEATURES_PER_CLASS]
pruned = _l2_normalize({k: feats[k] for k in top}, ZONE_NORMALIZE_TOTAL)
l2 = math.sqrt(sum(v * v for v in pruned.values()))
print(f"L2 pasca-pruning = {l2:.4f}  (target 100.0 ± 0.01)")
assert abs(l2 - 100.0) <= 0.01, f"L2 norm gagal: {l2}"

print("\nSEMUA VERIFIKASI ZONA LULUS")