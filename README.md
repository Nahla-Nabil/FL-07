# FL-07 Code Review Agent

FL-07 Code Review Agent, built for FlyRank's General AI Fluency track, based on the FL-06 spec: two read-only review subagents check small Python diffs in `sample_app/` against the 8 entries in `CONVENTIONS.md`, with a deterministic manager that merges their findings into one severity-ordered report.

## Architecture

- `scripts/manager.py` is a thin, **non-LLM** coordinator: it runs both subagents against the same diff and merges their findings by parsing each agent's `- [SEVERITY] ...` bullet lines and sorting HIGH -> MEDIUM -> LOW.
- `.claude/agents/convention-reviewer.md` checks the diff against the numbered entries in `CONVENTIONS.md` (bare `except:`, `print()` vs `logging`, hardcoded secrets, naming, type hints, docstrings, mutable defaults, HTTP timeouts).
- `.claude/agents/security-bug-reviewer.md` checks only two categories: hardcoded secrets/credentials and unhandled-exception/crash-risk paths introduced by the diff.
- Each subagent is restricted to `tools: Read, Grep, Glob` in its own frontmatter, and `scripts/review.sh` additionally passes `--allowedTools "Read,Grep,Glob"` at the CLI layer.
- Why the manager is non-LLM (per `build-log.md`, Milestone 3): an LLM-based summarize-and-merge step could decide a finding looks minor and drop it while paraphrasing, which is exactly the "does one agent's output silently disappear?" risk; a dumb regex-based parse either finds every bullet each sub-agent printed, or finds fewer than expected and says so loudly in a "Manager Warnings" section — it has no way to quietly lose one.

## How to run

Single-agent run (defaults to `convention-reviewer` when no agent name is given):

```bash
bash scripts/review.sh <diff-file> [agent-name]
```

Combined run (both agents plus deterministic merge):

```bash
python scripts/manager.py <diff-file>
```

Reproducing the documented runs (`eval-cases/diffs/` -> `reports/`):

| Diff fixture | Command | Saved report |
|---|---|---|
| `eval-cases/diffs/case-1-pattern-violation.diff` | `bash scripts/review.sh eval-cases/diffs/case-1-pattern-violation.diff` (convention-reviewer) | `reports/case-1-output.txt` |
| `eval-cases/diffs/case-2-correct-pattern.diff` | `bash scripts/review.sh eval-cases/diffs/case-2-correct-pattern.diff` (convention-reviewer) | `reports/case-2-output.txt` |
| `eval-cases/diffs/case-3-hardcoded-secret.diff` | `bash scripts/review.sh eval-cases/diffs/case-3-hardcoded-secret.diff security-bug-reviewer` | `reports/case-3-output.txt` |
| `eval-cases/diffs/case-4-unhandled-exception.diff` | `bash scripts/review.sh eval-cases/diffs/case-4-unhandled-exception.diff security-bug-reviewer` | `reports/case-4-output.txt` |
| `eval-cases/diffs/case-5-clean-diff.diff` | `bash scripts/review.sh eval-cases/diffs/case-5-clean-diff.diff` (convention-reviewer) | `reports/case-5-output.txt` |
| `eval-cases/diffs/case-7-combined-findings.diff` | `python scripts/manager.py eval-cases/diffs/case-7-combined-findings.diff` | `reports/case-7-output.txt` (per-agent raws: `reports/case-7-convention-raw.txt`, `reports/case-7-security-raw.txt`) |
| `eval-cases/diffs/case-8-new-pattern-hitl.diff` | `bash scripts/review.sh eval-cases/diffs/case-8-new-pattern-hitl.diff` (convention-reviewer) | `reports/case-8-output.txt` |
| Partial-failure run (tampered `AGENTS`, see `build-log.md`) | Temporarily set `AGENTS` to `["convention-reviewer", "typo-agent-does-not-exist"]`, then `python scripts/manager.py eval-cases/diffs/case-1-pattern-violation.diff`, then revert | `reports/case-partial-failure-test.txt` |

Note: `CONVENTIONS.md` is never piped into the prompt by the runner scripts; each agent reads it live with its own Read tool on every invocation.

## Guardrails

- Tool restriction: subagent frontmatter (`tools: Read, Grep, Glob`) plus the `--allowedTools "Read,Grep,Glob"` CLI flag deny Edit/Write/Bash, so there is no write/commit/push path even by accident.
- Secret redaction: a secret finding's detail must contain ONLY the file, line number, and finding type — never the secret value itself, not in full, not truncated, not partially masked (not even its prefix).
- Human-in-the-loop trigger: a deliberate-looking new pattern the agent cannot resolve from the current conventions list goes under a `NEEDS HUMAN INPUT` heading as a pause-and-ask, not a silent approve/reject (exercised by `case-8-new-pattern-hitl.diff` / `reports/case-8-output.txt`).
- Failure reporting: a missing diff exits 1 with `ERROR: diff file not found: ...`, an empty diff exits 1 refusing to fabricate a report, and manager failures surface verbatim under `Manager Warnings (reported, not swallowed)` without erasing the working agent's findings.

## Known Limitations

- Line-number citation reliability: re-running the same diff through the same agent does not always cite the same line number for a finding. A fresh consistency check against case-3 and case-4 found real disagreements (not just wording) where each run got some line citations right and others wrong, with no single run being uniformly more accurate. This is a genuine reliability limitation of LLM-based line citation, not a bug that was fixed; the saved reports in `reports/` are kept as the frozen, documented snapshot rather than the "best" run.
- Scope-adherence drift: `security-bug-reviewer`'s instructions explicitly say to ignore issues outside its two categories (secrets and unhandled exceptions). A fresh run on case-7 once surfaced a bare-except pattern under `NEEDS HUMAN INPUT` anyway, explicitly noting it was out of scope. The saved report does not show this. Documented here as an observed one-off drift, not corrected by re-running.

## Example output

Real content of `reports/case-7-output.txt`, verbatim:

```
## Combined Code Review Report
Diff: eval-cases/diffs/case-7-combined-findings.diff
Agents run: convention-reviewer, security-bug-reviewer
Findings per agent: convention-reviewer=4, security-bug-reviewer=1

### Findings (merged, severity-ordered)
- [HIGH] (convention-reviewer) sample_app/api_client.py:13 — Convention #3 (Never hardcode secrets): hardcoded credential assigned to a module-level constant.
- [HIGH] (convention-reviewer) sample_app/api_client.py:20 — Convention #1 (No bare `except:`): bare `except: pass` in `notify_slack` silently swallows all errors, including `KeyboardInterrupt`/`SystemExit`.
- [HIGH] (security-bug-reviewer) sample_app/api_client.py:13 — SECRET: Hardcoded Slack webhook URL (with embedded workspace/bot/token path segments) assigned to a module-level constant `SLACK_WEBHOOK_URL`, rather than being loaded from an environment variable or secrets manager.
- [MEDIUM] (convention-reviewer) sample_app/api_client.py:17 — Convention #2 (No `print()` for diagnostics): `notify_slack` uses `print()` instead of the module `logger`.
- [LOW] (convention-reviewer) sample_app/api_client.py:16 — Convention #6 (Docstrings on public functions): `notify_slack` is a public function (no leading underscore) but has no docstring.

### NEEDS HUMAN INPUT (merged)
(none)
```

## Deviations from the FL-06 spec

Full detail for each is in `build-log.md`; summaries:

- Implementation substrate choice: Claude Code subagents under `.claude/agents/*.md` invoked headlessly via `claude -p --agent <name>`, because restricting the tool list in frontmatter makes "no write access" enforced by the harness rather than hand-rolled in script code.
- Synthetic fixtures instead of a real A4 branch: no real A4 branch existed in this folder, so `sample_app/`, `CONVENTIONS.md`, and the `eval-cases/diffs/` fixtures were generated here from scratch.
- Non-LLM manager: `scripts/manager.py` merges by deterministic regex parse-and-sort with a loud `Manager Warnings` section, so one agent's output cannot silently disappear the way an LLM summarize-and-merge step could drop it.
- Milestone 4 pgvector deferral: deferred, not attempted — with 8 short conventions entries, reading the whole file every run is faster and more reliable than retrieval, which would add embedding/retrieval failure surface for no accuracy or latency benefit at this size.
- Severity label naming: the FL-06 spec calls for `Critical / Should Fix / Suggestion`; this build uses `HIGH / MEDIUM / LOW` throughout (agent instructions, manager sort order, and every saved report). Same three-level ordering and purpose, different vocabulary — not reconciled, since every eval case, screenshot, and the recording already use the `HIGH/MEDIUM/LOW` labels and changing them now would mean re-running and re-capturing everything for a naming difference with no behavioral effect.

## Real-world validation (beyond the graded eval cases)

The eval cases above use synthetic fixtures (see the deviation above) since no real A4 branch existed in this folder. As an extra check — not required for the graded submission — the same unmodified agents and manager were run against a genuine diff from Nahla's actual FastAPI To-Do API project (the one the FL-06 spec is written about): commit `Stage 4: auth middleware and logout endpoint` (`auth.py` + `main.py`, 97 real lines changed).

Two conventions were added to `CONVENTIONS.md` (entries 9-10, in their own labeled section) written from what that project's real code actually does — fresh-Supabase/Postgres/Redis-client-per-call, and the custom `AuthError(status_code, message)` pattern — so the test checks against real conventions, not an invented approximation.

Result (`real-world-test/todo-api-stage4-auth-report.txt`): `security-bug-reviewer` found nothing (correct — no secrets, no unhandled path in this diff); `convention-reviewer` found 8 real issues, all spot-checked against the actual file and confirmed accurate — a genuine `except Exception: pass` in the new `logout()` route with no logging (Convention #1), and missing docstrings/return-type-hints on 4 new/changed route functions (Conventions #5-6). Neither of the two new project-specific conventions (#9 fresh-client-per-call, #10 `AuthError`) was flagged — correctly, since that commit follows both. One nuance worth stating plainly: the flagged `except Exception: pass` in `logout()` carries a comment marking it as an intentional "best-effort revoke," a design choice the code's author made on purpose — the agent has no way to know that from the diff alone and correctly flagged the literal pattern per the written convention; a human (Nahla) reading the report is the one who decides whether that's a real fix or an accepted tradeoff, which is exactly the "report, not auto-fix, human decides" behavior the spec asks for.

## Screenshots

![](docs/screenshots/01-single-agent-violation.png)
Single-agent run flagging a real violation.

![](docs/screenshots/02-manager-case-7-merged.png)
Manager run on case-7 merging both agents' findings.

![](docs/screenshots/03-partial-failure-warning.png)
Partial-failure run showing a Manager Warning without losing the working agent's findings.

## Screen Recording

[~2-minute raw demo: a real diff going in, the manager running both agents, the merged report coming out](https://drive.google.com/file/d/11dtLrj18_8eO-GZqiFVnxthM2sG6aumk/view?usp=sharing)

## Build log

Full timestamped detail: [build-log.md](build-log.md)
