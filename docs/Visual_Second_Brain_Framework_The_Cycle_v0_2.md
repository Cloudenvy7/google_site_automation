<!-- MIRRORED FROM GOOGLE DRIVE. The Doc is canonical; edit it there.
     name     : Visual Second Brain Framework - The Cycle v0.2
     drive_id : 1G9MrBDKhs7UfrfHVauxcMw9_s09V3JgVT4QF8lI6Dy0
     modified : 2026-09-01
     exported : 2026-09-07 as markdown
-->

# **VISUAL SECOND BRAIN FRAMEWORK — THE CYCLE**

*v0.1 — 2026-08-31. The spine. This document names every stage of the cycle, the one artifact that governs each, and the canonical schema every per-site catalogue is copied from. Read this first. If a stage is being run without the artifact named here, stop.*

## **WHAT THIS IS**

A repeatable method for turning a client's Google Drive folder into an internal Google Site, where every decision about what appears is recorded with the reason it was made.  
The folder is the cabinet. The spreadsheet is the catalogue. The Site is the projection. The Sheet is always the intended state; the Site is always rebuildable from it.

## **WHY THIS DOCUMENT EXISTS**

Two per-site catalogues were built before this spine existed and they had already diverged — one with five tabs, one with seven, neither matching the other. Drift in the catalogue schema is the failure that quietly corrupts everything downstream, because every later stage reads columns by name. This document is the fix: one canonical schema, one governing artifact per stage, and a status column that admits what is not yet built.

## **THE SIX STAGES**

**STAGE 1 — INDEX**  
Purpose: catalogue what is in the cabinet. Metadata only; nothing is opened, moved, or shared.  
Input: a Drive folder id.  
Output: DRIVE\_INVENTORY, one row per file and folder, with a sensitivity tier.  
Governed by: Indexer Spec.  
Status: RUN ONCE (the first client, 85 rows) — spec and reusable script NOT YET WRITTEN.  
**STAGE 2 — CHARTER**  
Purpose: establish why the site exists and what belongs on it, in the client's words.  
Input: five questions, then a second grounded round after reading the inventory.  
Output: CHARTER — goals numbered GOAL-nn, each carrying the client sentence behind it.  
Governed by: Site Architect Master Prompt.  
Status: PROMPT WRITTEN (v0.2). Never run.  
**STAGE 3 — MANIFEST**  
Purpose: decide which files are in and which are out, and record why for both.  
Input: DRIVE\_INVENTORY \+ CHARTER.  
Output: MANIFEST — one row per file, decision, charter\_goal\_id, rule, tier.  
Governed by: Site Architect Master Prompt.  
Status: PROMPT WRITTEN. Tab does not exist in any catalogue.  
**STAGE 4 — PAGE PLAN**  
Purpose: decide which content sits on which page, in what order, and why.  
Input: MANIFEST.  
Output: PAGE\_PLAN — one tab, keyed by page\_id, one row per planned content item. No block column; rendering is not decided here.  
Governed by: Site Architect Master Prompt.  
Status: PROMPT WRITTEN. Tab shape not yet corrected in existing catalogues.  
**\=== THE GATE \===**  
The advisor ratifies the Charter, the Manifest and the Page Plan. Nothing is built before this. The council proposes with reasoning; the human ratifies. Refusal is a valid deliverable. Exclusions are recorded.  
**STAGE 5 — RENDER**  
Purpose: choose how each planned item is displayed.  
Input: ratified PAGE\_PLAN \+ the verified block catalogue.  
Output: SITE\_CONTENT\_BLOCKS and the per-page wireframe, with block types and cell maps.  
Governed by: Render Prompt.  
Status: NOT WRITTEN. This is the hole between analysis and build.  
**STAGE 6 — BUILD**  
Purpose: make the Site match the sheet.  
Input: SITE\_CONTENT\_BLOCKS.  
Output: a published Site; every run logged to SITE\_SYNC\_LOG.  
Governed by: Build Protocol.  
Status: v0.4 written. Builder places layouts correctly; plain paragraphs currently fail.  
**THROUGHOUT — AUDIT**  
A separate instance verifies each stage. Maker is never checker.  
Governed by: QA Auditor Prompt.  
Status: NOT WRITTEN.

## **THE CANONICAL PER-SITE CATALOGUE**

Every site gets ONE workbook, copied from the template, never hand-assembled. Tabs, in this order, with these names:  
00\_README · DRIVE\_INVENTORY · CHARTER · MANIFEST · PAGE\_PLAN · SITE\_PAGES · SITE\_CONTENT\_BLOCKS · SITE\_ASSETS · SITE\_SYNC\_LOG  
SITE\_PAGES carries managed\_by (PROP-007): agent-owned pages are rebuilt wholesale, human-owned pages are never touched. The rebuild strategy depends on it.  
A catalogue missing a tab is not a smaller catalogue; it is a broken one. Later stages read columns by name and fail silently when a name moves. If a tab genuinely does not apply to a site, it stays present and empty.  
The substrate does NOT hold this content. It holds a pointer to it — a RES- row in 06\_RESOURCES. The substrate's P\_SITE\_\* tabs are per-project TEMPLATES to be copied into a catalogue, not shared containers for every site.

## **THE BINDING RULE**

Every MANIFEST row cites a charter\_goal\_id. A row without one is invalid and does not execute. This mirrors the substrate's rule that every relation cites a source\_event\_id — provenance applied to content decisions rather than to facts.  
Read backwards, this means any block on a finished site can be traced to the sentence the client said that put it there.

## **DOCUMENT REGISTER**

Framework spine — this document — v0.1 — WRITTEN  
Indexer Spec — stage 1 — NOT WRITTEN  
Site Architect Master Prompt — stages 2, 3, 4 — v0.2 — WRITTEN, UNTESTED  
Render Prompt — stage 5 — NOT WRITTEN  
Build Protocol — stage 6 — v0.4 — WRITTEN  
QA Auditor Prompt — throughout — NOT WRITTEN  
Per-Site Catalogue Template — the schema — v1.0 — BUILT 2026-08-31  
Block Catalogue — 13\_BLOCK\_RECIPES — 2 of 13 verified

## **ORDER OF CONSTRUCTION**

1\. This spine.  
2\. Per-Site Catalogue Template — DONE v1.0. Nine tabs. Everything downstream reads it.  
3\. Indexer Spec — makes stage 1 repeatable rather than bespoke.  
4\. Render Prompt — closes the hole between the gate and the build.  
5\. QA Auditor Prompt — required by Delta 2; note it CREATES the role rather than upgrading one, since the Antigravity blueprint that held a QA Auditor is not recoverable.  
6\. Block Catalogue verification — raise 2-of-13 by proving recipes, not by asserting them.

## **OPERATING PRINCIPLE**

Build only after everything has been considered. Building feels like progress in a way that analysis does not, and that feeling is the thing to distrust.

TWO KINDS OF CONTENT — SELECTED AND AUTHORED

Ratified 2026-08-31, after the first full run of the cycle produced an empty Home page.

SELECTED content comes from the cabinet. A Drive file, chosen by the Manifest, traced by  
manifest row id.

AUTHORED content is written because it does not exist in the folder. Orientation, executive  
summaries, page descriptions, the note about what the site deliberately does not hold. None  
of that is a file anyone filed.

BOTH MUST TRACE. Selected items trace to a Manifest row. Authored items trace DIRECTLY to a  
Charter goal, written as "authored: GOAL-nn". An item with neither trace is invalid.

This closes the hole the first audit found: eleven Home items had no Manifest row, which was  
correct behaviour failing an incorrect check. The rule was missing, not the data.

THE HOME PAGE IS ALWAYS MOSTLY AUTHORED. It is a README and an executive summary, readable  
by a high school freshman in under five minutes, with a map of every other page beneath it.  
Selection alone can never produce it. A Page Plan that routes every included file to a  
content page and leaves Home empty has done the selection correctly and the site badly.

THE BINDING RULE APPLIES TO EXCLUSIONS TOO. Every Manifest row cites a charter\_goal\_id —  
includes AND excludes. The first run left twenty-six folder rows without one, on the  
assumption that structural exclusions did not need justifying. They do: folders are excluded  
under the goal that the site exists so nobody has to navigate folders. If an exclusion  
cannot name the goal it serves, the rule behind it has not been thought through.

ADDED 2026-08-31 — THE BUILD HARNESS  
The Cycle names the stages. It did not say what STOPS when a stage is run wrong, and four failures in four days went through it unimpeded — a build proposed with no ISA, a destructive routine run on the wrong page, a preset assumed rather than measured, and a Team page shipped with 6 of 15 people while the catalogue said ROSTER NOT ESTABLISHED. Every one passed its own verification.  
The Build Harness — Gates, Guards and Ledgers v1.0 is the enforcement layer: gates fire before a stage and block it, guards fire during execution and abort it, ledgers record what happened including what did not. Its central rule is THE LANDING RULE — information lands in the sheet before it lands on the page; gathering is proven in the catalogue, never on the site. The sheet is the only place where absence is visible.  
Document: https://docs.google.com/document/d/1\_4107tyX6IPRDxBfCXjheSkWBpd4cT7QwdOPzz9Set8/edit  
Implemented by: .agents/scripts/harness.py  
Register status: Build Harness — enforcement, all stages — v1.0 — WRITTEN, FIRES ON REAL DATA

CORRECTION 2026-09-01 — THE HARNESS IS STAGE 0, NOT AN ENFORCEMENT LAYER ADDED AFTERWARDS  
The entry added above on 2026-08-31 described the Build Harness as an enforcement layer derived from four failures and registered into a live site. That framing was wrong and is superseded. Both versions are kept per the never-overwrite rule.  
A harness written after the build is an audit. It cannot prevent anything, because by the time it exists the drift has already happened. The harness is a STARTING TEMPLATE, instantiated on the day a site's work opens — before the folder is indexed, before the client is asked anything, before any evaluation. Its authority comes from arriving early.

THE SIX STAGES ARE NOW SEVEN. STAGE 0 — HARNESS is added before STAGE 1 — INDEX.  
Purpose: put the method in place before there is any work to get wrong.  
Input: a new site.  
Output: catalogue copied from template with 00\_HARNESS and WAIVERS present; 00\_README Stage 0 keys filled; the Information Systems Architecture for this site WRITTEN AND RATIFIED.  
Governed by: TEMPLATE \- Build Harness and Guardrails v2.0.  
Note: the ISA is written before the first file is indexed — not between analysis and build. Stage 0 produces nothing a client would recognise, and skipping it for that reason is the specific temptation it exists to defeat.

THE CANONICAL PER-SITE CATALOGUE IS NOW ELEVEN TABS, NOT NINE:  
00\_HARNESS · WAIVERS · 00\_README · DRIVE\_INVENTORY · CHARTER · MANIFEST · PAGE\_PLAN · SITE\_PAGES · SITE\_CONTENT\_BLOCKS · SITE\_ASSETS · SITE\_SYNC\_LOG  
00\_HARNESS is the gate checklist; a blank status column is a stop, not an omission. WAIVERS is the only legitimate way past a flagged gap, and a waiver is a human act — the agent proposes, it does not grant. As with every other tab: a catalogue missing one is not a smaller catalogue, it is a broken one.

THE SECOND BINDING RULE — THE LANDING RULE  
The Cycle already binds every manifest row to a charter\_goal\_id. The Landing Rule binds content to the catalogue itself: information lands in the sheet before it lands on the page; gathering is proven in the catalogue, never on the site. The sheet is the only place where absence is visible — a finished-looking page proves nothing about what is missing from it.  
Document: https://docs.google.com/document/d/1\_4107tyX6IPRDxBfCXjheSkWBpd4cT7QwdOPzz9Set8/edit  
Implemented by: .agents/scripts/harness.py  
Register: Build Harness — STAGE 0 template, governs all stages — v2.0 — WRITTEN, SHIPS IN THE CATALOGUE TEMPLATE

ADDED 2026-09-01 — THE TEMPLATE SET IS COMPLETE, AND IT IS NOW A SKILL  
An audit of every framework document for site-specific content found the Site Architect, Render and QA Auditor prompts, the Block Catalogue, the Build Protocol and the Catalogue Template all clean. Two mentions of the first client remain, in this document and the Indexer Spec, and both are provenance — 'written from a run that actually happened' — which is worth keeping, because it marks those specs as evidence-based rather than designed.  
The real gap was that an ISA existed only as a the first client instance. There was no template. Three documents now close it:  
TEMPLATE \- Information Systems Architecture v1.0 — https://docs.google.com/document/d/15DWHdjKTuGoz\_Sr-E19HPm8xAts\_\_T3gWuXWPKcR-qw/edit  
Architecture Principles — https://docs.google.com/document/d/1QDeygsn1NslxVlH6OXWC9JnkvPH-EEymAmwxFoIf4Sk/edit  
First-Try Checklist — https://docs.google.com/document/d/1ADmv0f8IJJxzFDDd\_5LbiayCc-T7P9JvUgc3Xbgu1uI/edit  
The first client ISA is retained as a WORKED INSTANCE — read to see what a filled ISA looks like, never to copy pages, reader model or goals from. Reusing another site's architecture is the drift the template exists to prevent.  
All of it is packaged as the Claude Code skill 'information\_systems\_architecture', which loads the reading order, the stage order and the gates automatically when a site build opens. The skill carries each principle with the failure attached, so a later session can evaluate a rule rather than obey or discard it blindly.  
Register: Information Systems Architecture — stage 0 template \+ skill — v1.0 — WRITTEN  
