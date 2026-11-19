"""auto_skill_selector — benchmark_runner.py (Fase 2, Master Prompt §5).

Menjalankan tests/benchmark_35_labeled.json terhadap mesin Rust via model
terlatih, menghitung 7 Gerbang Kelulusan, dan menulis scorecard.json.

Gerbang:
  1. L2 Weight Normalization: semua kelas L2 = 100.0 ± 0.01 pasca-pruning.
  2. Domain Parity & Skew Resilience: parity >= 0.92 & CV <= 0.08 pada korpus
     inti 54; tetap >= 0.90 saat uji stres +10 skill ke 1 kategori.
  3. Benchmark 35: akurasi >= 97% (>=34/35) DAN 100% kasus negasi #1-#6.
  4. Zero Conversational FP: 0/5 kasus obrolan menghasilkan skill.
  5. Latensi: p50 < 200 µs, p99 < 500 µs (warmup + reps, seluruh pipeline).
  6. Live Hermes Hook: diisi oleh tests/test_gateway_live.py (invoke_hook +
     plugins validate/doctor) — runner membaca hasilnya bila ada.
  7. Git & Production Hygiene: diisi oleh skrip verifikasi akhir.

Semua angka dihitung dari eksekusi nyata; tidak ada nilai hardcoded.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
BENCH_PATH = _HERE / "tests" / "benchmark_35_labeled.json"

# Payload 500 kata untuk kasus #29 (teks rapat netral, bukan jargon domain).
_PAYLOAD_WORDS = (
    "rapat membahas progres proyek dan anggaran operasional bulan ini serta "
    "rencana kerja tim untuk kuartal berikutnya termasuk evaluasi vendor "
    "dan jadwal pelatihan karyawan baru di kantor pusat "
).split()
PAYLOAD_500 = " ".join((_PAYLOAD_WORDS * 40)[:500])


def load_cases() -> list[dict]:
    cases = json.loads(BENCH_PATH.read_text("utf-8"))
    for c in cases:
        if "__PAYLOAD_500__" in c["prompt"]:
            c["prompt"] = c["prompt"].replace("__PAYLOAD_500__", PAYLOAD_500)
    return cases


def check_case(case: dict, result: dict) -> tuple[bool, list[str]]:
    """Return (pass, reasons). Semua syarat kasus harus terpenuhi."""
    reasons: list[str] = []
    status = result.get("status", "")
    skills = result.get("skills", []) or []
    banned = set(result.get("global_banned_set", []) or [])
    probs = result.get("probabilities", {}) or {}
    clauses = result.get("clauses", []) or []
    hunts = result.get("hunt_clauses", []) or []

    if status != case["expect_status"]:
        reasons.append(f"status {status} != {case['expect_status']}")
    exp_skills = case.get("expect_skills", [])
    any_of = case.get("expect_any_of", [])
    if exp_skills and not any_of:
        if case["expect_status"] == "MATCHED_MULTI":
            # Semua skill target harus muncul, urutan step terjaga.
            missing = [s for s in exp_skills if s not in skills]
            if missing:
                reasons.append(f"missing skills {missing} (got {skills})")
            else:
                idxs = [skills.index(s) for s in exp_skills]
                if idxs != sorted(idxs):
                    reasons.append(f"order wrong: {skills}")
        elif case["expect_status"] in ("MATCHED_SINGLE", "MATCHED_PARTIAL_AND_HUNT"):
            if case.get("expect_all"):
                missing = [s for s in exp_skills if s not in skills]
                if missing:
                    reasons.append(f"missing skills {missing} (got {skills})")
            elif not any(s in skills for s in exp_skills):
                reasons.append(f"none of {exp_skills} in {skills}")
    # expect_any_of: tiap grup minimal satu skill harus muncul (dedup/alternatif sah).
    for group in case.get("expect_any_of", []):
        if not any(s in skills for s in group):
            reasons.append(f"none of group {group} in {skills}")
    for fb in case.get("forbid_skills", []):
        if fb in skills or fb in probs:
            reasons.append(f"forbidden skill {fb} present")
    for b in case.get("expect_banned_contains", []):
        if b not in banned:
            reasons.append(f"ban set missing {b} (got {sorted(banned)})")
    if case.get("expect_clause_count") is not None:
        if len(clauses) != case["expect_clause_count"]:
            reasons.append(f"clauses {len(clauses)} != {case['expect_clause_count']}")
    if case.get("expect_hunt") and not hunts:
        reasons.append("expected hunt_clauses non-empty")
    if case["expect_status"] in ("NO_SKILL_NEEDED", "CLARIFY_AMBIGUOUS") and skills:
        reasons.append(f"skills must be empty, got {skills}")
    return (not reasons), reasons


def measure_latency(brain, cases: list[dict], reps: int = 40) -> dict:
    """Warmup + per-call timing (bukan rata-rata batch) agar p99 jujur.

    Setiap pemanggilan analyze_prompt diukur individual; p50/p99 dihitung
    dari seluruh sampel individual lintas 35 kasus (termasuk pipeline
    negasi + split + 4 mode + payload raksasa).
    """
    samples: list[float] = []
    per_case: dict[int, float] = {}
    for c in cases:
        p = c["prompt"]
        for _ in range(8):
            brain.analyze_prompt(p)
        case_samples: list[float] = []
        for _ in range(reps):
            t0 = time.perf_counter()
            brain.analyze_prompt(p)
            dt = (time.perf_counter() - t0) * 1e6
            case_samples.append(dt)
        per_case[c["id"]] = statistics.median(case_samples)
        samples.extend(case_samples)
    samples.sort()
    p50 = statistics.median(samples)
    p99 = samples[min(len(samples) - 1, int(len(samples) * 0.99))]
    return {"p50": p50, "p99": p99, "avg": sum(samples) / len(samples),
            "per_case_us": {k: round(v, 1) for k, v in per_case.items()}}


def gate1_l2(model: dict) -> dict:
    norms = []
    for c in model.get("classes", []):
        fw = c.get("feature_weights", {})
        norms.append(math.sqrt(sum(v * v for v in fw.values())))
    if not norms:
        return {"pass": False, "max_deviation": None}
    dev = max(abs(n - 100.0) for n in norms)
    return {"pass": dev <= 0.01, "max_deviation": round(dev, 6),
            "min": round(min(norms), 4), "max": round(max(norms), 4)}


def gate2_parity(model: dict, brain, trainer_mod) -> dict:
    """Parity korpus inti + uji stres +10 skill ke 1 kategori tunggal.

    Uji stres meniru pipeline retrain nyata: 10 skill BERAGAM (bukan klon)
    masuk ke satu pilar, IDF stratified dihitung ulang (kontribusi 1/9 per
    pilar), lalu gain equalization dijalankan lagi seperti train_and_save.
    """
    import copy
    base = trainer_mod.measure_parity(model, brain)
    stressed = copy.deepcopy(model)
    target_cat = "software-devops"
    # 10 skill stres beragam: topik berbeda dalam SATU pilar, bobot L2=100.
    stress_topics = [
        ("stress-kafka-streams", "Kafka streams event processing pipeline, message broker, topic partition consumer lag."),
        ("stress-terraform-iac", "Terraform infrastructure as code modules, state backend, plan apply destroy cloud resources."),
        ("stress-grafana-observability", "Grafana observability dashboards, Prometheus metrics alerting, tracing logs correlation."),
        ("stress-redis-caching", "Redis caching layer design, eviction policy, TTL, cache invalidation patterns."),
        ("stress-nginx-loadbalancer", "Nginx load balancer reverse proxy configuration, upstream health checks, TLS termination."),
        ("stress-github-actions", "GitHub Actions CI workflows, matrix builds, caching dependencies, release automation."),
        ("stress-postgres-tuning", "Postgres performance tuning, vacuum analyze, index bloat, connection pooling pgbouncer."),
        ("stress-vault-secrets", "HashiCorp Vault secrets management, dynamic credentials, rotation policies, audit devices."),
        ("stress-argocd-gitops", "ArgoCD GitOps continuous delivery, app of apps, sync waves, rollback strategies."),
        ("stress-opentelemetry", "OpenTelemetry instrumentation, spans traces metrics export, collector pipelines sampling."),
    ]
    for slug, desc in stress_topics:
        rec = {"name": slug, "_slug": slug, "description": desc,
               "body": f"# {slug}\n\n## When to Use\n\n{desc}\n\n## Procedure\n\nFollow best practices for {slug}.",
               "_meta": {}, "category": target_cat, "status": "probationary"}
        feats = trainer_mod.zone_weights(rec, {})
        if not feats:
            continue
        top = sorted(feats, key=lambda k: feats[k], reverse=True)[:trainer_mod.MAX_FEATURES_PER_CLASS]
        pruned = trainer_mod._l2_normalize({k: feats[k] for k in top}, 100.0)
        total = sum(pruned.values()) or 1.0
        stressed["classes"].append({
            "name": slug, "category": target_cat, "status": "probationary",
            "description": desc,
            "doc_len": round(math.sqrt(sum(v * v for v in pruned.values())), 4),
            "log_prior": round(math.log(1.0 / len(stressed["classes"])), 4),
            "default_log_prob": round(math.log(1.0 / (total + len(pruned) + 1.0)), 4),
            "core_keywords": [t for t in trainer_mod.tokenize(f"{slug} {desc}")
                              if t not in trainer_mod._STOPWORDS][:12],
            "ban_tags": [],
            "feature_weights": {k: round(v, 4) for k, v in pruned.items()},
            "feature_log_probs": {k: round(math.log((v + 1.0) / (total + len(pruned) + 1.0)), 4)
                                  for k, v in pruned.items()},
        })
    # Pipeline retrain nyata: IDF stratified ulang + equalization + kalibrasi.
    stressed = trainer_mod.rebuild_idf_and_centroids(stressed)
    brain_s = type(brain)()
    brain_s.reload(json.dumps(stressed, ensure_ascii=False))
    stressed = trainer_mod.apply_category_gain_equalization(stressed, brain_s)
    stress = trainer_mod.measure_parity(stressed, brain_s)
    ok = (base.get("domain_parity_score") is not None
          and base["domain_parity_score"] >= 0.92
          and base.get("category_cv") is not None and base["category_cv"] <= 0.08
          and stress.get("domain_parity_score") is not None
          and stress["domain_parity_score"] >= 0.90)
    return {"pass": ok, "base": base, "stress_plus_10": stress}


def run(verbose: bool = True) -> int:
    import trainer as t
    import corpus_core

    root = t.get_skills_root()
    # Korpus inti 54 (6/pilar) selalu ditanam; harvest tambahan bila diminta.
    planted = corpus_core.plant_core_corpus(root)
    if verbose:
        print(f"Korpus inti: {planted} file baru ditulis ke {root}")
    model = t.train_and_save(root)
    brain_mod = t._import_brain()
    brain = brain_mod.SkillBrain()
    brain.reload(json.dumps(model, ensure_ascii=False))

    cases = load_cases()
    results = []
    passed = 0
    cat_stats: dict[str, list[bool]] = {}
    for c in cases:
        r = brain.analyze_prompt(c["prompt"])
        ok, reasons = check_case(c, r)
        passed += int(ok)
        cat_stats.setdefault(c["category"], []).append(ok)
        results.append({"id": c["id"], "category": c["category"], "pass": ok,
                        "status": r.get("status"), "skills": r.get("skills"),
                        "banned": r.get("global_banned_set"),
                        "clauses": r.get("clauses"), "reasons": reasons})
        if verbose:
            flag = "PASS" if ok else "FAIL"
            print(f"[{flag}] #{c['id']:02d} {r.get('status'):24s} skills={r.get('skills')}")
            if not ok:
                for reason in reasons:
                    print(f"       - {reason}")

    neg_cases = [r for r in results if r["category"] == "negation_global"]
    neg_pass = sum(1 for r in neg_cases if r["pass"])
    conv_cases = [r for r in results if r["category"] == "conversational"]
    conv_fp = sum(1 for r in conv_cases if r["status"] != "NO_SKILL_NEEDED")

    lat = measure_latency(brain, cases)
    g1 = gate1_l2(model)
    g2 = gate2_parity(model, brain, t)
    g3 = {"pass": passed >= 34 and neg_pass == len(neg_cases),
          "accuracy": round(passed / len(cases), 4), "passed": passed,
          "total": len(cases), "negation_pass": f"{neg_pass}/{len(neg_cases)}"}
    g4 = {"pass": conv_fp == 0, "false_positive_rate_conversational": round(conv_fp / max(1, len(conv_cases)), 4)}
    g5 = {"pass": lat["p50"] < 200 and lat["p99"] < 500,
          "latency_p50_us": round(lat["p50"], 1), "latency_p99_us": round(lat["p99"], 1),
          "latency_avg_us": round(lat["avg"], 1),
          "per_case_us": lat["per_case_us"]}

    # Gerbang 6 & 7 diisi oleh verifikasi terpisah (gateway live + git hygiene).
    g6_path = _HERE / "tests" / "gateway_live_result.json"
    g6 = json.loads(g6_path.read_text("utf-8")) if g6_path.exists() else \
        {"pass": False, "note": "belum dijalankan: tests/test_gateway_live.py"}
    g7_path = _HERE / "tests" / "git_hygiene_result.json"
    g7 = json.loads(g7_path.read_text("utf-8")) if g7_path.exists() else \
        {"pass": False, "note": "belum diverifikasi"}

    scorecard = {
        "fase": 2,
        "corpus": {"skills_indexed": len(model["classes"]),
                   "pillar_counts": model.get("pillar_counts", {})},
        "gates": {
            "1_l2_normalization": g1,
            "2_domain_parity_skew": g2,
            "3_benchmark_35": g3,
            "4_zero_conversational_fp": g4,
            "5_latency_sub_ms": g5,
            "6_live_hermes_hook": g6,
            "7_git_production_hygiene": g7,
        },
        "all_gates_pass": all(g["pass"] for g in (g1, g2, g3, g4, g5, g6, g7)),
        "category_results": {k: {"passed": sum(v), "total": len(v)} for k, v in cat_stats.items()},
        "cases": results,
        "calibration": model.get("calibration", {}),
    }
    (_HERE / "scorecard.json").write_text(json.dumps(scorecard, ensure_ascii=False, indent=2), "utf-8")
    if verbose:
        print("-" * 72)
        for name, g in scorecard["gates"].items():
            print(f"{'PASS' if g['pass'] else 'FAIL'}  {name}")
        print(f"Benchmark: {passed}/{len(cases)} | negasi {neg_pass}/{len(neg_cases)} | "
              f"FP conv {conv_fp}/{len(conv_cases)} | p50 {lat['p50']:.1f}µs p99 {lat['p99']:.1f}µs")
        print("scorecard.json ditulis")
    return 0 if scorecard["all_gates_pass"] else 1


if __name__ == "__main__":
    sys.exit(run(verbose=True))