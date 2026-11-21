#!/usr/bin/env bash
# Commit message lint for docs/COMMIT_RULES.md. Usage: commit-msg-lint.sh <msgfile>
set -u
f="${1:?usage: commit-msg-lint.sh <msgfile>}"
msg=$(cat "$f")
subj=$(printf '%s\n' "$msg" | head -n1)
err=0
say() { printf 'commit-msg-lint: %s\n' "$1" >&2; err=1; }

[[ "$subj" =~ ^(feat|fix|perf|refactor|test|docs|build|chore|revert)(\([a-z]+\))?:[[:space:]]+.+ ]] \
  || say "subject must be 'type(scope): subject' with lowercase type"
(( ${#subj} <= 72 )) || say "subject exceeds hard limit 72 chars"
(( ${#subj} <= 60 )) || say "subject exceeds 60 chars"
[[ "$subj" != *"." ]] || say "subject must not end with a period"
[[ "$subj" =~ ^[[:lower:]] ]] || say "subject must start lowercase"

# Imperative: reject known past/3rd-person openers.
[[ "$subj" =~ :[[:space:]]+(added|adds|fixed|fixes|removed|removes|updated|updates|changed|changes|corrected|corrects|rewrote|reverts?[[:space:]]+the) ]] \
  && say "subject must use imperative verb"

# Forbidden process/metrics anywhere.
for w in Fase Langkah Phase "Step " "Stage " P1a "P2a'" P-FMT "D3" HO14 V06 W33 X26 \
          comprehensive robust enhance leverage seamless streamline ensure properly various significant critical overall refine address \
          "Co-Authored-By" "Generated with"; do
  [[ "$msg" == *"$w"* ]] && say "forbidden token: $w"
done
[[ "$msg" =~ [0-9]+/[0-9]+ ]] && say "metric-like number in message"
[[ "$msg" =~ p99 ]] && say "metric token in message"
[[ "$msg" =~ [→⇒] || "$msg" =~ — || "$msg" =~ ✨ || "$msg" =~ \! ]] && say "forbidden symbol in message"

# Process labels in body; in subject 'held-out set' is allowed (spec example).
body=$(printf '%s\n' "$msg" | tail -n +2)
for w in STOP gate baseline "dev set"; do
  [[ "$body" == *"$w"* ]] && say "forbidden process word in body: $w"
done
[[ "$subj" == *STOP* || "$subj" == *gate* || "$subj" == *baseline* || "$subj" == *"dev set"* ]] \
  && say "forbidden process word in subject"
[[ "$body" == *held-out* ]] && say "forbidden process word in body: held-out"

exit "$err"
