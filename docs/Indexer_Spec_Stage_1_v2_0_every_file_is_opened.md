<!-- MIRRORED FROM GOOGLE DRIVE. The Doc is canonical; edit it there.
     name     : Indexer Spec - Stage 1 v2.0 (every file is opened)
     drive_id : 1kABU-BCwXsXWHz8YmnCmbZPdYfjqPydHwlFSJihexuo
     modified : 2026-09-01
     exported : 2026-09-07 as markdown
-->

# **INDEXER SPEC — STAGE 1**

v2.0 — 2026-09-01. Supersedes v1.0. Governs the crawl that turns a Drive folder into DRIVE\_INVENTORY.

# **WHAT CHANGED, AND WHY v1.0 WAS WRONG**

v1.0 said: "Metadata only; nothing is opened, moved, or shared."

That sentence was the defect. It produced an index of 85 rows — 59 files — in which no column held what any file SAYS. site\_candidate and proposed\_section were 0/85 populated. The two fields meant to drive the site were never filled, because filling them requires reading the file and the spec forbade it.

The downstream cost was not theoretical. Eighteen meeting briefs sat in the folder containing the full project roster, every attendee, every decision. None of it entered the catalogue. When the Team page was built, fifteen people existed in the folder and six reached the page — and the missing nine were then attributed to a judgment call needing the advisor. They were not. Nobody had opened the files.

# **THE PRINCIPLE v1.0 VIOLATED**

An index of filenames is a directory listing. It is not an index.

The Information Systems Architecture is built ON the index. If the index does not know what is in the cabinet, the architecture is guessing, and every later stage inherits the guess. Going through the whole folder IS the preliminary work — it is not a step to get past on the way to building.

Andrew, 2026-09-01: "go through all of that Google Drive folder that I give you, index everything... you shouldn't try to shorten it or get it done fast or just get it done, because to me that's the most important part."

# **THE RULE**

EVERY FILE IS OPENED AND READ. A file that cannot be read is recorded as unread WITH THE REASON. There is no third option, and "it looked unimportant" is not a reason — importance is an output of the index, not an input to it.

# **TWO PASSES**

PASS A — INVENTORY (metadata). Unchanged from v1.0. One row per file and folder: id, name, mime, size, link, path, depth, created, modified, owner, sharing, sensitivity tier and tier reason. Cheap, complete, no file opened.

PASS B — READ (content). Every file from Pass A is opened. Pass B fills the columns that make the index an index:

opened            yes / no  
not\_opened\_reason required when opened \= no. e.g. "scanned image, no text layer"; "22MB video, needs transcription". Never blank, never "n/a".  
doc\_type          what kind of thing it is: meeting brief, transcript, research report, roster, log spreadsheet, flyer, image, video, email thread, plan, evaluation.  
what\_it\_says      two to three sentences, written from reading it. Not the filename restated.  
key\_entities      people and organisations named in it. This is where a roster comes from.  
key\_dates         dates the content is about, not the file's modified date.  
priority          P1 governs the architecture · P2 substantive content · P3 supporting · P4 excluded/noise  
priority\_reason   why that priority. A priority without a reason is a guess.  
extracted\_to      which catalogue tab the content landed in. THIS IS THE LANDING RULE MADE AUDITABLE — a P1 or P2 file whose content went nowhere is a defect, visible in one column.  
chars\_read        volume actually processed. Distinguishes read from skimmed.  
indexed\_by        which agent produced the row.  
indexed\_at        timestamp.

site\_candidate and proposed\_section are filled in Pass B, not left empty. They were the point.

# **MULTI-AGENT EXECUTION — REQUIRED, NOT AN OPTIMISATION**

Pass B runs as parallel subagents, each taking a slice of the file list. This is required because the single-threaded alternative is what produces the shortcut: a lone agent reading 59 files in one context runs low on room and starts summarising instead of reading, and the summarising is invisible in the output.

Protocol:  
1\. Orchestrator partitions Pass A files into slices of 6-10, grouped by folder so related material stays together.  
2\. One subagent per slice. Each opens EVERY file in its slice and returns one structured row per file.  
3\. Each subagent reports its measured token usage. The orchestrator records it verbatim in RUN\_DEVLOG.  
4\. A subagent that cannot read a file returns opened=no with the reason. It does not omit the row.  
5\. The orchestrator writes rows to DRIVE\_INVENTORY and never edits a subagent's finding to make it tidier.  
6\. Coverage is asserted: rows returned \== files in Pass A. A shortfall is a stop, not a rounding error.

# **MANDATORY LEDGER**

Every step of both passes writes to RUN\_DEVLOG via run\_ledger.py: what was read, chars processed, seconds, measured subagent tokens, and every skip with its reason. Subagent tokens are measured; the orchestrator's own are an estimate and are labelled as such. Never report an estimate as a measurement.

The ledger exists so an auditor can establish whether a step actually did the work, rather than taking the agent's later account of it. The account was wrong once already.

# **EXIT CONDITION**

Stage 1 is complete when, and only when:  
1\. Every file from Pass A has a DRIVE\_INVENTORY row.  
2\. Every row has opened=yes, or opened=no with a reason.  
3\. Every opened row has doc\_type, what\_it\_says, key\_entities, priority and priority\_reason.  
4\. Every P1 and P2 row has extracted\_to naming a tab that holds its content.  
5\. RUN\_DEVLOG covers the run, and its coverage count matches Pass A.

A partially-read index does not advance to Stage 2\. The Charter is written against what is actually in the folder, and it cannot be.

# **IMPLEMENTATION**

.agents/scripts/drive\_indexer.py — Pass A.  
.agents/scripts/run\_ledger.py — the ledger, used by both passes.  
Pass B orchestration is agent work, not a script: the reading is judgment, and the spec's job is to make the judgment complete and auditable rather than to automate it away.  
