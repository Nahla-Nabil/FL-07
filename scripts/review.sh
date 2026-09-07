#!/usr/bin/env bash
# Run one review agent against one diff, headlessly.
#
# Usage:
#   scripts/review.sh <diff-file> [agent-name]
#
# Decision (logged in build-log.md): the diff is piped into Claude Code as context (via the
# prompt string), not pasted by hand each run. CONVENTIONS.md is NOT inlined here — the agent
# reads it live with its own Read tool every run, which is the one "live tool" requirement for
# the MVP slice and guarantees the agent can never be fed a stale/edited copy of the rules.
set -euo pipefail

DIFF_FILE="$1"
AGENT="${2:-convention-reviewer}"

if [ ! -f "$DIFF_FILE" ]; then
  echo "ERROR: diff file not found: $DIFF_FILE" >&2
  exit 1
fi

DIFF_CONTENT="$(cat "$DIFF_FILE")"

if [ -z "$DIFF_CONTENT" ]; then
  echo "ERROR: $DIFF_FILE is empty — nothing to review. Refusing to fabricate a report." >&2
  exit 1
fi

PROMPT="Review the following diff against this repository's CONVENTIONS.md. Read CONVENTIONS.md in full with your Read tool before judging anything, then produce the report in the exact format your instructions describe.

--- BEGIN DIFF ($DIFF_FILE) ---
$DIFF_CONTENT
--- END DIFF ---"

# --allowedTools is belt-and-suspenders on top of the agent's own frontmatter tools: list —
# both layers deny Edit/Write/Bash so there is no write/commit/push path even by accident.
claude -p --agent "$AGENT" --allowedTools "Read Grep Glob" "$PROMPT"
