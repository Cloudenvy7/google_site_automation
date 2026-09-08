# **INDEXER SPEC — STAGE 1 — v2.1 AMENDMENT**

v2.1 — 2026-09-07. **Amends v2.0; does not replace it.** v2.0's rule stands:
every file is opened and read, and a file that cannot be read is recorded as
unread with the reason. v2.1 adds the thing v2.0 could not do: **prove it.**

Ratified by Andrew Powers, 2026-09-07, in conversation:
> *"this we need to fix, need to make sure everything was read so that the
> information system architect is making the decisions based on all the
> information right?"* … *"yes build items and ratify and make sure that we
> have the chunking and guardrail and the canary eval and regression test."*

# **WHAT v2.0 COULD NOT SEE**

v2.0 measured reading with `chars_read`, and `verify_index_integrity.py`
compared the agent's `chars_read` to a re-derived extractor count. But the
packet **handed the agent that number**. An agent that read nothing could echo
it back and pass every check. The verifier proved the extractor was
deterministic; it proved nothing about reading.

The one v3 run on record — 3 files, 259,926 characters, 34,146 tokens — cost
roughly **half** the tokens its text should have needed. That is consistent
with a partial read, and nothing in the system could have said otherwise.

A second, quieter defect sat in the deterministic layer: the extractor read
spreadsheets as `A1:AZ400`, silently dropping every row past 400 and every
column past AZ, then reported `OPENED` with the smaller count. Skipping, in the
one place nobody was looking for it. Fixed in the same amendment.

# **THE RULE, EXTENDED**

**Coverage is proven, not claimed.** A row may be written only when the
orchestrator can show, from what the agent *returned* rather than what it
*said*, that every part of the file was in front of the model.

# **MECHANISM**

1. **CHUNK.** The orchestrator splits extracted text into fixed pieces
   (12,000 characters, about 3,000 tokens) small enough that a cheap model reads
   one in a single call with no paging. The agent is never handed a
   245,000-character file with "please page through it."
2. **MARK.** A random token — `⟦CHK:a3f9c1⟧` — is planted every 1,500
   characters, regenerated per run. The list of planted markers stays with the
   orchestrator and is never in the packet. The agent must return every marker
   it encountered. It cannot guess them. Missing markers are an exact map of
   what went unread; a marker that was never planted is a fabrication and is
   itself a finding.
3. **REFUSE — GUARD 9.** `harness.guard_9_coverage` refuses to commit any row
   whose returned markers do not cover the file. The file stays `PENDING` and
   is re-issued. A Refusal is not an error to route around; it is the statement
   that this row was not read.
4. **COUNT HERE.** `chars_read` keeps its name and changes meaning: it is the
   orchestrator's count of what it sliced, written over whatever the agent
   supplied. Three columns are appended to `DRIVE_INDEX`: `chunks_total`,
   `chunks_verified`, `coverage_pct`.
5. **READ-ONLY REACH.** The indexing agent runs with `--allowedTools Read,Write`
   — no Grep, no Bash. With no way to search, the only way to see a marker is to
   read the chunk it sits in. This is the deterministic half of the guard.

# **WHAT MARKERS DO NOT PROVE — AND WHAT DOES**

A marker proves the text was in the model's context. It does not prove the
text was understood. So the amendment carries an eval, per the AI-native SDLC
playbook's continuous-eval play:

**The canary eval** (`evals/canary_partial_read.py`) plants a distinctive,
entirely synthetic fact at 93% of a long document and asserts it reaches the
row's `what_it_says` / `key_entities` / `key_dates`. Then a **negative
control** runs the same packet with the agent told to read only the first
chunk, and asserts GUARD 9 refuses. A guard that never fires is
indistinguishable from no guard; the negative control is the regression test
for the guardrail itself.

Markers prove presence. The canary proves comprehension. Both run.

# **WHEN THE EVALS RUN**

- **Every commit** touching the indexer, the harness, the skills or `CLAUDE.md`
  runs the deterministic tests (`evals/test_coverage_unit.py`) via
  `.githooks/pre-commit`. Seconds, no model.
- **On demand and nightly** (`.github/workflows/agent-evals.yml`), the canary
  runs on a real model. It appends one line per run to `evals/history.jsonl`
  so a regression can be dated, not just noticed.
- A **monotone-decreasing baseline** (`evals/baseline.json`, a pattern taken
  from ruvnet/ruflo) holds counts that may never rise.

# **EXIT CONDITION, EXTENDED**

Stage 1 is complete when every file has a `DONE` row **and** every `DONE` row
with `opened = yes` carries `coverage_pct = 100`. `status` reports any row that
violates this as *"should be impossible under GUARD 9."*

# **REVISION LOG**

> **REVISION — 2026-09-07, from Andrew's standing concern.** v2.0 said "every
> file is opened and read" and had no way to know whether it had been. The
> mechanism that verified reading verified only that a number had been copied.
> Principle extracted: **a check that compares a claim to the source of the
> claim is not a check.** Prove from what was returned, never from what was
> reported.
