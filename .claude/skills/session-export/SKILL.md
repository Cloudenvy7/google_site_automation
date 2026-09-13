---
name: session-export
description: Export a past Claude Code session transcript to readable markdown, or build an audit ledger of what it claimed versus what it did. Resolves from a claude.ai/code link, session id, UUID, or path. Use when asked to recover, review, audit, archive, or "pull up" an earlier session, to check whether promised work actually happened, or when a session died and its history is needed. Also use instead of asking the user to copy and paste conversation text.
---

# Export a past session

Claude Code writes every local session to JSONL under `~/.claude/projects/`.
Nothing is lost when a session dies. **Never ask the user to copy and paste a
conversation** — the file is already on disk, and it holds more than was ever on
their screen.

## The size problem — read this before running anything

A single session here reaches **15 MB, roughly 4 million tokens.** It does not
fit in any context window. `cat`-ing a transcript into context will fail or
blow the budget.

That is the whole reason this tool has levels. Pick the smallest one that
answers the question:

| Level | What it holds | Typical size |
|---|---|---|
| `talk` | user + assistant text only — what was visible on screen | ~380 KB / ~94k tok |
| `tools` | + tool calls and truncated results **(default)** | ~700 KB / ~176k tok |
| `thinking` | + the model's reasoning, where it was stored | same or larger |
| `full` | nothing truncated — **archival, not for reading into context** | megabytes |

Sizes are from one real 1,269-line session; scale accordingly.

## Usage

```bash
python3 ~/.claude/skills/session-export/export_session.py <token> [options]
```

`<token>` may be a `claude.ai/code/session_...` link, a bare session id, a
session UUID, or a path to the `.jsonl`.

```bash
# see everything on this machine, newest first
export_session.py --list

# the common case: a link, conversation + tool calls, written to a file
export_session.py "https://claude.ai/code/session_01ABC..." --out review.md

# a link that covers more than one transcript
export_session.py "...session_01ABC..." --all --out review.md

# reasoning included
export_session.py <uuid> --level thinking --out audit.md

# include Task subagent transcripts
export_session.py <uuid> --subagents --out full.md
```

## How resolution works, and where it fails

The id in a `claude.ai/code` link is **not stored as a field.** It appears only
in `cwd` and `gitBranch`, because a worktree session is named after it. Roughly
half of a typical machine's sessions are not worktree sessions, so a link will not resolve
them. Order tried: explicit path → session UUID → link id → give up and list.

**It never picks between two matches.** If a token is ambiguous it prints the
candidates with dates and titles and stops. Exporting the wrong transcript and
saying nothing is the failure worth preventing; `--all` is the deliberate
override.

## Two honest limits

**Thinking text is not always recoverable.** Some sessions store the block with
an empty body and only a signature — across this machine, 3,272 thinking blocks
exist but only 1,837 carry text. The export **counts those as redacted, never as
recovered**, and says so in the header. An export that claimed to hold reasoning
it did not would be worse than one that omitted it.

**Local sessions only.** Anything that ran in the cloud is not on this disk.

## What this is for

A dead session was rebuilt by hand, twice, to feed its history to a fresh
session — so that a new session could check *what was claimed* against *what was
actually built*. That check is worth keeping; the manual copying is not.

Committing an export next to the code gives a later session both the artifact and
the reasoning. The DEVLOG is the curated layer; this is the raw record underneath
it, and the point of having both is that **a summary written by the thing being
audited is not an audit.**


---

# Auditing — `audit_session.py`

```bash
python3 ~/.claude/skills/session-export/audit_session.py <token> --out ledger.md
```

Answers: *what did we say we'd do, was it done, and why not.* Emits a **ledger,
not a verdict** — a shortlist with evidence attached, for a human or a fresh
session to judge.

**The ledger is the claim. git, the files, the Sheet and the Site are the truth.**
Every check runs ledger → reality, never the reverse. Treating the ledger as the
record of what happened rebuilds the problem it exists to catch.

## Sections

| § | What it holds |
|---|---|
| 1 | **Did the work leave the machine** — commits with no push after them, and every settlement claim with what changed after it. *Mechanical; needs no model.* |
| 2 | Completion claims, each with the tool results from its turn. Claims with **no** result are flagged as unverified assertion. |
| 3 | Intents with no later completion claim. |
| 4 | Stated failures, blocks and limits. |
| 5 | The commands to run against reality. |

## The failure it was built from

2026-09-08, 11:21 UTC: *"Both repos clean and pushed, everything green. Yes —
we're done."* **True when written.** Work resumed five hours later and produced
four commits — `8505b45`, `c2291f7`, `ac6553a`, `770f586` — none pushed. 991
lines sat on a disposable worktree branch for five days.

Nobody lied. The claim **expired**, and nothing re-checked it. §1 catches exactly
this, and it found those four commits unaided.

## Two iterations, recorded because the reasoning is the point

**v1 checked "the last claim of any kind"** and missed the failure it was written
for — the last claim in that session was *"9 files, verified as real images,"*
true, local, and not about the repo at all. **v2 flagged all 117 mutating actions
after a settlement claim** — correct but unreadable, the signal buried.

**v3 asks the narrow question: were there commits after the last push.** Precise,
low-noise, directly actionable. *A check that is too broad to read is not a check.*

## Audit is not eval — do not confuse them

An **audit** is retrospective, one-off, has no expected answer, and a human
judges it. An **eval** is repeatable, has a known correct answer, runs
automatically and fails loudly.

**Audits generate evals.** Every gap an audit finds should become a deterministic
check so it can never recur silently. §1 began as an audit finding and is now
mechanical.

## Verification layers, strongest first

1. **Deterministic** — `git log`, file exists, `evals/run.sh`, a live probe.
   Free, no opinion, cannot be talked around.
2. **Fresh-context agent grounded in artifacts.** No commitment to prior reasoning.
3. **A different model reviewing.** Different blind spots — but still a model.

Reach for 3 last. Anything that can be made deterministic should be: an audit
finds it once, a check catches it forever.
