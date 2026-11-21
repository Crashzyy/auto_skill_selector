# Reconciliation of the previous lexicon experiment

## Delta count

The differential harness reported 20 changed cases. The classification table
later listed 24 rows. Both numbers are explainable, and the table was wrong
to present them as the same population.

- 20 unique `(file, id)` delta keys reported by the harness.
- 24 rows in the classification table, because five IDs occur in two files:
  F02 and F08 (v2 and FMT_GUARD), G04 (v2 and P2A_GUARD),
  V03 (v4 and v11), V17 (v4 and v11).
- Distinct case IDs: 19.

Population reconciliation: 24 rows = 19 distinct IDs + 5 repeated IDs in a
second set. The class totals (correct 6, neutral 16, wrong 2) sum to 24 rows.
The harness total of 20 is a different counting key and should not have been
compared with those class totals. No correction to the decision is implied:
the two wrong cases were both in FMT_GUARD and remain the blocking evidence.

## Reproducible false positives

Of the 19 previously reported conversational false positives, five reproduce
with the pinned model. The earlier report also mentioned seven cases already
present in older suites; those seven were not reproducible as false positives
under the pinned model and therefore were not added to the new fixture.
`docs/NEG_CONV2.json` contains five new topical-variant cases, not seven.
Its own hash and contents are authoritative; the earlier prose was not.

## Corrections applied

- The previous report was annotated to state the ceiling effect in the AUC
  calculation, that the dev-versus-main comparison is invalid, and that the
  v9 score is 15/30 rather than 15/40.
- This document records the counting-key distinction without rewriting
  history.
