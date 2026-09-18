<!-- MIRRORED FROM GOOGLE DRIVE. The Doc is canonical; edit it there.
     name     : TEMPLATE - Build Harness and Guardrails v2.0 (instantiate at Stage 0)
     drive_id : 1_4107tyX6IPRDxBfCXjheSkWBpd4cT7QwdOPzz9Set8
     modified : 2026-09-08
     exported : 2026-09-07 as markdown (re-exported after the v2.1 / GUARD 9 correction was appended)
-->

# TEMPLATE — BUILD HARNESS AND GUARDRAILS

v2.0 — instantiated at STAGE 0, before any evaluation begins.

THIS IS A STARTING ARTIFACT, NOT A POST-MORTEM. It is copied into a site's catalogue on the day that site's work opens — before the Drive folder is indexed, before the client is asked anything, before a single decision about content is made. It states what is supposed to happen and how the build is supposed to proceed, so that the method is in place before there is any work to get wrong.

v1.0 was written the other way round: after the failures, into one live site, as a description of controls that already existed. That is an audit, not a harness. A harness that arrives after the build cannot prevent anything.

# WHY IT GOES FIRST

The failure mode this exists to stop is not carelessness. It is an agent moving faster than the method and producing output that no one can distinguish from correct output. Every failure this template encodes PASSED ITS OWN VERIFICATION at the time it happened.

That is the whole problem in one sentence. A builder that confirms "the block is on the page" reports success while the page is scrambled, incomplete, or built on top of something it destroyed. Checking the artifact cannot catch it, because the artifact looks fine. Only the method can catch it, and only if the method is in place first.

So the harness is instantiated before there is anything to check. Its authority comes from arriving early.

# THE STANDING INSTRUCTION

Everything below is advisory in tone and binding in force. An agent reading this does not weigh it against its own judgment about what would be faster. If a rule seems wrong for this site, that is a question for the human, not a licence to proceed.

# STAGE 0 — INSTANTIATE THE HARNESS

Nothing else begins until all four are true:

0.1  Copy the per-site catalogue template. Never hand-assemble. All tabs present, including 00\_HARNESS and WAIVERS, even where they are empty.  
0.2  Fill 00\_README: site\_name, drive\_folder\_id, isa\_doc\_id, isa\_status, harness\_doc\_id, harness\_version. isa\_status starts as NOT WRITTEN. That is a correct starting value, not a gap.  
0.3  Write the Information Systems Architecture for this site, and have the human ratify it. THE ISA IS WRITTEN BEFORE THE FIRST PAGE IS INDEXED, NOT BETWEEN ANALYSIS AND BUILD.  
0.4  Record the harness version in 00\_README so a later reader knows which rules governed this build.

Stage 0 has no deliverable a client would recognise. That is expected. Skipping it because it produces nothing visible is the specific temptation this stage exists to defeat.

# THE ORDER OF WORK

The order is not a suggestion and stages do not overlap.

0  HARNESS ....... this document, instantiated. ISA written and ratified.  
1  INDEX ......... catalogue the folder. Metadata only. Nothing opened, moved or shared.  
2  CHARTER ....... why the site exists, in the client's words. Goals numbered, each carrying the sentence behind it.  
3  MANIFEST ...... what is in and what is out. Both decisions recorded, with the reason.  
4  PAGE PLAN ..... what sits on which page, in what order, and why. No block types yet.  
   \>\>\> THE GATE — the human ratifies Charter, Manifest and Page Plan. Nothing is built before this. \<\<\<  
5  RENDER ........ how each planned item is displayed. Block types and cell maps, from measured presets.  
6  BUILD ......... make the Site match the sheet. Every run logged.  
   THROUGHOUT .... a separate instance audits. Maker is never checker.

Analysis is complete before rendering is considered. Rendering is complete before building starts. An agent that reaches for a block type while the charter is still open has skipped two stages.

# THE LANDING RULE

INFORMATION LANDS IN THE SHEET BEFORE IT LANDS ON THE PAGE. GATHERING IS PROVEN IN THE CATALOGUE, NEVER ON THE SITE.

If a name, date, role, number or sentence will appear on the Site, it must first exist as a cell in the catalogue with its source recorded. Not summarised into the catalogue afterwards. First.

The reason is not tidiness. THE SHEET IS THE ONLY PLACE WHERE ABSENCE IS VISIBLE. A finished-looking page proves nothing about what is missing from it; a tab with a source\_evidence column shows the gap immediately. A projection cannot be evidence of the thing it projects.

Two corollaries that carry most of the weight in practice:

\- When you are pulling information, you cannot skip. You go back and put it into the spreadsheet, and that is how it is determined that all the information is gathered.  
\- The correct response to missing information is to GO AND LOOK, then write rows. It is not to write a flag and build around it.

# THE GATES — preconditions, per stage

Each gate is a question the human can also ask, answered by the catalogue rather than by the agent's reasoning.

## GATE 1 — ARCHITECTURE BEFORE ANYTHING

Fires at: Stage 0 exit.  
Check: 00\_README names an isa\_doc\_id and isa\_status is RATIFIED.  
On failure: stop. Write the ISA. A "quick version to see how it looks" is the same failure in different words.

## GATE 2 — THE LANDING RULE

Fires at: Stage 5 entry and again at Stage 6 entry.  
Check: every value in the wireframe resolves to a source tab and row. The builder reads the sheet and never accepts inline content from a prompt.  
On failure: stop. Gather the values into a tab first.

## GATE 3 — A FLAGGED GAP BLOCKS ITS OWN BLOCK

Fires at: Stage 6 entry.  
Check: no row carrying UNKNOWN, NOT ESTABLISHED, TBD or NOT RECORDED has a dependent block in the build set.  
On failure: stop. Search the archive. A waiver is a human act, recorded in WAIVERS with a name and a date. An honest flag that stops nothing is decoration.

## GATE 4 — EVERY RENDERED ROW CITES A CHARTER GOAL

Fires at: Stage 3, 4 and 5 exit.  
Check: wireframe row \-\> page plan row \-\> manifest row \-\> charter\_goal\_id, unbroken.  
On failure: attach the goal, or exclude the row and record the exclusion.  
Read backwards this means any block on a finished site traces to the sentence the client said that put it there.

## GATE 5 — RATIFICATION

Fires at: THE GATE, between Stage 4 and Stage 5\.  
Check: Charter, Manifest and Page Plan carry ratified\_by and ratified\_date.  
The council proposes with reasoning; the human ratifies. Refusal is a valid deliverable. Exclusions are recorded.

# THE GUARDS — invariants during Stage 6

## GUARD 1 — ASSERT THE TARGET BEFORE DESTROYING

Read the target's identity back from the environment and match it against the intended target. A click returning true is not evidence that the click worked.

## GUARD 2 — OWN THE ENVIRONMENT, NEVER INHERIT IT

Set the viewport explicitly at the start of every run and abort if it does not take. Leave nothing altered for the next run. A DIAGNOSTIC MUST NOT CHANGE THE SYSTEM IT IS DIAGNOSING — screenshots and probes are the first suspects when later steps behave strangely.

## GUARD 3 — ADDRESS CELLS BY INDEX, SCOPED TO THE BLOCK JUST PLACED

Record the cell count before an insert; the new block owns the cells from that count onward. Fill only those. "First empty cell on the page" wanders.

## GUARD 4 — READ BACK THROUGH THE SURFACE A HUMAN SEES

Verify text through its contenteditable, not the container. Verify images from the published page, not the editor.

## GUARD 5 — MEASURE THE PRESET, DO NOT TRUST ITS NAME

A preset's shape is established by placing it and reading it back, and the measurement is recorded in the block catalogue before it is used.

## GUARD 6 — TYPE SLOWLY ENOUGH TO BE CORRECT

Character transposition is silent and survives verification that only checks presence. Throughput is the cost of correctness.

## GUARD 7 — NEVER FABRICATE A VALUE TO FILL A CELL

If the source does not state it, the cell says what is missing. A blank with a reason outranks a plausible guess.

# THE LEDGERS — after

LEDGER 1  Every run writes to SITE\_SYNC\_LOG: successes, failures and open defects. An unlogged failure is rediscovered from scratch next session.  
LEDGER 2  Every entity on a page has a row carrying evidence and confidence. Affiliation is evidenced, never inferred from a name.  
LEDGER 3  Corrections supersede visibly. Both versions survive; the correction is marked.  
LEDGER 4  A recipe is "verified" only with its method of verification named. Unchecked claims say so.

# THE STOP TEST

Before any build run, all five must be yes. Any no is a stop, not a caveat.

1  Does this site have a ratified Information Systems Architecture?  
2  Does every value about to be rendered already exist as a cell in the catalogue?  
3  Is every dependent row free of unresolved flags, or explicitly waived by the human?  
4  Does every row trace to a charter goal?  
5  Has the human ratified Charter, Manifest and Page Plan?

# WHAT THIS DOES NOT DO

It does not make the build correct. It makes the build STOPPABLE, and it makes incompleteness visible in the one place that can show it. Judgment about a client, a community's work or a relationship stays human. The AI assists; it does not author.

# APPENDIX A — WHERE EACH RULE CAME FROM

Kept separate from the operating rules above, because a rule is followed on its own terms, not because of a story. Recorded so the next session can evaluate a rule rather than obey or discard it blindly. All from the first client site build, 2026-08-28 to 08-31.

GATE 1  Build was proposed twice with no ISA written. Stopped both times by the human: "the whole point of this was the right the information systems architecture now before spending a second building."  
GATE 2  A Team page shipped with 6 people. Fifteen were present in the source folder throughout. Names had been typed from an agent's recall of a conversation instead of read from a tab, so the page inherited the agent's memory rather than the folder's contents. The roster was recoverable in full from the meeting logs; nobody had looked.  
GATE 3  The catalogue said ROSTER NOT ESTABLISHED. The page was built around it with one client name. The flag was recorded honestly and ignored operationally.  
GATE 4  Twenty-six rows were found carrying no charter goal during an audit; the binding rule existed but nothing enforced it.  
GUARD 1  A page-selection click returned success and landed nowhere. The clear routine then deleted eighteen sections from a finished Home page and rebuilt another page's content onto it.  
GUARD 2  A screenshot set a 1400px device-metrics override and did not clear it. The clear call returns ok and does nothing. Every later coordinate was computed against a layout the editor was not using — which is what caused GUARD 1's failure.  
GUARD 3  Three separately scrambled pages. Attribute tags do not survive re-rendering; geometry fails because the editor scrolls an inner container.  
GUARD 4  A newly inserted text box renders its style picker inside the cell, so an emptiness test read "Normal text / Title / Heading" and concluded the box was occupied. Three text boxes placed, none filled, run reported clean. Separately, the editor lazy-renders images, and five real images were reported as empty.  
GUARD 5  "Four column image and captions" was assumed to hold a name and a role per column. It holds ONE caption per column. Eight values went into four slots; two people vanished silently and the build reported success.  
GUARD 6  Typing at 0.04 and 0.05 seconds per character transposed characters — "PAARGRAPH", "Prgoramm eContext". 0.11 is clean.  
GUARD 7  Four programme staff have no stated role anywhere in the source folder. Two people appear by first name because no surname exists in any file.  
LEDGER 2  An organisation was assigned from a name rather than evidence, placing a consultant inside the client organisation. Email domains in a message thread settled it correctly.

# APPENDIX B — INSTANTIATION CHECKLIST

Copy into the new catalogue's 00\_HARNESS tab and work down. The build does not start until every row reads PASS or WAIVED.

AMENDMENT 2026-09-01 — THE INDEX GATE AND THE RUN LEDGER  
Added after Andrew identified the failure the v2.0 gates did not cover: not a single dramatic mistake, but a pattern of taking the cheaper path at every step — placing a text box where the plan specified an element block, assuming a preset instead of measuring it, indexing filenames instead of opening files — and then attributing the accumulated cost to a judgment call that needed the human. The attribution was wrong and it was unfalsifiable, because nothing recorded what each step had actually done.

GATE 6 — THE INDEX IS COMPLETE BEFORE THE CHARTER IS WRITTEN  
Fires at: Stage 1 exit.  
Check: every file has a row; every row has opened=yes or opened=no WITH A REASON; every opened row has doc\_type, what\_it\_says, key\_entities, priority and priority\_reason; every P1 and P2 row has extracted\_to naming a tab that holds its content.  
On failure: stop. A partially-read index does not advance. The Charter is written against what is actually in the folder, and it cannot be.  
Reasoning: an index of filenames is a directory listing, not an index. The architecture is built ON the index; if the index does not know what is in the cabinet, the architecture is guessing and every later stage inherits the guess. Going through the whole folder IS the preliminary work. Evidence: an 85-row inventory in which site\_candidate and proposed\_section were 0/85 populated, and eighteen briefs containing the full project roster were never opened.

GUARD 8 — READ EVERY FILE; RECORD EVERY FILE NOT READ  
A file that cannot be read is recorded as unread with the reason. There is no third option, and 'it looked unimportant' is not a reason — importance is an OUTPUT of the index, not an input to it.  
Pass B runs as parallel subagents by requirement, not as an optimisation: a lone agent reading dozens of files in one context runs low on room and begins summarising instead of reading, and the summarising is invisible in the output. Coverage is asserted — rows returned must equal files found. A shortfall is a stop, not a rounding error.

LEDGER 5 — RUN\_DEVLOG ON EVERY STEP  
Every step records what it read, chars processed, seconds elapsed, measured subagent tokens, and EVERY SKIP WITH ITS REASON. A skip without a reason is refused by the ledger itself.  
Subagent token usage is MEASURED and recorded verbatim. The orchestrating session's own token usage is not available to it programmatically, so the ledger records content volume and marks any derived figure as an ESTIMATE with its divisor. An estimate is never reported as a measurement.  
The ledger exists so an auditor can establish whether a step did the work, rather than taking the agent's later account of it. The account was wrong once already.  
Implemented by: .agents/scripts/run\_ledger.py — writes to the RUN\_DEVLOG tab of the catalogue.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

CORRECTION — GUARD 9 ADDED, 2026-09-07 — COVERAGE IS PROVEN, NOT CLAIMED  
Ratified by Andrew Powers, 2026-09-07. Appended; Guards 1–8 above stand.

GUARD 9 — coverage is proven, not claimed. Fires DURING Stage 1 commit. Failure: verify\_index\_integrity.py compared the agent's reported chars\_read to a re-derived count — but the packet had handed the agent that number, so an agent that read nothing could echo it and pass. The orchestrator now plants unforgeable markers through chunked text (coverage.py) and the agent must hand them back; coverage is arithmetic on what was RETURNED. Any missing or fabricated marker is a Refusal and the row is not written. No-text files (image, video, scanned PDF) are exempt only because GUARD 7 already demands opened=no with a reason. The deterministic half: the indexing agent runs with Read-only tools, so the only way to see a marker is to read.

Regression test: evals/canary\_partial\_read.py — a synthetic fact at 93% of a long file must reach the row, and a deliberately partial read must be refused. A guard that never fires is indistinguishable from no guard. Full text: Indexer Spec v2.1.  
