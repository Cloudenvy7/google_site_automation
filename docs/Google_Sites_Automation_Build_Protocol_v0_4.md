<!-- MIRRORED FROM GOOGLE DRIVE. The Doc is canonical; edit it there.
     name     : Google Sites Automation - Build Protocol v0.4
     drive_id : 1kslI1OR2465R5Z2IQsR62dtO4FqGEKQzCdb6w0m0WQE
     modified : 2026-09-01
     exported : 2026-09-07 as markdown
-->

# **Google Sites Automation — Build Protocol v0.2**

*Corrected from Visual Knowledge Catalog v0.1 using evidence from the 2026-08-28 build, in which nine blocks were placed and published end to end. Every "verified" claim below names how it was checked. Claims that were not checked say so.*

## **0\. Iteration scope — decided 2026-08-29**

**Iteration 1 is block placement only. Apps Script and embed render paths are deferred.** Andrew's call, and the reasoning matters more than the rule: an embed would satisfy the page while skipping the block vocabulary, and that vocabulary is the reusable product. A site template cannot be derived from an embed — you would end up with a working page and no method. This knowingly accepts the scaling cost below (\~30-45s per block through the browser) as the price of learning the presets.  
Recorded as PROP-010. 13\_BLOCK\_RECIPES now carries render\_path and iteration columns: nine block types are in scope for iteration 1; embedded\_website and the three drive\_\* types are deferred to iteration 2\.

## **1\. The loop already exists in Advisor OS**

This is not a new system. School of Thought §7 already specifies it: *"Google Antigravity is the headless CMS and agentic middleware — the orchestrator that monitors the Sheets and Drive, reads new files, evaluates their relevance, and updates the front end."* The Session Pipeline Spec already runs the four beats — extract, stage, human checkpoint, promote — and advisor\_cycle.py implements them (--run-once stages, \--promote writes). SUBSTRATE\_READ\_PROTOCOL already requires a confidence score on every proposal and prohibits a silent CREATE.  
**The only genuinely new artifact is the site template.** A repo-wide search for "site template", "block preset", "content block preset" and "page template" returns nothing. Build that; do not rebuild the loop.

## **2\. Image placement — three paths, not two**

v0.1 framed this as By-URL vs From-Drive and asked which was used. The answer is neither.

| Path | Needs public sharing? | Status |
| :---- | :---- | :---- |
| Insert \> Image \> By URL | Yes — file must be link-shared and hotlinkable | Not used |
| Insert \> Image \> From Drive | No, but viewer needs file access | Not used |
| **Insert \> Upload (local file)** | **No** | **PROVEN — all 9 blocks** |

Upload pushes local bytes through the native OS file chooser, intercepted with CDP Page.setInterceptFileChooserDialog \+ DOM.setFileInputFiles. Sites then holds its own copy.  
**Consequence for PROP-008.** The GREEN/BLUE link-sharing gate is not required to make images render. It still applies to drive\_file\_embed and drive\_folder\_embed, which genuinely expose the file. For RCRC, upload is the safer default: no camper image is ever retrievable by URL, which is a system guarantee rather than an eyeball guarantee.  
content\_image\_url on uploaded blocks is asset provenance only. It is not what the Site consumes. Do not read it as proof the page renders.

## **3\. layout\_media\_text — the open test is closed**

13\_BLOCK\_RECIPES marked this "NO — THIS IS THE OPEN TEST" on the theory that Layouts use drag targets. Three corrections:

> * **No drag is needed.** A single click on the tile places the layout. Verified by gridcell count rising by 3 on every insert.  
> * **The preset is named "Image and caption."** There is no "media-left/text-right" preset. The aria-label is Add layout: Image and caption. The six available presets are Image and caption, Two column image and captions, Three images, Three column image and captions, Two column image and side captions, Four column image and captions.  
> * **Scroll the placeholder into view before clicking.** Off-screen coordinates click nothing, and the failure presents as a missing Upload menu item rather than a scroll problem.

PROP-009 (two text values, one content\_text column): the convention works because the editor exposes two separate contenteditable cells. Recommend a real content\_heading column anyway — the convention is invisible to anyone reading the schema.

## **4\. Block ordering — a defect worth encoding**

Sites inserts a new layout relative to the **current selection**, not at the end of the page. Building in three batches produced a page whose block order bore no relation to the order the blocks were added. Fix: scroll to the bottom and click the last section before each insert. **Verify position, not just existence** — a builder that confirms "the block is on the page" will pass while the page is scrambled.

## **5\. Verification rules learned the hard way**

> * **A status code is not proof of content.** HTTP 200 with content-length 0 is a redirect landing page. Check content-type and file magic. Same failure shape as a dashboard looking healthy while serving demo numbers.  
> * **curl is not a browser.** The Federal Way event page returned 404 to curl and rendered fine in Chrome. Do not declare a link dead from curl alone.  
> * **Read the image, do not match the filename.** A file named for the right organisation was an unrelated event; a page screenshot would have been wrong. Opening images before use changed three of four matches.  
> * **Read back after every write.** Typing into Sheets grid cells silently failed while the formula bar showed correct text. Clipboard paste commits; per-character typing does not. In the Sites editor the opposite holds — inputs need real key events and ignore clipboard.  
> * **Prove focus before typing.** Tag the target element, click, assert document.activeElement is inside it, and abort otherwise. Blind typing put text in unrelated cells.

## **6\. Use the Sheets API, not the browser**

service\_account.json → <your-service-account>@<project>.iam.gserviceaccount.com writes to Sheets in a Shared Drive. Service accounts have zero personal Drive quota, so spreadsheets.create in My Drive fails as storageQuotaExceeded; inside a Shared Drive it works. Ten rows in one batchUpdate call, versus roughly eight seconds per cell through browser automation with retries. Browser automation is for Sites only.

## **7\. The build sequence**

> 1. **Index** — crawl the Drive folder and subfolders, metadata only, into 12\_DRIVE\_INVENTORY with a sensitivity tier per file. Nothing is read, moved, or shared.  
> 2. **Template** — the new artifact. Block presets derived from existing Sites, plus the site's theme, focus, audience and goals.  
> 3. **Propose** — AI drafts SITE\_PAGES and SITE\_CONTENT\_BLOCKS rows, each carrying a confidence score. Status stays Pending. Nothing touches the Site.  
> 4. **Human gate** — the client reads rows, not a live site, and approves. This is the existing hard gate, not a new one.  
> 5. **Build** — walk SITE\_CONTENT\_BLOCKS in block\_order and make the Site match. Log every run to SITE\_SYNC\_LOG.

**Idempotency:** Sites exposes no block IDs, so a second run cannot tell an existing block from a new one. Rebuild generated pages wholesale rather than diffing. That destroys manual edits, which is why PROP-007 managed\_by exists — agent-owned pages are rebuilt without mercy, human-owned pages are never touched.  
**Scaling limit (iteration 1 accepts this):** browser placement costs several UI interactions per block, roughly 30-45s each. Nine blocks is about seven minutes; a hundred is over an hour with a hundred chances to fail. The embed escape hatch is deliberately NOT used in iteration 1 — see §0. Keep pages block-count-bounded instead, and revisit render paths in iteration 2 once the presets exist.

## **8\. Browser session hygiene**

ws.close() closes the websocket, not the tab — tabs opened with /json/new survive it. The first build leaked one tab per script call. Use attach() to reuse a single tab and close\_tab() to actually close it.  
The larger cost was not tabs but **reloading the Sites editor on every invocation** (30-45s of load, exit-preview, open Pages panel, navigate) before doing \~30s of real work. One attached tab with the editor loaded once, iterating all blocks in a single pass, removes that entirely. The original three-block batching was a tool-timeout artifact, not a design constraint.  
**Claude in Chrome does not solve this.** The extension drives the active tab through the same debugger permission — the same CDP pipe, a different client. It is interactive-only (needs a human with the browser open) and unavailable to remote-control sessions, which have no \--chrome flag. The sidebar is a UX affordance, not a performance one.

## **9\. Open items**

> * Block heights vary because image aspect ratios differ. Normalise to one canvas before upload.  
> * The nine SBDC images live in a folder owned by a personal Gmail account while the catalog is org-owned in the shared drive. The catalog is durable; its assets are not.  
> * Most rows in 13\_BLOCK\_RECIPES remain "NO — untested." Only image (partial), embedded\_website, and layout\_media\_text (now proven) have evidence.  
> *   
> * GOVERNANCE — RATIFIED BY ANDREW, 2026-08-30  
> *   
> * These three are decisions, not observations. They govern every AI role in the  
> * Visual Second Brain Framework.  
> *   
> * 1\. THE COUNCIL PROPOSES WITH REASONING; THE HUMAN RATIFIES.  
> * No AI role decides what belongs on a client's site. Roles produce proposals that  
> * carry their reasoning; Andrew ratifies. The Site Charter carries a human  
> * signature, never a model's.  
> * WHY: the Constitution's Librarian Layer "does retrieval, not synthesis \- they  
> * tell the advisor what is relevant; they do not decide what to do with it," and  
> * CLAUDE.md \#2 holds that the AI assists and does not author. A firm operating at  
> * a high standard is tempting to delegate judgement to; this is the line that  
> * stops that drift.  
> *   
> * 2\. REFUSAL IS A FEATURE.  
> * The Curator may refuse to include a file the Charter does not justify. The  
> * Architect must refuse to plan pages when no Charter exists. A refusal is a valid  
> * deliverable and is never treated as a failed run.  
> * WHY: without it the council will generate a plausible site out of nothing,  
> * because producing something always looks more useful than declining. Refusal is  
> * what makes selection mean anything.  
> *   
> * 3\. EXCLUSIONS ARE RECORDED.  
> * Every file the Curator excludes is written to the Manifest with the rule that  
> * excluded it. Silent drops are prohibited.  
> * WHY: "why isn't this document on the site?" must be answerable in one lookup.  
> * If it cannot be answered, the client cannot tell a decision from an oversight,  
> * and trust in the whole catalogue goes with it.  
> *   
> * BINDING RULE. Every Manifest row cites a Charter goal (charter\_goal\_id). A row  
> * without one is invalid and does not execute. This mirrors the substrate's  
> * existing hard rule that every relation cites a source\_event\_id \- provenance  
> * applied to content decisions rather than facts.  
> *   
> *   
> * ADDED 2026-08-31 — THE GUARDS NOW LIVE IN THE HARNESS  
> * Sections 4 and 5 of this protocol were correct and were still not followed, because a written rule an agent can read past is not a control. The stage-6 guards are now executable in .agents/scripts/harness.py and are governed by The Build Harness v1.0.  
> * Two guards added from failures after v0.4 was written:  
> * GUARD 1 — assert the target before destroying. A page-selection click returned true and landed nowhere; clear\_page then deleted 18 sections from a finished Home page. clear\_page is now unreachable except through a function that has matched the page id parsed from the live URL. A click returning true is not evidence that the click worked.  
> * GUARD 2 — own the environment, never inherit it. A screenshot left Emulation.setDeviceMetricsOverride at 1400px. clearDeviceMetricsOverride returns ok and does nothing. Every later coordinate was computed against a layout the editor was not using. General form: a diagnostic must not change the system it is diagnosing.  
> * Also corrected: 'Four column image and captions' holds ONE caption per column, not two. Assuming two silently dropped two people from a page that reported success. Measure the preset; do not trust its name.  
> * Governing document: https://docs.google.com/document/d/1\_4107tyX6IPRDxBfCXjheSkWBpd4cT7QwdOPzz9Set8/edit  
> * 