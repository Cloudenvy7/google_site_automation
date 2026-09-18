---
name: information_systems_architecture
description: Write the Information Systems Architecture for a client site before anything is built, and run the Visual Second Brain cycle from Stage 0. Use when opening a new site build, when asked for an ISA, a site architecture, a page plan, or a Google Sites build from a Drive folder. Also use before proposing any page structure, block type, or build step.
---

# Information Systems Architecture — the first-try procedure

This skill exists because the first client site build took many passes to reach
a correct page. Almost none of that cost was technical. It was structural: the
architecture was written late, the roster was never gathered into a tab, presets
were assumed rather than measured, and a destructive step ran without checking
its target. Every one of those is preventable by order of operations.

**Nothing in this skill is the first client-specific.** the first client is the instance that
produced the lessons; `references/ARCHITECTURE_PRINCIPLES.md` records them as
principles, with the failure attached so a later session can evaluate them rather
than obey blindly.

## The one rule that governs the rest

**The Landing Rule — information lands in the sheet before it lands on the page.
Gathering is proven in the catalogue, never on the site.**

The sheet is the only place where absence is visible. A finished-looking page
proves nothing about what is missing from it. When you are pulling information,
you cannot skip: you go back and put it into the spreadsheet, and that is how it
is determined that all the information is gathered.

## Order of work — stages do not overlap

```
0  HARNESS   instantiate the harness; write and ratify THIS site's ISA
1  INDEX     catalogue the folder, metadata only
2  CHARTER   why the site exists, in the client's words
3  MANIFEST  what is in, what is out, both with reasons
4  PAGE PLAN what sits on which page, in what order, and why
   >>> THE GATE — the human ratifies Charter, Manifest, Page Plan <<<
5  RENDER    how each item is displayed, from MEASURED presets
6  BUILD     make the Site match the sheet; every run logged
```

An agent reaching for a block type while the charter is still open has skipped
two stages. **The ISA is written at Stage 0, before the folder is indexed** — not
between analysis and build, which is where it keeps getting pushed.

## Step 1 — Read before writing anything

All Drive documents live in **Google Sites Automation**
(`1ZLG4E66kgHewdmRBXh2T1dqsF5D7r9wn`), Blackfox Studios shared drive. Read them
with the service account (`drive.files.export_media`), not the MCP connector.

| Read | ID |
|---|---|
| TEMPLATE - Build Harness and Guardrails v2.0 | `1_4107tyX6IPRDxBfCXjheSkWBpd4cT7QwdOPzz9Set8` |
| VISUAL SECOND BRAIN FRAMEWORK - THE CYCLE | `1G9MrBDKhs7UfrfHVauxcMw9_s09V3JgVT4QF8lI6Dy0` |
| TEMPLATE - Information Systems Architecture v1.0 | `15DWHdjKTuGoz_Sr-E19HPm8xAts__T3gWuXWPKcR-qw` |
| TEMPLATE - Per-Site Visual Knowledge Catalogue | `14lvGzhN1I6urSavZ7yCBLgcqbptz57C2dh3IkGn60H4` |
| Site Architect Master Prompt (stages 2-4) | `15yyd264DEuEPVNwpYKW9-EY0p4jDesTFJuqDOARiYmY` |
| Render Master Prompt (stage 5) | `16BFdNxcxQkvirkC2R8CPnUJSYtnv9mJsKOVConAPAAE` |
| QA Auditor Master Prompt (audit) | `1845LuFLmlwU0hOIgZRGvsUPcboWpTa5UKHZCij1JAHM` |
| Build Protocol (stage 6) | `1kslI1OR2465R5Z2IQsR62dtO4FqGEKQzCdb6w0m0WQE` |
| BFS Block Catalogue | `15_eyJizpy6TqZFOV5P4xT5LhxxxbI7FzuluPrkNaJ4s` |
| Indexer Spec (stage 1) | `1kABU-BCwXsXWHz8YmnCmbZPdYfjqPydHwlFSJihexuo` |

> **CORRECTION 2026-09-13 — where to read the doctrine in this repository.**
> The table above resolves only from the Blackfox Studios shared drive, with a
> service account that has been granted it. On a client's machine neither holds,
> and following it literally yields HTTP 404 on every row.
>
> **In this repository, `docs/` is the source and it is complete** — all eleven
> documents above, exported as markdown, each carrying its Drive id and export
> date. Read those. Use the Drive ids only when you can actually reach that
> drive, in which case the Doc is canonical and `docs/` is the mirror.
>
> **Script paths:** this repository keeps them in `scripts/`, not
> `.agents/scripts/` as written below. That path is correct in the `advisor-os`
> repository, where this skill was first written, and wrong here.
>
> Both are recorded rather than edited away, because the original text is
> accurate in its own repository and the difference between the two is itself
> the thing worth knowing.

Also read, in this folder:
- `references/ARCHITECTURE_PRINCIPLES.md` — what makes an architecture correct.
- `references/FIRST_TRY_CHECKLIST.md` — the specific mistakes, and their fixes.
- `references/ISA_TEMPLATE.md` — the section-by-section fill-in.

And the site's own `DRIVE_INVENTORY` and `CHARTER` tabs, if Stage 1–2 have run.

Scripts: `.agents/scripts/` — `harness.py` (gates and guards),
`indexer_v3.py` (stage 1 — v3.1, coverage proven by planted markers; GUARD 9),
`build_from_wireframe.py` (stage 6), `sites_automation.py` +
`wireframe_build.py` (CDP primitives). `drive_indexer.py` is the superseded
v1.0 metadata-only crawl; do not use it for Stage 1.

Evals: `.agents/evals/run.sh` — deterministic coverage tests on every commit
that touches the indexer, harness, skills or CLAUDE.md; `--with-model` runs
the canary (a synthetic fact at 93% of a long file must reach the row, and a
deliberately partial read must be refused). If you change `AGENT_PROMPT`, run
the canary before you trust the change.

**A worked instance to compare against, never to copy from:** the first client Ride
Ready ISA (`<first-client-isa-id>`). Read it to see what a
filled-in ISA looks like, including its revision log. Do not lift its pages, its
reader model, or its goals — those are that site's, and reusing them is the drift
this skill exists to prevent.

If a stage's governing artifact does not exist, **stop and say so.** Do not
proceed on the assumption that it is implied.

## Step 2 — Copy the catalogue, never hand-assemble

Copy the per-site catalogue template. Eleven tabs, `00_HARNESS` and `WAIVERS`
first. Fill the Stage 0 keys in `00_README`. `isa_status` starts at
`NOT WRITTEN` — that is a correct starting value, not a gap.

A catalogue missing a tab is not a smaller catalogue; it is a broken one. Later
stages read columns by name and fail silently when a name moves.

## Step 3 — Establish the reader before the pages

You cannot write the architecture until you can answer:

- **Who reads this, and how many of them are there?**
- **What changes about them?** Turnover, rotation, onboarding — this is usually
  the real design constraint. the first client's site existed *because the people did not
  persist*.
- **What questions do they arrive with?** List them, then **order them by how
  often each is asked** — not by how important the content is.

**One question becomes one page.** The structure is the list of things people
actually come to find out. It is not a filing scheme and it is not the folder
tree.

## Step 4 — Ask the client at most five questions

Five is the target; ten is the ceiling. Block rules are considered **only after**
content, themes and philosophy have been settled. Do not rush toward building.

Every charter goal is numbered `GOAL-nn` and carries **the client's own sentence**
that produced it. A goal you can't quote is a goal you invented.

## Step 5 — Write the ISA

Use `references/ISA_TEMPLATE.md`. Fill every section. The sections exist because
each one caught a real error.

State plainly what the site **deliberately does not do**, and cite the goal behind
each exclusion. Exclusions are recorded, and the significant ones are stated on
the site itself so an absence reads as a decision rather than a gap.

**Design only with blocks that are verified buildable.** Designing around a block
that cannot be placed is designing a site that cannot be built.

End with **open questions for the advisor**. Refusal is a valid deliverable. The
council proposes with reasoning; the human ratifies.

## Step 6 — Ratify, then and only then render and build

The human ratifies Charter, Manifest and Page Plan. Record `ratified_by` and
`ratified_date`. Then run the gates in `harness.py`:

```
stage_0_instantiated · harness_checklist · gate_1_architecture
gate_2_landing · gate_3_flags · gate_4_charter · gate_5_ratified
```

**The hook makes this deterministic.** `.claude/hooks/site_build_gate.py`
fires on every Bash call. The Sites editor is reachable only through the door
(`build_from_wireframe.py` / `run_wireframe.py`), and the door opens only
after `harness.py preflight <catalogue> <site>` has left a fresh `RATIFIED`
stamp. Inline writes in any syntax, `clear_page` outside the door, and stale or
refused stamps are blocked; publish asks the human. Every decision is logged
to `~/.advisor_os/hook_log.jsonl`. A blocked command is not a bug to code
around — it is the harness working.

A `Refusal` is a finding for the human, not an error to route around. An agent
that works around a refusal has reproduced the failure the refusal prevents.

## What this skill will not do for you

It does not make the architecture good. It makes it **stoppable**, and it puts
the thinking before the building. Judgment about a client, a community's work, or
a relationship stays human. The AI assists; it does not author.
