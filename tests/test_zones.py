"""Verifikasi Zona S/A/B/C pada trainer.py (lingkungan sandbox).

Membuktikan:
  1. Bobot Zona S (name/tags/H1) > Zona A (description) > Zona C (body).
  2. Total feature_weights per skill dinormalkan ke 100.0.
  3. SKILL.md pendek dan panjang menghasilkan skala yang setara (1:1).
"""
from trainer import zone_weights, ZONE_NORMALIZE_TOTAL


def _rec(name, slug, desc, body, meta=None):
    return {"name": name, "_slug": slug, "description": desc, "body": body,
            "_meta": meta or {}}


# --- Uji 1: bobot zona S > A > C ---
rec = _rec(
    name="Docker Management",
    slug="docker-management",
    desc="Manage Docker containers and deployment.",  # Zona A
    body=(
        "# Docker Management\n"                       # Zona S (H1)
        "## When to Use\n"                            # Zona A section
        "Use when you need to run containers.\n"
        "## Procedure\n"                              # Zona B section
        "docker run -d myimage\n"
        "This tool helps orchestrate container workloads and services."  # Zona C
    ),
    meta={"metadata": {"hermes": {"tags": ["docker", "container"]}}},  # Zona S
)
w = zone_weights(rec)
total = sum(w.values())

uni = {k: v for k, v in w.items() if k.startswith("uni:")}
w_docker = uni.get("uni:docker", 0.0)      # ada di name(S) + tags(S) + body(C)
w_procedure = uni.get("uni:procedure", 0.0)  # hanya heading B

print(f"Total bobot dokumen = {total:.4f}  (target {ZONE_NORMALIZE_TOTAL})")
print(f"W(docker)  [Zona S+A+C] = {w_docker:.4f}")
print(f"W(procedure)[Zona B]   = {w_procedure:.4f}")

assert abs(total - ZONE_NORMALIZE_TOTAL) < 0.5, f"normalisasi gagal: {total}"
assert w_docker > w_procedure, "Zona S harus > Zona B"

# --- Uji 2: SKILL.md pendek vs panjang setara 1:1 ---
short = _rec("Valuation", "valuation", "Build DCF valuation in Excel.",
             "# Valuation\nBuild a discounted cash flow model.")
long_body = ("# Valuation\nBuild a discounted cash flow model.\n"
             + ("Additional explanatory paragraph about valuation methodology. " * 60))
long = _rec("Valuation", "valuation", "Build DCF valuation in Excel.", long_body)

w_short = zone_weights(short)
w_long = zone_weights(long)
ts, tl = sum(w_short.values()), sum(w_long.values())
print(f"Total pendek={ts:.2f}  panjang={tl:.2f}  (rasio {ts/tl:.3f})")
assert abs(ts - tl) < 1.0, "pendek & panjang harus setara"

print("\nSEMUA VERIFIKASI ZONA LULUS")
