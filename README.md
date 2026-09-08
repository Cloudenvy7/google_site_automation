# google_site_automation

Turning a client's Google Drive folder into an internal Google Site — indexing
the folder, deciding what belongs on the site and why, and placing the blocks,
with every decision recorded with its reason.

Part of Andrew Powers' Advisor OS / Visual Second Brain practice system
(BlackFox Studios). The governing documents, the substrate and the extraction
pipeline live in the private `Cloudenvy7/advisor-os` repository. **This repo is
the Sites publishing track only.**

## Start here

1. **`skills/information_systems_architecture/SKILL.md`** — the procedure. Load
   it before touching a Site or a client Drive folder.
2. **`skills/information_systems_architecture/references/FIRST_TRY_CHECKLIST.md`**
   — read before placing a single block. Every line on it cost at least one
   rebuild.
3. **`DEVLOG.md`** — what was built 2026-08-28 → 09-07, including the failures
   and what each one produced.

## The rule that governs the rest

> **The Landing Rule** — information lands in the sheet before it lands on the
> page. Gathering is proven in the catalogue, never on the site.

The sheet is the only place where absence is visible. A page with six people
looks finished; a roster tab with six rows and an evidence column shows
immediately that nobody counted. A projection cannot be evidence of the thing it
projects.

## Order of work — stages do not overlap

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

The ISA is written at **Stage 0**, before the folder is indexed — not between
analysis and build, which is where it keeps getting pushed. A harness written
after the build is an audit; its authority comes from arriving early.

## Why browser automation

Google Sites has no public write API. Driving the editor front end over the
**Chrome DevTools Protocol** is the sanctioned surface, not a workaround. Two
house rules apply to every helper here:

1. **Read back after every action.** A click that returned SUCCESS is not
   evidence the editor changed.
2. **Fail loudly.** Helpers return `NOT_FOUND` / `TIMEOUT` rather than
   pretending.

Every failure this codebase guards against **passed its own verification**. A
builder that confirms "the block is on the page" passes while the page is
scrambled, incomplete, or built on top of something it destroyed. So the guards
do not ask whether the artifact looks right — they ask whether the method was
followed, which is the thing the artifact cannot show you.

## Scripts

| File | What it is |
|---|---|
| `sites_automation.py` | Sites-over-CDP primitives; `probe_controls()` so selectors can be rediscovered rather than guessed |
| `chrome_automation.py` | The CDP transport, shared with the Docs pipeline |
| `harness.py` | The gates, guards and ledgers. One definition of each; `Refusal` is a distinct exception |
| `wireframe_build.py` | Geometric cell identity — mark cells before insert, the unmarked ones are this block's |
| `build_from_wireframe.py` | Stage 6 build from `PAGE_WIREFRAME`; imports the guards, does not re-derive them |
| `build_page.py`, `run_wireframe.py`, `build_blocks.py` | Block placement, per-block status for `SITE_SYNC_LOG` |
| `indexer_v3.py` | Resumable, sheet-as-state indexer built to run on a client's own Claude Pro account |
| `drive_indexer.py` | Stage 1 crawl (still on the v1.0 metadata-only contract — see Open) |
| `merge_index_pass_b.py` | Merges subagent output verbatim; refuses to write if coverage is short |
| `verify_index_integrity.py` | Independent re-derivation of char counts, keyed on `file_id` |
| `run_ledger.py` | `RUN_DEVLOG` — per-step reads, writes, skips-with-reason, timings |
| `extract_site_template.py`, `catalog_site.py` | Site → template catalogue; embeds recorded with contents via `data-code` |
| `capture_page_images.py` | Fixed-size page capture, verified non-blank |
| `drive_upload.py` | Native file-chooser upload over CDP |
| `sheet_write.py` | Browser writes to Sheets with read-back per cell |

## Hard-won specifics

These are measured, not assumed. The full list is in `FIRST_TRY_CHECKLIST.md`.

- **`clearDeviceMetricsOverride` returns ok and does nothing.** A screenshot that
  leaves a 1400px override makes every later coordinate wrong. It destroyed a
  finished page. Set the viewport explicitly at run start; abort if it does not
  take. **A diagnostic must not change the system it is diagnosing.**
- **Assert the page id from the live URL before any destructive step.** A click
  returning true is not evidence the click worked.
- **DOM index scoped to the block just placed** is the only stable cell address.
  Attributes vanish (Sites recycles nodes) and geometry goes stale (the editor
  scrolls an inner container, so `window.scrollY` is 0). Record the cell count
  before insert; the new block owns everything from that count on.
- **Layout cells fill column-major**, not row-major. A two-column layout owns
  **six** cells — media + heading + body per column.
- **Type at 0.11 s/char.** 0.04–0.05 transposes silently: `PAARGRAPH`.
- **Measure the preset; names lie.** "Four column image and captions" holds ONE
  caption per column. "Image and caption" is image-*left*, not stacked.
- **Verify images from the published page.** The editor lazy-renders them as
  `ar-gradient(...)` placeholders.
- **Clipboard paste works in Sheets grid cells and fails in Sites text boxes.**
- **Custom embeds are only catalogable via `data-code`.** Sites wraps them in a
  cross-origin gstatic shim, so the iframe `src` tells you nothing.
- `spreadsheets.create()` 403s for a service account (My Drive, zero quota).
  Use `drive.files.create` with `parents=[shared folder]`.
- Chrome launched from a non-desktop shell cannot reach the keyring and presents
  as logged out. Attach `DBUS_SESSION_BUS_ADDRESS`.

## Open — nothing here is done

1. **The paragraph build path is broken.** Layout blocks fill correctly; a plain
   `Text box` insert reports `ONLY_0_EMPTY_FOR_1_TEXTS`. Layouts work,
   paragraphs do not — and `paragraph` is the most common block type.
2. **GATE 6 refuses on HopeLink** — 53 P1/P2 files are read but `extracted_to`
   is empty. Content indexed, not landed in tabs. This is the Landing Rule
   working, not a bug.
3. **`drive_indexer.py` still implements the v1.0 metadata-only contract.** The
   spec is v2.0. `indexer_v3.py` is the v2.0-shaped path.
4. **The template itself is not derived.** One site (BFS X JBL) is decomposed
   into 8 pages and 100 blocks. "Template" means what is constant *across*
   sites, and that needs a second site run through the extractor and diffed.

## Requirements

Python 3, `websocket-client`, `google-api-python-client`,
`google-auth`, and a Chrome running with `--remote-debugging-port=9222` under an
authenticated Google session. A service account with Drive and Sheets scopes is
required for the indexers; its key file is **not** in this repo and never should
be.
