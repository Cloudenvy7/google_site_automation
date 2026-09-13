# Google Sites automation — mandatory orientation

You are working in a system that builds Google Sites from a client's Drive
folder, under a governance model that exists because earlier builds failed in
specific, repeatable ways. This file loads automatically. Read it before your
first substantive action.

**Why this file exists.** Every rule below was written after something went
wrong: a finished Home page destroyed by a delete whose target click silently
missed, three pages scrambled by assuming a new block appends to the end, an
entity fabricated from a grounding file, and a build proposed twice before the
site's architecture had been written at all. The rules are not preferences.
They are the failures, inverted.

---

## The one rule that governs the rest

**The Landing Rule — information lands in the sheet before it lands on the page.**

Gathering is proven in the catalogue, never on the site. The sheet is the only
place where absence is visible; a finished-looking page proves nothing about what
is missing from it. Content typed onto a Site from a script is content that is
not a cell, and it is invisible to every check downstream.

## Before you do anything

Load the **`information_systems_architecture` skill.** It is the procedure —
stage order, the ISA, and what to read first. Do not propose a page structure, a
block type, or a build step before you have it loaded.

Then read, in this order:

| # | Read | Why |
|---|---|---|
| 1 | `docs/TEMPLATE_Build_Harness_and_Guardrails_v2_0_instantiate_at_Stage_0.md` | Gates 1–6, Guards 1–8, Ledgers 1–5, each with the failure behind it |
| 2 | `docs/Visual_Second_Brain_Framework_The_Cycle_v0_2.md` | The whole cycle, Stage 0 → 6 |
| 3 | `.claude/skills/information_systems_architecture/references/FIRST_TRY_CHECKLIST.md` | Every line cost at least one rebuild |
| 4 | `DEVLOG.md` | What was built, what failed, what each failure produced |

`START_HERE.md` maps every stage to both its document and its code.

## Stage order — stages do not overlap

```
0  HARNESS   instantiate the harness; write and ratify THIS site's ISA
1  INDEX     catalogue the folder
2  CHARTER   why the site exists, in the client's words
3  MANIFEST  what is in, what is out, both with reasons
4  PAGE PLAN what sits on which page, in what order, and why
   >>> THE GATE — the human ratifies Charter, Manifest, Page Plan <<<
5  RENDER    how each item is displayed, from MEASURED presets
6  BUILD     make the Site match the sheet; every run logged
```

Reaching for a block type while the charter is still open has skipped two
stages. **The ISA is written at Stage 0** — before the folder is indexed, not
between analysis and build, which is where it keeps getting pushed.

## The non-negotiables

1. **The human ratifies; the agent proposes.** Charter, Manifest and Page Plan
   are not yours to approve. Ratification is recorded in the catalogue by a
   person. `harness.py preflight` only checks that it happened.
2. **Never overwrite.** Corrections supersede; both versions survive; mark
   corrections visibly rather than editing silently. This applies to governing
   documents, the DEVLOG, and Sheets alike.
3. **Never fabricate.** No invented names, files, test data, matches, or
   confidence scores. If real data exists, use it. If it does not, say so.
4. **Maker is never checker.** Verify by independent read-back, not by trusting
   a build's own status string. A build that reports success and a page that
   holds the content are two different claims.
5. **A rule without its why is cargo.** Record the reasoning with the decision,
   or the next session cannot evaluate it and will discard it or obey it blindly.
6. **Measure, do not assume.** Presets, aria-labels and cell indices change.
   Google renamed a layout tile mid-2026 and every insert failed with a bare
   timeout. Probe first.

## The deterministic layer — it will refuse you

`.claude/settings.json` registers a **PreToolUse hook** on Bash:
`.claude/hooks/site_build_gate.py`. Skills are advisory and `harness.py` runs
only if the code calls it; **the hook runs on every Bash call regardless of what
you wrote.**

- Any command that can reach the Sites editor is refused unless it goes through
  the door — `build_from_wireframe.py` / `run_wireframe.py`.
- The door opens only on a fresh (< 12h) `preflight` stamp reading `RATIFIED`
  for that site.
- `clear_page` outside the door is refused, even under a waiver.
- Waivers are human acts: `~/.advisor_os/waivers/<name>.json`.
- Every decision is logged to `~/.advisor_os/hook_log.jsonl`.

**Working rule:** edit files with Edit/Write, run things with Bash. The hook
matches Bash text, so a heredoc that patches the hook — or a test that merely
quotes a Site write — is refused as if it were the write.

If it refuses you, it is probably right. Read the reason before working around
it, and never disable it to make progress.

## Reading the doctrine

`docs/` mirrors the governing Google Docs as markdown. **The Doc is canonical
where you can reach it; edit it there and re-export.** Editing the markdown
instead produces two disagreeing copies of a governing rule, which is worse than
one, because a drifted rule still reads as authoritative.

On a machine without access to the Blackfox Studios shared drive — which is the
normal case for a client — `docs/` **is** your source. It is complete.

## Setup

`SETUP.md` — credentials, dependencies, and Chrome. Do not improvise around a
missing credential; the code raises and names every location it looked in.
