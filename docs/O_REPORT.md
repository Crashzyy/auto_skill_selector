# Last lexicon experiment — closing report

## Outcome

The experiment failed the pre-registered success criterion and was not
committed. The scratch worktree was discarded. The lexicon path is now closed;
the engine is frozen.

## Commit rules

`docs/COMMIT_RULES.md` was written verbatim from the supplied appendix and a
machine-checkable lint was installed as a local `commit-msg` hook. Six bad
messages were rejected and six good messages were accepted. The hook refuses
the default `git revert` subject, so any future revert needs an explicit
compliant message. A history audit found 99 of 100 existing commits violate
the new rules. No history was rewritten.

## Reconciliation

The differential harness counted 20 unique case keys; the earlier
classification table had 24 rows because five IDs appeared in two sets.
The class totals (6 correct, 16 neutral, 2 wrong) sum to 24 rows, not 20.
The old report also said seven older false positives were reproducible;
with the pinned model only five of nineteen reproduce. The new fixture
contains five cases. These distinctions are now recorded in
`docs/N_RECONCILIATION.md`.

## Narrow taxonomy

`docs/LEX_TAXONOMY_V2.md`, sha
`cdc001f43ed9008ef84241fd274675b50cca93ba71e2c1dced2b84a953fd7f90`.
The old taxonomy actually had 122 tokens, not the previously claimed 72.
Rule (a) removed four generic tokens; rule (b) removed twelve tokens used in
more than one category; 106 tokens remain across 12 non-empty categories.
The generic-verb list was written after the prior failure, as disclosed.

## Experiment

Eighty-six aliases were added in a scratch worktree through the existing
`en_to_id` path, mapping to IDF keys already in the pinned model. No pin,
fixed weight, per-skill boost, token removal, retrain, or change to threshold,
margin, probes, descriptions, ban path, or Stage 0 bypass.

The differential harness found 14 unique case keys. Classification produced
13 correct and 4 neutral rows across 17 file-ID rows; no wrong-class delta.
Because five IDs occur in two files, the row and key counts differ. The two
previously blocking cases in FMT_GUARD are unchanged, and all other hard
gates pass: v2 156/167, b35 35/35, negation 6/6, guard 12/12, FMT_GUARD
10/10, FMT_ADV_GUARD 7/14, NEG_CONV 0/40, NEG_CONV2 4/5 (unchanged from
baseline), 7/7 gates. p99 medians were 245.2 µs for the candidate and
238.8 µs for the baseline, a 2.7% increase within the 10% budget.

## Evaluation

- Held-out v11: 25/36 → 27/36. Paraphrase subgroup stayed at **8/12**,
  so the required gain of at least three paraphrase cases was not met.
  Other gains came from controls, negatives, and typos.
- Held-out v10: 16/30 → 18/30, total only; no per-case details reported.
- Dev sets: v3 43/52, v4 29/38, v5 15/40, v6 28/41 → 30/41,
  v7 20/30 → 23/30, v8 15/30 → 17/30, v9 15/30 → 16/30.
  No dev-set regressions were observed.

## Self-correction

1. The differential harness necessarily prints changed cases from held-out
   sets before the formal evaluation step; only aggregate scores are reported
   here, but the procedural overlap with "do not open case details" is noted.
2. The earlier 72-token taxonomy count was wrong; the corrected count is 122
   tokens before filtering and 106 after.
3. I did not narrow the alias list after seeing results. No third iteration.
4. The model sha stayed `a6a14d6a…`; no expectation or set hash changed.

## Decision

Frozen engine. No merge to main. The remaining recall gap is a feature and
lexicon limitation that cannot be fixed with the current alias mechanism
without hurting guard behavior. Any further work requires a new mandate.
