# DEVLOG — Google Sites Automation

The running record of what was built on this track, when, and why.

**This entry is mirrored.** The canonical practice-wide log is
`07_Changelog/DEVLOG.md` in the private `Cloudenvy7/advisor-os` repository,
where this same entry sits alongside the substrate and extraction-pipeline
history. This file is the Sites-track extract. **A correction made in one must
be made in the other** — two copies of a log drift, and a drifted log is worse
than no log because it still reads as authoritative.

________________

## 2026-09-13 — Make the repository portable: it documented a system that only ran on one machine

Author: Claude Code (claude-opus-5) + Andrew Powers. Andrew, 2026-09-13:
*"yeah fix the stand alone google site automation repo becuase that is where
everythign is actually supposed to go"* — ratifying this repo, not
`advisor-os`, as the thing a client clones.

### What prompted it

A review of what was actually pushed, against the goal Andrew stated: *"pull
onto a new computer and run it on the claude account of the user and computer
so they can run it on their own accounts claude and google."*

The doctrine layer was complete and the code worked. **Neither fact survived
leaving this machine.** The gap was not in what the system does; it was that
nothing in the repository had ever been executed anywhere else, so every
machine-specific assumption was still load-bearing and invisible.

### 1. Four scripts existed only on this laptop

The 2026-09-08 Highline StartZone build — `site_survey.py`,
`build_workshops.py`, `fetch_flyers.py`, `upload_to_drive.py`, 991 lines —
was committed to a Claude worktree branch and never pushed anywhere. Five days.
That branch is disposable by design; a cleanup would have taken the second-site
proof with it.

Pushed to `advisor-os` (`375b756..770f586`), then brought into this repo.

*The lesson is not "remember to push." It is that work living only on a branch
named after an ephemeral worktree is work that nothing is protecting.*

### 2. The skill was in a folder Claude Code does not read

`skills/information_systems_architecture/SKILL.md`. Claude Code discovers
skills under `.claude/skills/` only. A client cloning this repo would get the
ISA procedure as an inert file — **the governance model's entire enforcement of
stage order, silently absent**, with nothing to signal it.

Moved to `.claude/skills/`. Verified by the skill loading in-session.

### 3. There was no `CLAUDE.md`

`advisor-os` has one and it is the reason a session there starts grounded. This
repo had `START_HERE.md`, which is good and which nothing made an agent read.

Added, covering the Landing Rule, stage order, the six non-negotiables, and the
hook's refusal behaviour. **It is not a copy of the advisor-os one** — that file
governs the practice OS; this one governs a Site build.

### 4. Seven files named one person's home directory

`/home/tyler/Projects/Blackfox Studios/...` as a literal default in
`harness.py`, `indexer_v3.py`, `read_drive_file.py`, `drive_indexer.py`,
`merge_index_pass_b.py`, `verify_index_integrity.py`, `evals/run.sh`.

Four were env-overridable. **Two were not** — `drive_indexer.py` and
`merge_index_pass_b.py` had no override at all, so on a clone there was no way
to run them without editing source.

Worse: `merge_index_pass_b.py` hard-coded **HopeLink's catalogue id** and wrote
to it. On a client's machine that is not a crash. It is a successful write into
the wrong client's spreadsheet.

New `scripts/config.py` resolves all of it, most-explicit-first, and **raises
naming every location it looked in** rather than guessing. `catalogue_id()` has
no default and must not acquire one.

### 5. A regression I introduced, and how it surfaced

Moving the credential lookup to `config.service_account_path()` at module level
made `indexer_v3.py` **raise on import** — breaking the coverage eval, which
imports it to test pure functions. It had not raised before only because the
hard-coded path made it silently wrong instead of loudly absent.

Caught by running the evals, not by reading the diff. Fixed by resolving inside
the functions that need Google. *Importing a module must never require a
credential.*

### 6. The skill pointed clients at a Drive folder they cannot reach

`SKILL.md` step 1 resolves eleven governing documents by Drive id, from the
Blackfox Studios shared drive, via a service account granted to it. On a client
machine that is eleven 404s.

`docs/` already mirrors all eleven. Recorded as a visible **CORRECTION**
appended below the table, not an edit — the original is correct in `advisor-os`
where it was written, and the difference between the two repos is itself the
thing worth knowing. Same correction covers `.agents/scripts/` → `scripts/`.

### 7. Packaging

`requirements.txt` (three direct deps, lower bounds, proven on Python 3.13.5),
`.env.example`, `SETUP.md`, and `scripts/launch_chrome.sh` — which refuses
quietly-wrong setups by warning when `DBUS_SESSION_BUS_ADDRESS` is unset, the
condition that makes a signed-in Chrome present as signed out.

`SETUP.md` states the service-account limit plainly rather than burying it:
Andrew ratified *"OAuth as the user"* on 2026-09-07 and **it is not built.**

### Verified

| | |
|---|---|
| `evals/run.sh` | ALL PASS — 40 coverage + 35 hook cases |
| Import without any credential | clean, all modules |
| Missing / wrong credential | raises, names every path searched |
| Drive + Sheets via `config.py` | 14 docs, 11 catalogue tabs |
| `site_survey.py` from new layout | OK — account, 3 pages, 27 cells |
| Live `PreToolUse` refusal | blocked an out-of-door write, logged `12:11:41` |

### Open

1. **OAuth as the user is still unbuilt.** Until it is, a client needs their own
   service account and must share folders with it explicitly — link-sharing does
   not grant service accounts.
2. **No one has actually cloned this onto a second machine.** Every check above
   ran on the machine the code was written on, with its dependencies already
   installed. *Maker is never checker* — the portability claim is not proven
   until a clone runs somewhere else.
3. `upload_to_drive.py` still does not work — chooser arms, Drive never ingests.
4. This entry must be mirrored into `advisor-os/07_Changelog/DEVLOG.md`.


## 2026-09-07/08 — The deterministic layer for Site builds: `PreToolUse` hook, preflight stamp, and three failures the hook found in its own author

Author: Claude Code (claude-fable-5-1) + Andrew Powers. Andrew, 2026-09-07:
*"okay go to the next part"* — the hooks build agreed in principle earlier that
day, after the playbook review named the gap: *a skill is advisory; nothing
forces a session to comply with it.*

### What it enforces, and the failure behind each

`.claude/settings.json` + `.claude/hooks/site_build_gate.py` (stdlib, offline,
< 50 ms). Fires on **every** Bash call, whether or not the agent chose to call
the harness — which is the point. `harness.py` runs only if code calls it;
this runs regardless.

| Rule | Failure it answers |
|---|---|
| **Use the door.** An executing command that reaches the Sites editor is refused unless it goes through `build_from_wireframe.py` / `run_wireframe.py` — the path that enforces the Landing Rule (GATE 2) and asserts the page id (GUARD 1). | 2026-09-07: placement-test blocks typed by hand from an inline script. Harmless that day; the exact path by which content that is not a cell reaches a page. |
| **Ratified first.** The door opens only on a fresh (< 12 h) stamp from `harness.py preflight <catalogue> <site>` that says `RATIFIED`, for that site. | Build proposed twice before the HopeLink ISA existed. |
| **No blind delete.** `clear_page` outside the door is refused, even under a waiver. | 2026-08-31: a page click silently missed; `clear_page` destroyed a finished Home. |
| **Publish asks.** `permissionDecision: ask`. | Outward-facing. |
| **Waivers are human acts.** `~/.advisor_os/waivers/*.json` with `waived_by`, `site_id`, `expires`, `reason`; one named site; every use logged. | Scratch testing needs a door too — one a human opened. |
| **Every decision logged** to `~/.advisor_os/hook_log.jsonl`. | The auditor reads the ledger, not the summary. |

`permissions.deny` also keeps `service_account.json` and `.env*` out of the
agent's file tools — the playbook's cheapest control.

**The preflight is the bridge.** A hook must be fast and offline and must not
be the thing that decides ratification. So `harness.py preflight` reads the
catalogue once, applies STAGE 0 / `00_HARNESS` / GATE 1 / GATE 5, and leaves a
stamp; the hook answers one question — fresh, this site, RATIFIED? — and
refuses anything else. Run for real against the HopeLink catalogue: **REFUSED,
truthfully** — no `00_HARNESS` tab (built before the harness existed), ISA
`DRAFT`, and no `ratified_by` on CHARTER, MANIFEST or PAGE_PLAN. Its first run
reported GATE 5 as *"could not evaluate"* because `gate_5_ratified` reads dict
rows and a sheet arrives as lists; fixed by keying rows on the header.

### Verified

- **35 hook cases + 40 coverage checks, all green**, in the pre-commit hook and
  in `evals/run.sh`, from this repo's own layout.
- **A fresh `claude -p` session tried the ad-hoc write and was refused** — 2
  turns, $0.037, and a `BLOCK` in the ledger at 23:46:50 carrying the exact
  command. The proof is the ledger line, not the session's report.

### Three failures the hook found in its own author, in order

**1. It refused a documentation edit.** The first live block was a Bash heredoc
that merely *mentioned* `build_from_wireframe.py`. The matcher read text and
treated a mention as an invocation. Fix: a command that cannot execute code
cannot reach the editor (`cat >`, `cp`, `git` pass); invocations must sit at a
command boundary and may not begin with a quote or backtick.

**2. It refused the Bash call that tried to fix it.** Chicken-and-egg — the
patch script's text contained the tokens. The fix went in through the Edit
tool, which the hook does not match, and a working rule fell out: **edit files
with Edit/Write; run things with Bash.** Now in the checklist.

**3. Tightening opened a hole.** Requiring imports at line start let the
one-liner `python3 -c "import sites_automation as S; …"` straight through. This
was caught not by a failing test but by the fresh-session run producing **no
ledger entry** — the guard had gone quiet. Fix: an import counts when it sits in
code context (followed by `as`, `;`, `,`, `)` or end of line — prose reads
*"import sites_automation is refused"*, code never does), plus a catch-all: an
executing command that names a site module *and* a write token is a write in
any syntax. Both shapes are unit-tested.

Principle, extending the canary's: **a guard that refuses correct work is as
broken as one that passes bad work — and a guard that goes quiet is worse than
either, because nothing reports it.** That is why the end-to-end check reads
the ledger, not the exit code.

### Limits, stated so they are not oversold

- The hook reads **command text, not the DOM**. A `python -` heredoc that
  imports a site module and contains a write token is refused even when it only
  writes a file — recorded in the tests as `KNOWN LIMIT`. Use Edit/Write.
- On a client's own Pro account the hook lives in the project's
  `settings.json`, which a human can edit. Managed, non-overridable settings are
  an Enterprise channel. **It stops an agent from drifting; it does not stop a
  person from deciding.**
- Landing-Rule enforcement itself lives inside the door (`gate_2_landing` over
  `PAGE_WIREFRAME`). The hook enforces "use the door"; the door enforces the
  rule. Two layers, one definition of each.

### Not done, deliberately

**No waiver was written.** The two scratch sites used for placement tests
(SBDC `test` page, HopeLink scratch) will now be refused until a human places a
waiver naming them. `waived_by` is a person; writing one on Andrew's behalf
would be the agent granting itself the thing the file exists to withhold.

### Open

- HopeLink's catalogue has no `00_HARNESS` tab and will keep refusing preflight
  until it is retrofitted — raised 2026-09-01, still Andrew's call.
- No `SessionStart` hook; `CLAUDE.md` carries the standing instruction.
- Plugin conversion of the repo — later, per Andrew.


________________


## 2026-09-07 — Coverage is proven, not claimed: Indexer Spec v2.1, GUARD 9, the canary eval — and the Ruflo review

Author: Claude Code (claude-fable-5-1) + Andrew Powers.

**Ratified by Andrew, 2026-09-07**, in conversation, before any of it was built:
*"this we need to fix, need to make sure everything was read so that the
information system architect is making the decisions based on all the
information right?"* and *"yes build items and ratify and make sure that we
have the chunking and guardrail and the canary eval and regression test as u
have explained it as the playbook's continuous eval play."* Two other rulings
from the same conversation: **client credentials are OAuth as the user, not a
service account** (his words: *"OAuth as the user."*); and the client package is
**a repo first, converted to a plugin later**, laid out plugin-shaped from day one.

### The defect, precisely

`verify_index_integrity.py` compared the agent's reported `chars_read` to a
re-derived extractor count. **But the packet had handed the agent that number.**
An agent that read nothing could echo it and pass. The check proved the extractor
was deterministic; it proved nothing about reading. The one v3 run on record
(3 files, 259,926 chars, 34,146 tokens) cost roughly half the tokens its text
implied, and nothing in the system could say whether the rest had been read.
Andrew's framing, and it is the right one: *"the AI stopping the reading and
saying it's done when it's only read a part … that is a form of lying."*
Claude's reframing, recorded because it decides the fix: *"I have read the whole
file"* is generated text unconstrained by whether reading happened, so demanding
honesty cannot work; **making the claim checkable** can.

**A second defect found while reading the extractor:** spreadsheets were read as
`A1:AZ400`. Rows past 400 and columns past AZ were silently dropped and the file
still reported `OPENED` with the smaller count. Skipping, in the deterministic
layer where nobody was looking for it. Fixed — bare tab name returns the whole
used range.

**And a withdrawn proposal.** Claude had suggested a "format-aware digest" for
spreadsheets (headers, counts, samples). Withdrawn in the same conversation as
wrong under Andrew's rule that importance is an output of the index, not an
input: a digest is a lossy transform and a lossy transform is a decision about
what matters, made by code before the index runs. Andrew's counter-instinct
("download it as CSV and read the whole thing") was right in aim; CSV does not
shrink the content, so the answer is to prove full reading and treat cost as a
budget question.

### What was built (all committed)

**`coverage.py`** — pure Python. `plant()` splits text into 12,000-char chunks
and plants a random `⟦CHK:xxxxxx⟧` every 1,500 chars, regenerated per run; the
expected list stays with the orchestrator, never in the packet. `coverage()` is
arithmetic on what the agent *returned*. `orchestrator_chars()` is the only
legitimate source of `chars_read`.

**`harness.py` — GUARD 9, coverage is proven not claimed.** Refuses any missing
or fabricated marker. Exempts no-text statuses (image, video, scanned PDF) only
because those rows already carry `opened=no` + reason under GUARD 7. Browser
imports made lazy so the guards load on a machine with no browser stack.

**`indexer_v3.py` → v3.1.** `next` extracts, chunks, marks; the packet carries
paths and no sizes. New `prompt` and `agent` commands: `agent` runs
`claude -p … --allowedTools Read,Write` — **no Grep, no Bash, so the only way to
see a marker is to read the chunk it sits in.** `commit` runs `check_results()`
(GUARD 9 per row; `chars_read` overwritten with the orchestrator's count; a
packet file with no row is refused; a refused file stays `PENDING` and is
re-issued) and logs every row and every refusal to `RUN_DEVLOG`. Three columns
appended to `DRIVE_INDEX`: `chunks_total`, `chunks_verified`, `coverage_pct`;
existing tabs get the header extended in place. `/tmp` paths replaced with
`~/.advisor_os/index_work`; the reader now lives beside the script.
`AGENT_PROMPT` is a single constant so the eval tests the text production uses.

**`verify_index_integrity.py`** — correction appended to its docstring: it
catches the *wrong* file and cannot catch a *partial* read. Kept for the first
case; not to be cited as proof of reading.

**`.agents/evals/`** — the playbook's continuous-eval play.
- `test_coverage_unit.py`: 40 deterministic checks, seconds, no model. Every
  chunk marked (incl. 0, 1, 1499, 1500, 1501, 12001 chars); full read passes;
  0/50/90/97% reads refused; fabricated marker refused; image exempt only with
  reason; `chars_read` never from the agent; packet carries no counts; missing
  row refused; prompt/eval share one text; marker presentation ignored;
  monotone baseline holds.
- `canary_partial_read.py`: a synthetic 90k-char document (all names and places
  invented, stated in the file) with a distinctive fact at 93% and a control at
  8%; the row must reflect the late fact. Then a **negative control** — same
  design, agent told to read only the first chunk — and GUARD 9 must refuse. A
  guard that never fires is indistinguishable from no guard. Appends to
  `history.jsonl` with commit sha, model, tokens, cost.
- `baseline.json`: counts that may never rise. `run.sh`: unit always,
  `--with-model` for the canary.
- `.githooks/pre-commit` runs the unit suite when a staged change touches the
  indexer, coverage, harness, reader, evals, skills or `CLAUDE.md`
  (`git config core.hooksPath .githooks`). `.github/workflows/agent-evals.yml`:
  unit on every PR to those paths, canary nightly when a key is configured.

### Measured — the canary on Haiku, 2026-09-07

**Run 1: FAIL, instructively.** The agent read the whole file — both canaries
found, 61 markers returned, 61 planted — and GUARD 9 refused it: *"61 markers
never planted."* The agent had transcribed the ids as bare hex (`'4b2e32'`)
and exact string equality failed. **A guard that refuses correct work is as
broken as one that passes bad work.** Fixed: a marker's identity is its random
hex, not its punctuation; brackets, spacing and case are presentation.
Fabrication is still caught — an unknown hex is unknown however it is dressed.
Unit test added for all four presentations. The negative control on run 1 had
"passed" for the wrong reason (refused on presentation, not on missing
markers) — which is exactly why the second run mattered.

**Run 2: PASS.**

| | positive | negative control |
|---|---|---|
| corpus | 90,151 chars · 8 chunks · 61 markers | 30,000 chars · 3 chunks · 21 markers |
| result | **coverage 100%**, late canary found, early canary found | **refused at 38.1%** — 8/21 markers, 13 unread stretches |
| turns / wall | 11 · 45.5 s | 4 · 31.0 s |
| tokens | in 34 · out 4,239 · cache-read 127,498 | in 34 · out 2,312 · cache-read 115,399 |
| cost | **$0.1047** | $0.0603 |

Both lines are in `evals/history.jsonl` against commit `0c7a737`.

**What the numbers say about cost.** `input_tokens` is 34; the volume is
`cache_read` at 127k — the accumulated context re-read on each of 11 turns as
chunks pile up. The chunk text itself is not the driver; **context growth
across turns is.** About **$0.10 per 90k-char file on Haiku**, read in full and
proven. For a client Drive that puts a 1,000-file index in the low tens of
dollars — a budget question, no longer a truth question.

### The Ruflo review (ruvnet/ruflo) — borrow two patterns, install nothing

Read from a sparse clone of the repo, not from its README. Their **"harness"**
(`.harness/`) is a supply-chain and MCP-security posture tool: signed manifests,
threat models, `mcp-scan`. Their **"verification"** (`verification/`) is
regression protection *for their own codebase* — Ed25519-signed witness
manifests attesting that a documented fix's load-bearing line is still present.
Their **"truth scoring"** — the part that sounds like Andrew's concern — is
labelled in their own skill doc: *"partly shipped … and partly design — treat
the CI Guards section as the authoritative current state."* Their hooks are
routing, memory sync and session restore; the handler's own comment reads
*"MUST NOT block."* Their `CLAUDE.md` is 1,493 lines and 167 headings against
the playbook's "keep it under a page."

Not installed, and not to be: a Node/Rust monorepo with 100+ agents, 35
plugins, its own MCP server and 27 always-on hooks is the wrong shape for a
client on a $20 Pro plan who needs Python and a browser, and its self-learning
loop (SONA / ReasoningBank) adjusts behaviour from trajectories with no
attribution — a tier promoting itself, by design.

**Taken:** (1) the **monotone-decreasing baseline** — a count that may never
rise, lowered deliberately after a fix (`evals/baseline.json`); (2) **marker
substrings over hashes** — a specific unforgeable string is a better proof than
a hash of a claim, which is the same shape as GUARD 9; (3) **append-only
temporal history** so a regression can be dated (`evals/history.jsonl`); (4) the
documentation habit of stating **"shipped vs aspirational"** plainly.

### Principle extracted

**A check that compares a claim to the source of the claim is not a check.**
Prove from what was returned, never from what was reported. Appended to the
Indexer Spec as v2.1 (repo: `docs/Indexer_Spec_Stage_1_v2_1_coverage_is_proven.md`;
Drive Doc: correction section appended, both versions survive).

### Open

- `drive_indexer.py` still implements the v1.0 metadata-only contract; marked
  superseded in the skill. Delete or rewrite is Andrew's call.
- The canary runs on Haiku. Sonnet on the client's Pro account is the stated
  target (memory: ISA must run on client Pro account); not yet measured.
- Hooks for the Landing Rule and ratification gate (`.claude/settings.json`,
  `PreToolUse`) — the deterministic layer for *Site builds* — are the next
  build, agreed in principle, not yet started.


________________

## 2026-08-28 → 2026-09-07 — Session: Automation for Google Sites

Author: Claude Code (claude-opus-5) + Andrew Powers. Named by Andrew, 2026-09-07:
*"name this Session Automation for Google Sites."*

**Provenance of this entry.** Written by Claude from the two session transcripts,
not from memory or from a compaction summary. Sources:
`~/.claude/projects/-home-tyler-Projects-Blackfox-Studios-SBDC-OS--claude-worktrees-bridge-cse-01MJ8iLevwwWgR18jWYPWbyv/`
— `71886fa7-8de2-4a40-a04b-d80943d18df5.jsonl` (1,269 lines, 2026-08-28 → 08-30)
and `25770d44-e0db-5fb6-b127-59c98e792efe.jsonl` (617 lines, 08-31 → 09-07).
Per Writing With Memory Protocol §9.6, **this entry treats those transcripts'
assistant turns as `AI_GENERATED_ANALYSIS`.** Quotes attributed to Andrew below
are from `type == "user"` turns and are his words. Everything not so attributed
is Claude's, and is marked where it is an inference rather than a measurement.

---

### What this session was

The build of a repeatable pipeline that turns a client's Google Drive folder into
an internal Google Site — indexing the folder, deciding what belongs on the site
and why, and placing the blocks — with every decision recorded with its reason.
Andrew's framing, 2026-08-29: the goal is *"a system that is much more human
readable ... content block presets based on how i've designed my other google
sites ... another AI action that would eventually turn into a skill that can go
into a google drive folder and all of its sub folders and index all the content
in the folder first."*

It is not a new system. Claude verified against the archive before building
(2026-08-29) that the loop was **already specified in Andrew's own documents** —
School of Thought §7 line 164 describes an orchestrator that *"monitors the
Sheets and Drive, reads new files, evaluates their relevance, and updates the
front end"*, and the Session Pipeline Spec already runs extract → stage → human
gate → promote. Searches for `site template`, `block preset`, `page template`
returned zero hits. **The genuinely new artifact was the template/vocabulary, not
the loop.** That finding is what kept this session from forking the architecture
(SYSTEM_INTEGRATION §11).

---

### 1. The write path — Google Sites over CDP

Sites has no public write API, and `SYSTEM_INTEGRATION.md` §10 Phase 3 already
routed Sites work to browser automation. This session proved that path.

- **Chrome DevTools Protocol on `localhost:9222` works against the live Sites
  editor.** 166 controls with stable `aria-label`s. Verified 2026-08-28.
- **Layout presets place on a single click.** The drag-and-drop fear carried in
  from a prior session was wrong — that had been the reason to think this path
  was unviable.
- **The "logged out" browser was never stale cookies.** Chrome launched from a
  non-desktop shell cannot reach the keyring and silently fails to decrypt its
  own cookies. `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus` fixes it.
  It presents as a logout when you are not logged out.
- **`blackfoxstudios.org` is multi-login index `/u/1`**; `/u/0` is the gmail
  account. The two artifacts from prior sessions were owned by
  `andrewpowerswa@gmail.com`, to which `andrew@blackfoxstudios.org` had no
  access — a permissions fact, not a preference.
- **Uploads go through the native OS file chooser**, which no DOM scripting can
  reach. `Page.setInterceptFileChooserDialog` converts it into an event carrying
  the input's `backendNodeId`; `DOM.setFileInputFiles` then hands it a path. The
  bytes go disk → Chrome without passing through the agent. In `drive_upload.py`.
- **Sheets and Sites need opposite input methods.** Sites' inputs are Closure
  widgets that ignore the clipboard and need real per-character key events;
  Sheets grid cells accept clipboard paste after character typing silently
  failed. Read-back after every write is the only reason this was caught.

**On Claude-in-Chrome.** Andrew asked repeatedly for the extension, on the
premise that it would avoid opening a tab per action (2026-08-29: *"opening a
new tab every single time when doing multiple pages is probably going to crash
the computer"*). Two findings, both Claude's, both stated to him at the time:
the extension's `debugger` permission **is** CDP — the same pipe — so it is a
different client, not a different capability; and the tab leak was real
(`ws.close()` drops the socket, the tab lives on) but was **not** the expensive
part. The real cost was ~25 script runs each reloading the editor from scratch,
roughly 15 minutes of pure reloading. Fixed with `attach()` / `close_tab()`.
Claude's judgment, recorded as a judgment: the extension cannot run unattended,
which is the operating premise for a client's machine.

---

### 2. First end-to-end build — SBDC Advisor Workshops

https://sites.google.com/blackfoxstudios.org/sbdc-advisor-workshops/workshops

Nine workshop blocks, built entirely by agent from the SBDC hours/workshops
spreadsheet: layout placed, heading and body typed, image uploaded, published.
Andrew's requirement was uniformity — *"embedded of the url and then for it to be
shaped to the same size as the image and text block so all of them can be the
same size and format of blocks."*

**Embeds turned out to be unavailable for that slot, and the finding is
structural:** a Sites layout placeholder accepts only an image (Upload / Select /
From Drive / YouTube / Calendar / Map) — verified by probing the live editor.
Three of the five event pages also send `X-Frame-Options: SAMEORIGIN`, so they
cannot be framed anywhere. The resolution was to render each event page to a PNG
at one fixed size (`capture_page_images.py`), which sidesteps both limits.
Andrew's rule, given directly: *"you're supposed to take a screenshot of whatever
link I just gave you."*

**The spreadsheet became the deterministic key**, which was Andrew's actual
point: *"utilizing the spreadsheet rather than just utilizing the Google Drive
is a more deterministic way of pulling information."* Two columns added and
verified by read-back — `Flyer Embed URL` (L) and `Block Image File` (M) — with
all nine images in one Drive folder named date-first so filenames sort
chronologically and read back to their row without opening anything.

**Three defects found by screenshot, not by the builder's own status:**
1. **Order scrambled.** Sites inserts a new layout relative to the current
   selection, not at the end. The builder verified each block *existed* and never
   verified its *position*.
2. **"Same size" was not achieved.** One layout, but the image slot sizes to each
   picture's aspect ratio. Uniform format, not uniform size. **Still open.**
3. **A published page arguing with itself** — the Highline caption read "Jan 4,
   2026" while the flyer in the same block read "Wednesday January 28th."

**The Jan 4 → Jan 28 discrepancy is Andrew's to rule on and was not changed.**
Evidence: the flyer states Wednesday January 28th, 2:00–3:00pm; Jan 28 2026 is a
Wednesday, Jan 4 2026 is a Sunday; the sheet also says "30 minutes" against the
flyer's one hour. It sits in Workshops row 7 and Hours Log row 7. **Open.**

Two recovered facts worth keeping: two URLs existed as embedded hyperlinks in the
source PDF but never survived text extraction into the sheet, and were written
back into Registration Link (I9, I10). And a filename match that would have been
wrong — `Filipino Community of Seattle and CACCWA.png` reads like the Dec 8
workshop and is actually a June 14 "AI Tools for Small Business" thank-you post.
**Filename matching would have put the wrong flyer on that row.**

---

### 3. Reading the existing design language — BFS X JBL

Andrew: *"review the jbl.blackfoxstudios.org site ... this is about cataloging
the site as a template to repeat."*

**Published HTML cannot yield the block vocabulary.** Sites compiles every block
to generic divs; a `layout: Image and caption` preset and a hand-placed image
beside a text box are indistinguishable in the output. The editor is where the
vocabulary lives — `aria-labels` and grid geometry. Two views are required and
neither is sufficient alone: **editor for block type and arrangement, published
page for image URLs.** Claude initially reported five JBL image cells as empty;
they were real 1280px images, and the editor lazy-renders `ar-gradient(...)`
placeholders until a cell scrolls into view. That correction is in
`catalog_site.py` as a stated rule, because an agent trusting the editor alone
will faithfully record every image block as empty.

**Result: 8 pages, 100 blocks catalogued** — four visible pages plus four hidden
from navigation (`Meeting Notes`, `Calendars`, `Team`, `FAQ`), which are part of
the client-management template even though a visitor never sees them.

Vocabulary as measured, not as assumed:
```
 40 paragraph      25 spacer          6 paragraph_x3     4 image
  4 paragraph_x2    4 layout_media_text 3 drive_file_embed 3 image_x2
  1 calendar_button 1 embedded_website 1 image_x3
```
Plus `Drive Folder`, `Spreadsheet`, `Calendar`, `Table of contents`, `IFRAME`,
`Content placeholder` — six types **not in** the 12-type vocabulary in
`13_BLOCK_RECIPES`.

Three findings from that data, all Claude's reading of it: `spacer` is 25% of the
site and is not a block type in the catalogue at all, so a template omitting it
produces pages that are structurally right and visually wrong; multi-column text
(`paragraph_x2`/`_x3`, ten occurrences) is used far more than `layout_media_text`
(four); and the **hidden pages carry the heaviest machinery** — the embeds live
there. A repeated two-up feature pair (2-col text / 2-col image / 2-col text) is
used twice on one page and emerged from the site rather than being invented.

**Custom embeds are only catalogable via `data-code`.** Sites wraps them in a
cross-origin gstatic shim, so the iframe `src` tells you nothing and
`contentDocument` throws. The original embed code survives on a `data-code`
attribute. Without it a "Custom Embed" block is unrepeatable. In
`extract_site_template.py`.

**Andrew ruled the scope of iteration 1**, 2026-08-29: *"embeds are the wrong
method for this to start — we only want to use embeds on the next iteration this
iteration we want the blocks and placement — we want to avoid the Appscript build
until we have the block builds of sites first."* Logged as PROP-010. Claude
stated the cost at the time: of nine in-scope types, one was proven and seven
were untested. Claude also flagged the tension — every JBL page carries 1–2
iframes, so a template derived from Andrew's own sites and excluding embeds
cannot reproduce his own pages; the resolution proposed was to record embed types
as *deferred* rather than absent.

---

### 4. Andrew's correction: one catalogue per site

Claude had written JBL's 8 pages and 100 blocks into the practice-wide Visual
Second Brain substrate. Andrew, 2026-08-29:

> *"the visual second brain would have a link to the sheet but wouldn't try to
> hold all the information of the sheet on its own."*

Corrected: each site gets its own **Visual Knowledge Catalog** workbook; the
substrate holds a pointer (`RES-VKC-JBL`, `RES-VKC-HOPELINK` in `06_RESOURCES`),
not the contents. `P_SITE_PAGES` returned 13 → 4 rows, `P_SITE_CONTENT_BLOCKS`
113 → 4.

**A failure worth keeping**, in Claude's account of it: the substrate tab said
*"Copy this tab into each project workbook"* in its own second row. Claude read
that row, quoted the schema back from it, and still treated the tab as a shared
container — processing an instruction as description. The proposed fix is a
machine-readable `scope: per-project | practice-wide` field rather than a prose
note an agent will read past. **Not yet built.**

Related, and now in the build protocol: `spreadsheets.create()` 403s for the
service account because it targets a My Drive with zero quota;
`drive.files.create` with `parents=[shared folder]` works on the same
credentials. The Sheets API reports it as a bare permission error, which is why
it was misdiagnosed once before as `storageQuotaExceeded`.

---

### 5. HopeLink Ride Ready — the full cycle, and four failed page builds

Andrew asked for one complete turn of the cycle on a real client folder, mirroring
JBL: *"i want it to mirror the JBL website so that we are making it as much alike
as possible."*

The page build failed four times, and the sequence is the most instructive part
of this session because **every failure passed its own verification.**

| Attempt | What was believed | What was true |
|---|---|---|
| 1 | `fill_next_empty_caption` finds this block's cell | "First empty in DOM order" wanders across blocks |
| 2 | Filling immediately after placing closes the window | Sites reflows as blocks are added; it only narrows it |
| 3 | `data-*` attributes identify cells | Sites recycles DOM nodes; tags vanish, old cells look new |
| 4 | Geometry identifies cells | The editor scrolls an **inner container**, so `window.scrollY` is 0 and y is viewport-relative — a saved floor goes stale |
| ✅ | — | **DOM index, scoped to the block just placed.** Blocks append, so the new block owns every cell from the pre-insert count onward |

Two more measured corrections at the same time: layout cells fill **column-major**
(entire left column, then entire right), not row-major; and typing at 40–50 ms per
character transposes silently — `PAARGRAPH`, `One call ro one click`. **0.11 s/char
is clean.** A two-column layout owns **six** cells (media + heading + body per
column), which is why JBL's "three blocks" were always one.

Claude reported per-block success on three scrambled pages before stopping. The
recorded diagnosis: *"my verification confirms a cell received the text — it never
confirms that cell was the right one for that block."*

**`PAGE_WIREFRAME` came out of this and is the durable artifact.** Andrew asked
for it directly: *"if we can create the layout in the cells of the sheets so that
we can have the wireframe of the whole page."* One row per Sites block, explicit
`col_1..col_3` addresses that are the page's columns rather than the sheet's
convenience. It removed the pipe convention (PROP-009), removed the "next empty"
search, and made the human gate workable — 26 rows of a flat list is a chore, a
wireframe is a glance.

---

### 6. The destroyed Home page — 2026-08-31

`clear_page` ran after a page-selection click that returned true and had landed
nowhere. It cleared whatever was open — **Home, with 11 verified blocks** — and
rebuilt Team's content onto it. The site was published, so the broken page was
live.

Root cause: `Emulation.setDeviceMetricsOverride` was set to 1400px to take a
screenshot and never cleared. **`clearDeviceMetricsOverride` returns ok and does
nothing.** Every later coordinate was computed against a layout the editor was
not using.

Two rules, both now enforced in `harness.py` rather than reimplemented per script
(*"re-deriving a guard locally is how the first one got lost"*):
- **A diagnostic must not change the system it is diagnosing.** Force the
  viewport explicitly at the start of every run; abort if it does not take.
- **Assert the target from the live URL before any destructive step.** A click
  returning true is not evidence the click worked.

The page-ID guard fired correctly on a later run, aborting instead of clearing —
the same failure, caught.

---

### 7. The roster failure — and the Landing Rule

Andrew: *"Why is the full hopelink team not being displayed?!? Didn't you have
more people associated with hopelink?"*

The Team page had 6 people. There were 15. Claude had marked the roster
`NOT ESTABLISHED` in the catalogue and **built around its own flag** — the names
were in the `Present`/`Absent` columns of the master meeting log the whole time.
That is a direct breach of archive-first: a gap was asserted rather than looked
for.

Where a roster actually lives, since no roster document exists: **who** comes from
`Present`/`Absent` in meeting logs; **which organisation** comes from email
domains in a message thread, never from a name. A consultant had been placed
inside the client organisation because the architecture had no evidence column.

The rule Andrew stated, which Claude named **the Landing Rule**:

> **Information lands in the sheet before it lands on the page. Gathering is
> proven in the catalogue, never on the site.**

The reasoning recorded with it, per non-negotiable 8 — *the sheet is the only
place where absence is visible.* A page with six people looks finished. A roster
tab with six rows and an evidence column shows immediately that nobody counted.
A projection cannot be evidence of the thing it projects.

Also measured against the four-column preset: **"Four column image and captions"
holds ONE caption per column, not two.** Eight values went into four slots, two
people vanished, and the build reported success. Two other presets are also not
what their names suggest — `Image and caption` is image-**left**, text-right, not
stacked, and therefore wrong for person cards.

---

### 8. Harness v1 → v2 — "a harness written after the build is an audit"

Claude built the Build Harness after the drift. Andrew's correction, 2026-09-01:

> *"this is supposed to be at the beginning before the evaluation is done. This
> is supposed to be a beginning template build harness and guardrails so that the
> drift we were having and hallucinations and all that doesn't happen."*

Claude's acceptance of that, recorded because the distinction is the point: *what
I built was an audit, not a harness. It arrived after the drift, so it couldn't
have prevented any of it.* Rebuilt as **TEMPLATE — Build Harness and Guardrails
v2.0**, instantiated at **Stage 0**, before the folder is indexed and before the
client is asked anything. Six stages became seven. The failure history moved to
an appendix so a rule is followed on its own terms while its reasoning stays
recoverable.

**It ships inside the catalogue template so it cannot be skipped** — 9 tabs
became 11, with `00_HARNESS` (17 gate rows, blank status = stop) and `WAIVERS`
first. Three control types by when they fire: **Gates** before a stage and block
it; **Guards** during, and abort; **Ledgers** after. `Refusal` is a distinct
exception type, because refusal is a valid deliverable.

Two honest results from testing it, both left as they are: the blank template
refuses Stage 0 (correct — it has no `site_name`, no `drive_folder_id`, no ISA),
and **HopeLink refuses differently** because it has no `00_HARNESS` tab at all,
having been built before the harness existed. Claude left it refusing rather than
backfilling, since retrofitting would make it look like Stage 0 had been done.

**Four waivers were proposed and none granted.** `waived_by` blank means still
blocked. The agent proposes; a waiver is a human act.

---

### 9. The index was the real defect — Indexer Spec v2.0 and Pass B

Andrew, 2026-09-01, on why the build had been slow — this is the correction that
reframed the whole session, and Claude's earlier account was wrong:

> *"It wasn't the roster that took that long. It was the fact that you kept
> placing text blocks down and other things down that were wrong ... every step
> of the way you ignored some details just to make the task easier ... you should
> be running multiple agents to index that you shouldn't try to shorten it or get
> it done fast."*

**The defect was one sentence in Indexer Spec v1.0: *"metadata only; nothing is
opened."*** The HopeLink index was 85 rows of filenames, `site_candidate` 0/85,
with no column holding what any file said. The Charter, Manifest, Page Plan and
both built pages all rested on a guess about the folder's contents.

**v2.0 replaces it:** every file is opened and read; a file that cannot be read is
recorded as unread with the reason; there is no third option, and *"it looked
unimportant" is not a reason — importance is an output of the index, not an input
to it.* `DRIVE_INVENTORY` went 17 → 29 columns; `extracted_to` is the one that
catches the remaining failure, because a P1/P2 file whose content landed in no tab
is a defect visible in one column.

**Pass B, measured** (2026-09-01): **59 files, 9 parallel agents, 58 opened,
1,250,749 characters read, 796,110 measured tokens.** Priority spread P1 31 / P2
22 / P3 5 / P4 1. One file not opened — `Tacoma Commuter.mp4`, reason recorded
before the run, needs transcription. The merge script refuses to write at all if
coverage is short, because writing 54 of 59 rows and reporting success is the
failure the pass exists to end.

**What the old index could not have known**, all found by opening files:
- **Camy Naasz is HCD Director at Anthro-Tech, not Hopelink**, and her surname was
  in a brief that had never been opened. Two of the four waivers Claude had put in
  front of Andrew were requests to ratify its own failure to read — precisely the
  pattern Andrew had named: a flag recorded honestly, then used to justify not
  looking. **An entire organisation, Anthro-Tech, was missing from the site.**
- **Kevin Chambers authored the 2020 King County One-Call/One-Click Business Plan
  and the Phase 1A Evaluation** — the programme's foundational documents, not a
  meeting attendee.
- **The Phase 1A Evaluation records that Cambridge Systematics stopped supporting
  the one-click software as a single product**, removing the sustainable
  open-source model the project was conceived around. A strategic risk that the
  old index held as a filename.
- **The funding position** — FTA ICAM grant, ~$500K, state contract ending
  December with a one-year extension sought — and the **contractual performance
  targets** (90 calls, 5,600 unique FindARide.org visits after beta launch).
- **A duplicate with a date trap:** a transcript in the June 8 folder is
  line-for-line the June 1 kickoff. Anything treating folder name as date files
  June 1 decisions as June 8 — and the Page Plan had been built on folder names.
- **Attendance data already used is wrong.** For Aug 19 both logs list five people
  present; the transcript has three speaking. *The log is the projection; the
  transcript is the source.*

**Three of nine agents hit shared scratch-path collisions** — one agent's output
spliced onto another's — and all three caught it themselves and re-ran isolated.
Claude's judgment: that the design was unsound, and that catching it three times
says nothing about the times it was not caught. `verify_index_integrity.py`
re-opens every file keyed on `file_id` (which cannot collide) and compares char
counts, **and it runs in the orchestrator, not in the agent that produced the
row** — maker is never checker. Recorded in `RUN_DEVLOG`, including that the same
shared-scratch-path bug was committed inside the tool built to catch it.

**A root-folder error found only by independent re-crawl** (2026-09-01): Pass A
had recorded the root as "Hopelink Project Site Folder", which is a **sibling** of
"HopeLink - Dev Team Meetings", not the project root. Listing it returns **2 files,
not 59**. A second latent trap alongside it: shared-drive listings need
`corpora='drive'` and `driveId`, and without them a crawl quietly under-returns.
The 59 came out right by luck — the original crawler walked the correct tree and
mislabelled its root row. Rebuilding from the recorded root ID would have indexed
2 files and reported success.

**`run_ledger.py` exists because of Andrew's demand for an auditable trail** —
*"on every step there's a devlog ... talking about all the steps it did how long
it took how many tokens it took because we need an ability for the auditor to go
back and see that if it skipped stuff."* It refuses a skip with no reason
(tested; it throws). **On token honesty:** subagent tokens are measurable and are
recorded verbatim; the orchestrating session's own per-step usage is not
available to it programmatically, so the ledger records content volume and labels
any derived figure `orchestrator_tokens_ESTIMATE` with its divisor. An estimate
is never reported as a measurement (Rule 7).

---

### 10. `indexer_v3.py` — the client-account constraint

Andrew, 2026-09-01, and this changes the system design rather than one script:

> *"we aren't just doing this for Hopelink and we need the ai system and or skill
> that we are developing to run with all the guardrails and harnesses in place so
> that it can run on her system which is claude pro $20 account and still do the
> indexing while using Sonnet 5 and run on a long history of files and folders in
> a google drive and be successful without skipping anything."*

Pass B's 796,000 tokens across 9 Opus subagents was complete and correct and is
**unusable on a $20 Pro account**. Andrew's constraint is that coverage is not
the thing to trade away, so the cost had to come out of the architecture.
`indexer_v3.py` — four commands, `seed` / `next` / `commit` / `status`:

- **State lives in the sheet, not in context.** Every file gets a PENDING row
  *before* any reading starts. Resume is `select where status != DONE`. It
  survives usage limits, crashes, model switches, closing the laptop.
- **One file committed at a time.** An interruption loses at most one file; v2
  held nine agents' work in flight.
- **Text extraction is free** — deterministic Python, no model. The agent receives
  paths to text on disk, so a 286,000-character document costs only what the model
  reads and costs the orchestrator nothing.
- **Small packets to Haiku.** Context never grows past the packet, which is what
  parallel fan-out was actually buying.

**Tested end to end against the real folder.** A Haiku agent indexed a 3-file
packet including a 245,766-char spreadsheet for **34,146 tokens**. Seed on the
true root: 61 files, 27 folders, 59 new PENDING rows, idempotent. A **sibling
guard** was added mid-test and now refuses to seed from the wrong root — it
reproduces and catches the exact Pass A error, names the correct root, and hands
over the command to fix it.

---

### 11. The skill — `information_systems_architecture`

Andrew asked for the HopeLink-specific work to be generalised: *"create a new
file basically called the information systems architecture skills folder ... so
that we can utilize what we've already done in a template version ... in a way
that's going to clearly do it on the first try rather than you know how many
times it took."*

`.claude/skills/information_systems_architecture/` — `SKILL.md` plus
`references/ISA_TEMPLATE.md`, `ARCHITECTURE_PRINCIPLES.md`,
`FIRST_TRY_CHECKLIST.md`. Stage order, with the gate made explicit:

```
0 HARNESS   instantiate the harness; write and ratify THIS site's ISA
1 INDEX     catalogue the folder
2 CHARTER   why the site exists, in the client's words
3 MANIFEST  what is in, what is out, both with reasons
4 PAGE PLAN what sits on which page, in what order, and why
  >>> THE GATE — the human ratifies Charter, Manifest, Page Plan <<<
5 RENDER    how each item is displayed, from MEASURED presets
6 BUILD     make the Site match the sheet; every run logged
```

The HopeLink ISA is registered as **a worked instance to compare against, never
to copy from** — reusing another site's pages, reader model or goals is the exact
drift the template prevents.

**HopeLink references were deliberately left in `SKILL.md` and
`ARCHITECTURE_PRINCIPLES.md`** and removed from the other two. Each principle
names the failure that produced it, per non-negotiable 8: a rule without its why
is cargo, and the next session will either discard it or obey it blindly.

**Claude's stated limit on the skill, recorded so it is not oversold:** it makes
the *structure* first-try, not the *thinking*. The two things that took the most
passes — the audience split and the roster — were judgment calls only Andrew
could settle. What the skill does is put those questions before the build.

---

### Architecture principles ratified by Andrew this session

Each carries the failure that produced it; full text in
`.claude/skills/information_systems_architecture/references/ARCHITECTURE_PRINCIPLES.md`.

- **The council proposes with reasoning; the human ratifies.** Refusal is a
  feature. Exclusions are recorded.
- **Separate by AUDIENCE before separating by TIME.** Andrew: *"There are two
  separate team meetings that might have the same type of people but they're not
  on the same page because we only need one team to look at one."* The ISA had
  merged two meeting tracks and argued chronology. Chronology is how a person
  reads *within* a page; audience decides which page they open.
- **Order pages by frequency of the question, not importance of the content.**
- **One reader question = one page.** Not a filing scheme, not the folder tree.
- **Home is never empty** — README plus executive summary at a high-school-
  freshman reading level, under five minutes, ending with a map of every page.
- **Do not publish the folder tree.** The site exists so nobody has to navigate
  folders; reproducing the tree reproduces the problem.
- **Analysis completes before rendering; rendering completes before building.**
  Andrew: *"block rules should only be considered after all the content and
  themes and philosophy has been considered."*
- **Ask at most five questions; ten is the ceiling.** Fifteen was too many.
- **Design only with blocks that are verified buildable.**
- **The architecture removes blockers rather than solving them.** The first
  render pass wanted 33 external link rows because nothing told it not to;
  grouping and embedding removed the need entirely.
- **Measure the preset; do not trust its name.**
- **A goal you cannot quote is a goal you invented.**

---

### Code shipped (this commit)

All in `.agents/scripts/` unless noted. None of it was in version control before
this commit — it existed only as untracked files in a worktree.

| File | What it is |
|---|---|
| `sites_automation.py` | Sites-over-CDP primitives; `probe_controls()` so selectors can be rediscovered rather than guessed |
| `harness.py` | The gates, guards and ledgers. One definition of each; `Refusal` is a distinct exception |
| `wireframe_build.py` | Geometric cell identity — mark cells before insert, the unmarked ones are this block's |
| `build_from_wireframe.py` | Stage 6 build from `PAGE_WIREFRAME`; imports the guards, does not re-derive them |
| `build_page.py`, `run_wireframe.py`, `build_blocks.py` | Block placement and per-block status for `SITE_SYNC_LOG` |
| `drive_indexer.py` | Stage 1 crawl (pre-v2.0 schema — see open items) |
| `indexer_v3.py` | Resumable, sheet-as-state indexer for a client Pro account |
| `merge_index_pass_b.py` | Merges subagent output verbatim; refuses to write if coverage is short |
| `verify_index_integrity.py` | Independent re-derivation of char counts, keyed on `file_id` |
| `run_ledger.py` | `RUN_DEVLOG` — per-step reads, writes, skips-with-reason, timings |
| `extract_site_template.py`, `catalog_site.py` | Site → template catalogue; embeds recorded with contents via `data-code` |
| `capture_page_images.py` | Fixed-size page capture, verified non-blank |
| `drive_upload.py` | Native file-chooser upload over CDP |
| `sheet_write.py` | Browser writes to Sheets with read-back per cell |
| `.claude/skills/information_systems_architecture/` | The skill: `SKILL.md` + 3 references |

---

### Open — nothing here is done

1. ~~**`build_page.py` paragraph path is broken.**~~ **DIAGNOSED AND FIXED
   2026-09-07 by testing on the live sites.** The symptom was
   `ONLY_0_EMPTY_FOR_1_TEXTS`; the guessed cause ("it lands as its own section
   wrapper") was wrong. **The real cause: `cells_from(before_count)` assumed a
   new block appends at the end of the DOM. It does not.** Sites inserts at the
   current insertion point, and when `append_point` misses the bottom the block
   lands *above* existing content — observed on a live page with 21 cells, where
   a two-column block took indices 1–6 and pushed the previous block's cells
   from 10–14 down to 15–20. Reading "from the old count onward" therefore
   addressed *other blocks' cells*, which read as non-empty, so the fill was
   refused. **Nothing was corrupted: the occupancy check refused to write into
   occupied cells.** That refusal is the only reason this surfaced as a finding
   rather than a fourth scrambled page. Fixed in `wireframe_build.py` —
   `cell_signatures()` + `inserted_range()` locate the new block by diffing the
   page across the insert (common prefix, common suffix, remainder). Verified on
   both live sites: a block landing at indices 7–9 with 21 cells present was
   targeted and filled correctly.

   **A second, unrelated break found in the same pass:** the layout tile's
   aria-label changed from `Image and caption` to **`Add layout: Image and
   caption`**, so every `insert_layout()` call failed with a bare TIMEOUT.
   Google owns this DOM and renames things; `build_page.insert_layout` now tries
   the current form then the old one, and `probe_controls()` exists precisely so
   the next rename is rediscovered rather than guessed.

   **Both block paths are now proven on live sites (2026-09-07).** `paragraph`
   — the type reported broken — placed and filled at DOM index 5 on a page with
   8 cells, landing *between* two existing layout blocks and disturbing
   neither. `layout_media_text` and the two-column layout likewise. Verified by
   independent read-back of every cell, not by the builder's own status string.

10. **The Cycle v0.2 carries one stale status line.** It still reads *"Status:
   RUN ONCE (HopeLink, 85 rows) — spec and reusable script NOT YET WRITTEN"* for
   Stage 1. Both exist: Indexer Spec v2.0 and `indexer_v3.py`. Flagged to Andrew
   on 2026-09-01 and again 2026-09-07; **he has not ruled, so it is left as
   written.** Correcting a doc in his Drive is his call, and per "never
   overwrite" the fix is an appended correction, not an edit to the line.
2. **GATE 6 still refuses on HopeLink** — 53 P1/P2 files are read but their
   `extracted_to` is empty. Content indexed, not landed in tabs. The Charter and
   Page Plan cannot be trusted until it is. This is the Landing Rule working.
3. **HopeLink's Charter, Manifest and Page Plan were built on the old
   filename-only index** and have not been rewritten against the real one.
   `isa_status` is DRAFT; ratification is Andrew's.
4. **`drive_indexer.py` still implements the v1.0 metadata-only contract.** The
   spec is v2.0; the Stage 1 script is not. `indexer_v3.py` is the v2.0-shaped
   path and is the one to use.
5. **SBDC workshops page:** block heights still vary (image aspect ratios);
   White Center and SBCAP share a picture because they share a registration URL;
   the Jan 4 / Jan 28 contradiction is live on the published page.
6. **The `scope: per-project | practice-wide` field** proposed after the substrate
   mix-up is not built.
7. **The template itself is still not derived.** JBL is decomposed; "template"
   means what is constant *across* sites, and that needs a second site (BFS X CG
   or BFS X RCRC) run through the extractor and diffed.
8. **`Tacoma Commuter.mp4`** is unindexed pending a transcription step.
9. ~~**No GitHub remote exists.**~~ **CORRECTION, 2026-09-07.** Reading only the
   checkout's `origin` (a local filesystem path) produced the answer "there is no
   GitHub repo." **`Cloudenvy7/advisor-os` existed all along and is private.**
   Checking the remote a repo declares is not the same as checking the account.
   This track now lives in **`Cloudenvy7/google_site_automation`** (private), and
   also on the `google-sites-automation` branch of `advisor-os`.

### Privacy flags

- **`Automated System for Claude Briefs`** (Google Doc, 286,213 chars) sits at the
  root of the HopeLink folder and is **predominantly SBDC content filed in a
  HopeLink folder** — SBDC 61 mentions, King County 82, Hopelink 32. It is a
  pasted transcript of Claude Code sessions where the brief system was built,
  using real advisory work as test data: **session notes naming two real SBDC
  clients, a King County solicitation with bid positioning, and a narrative
  client session note covering a home-based business's insurance coverage.**
  The names, the solicitation number and the client details are deliberately
  **not** recorded here — they are in the indexed row in the catalogue, which is
  where they belong, and repeating them in a document that may be mirrored to a
  git remote would propagate exactly the exposure this flag exists to prevent.
  Indexed P1 (it governs the brief methodology), `site_candidate: no`. Nothing is exposed today because it is
  unpublished. The point is narrower and is the argument for the whole index
  rewrite: **under the filename-only index it was a row that read like project
  documentation, and any Charter written from that index had no way to know it
  carried another client's session notes.**
- **Every HopeLink brief carries a "Confidential, Internal Distribution Only"
  footer.** Relevant to anything published.
- Because of the first item, **a private GitHub repo is not automatically safe** —
  it changes where this material can be copied to. Andrew's call, not Claude's.

### For the next session

Read `.claude/skills/information_systems_architecture/SKILL.md` and
`references/FIRST_TRY_CHECKLIST.md` before touching a Site. Then fix the
paragraph path (open item 1) — it blocks Stage 6 on the most common block type,
and it is isolated and testable without touching a real page.


________________


