# START HERE

Everything for the Google Sites automation track lives in this repository: the
governing documents, the code that enforces them, and the development log.

**One thing is deliberately not here: the live Sheets.** They are working data,
not artifacts. Copying them into git would create a second copy that goes stale
the moment someone edits the real one, and *Sheets are truth — Docs, Sites and
catalogues are projections.* They are linked below instead.

---

## Read in this order

| # | Read | Why |
|---|---|---|
| 1 | [`skills/information_systems_architecture/SKILL.md`](skills/information_systems_architecture/SKILL.md) | The procedure. Load this before touching a Site or a client folder. |
| 2 | [`docs/TEMPLATE_Build_Harness_and_Guardrails_v2_0_instantiate_at_Stage_0.md`](docs/TEMPLATE_Build_Harness_and_Guardrails_v2_0_instantiate_at_Stage_0.md) | Stage 0. Gates 1–6, Guards 1–8, Ledgers 1–5, each with the failure that produced it. |
| 3 | [`docs/Visual_Second_Brain_Framework_The_Cycle_v0_2.md`](docs/Visual_Second_Brain_Framework_The_Cycle_v0_2.md) | The whole cycle, Stage 0 through Stage 6. |
| 4 | [`skills/information_systems_architecture/references/FIRST_TRY_CHECKLIST.md`](skills/information_systems_architecture/references/FIRST_TRY_CHECKLIST.md) | Every line cost at least one rebuild. Read before placing a block. |
| 5 | [`DEVLOG.md`](DEVLOG.md) | What was built, what failed, and what each failure produced. |

## The cycle — document and code, per stage

| Stage | Governing document | Code |
|---|---|---|
| **0 · HARNESS** | `docs/TEMPLATE_Build_Harness_and_Guardrails_v2_0...md`<br>`docs/TEMPLATE_Information_Systems_Architecture_v1_0.md` | `scripts/harness.py` |
| **1 · INDEX** | `docs/Indexer_Spec_Stage_1_v2_0_every_file_is_opened.md` | `scripts/indexer_v3.py` *(current)*<br>`scripts/drive_indexer.py` *(v1.0 contract — superseded)*<br>`scripts/merge_index_pass_b.py`, `scripts/verify_index_integrity.py` |
| **2 · CHARTER** | `docs/Advisor_OS_Site_Architect_Master_Prompt_v0_3.md` | — |
| **3 · MANIFEST** | same | — |
| **4 · PAGE PLAN** | same | — |
| | **>>> THE GATE — the human ratifies Charter, Manifest, Page Plan <<<** | |
| **5 · RENDER** | `docs/Advisor_OS_Render_Master_Prompt_v1_0.md`<br>`docs/BFS_Block_Catalogue_The_House_Patterns_v1_3.md` | `scripts/extract_site_template.py`, `scripts/catalog_site.py` |
| **6 · BUILD** | `docs/Google_Sites_Automation_Build_Protocol_v0_4.md` | `scripts/build_from_wireframe.py`, `scripts/wireframe_build.py`,<br>`scripts/build_page.py`, `scripts/sites_automation.py`,<br>`scripts/drive_upload.py`, `scripts/capture_page_images.py` |
| **audit** | `docs/Advisor_OS_QA_Auditor_Master_Prompt_v1_0.md` | `scripts/run_ledger.py` (`RUN_DEVLOG`) |

Reference, not stage-bound:
`docs/Architecture_Principles_what_makes_a_site_architecture_correct_v1_0.md`,
`docs/First_Try_Checklist_Google_Sites_build_v1_0.md`.

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
