# START HERE

Everything for the Google Sites automation track lives in this repository: the
governing documents, the code that enforces them, and the development log.

**One thing is deliberately not here: the live Sheets.** They are working data,
not artifacts. Copying them into git would create a second copy that goes stale
the moment someone edits the real one, and *Sheets are truth — Docs, Sites and
catalogues are projections.* They are linked below instead.

---

## First run on this machine?

**[`SETUP.md`](SETUP.md)** — credentials, dependencies, Chrome. Do that first;
nothing below works without it. `CLAUDE.md` loads automatically in Claude Code
and carries the rules an agent must not drift from.

---

## Read in this order

| # | Read | Why |
|---|---|---|
| 1 | [`.claude/skills/information_systems_architecture/SKILL.md`](.claude/skills/information_systems_architecture/SKILL.md) | The procedure. Load this before touching a Site or a client folder. |
| 2 | [`docs/TEMPLATE_Build_Harness_and_Guardrails_v2_0_instantiate_at_Stage_0.md`](docs/TEMPLATE_Build_Harness_and_Guardrails_v2_0_instantiate_at_Stage_0.md) | Stage 0. Gates 1–6, Guards 1–8, Ledgers 1–5, each with the failure that produced it. |
| 3 | [`docs/Visual_Second_Brain_Framework_The_Cycle_v0_2.md`](docs/Visual_Second_Brain_Framework_The_Cycle_v0_2.md) | The whole cycle, Stage 0 through Stage 6. |
| 4 | [`.claude/skills/information_systems_architecture/references/FIRST_TRY_CHECKLIST.md`](.claude/skills/information_systems_architecture/references/FIRST_TRY_CHECKLIST.md) | Every line cost at least one rebuild. Read before placing a block. |
| 5 | [`DEVLOG.md`](DEVLOG.md) | What was built, what failed, and what each failure produced. |

## The cycle — document and code, per stage

| Stage | Governing document | Code |
|---|---|---|
| **0 · HARNESS** | `docs/TEMPLATE_Build_Harness_and_Guardrails_v2_0...md`<br>`docs/TEMPLATE_Information_Systems_Architecture_v1_0.md` | `scripts/harness.py` |
| **1 · INDEX** | `docs/Indexer_Spec_Stage_1_v2_0_every_file_is_opened.md`<br>`docs/Indexer_Spec_Stage_1_v2_1_coverage_is_proven.md` *(amendment)* | `scripts/indexer_v3.py` *(v3.1 — chunk, mark, GUARD 9)*<br>`scripts/coverage.py`, `scripts/read_drive_file.py`<br>`scripts/drive_indexer.py` *(v1.0 contract — superseded)*<br>`scripts/merge_index_pass_b.py`, `scripts/verify_index_integrity.py` *(wrong-file check only)* |
| **2 · CHARTER** | `docs/Advisor_OS_Site_Architect_Master_Prompt_v0_3.md` | — |
| **3 · MANIFEST** | same | — |
| **4 · PAGE PLAN** | same | — |
| | **>>> THE GATE — the human ratifies Charter, Manifest, Page Plan <<<** | |
| **5 · RENDER** | `docs/Advisor_OS_Render_Master_Prompt_v1_0.md`<br>`docs/BFS_Block_Catalogue_The_House_Patterns_v1_3.md` | `scripts/extract_site_template.py`, `scripts/catalog_site.py` |
| **6 · BUILD** | `docs/Google_Sites_Automation_Build_Protocol_v0_4.md` | `scripts/build_from_wireframe.py`, `scripts/wireframe_build.py`,<br>`scripts/build_page.py`, `scripts/sites_automation.py`,<br>`scripts/drive_upload.py`, `scripts/capture_page_images.py` |
| **audit** | `docs/Advisor_OS_QA_Auditor_Master_Prompt_v1_0.md` | `scripts/run_ledger.py` (`RUN_DEVLOG`) |

Added 2026-09-08, from the Highline StartZone second-site build:

| Script | What it is |
|---|---|
| `scripts/site_survey.py` | The sanctioned **read-only** Site probe — account, pages, cells. On the hook's allowlist, which is why it must never gain a mutating call. |
| `scripts/build_workshops.py` | Sheet-to-Site build: nine Image-and-caption blocks from a Sheet, with reconciliation against the page so a rerun does not duplicate. |
| `scripts/fetch_flyers.py` | Pulls Drive files through the browser's own session, for folders the service account was never granted. |
| `scripts/upload_to_drive.py` | Browser upload path. **Recorded as not working** — the chooser arms, Drive never ingests. Kept because the finding is the value. |

Machine setup, not stage-bound: `scripts/config.py` (path and id resolution —
read its docstring before adding a new credential lookup),
`scripts/launch_chrome.sh`, `requirements.txt`, `.env.example`.

Reference, not stage-bound:
`docs/Architecture_Principles_what_makes_a_site_architecture_correct_v1_0.md`,
`docs/First_Try_Checklist_Google_Sites_build_v1_0.md`.

## The evals

[`evals/`](evals/) — the playbook's continuous-eval play, aimed at one failure:
an indexing agent reporting a file read when it read part of it.

| | |
|---|---|
| `evals/run.sh` | Deterministic tests — coverage (40 checks) and the Site-build hook (35 cases) — seconds, no model. Runs from `.githooks/pre-commit` on any change to the indexer, harness, hooks, skills or `CLAUDE.md`. |
| `evals/run.sh --with-model haiku` | The **canary**: a synthetic fact at 93% of a 90k-char file must reach the row, and a deliberately partial read must be refused by GUARD 9. Costs real tokens. |
| `evals/history.jsonl` | One line per model run — commit, model, tokens, cost, pass/fail — so a regression can be dated. |
| `evals/baseline.json` | Counts that may never rise (pattern from ruvnet/ruflo). |
| `.github/workflows/agent-evals.yml` | Unit on every PR; canary nightly when `ANTHROPIC_API_KEY` is set. |

Enable the pre-commit hook once per clone: `git config core.hooksPath .githooks`.

## The hooks — the deterministic layer

`.claude/settings.json` + `.claude/hooks/site_build_gate.py`. Skills are
advisory; `harness.py` runs only if the code calls it. **A hook runs on every
Bash call regardless of what code the agent wrote.** Stdlib only, offline, fast.

| Rule | What happens | The failure behind it |
|---|---|---|
| **Use the door** | Any executing command that reaches the Sites editor is refused unless it goes through the door — `build_from_wireframe.py` / `run_wireframe.py` — the path that enforces the Landing Rule and asserts the page id. Inline writes, in any syntax, are refused. | Content typed from a script is content that is not a cell. |
| **Ratified first** | The door opens only on a fresh (< 12h) `preflight` stamp that says `RATIFIED`, for that site. | Build proposed twice before the HopeLink ISA existed. |
| **No blind delete** | `clear_page` outside the door is refused, even under a waiver. | 2026-08-31: a page click silently missed and `clear_page` destroyed a finished Home. |
| **Publish asks** | Publishing prompts the human. | Outward-facing. |
| **Waivers are human acts** | `~/.advisor_os/waivers/<name>.json` with `waived_by`, `site_id`, `expires`, `reason` permits builds on that one named site. | Scratch testing needs a door too — one a human opened. |
| **Every decision is logged** | `~/.advisor_os/hook_log.jsonl` — allow / block / ask, with the command's hash. | The auditor reads the ledger, not the summary. |

Read-only probes (`probe_controls`, `whoami`, `list_pages`, `catalog_site.py`)
stay allowed so diagnosis is possible. `eval_js` counts as a write.

**Before a build:**
```
python scripts/harness.py preflight <catalogue_sheet_id> <site_id>
```
It reads the catalogue once, applies STAGE 0 / `00_HARNESS` / GATE 1 / GATE 5,
and leaves the stamp. It does not decide ratification — that is recorded in the
catalogue by a human — it only checks it was done.

**Two limits, stated plainly.** The hook reads command text, not the DOM. And
on a client's own Pro account it lives in the project's `settings.json`, which
a human can edit: it stops an agent from drifting, not a person from deciding.

**One working rule that fell out of building it:** edit files with Edit/Write,
run things with Bash. The hook matches only Bash, so a heredoc that patches the
hook — or a test that quotes a Site write — is refused as if it were the write.

## Checking a past session — `session-export`

[`.claude/skills/session-export/`](.claude/skills/session-export/) — two tools
over the local Claude Code transcripts in `~/.claude/projects/`.

| | |
|---|---|
| `export_session.py` | Renders a session to markdown at four levels. **Never ask a human to copy and paste a conversation** — the transcript is on disk and holds more than was on screen. Do not `cat` one: a session reaches 15 MB, roughly 4M tokens. |
| `audit_session.py` | **The ledger: what was promised, what was claimed done, and the evidence under each.** §1 is mechanical — commits with no push after them. It found four commits stranded on a disposable branch for five days, unaided. |

**The ledger is the claim; git, the files, the Sheet and the Site are the truth.**
Checks run ledger → reality, never the reverse. An audit is not an eval — it has
no expected answer. But **audits generate evals**: anything an audit finds once
should become a deterministic check that catches it forever.

## The catalogue template

[`catalogue_template/`](catalogue_template/) — the 11 tabs of
**TEMPLATE — Per-Site Visual Knowledge Catalogue v1.0**, exported as CSV so the
schema is readable and diffable here. `00_HARNESS` and `WAIVERS` come first and
carry the 17 gate rows; a blank status means stop.

**Copy the Sheet, never hand-assemble from these CSVs.** A catalogue missing a
tab is not a smaller catalogue, it is a broken one — later stages read columns by
name and fail silently when a name moves.

## Where the live things are

These are working documents. This repo mirrors the *docs*; it does not mirror
these.

| What | Where |
|---|---|
| Drive folder (canonical docs) | `1ZLG4E66kgHewdmRBXh2T1dqsF5D7r9wn` — "Google Sites Automation", Blackfox Studios shared drive |
| Catalogue template (Sheet) | `14lvGzhN1I6urSavZ7yCBLgcqbptz57C2dh3IkGn60H4` |
| JBL — Visual Knowledge Catalog | `1RDCybCvyL6Bra2At7VKFoDEnOWfodmiQQukZKv_vzJw` — 8 pages, 100 blocks, the extracted vocabulary |
| Visual Second Brain Substrate | `1pq0KZeLXC_sdY3qrdQkIVctlEwhUNDalTLX3SwvNx5U` — **not mirrored: holds real people and organisations** |
| HopeLink ISA (worked instance) | `1MpXVxdm3nY0m_mH6P8a4091WhkJuSghUtxxxJEoK0M0` — in `Hopelink Project Site Folder` |
| HopeLink Visual Knowledge Catalog | `1RZnHy1Lq2rFzkimVZRqhcAvlveTo-H7SL7sosevCqSY` — same folder |

Read the HopeLink ISA **to see what a filled-in ISA looks like, never to copy
from.** Reusing another site's pages, reader model or goals is the drift the
template exists to prevent.

## The sites built on this

| Site | ID | State |
|---|---|---|
| SBDC Advisor Workshops | `1e7y_nvGjz6sMHxDZPbbfb2wMP9yG_mn9` | published — `sites.google.com/blackfoxstudios.org/sbdc-advisor-workshops/workshops?authuser=1` |
| HopeLink Ride Ready (scratch) | `16rOjT22qmA8BhZSpcLVSH4XSnNTXPd5W` | draft only, Home is a placement test harness |
| BFS X JBL (read for vocabulary, not built by this) | `1QFaboCAS4UaUVer6LigMDpcHrrvwADSW` | published |

## On the mirror

Every file in `docs/` carries a header naming its Drive ID and export date.
**The Google Doc is canonical; edit it there and re-export.** Editing the
markdown copy instead produces two disagreeing versions of a governing document,
which is worse than having one — a drifted rule still reads as authoritative.
