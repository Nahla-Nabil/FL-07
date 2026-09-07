#!/usr/bin/env python3
"""
Thin manager: runs both review agents against one diff and merges their findings into a
single severity-ordered report.

Deliberately NOT another LLM call. The Milestone-3 risk called out in the build checklist is
"does merging actually work, or does one agent's output silently disappear?" -- an LLM-based
merge step would reintroduce exactly that risk (a model summarizing away a finding it decided
looked minor). A dumb, deterministic parse-and-sort has no way to quietly lose a bullet: either
the regex matches every finding line each sub-agent printed, or the count check at the bottom
fails loudly and says so.

Usage:
    python scripts/manager.py <diff-file>
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

AGENTS = ["convention-reviewer", "security-bug-reviewer"]
# On Windows the npm-installed CLI is a `claude.cmd` shim; subprocess without shell=True won't
# resolve the extension-less "claude" the way a real shell (or CreateProcess's .bat/.cmd loader
# hook) does in every environment, so resolve it explicitly once up front.
CLAUDE_BIN = shutil.which("claude.cmd") or shutil.which("claude") or "claude"
SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

FINDING_RE = re.compile(r"^-\s*\[(HIGH|MEDIUM|LOW)\]\s*(.+)$")
NEEDS_HUMAN_HEADING_RE = re.compile(r"^###\s*NEEDS HUMAN INPUT", re.IGNORECASE)
FINDINGS_HEADING_RE = re.compile(r"^###\s*Findings", re.IGNORECASE)
SECTION_HEADING_RE = re.compile(r"^###\s")


def run_agent(agent: str, diff_file: str) -> tuple[bool, str]:
    """Returns (ok, raw_stdout_or_error).

    Calls `claude` directly rather than shelling out to review.sh. First attempt shelled out to
    bash review.sh via subprocess and hit a Windows-specific footgun: Python's subprocess
    resolved "bash" to the WSL relay stub in System32 (bash.exe there just launches WSL), not
    the Git Bash the Bash tool uses -- it failed with
    "execvpe(/bin/bash) failed: No such file or directory". Calling claude with an explicit
    argv list sidesteps shell/PATH resolution entirely and works the same on any OS.
    """
    path = Path(diff_file)
    if not path.is_file():
        return False, f"{agent}: diff file not found: {diff_file}"
    diff_content = path.read_text()
    if not diff_content.strip():
        return False, f"{agent}: {diff_file} is empty -- refusing to fabricate a report"

    prompt = (
        "Review the following diff per your own instructions, and produce the report in the "
        f"exact format they describe.\n\n--- BEGIN DIFF ({diff_file}) ---\n{diff_content}\n"
        "--- END DIFF ---"
    )
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", "--agent", agent, "--allowedTools", "Read,Grep,Glob"],
            input=prompt, capture_output=True, text=True, timeout=180,
        )
    except subprocess.TimeoutExpired:
        return False, f"{agent} timed out after 180s"
    except FileNotFoundError as exc:
        return False, f"{agent}: could not launch `claude`: {exc}"
    if result.returncode != 0:
        return False, f"{agent} exited {result.returncode}: {result.stderr.strip()}"
    if not result.stdout.strip():
        return False, f"{agent} produced no output"
    return True, result.stdout


def parse_report(agent: str, text: str) -> tuple[list[dict], list[str]]:
    """Extract (findings, needs_human_lines) from one agent's report text."""
    findings = []
    needs_human = []
    in_findings, in_needs_human = False, False
    for line in text.splitlines():
        if FINDINGS_HEADING_RE.match(line):
            in_findings, in_needs_human = True, False
            continue
        if NEEDS_HUMAN_HEADING_RE.match(line):
            in_findings, in_needs_human = False, True
            continue
        if SECTION_HEADING_RE.match(line):
            in_findings, in_needs_human = False, False
            continue
        m = FINDING_RE.match(line.strip())
        if in_findings and m:
            findings.append({"severity": m.group(1), "detail": m.group(2), "source": agent})
        elif in_needs_human and line.strip().startswith("-"):
            needs_human.append(f"[{agent}] {line.strip()[1:].strip()}")
    return findings, needs_human


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/manager.py <diff-file>", file=sys.stderr)
        return 2
    diff_file = sys.argv[1]

    all_findings: list[dict] = []
    all_needs_human: list[str] = []
    per_agent_counts: dict[str, int] = {}
    failures: list[str] = []

    raw_outputs: dict[str, str] = {}
    for agent in AGENTS:
        ok, output = run_agent(agent, diff_file)
        if not ok:
            failures.append(output)
            per_agent_counts[agent] = 0
            continue
        raw_outputs[agent] = output
        findings, needs_human = parse_report(agent, output)
        per_agent_counts[agent] = len(findings)
        all_findings.extend(findings)
        all_needs_human.extend(needs_human)
        # Sanity check: if the agent's report clearly says there ARE findings in prose but our
        # regex caught zero, that's a parse failure -- report it (with the raw text attached so
        # the failure is actually actionable), don't silently show "0 findings".
        if len(findings) == 0 and "no convention violations" not in output.lower() \
                and "no security or unhandled-exception issues" not in output.lower():
            failures.append(
                f"{agent}: parsed 0 findings but output did not contain a recognized 'no "
                f"issues' phrase either -- possible parse mismatch. Raw output:\n"
                + "\n".join(f"    {l}" for l in output.splitlines())
            )

    all_findings.sort(key=lambda f: SEVERITY_ORDER.get(f["severity"], 99))

    print("## Combined Code Review Report")
    print(f"Diff: {diff_file}")
    print(f"Agents run: {', '.join(AGENTS)}")
    print(f"Findings per agent: " + ", ".join(f"{a}={per_agent_counts.get(a, 0)}" for a in AGENTS))
    print()

    if failures:
        print("### Manager Warnings (reported, not swallowed)")
        for f in failures:
            print(f"- {f}")
        print()

    print("### Findings (merged, severity-ordered)")
    if not all_findings:
        print("No findings from either agent.")
    else:
        for f in all_findings:
            print(f"- [{f['severity']}] ({f['source']}) {f['detail']}")
    print()

    print("### NEEDS HUMAN INPUT (merged)")
    if not all_needs_human:
        print("(none)")
    else:
        for line in all_needs_human:
            print(f"- {line}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
