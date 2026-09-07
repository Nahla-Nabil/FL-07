# Build Log — FL-07 Code Review Agent

Raw, timestamped, written as I go. Not cleaned up afterward.

---

### 2026-09-08 01:04 — Start

Starting FL-07, MVP scope: Convention Agent only, flat file, no manager, no RAG yet.

Repo state at kickoff: `Build_Agent_FlyRank/` was completely empty — no git repo, no
CONVENTIONS.md, no A4 branch, no FL-06 eval case files. Two decisions made with the user
before touching anything (asked because they change the deliverable, not something I should
guess):

1. **Implementation substrate**: Claude Code subagent(s) under `.claude/agents/*.md`, invoked
   headlessly via `claude -p --agent <name>`, with `tools:` restricted to `Read`/`Grep`/`Glob`.
   Rejected a raw Python+Anthropic-API script and a Node+Agent-SDK script for MVP — both would
   need me to hand-roll the "no write access" guarantee in code/prompt, whereas restricting the
   subagent's tool list in frontmatter is enforced by the harness itself. That directly satisfies
   the later guardrail checklist item ("no write/commit/push capability, not just an instruction").
   Verified `claude --version` (2.1.247) and confirmed `--agent`, `--allowedTools` exist before
   committing to this.
2. **Fixtures**: no real A4 branch exists in this folder, so generating a small synthetic Python
   "codebase" + CONVENTIONS.md + eval-case diffs from scratch here, rather than pointing at another
   repo. Documenting this since it's a deviation from "use a real diff from your A4 branch."

Plan for the next hour: git init a tiny sample Python app, write CONVENTIONS.md (8 entries,
Python-focused, no padding), commit a clean baseline, then branch-per-eval-case to produce real
`git diff` output for cases 1/2/3/4/5 (skipping case 6 — retrieval — until/unless Milestone 4 is
reached, and case 7 until Milestone 3's manager exists).
