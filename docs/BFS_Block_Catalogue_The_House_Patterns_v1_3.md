<!-- MIRRORED FROM GOOGLE DRIVE. The Doc is canonical; edit it there.
     name     : BFS Block Catalogue - The House Patterns v1.3
     drive_id : 15_eyJizpy6TqZFOV5P4xT5LhxxxbI7FzuluPrkNaJ4s
     modified : 2026-08-31
     exported : 2026-09-07 as markdown
-->

# **BFS BLOCK CATALOGUE — THE HOUSE PATTERNS**

*v1.0 — 2026-08-31. Extracted by measurement from the reference site and Entrepreneurship: Business Launchpad, both live. These are not Google's presets. They are the patterns Andrew builds, named so they can be referenced, reproduced and verified. Names are proposed and are Andrew's to confirm.*

## **THE HOUSE RULE — HEADING ABOVE THE IMAGE**

Every multi-part block on both sites reads TOP DOWN: heading, then image, then body. Never image first with a caption beneath.  
The reason, in Andrew's words: an image followed by text underneath makes the reader associate the wrong caption with the wrong picture. A headline above the image tells you what you are about to look at, and the subtext below explains it. It reads correctly on a phone, where columns collapse into a single stack, and on desktop, where the eye scans left to right across the headings before descending.  
**This is the single most important thing in this catalogue.** Google's stock "Image and caption" preset puts the image FIRST. Using it unmodified produces the layout Andrew specifically rejects. Every house pattern below moves the heading above the image.

## **QUICK REFERENCE — ID, NICKNAME, PATTERN**

Call a block by its nickname in conversation, by its ID in a sheet. Both are permanent: a retired nickname is never reused, because an old sheet may still reference it.

| ID | Nickname | Pattern | Cells | Cols | Verified |
| :---- | :---- | :---- | :---- | :---- | :---- |
| BFS-01 | **MAINE** | Title Stack | 2 | 1 | no |
| BFS-02 | **OHIO** | Section Heading | 1 | 1 | no |
| BFS-03 | **NEVADA** | Rhythm Spacer | 1 | 1 | **YES** |
| BFS-04 | **TEXAS** | Full Bleed Image | 1 | 1 | partial |
| BFS-05 | **OREGON** | Media Left, Text Right | 3 | 2 | no |
| BFS-06 | **UTAH** | Two Up Feature Pair *(signature)* | 6 | 2 | no |
| BFS-07 | **KANSAS** | Four Up Course Card | 24 | 4 | no |
| BFS-08 | **IOWA** | Profile Row | 11 | 4 | no |
| BFS-09 | **GEORGIA** | Action Button | 1 | 1 | no |
| BFS-10 | **VERMONT** | Contact Row | 3 | 3 | no |
| BFS-11 | **ALASKA** | Drive Document Embed | 1 | 1 | no |
| BFS-12 | **HAWAII** | Custom Embed | 1 | 1 | **YES** |

**Why states.** One word, universally known, no collision with web or design vocabulary, and a large reserve — thirty-eight names remain unassigned for patterns not yet found. Four carry a mnemonic worth keeping: **NEVADA** is empty space, **TEXAS** is the full-width one, and **ALASKA** and **HAWAII** are the two detached ones that pull content from outside the site.  
Two-word states (New York, Rhode Island) and long ones (Massachusetts) are deliberately avoided — the whole point is that the name is faster to say than the pattern.

THE NAMING CONVENTION

Tier 1 — STATES. House patterns: shapes that recur across more than one BFS site. Twelve assigned, thirty-eight remain.

Tier 2 — US CITIES. Everything after the states run out, and site-specific variants. Austin, Denver, Tacoma, Boise, Reno, Tulsa, Fargo, Erie, Provo, Bend and several hundred more all pass the rules below.

The tiers carry meaning, and that is the point of splitting them: if you hear a STATE it is part of the house vocabulary and should look familiar across clients. If you hear a CITY it is a local variant built for one site. That tells you, before opening anything, whether changing it affects one client or all of them.

RULES FOR ANY NEW NAME

1\. One word. No New York, no Salt Lake City, no Rhode Island.  
2\. Short. Two or three syllables. Massachusetts and Indianapolis are out.  
3\. Passes the speech test — clearly distinct from every name already assigned when said aloud on a call. IDAHO was rejected for being too close to IOWA.  
4\. No state/city collisions. Kansas City, Oklahoma City and New York are barred because KANSAS and NEW YORK already mean something, or could.  
5\. Avoid cities that exist in several states where the ambiguity could matter in conversation. Springfield is barred. Portland is usable but only once.  
6\. Names are permanent. A retired pattern keeps its name forever; an old sheet may still reference it, and a reused name silently repoints history at the wrong shape.

The register of assigned names lives in this document. Check it before assigning, or two people will name two different blocks OHIO in the same month.  
**Speech test:** nicknames must be distinguishable when spoken aloud. IDAHO was rejected for the Action Button because it is too close to IOWA; GEORGIA replaced it.

## **BFS-01 · MAINE — TITLE STACK**

One column, two text cells stacked. Site title then subtitle.  
Observed: the reference site Home s1 (y \-163, \-98) · BLP Home s1  
Cells: 2 · Fill order: title, subtitle · Verified: NO

## **BFS-02 · OHIO — SECTION HEADING**

One column, one text cell, full width. Announces the group that follows.  
Observed: BLP "The Four Part Series" (s9), "The Instructors" (s16)  
Cells: 1 · Verified: NO

## **BFS-03 · NEVADA — RHYTHM SPACER**

One spacer. Used in runs of two to four between major groups.  
Observed: the reference site s2-s5 (four consecutive), s9-s11, s17-s18 · BLP s14-s15  
Cells: 1 · Verified: YES — placed and read back 2026-08-30  
Note: roughly a quarter of all blocks on the reference site Home. Omitting these produces a page that is structurally correct and visually wrong. Spacers are content.

## **BFS-04 · TEXAS — FULL BLEED IMAGE**

One column, one image, full content width (1154px on desktop).  
Observed: the reference site s8 · BLP s5  
Cells: 1 · Verified: PARTIAL — Drive and Upload paths proven; placement not isolated

## **BFS-05 · OREGON — MEDIA LEFT, TEXT RIGHT**

Two columns. Media occupies the left; heading and body stack on the right.  
Observed: the reference site s12 (Drive PDF embed \+ "A Legacy at a Crossroads" \+ body) · BLP s7 (image \+ "The Overview & Objectives" \+ body)  
Cells: 3 · Columns: media x121, text x545 · Fill order: media, heading, body  
Verified: NO — the closest stock preset is "Image and caption", which is not this shape

## **BFS-06 · UTAH — TWO UP FEATURE PAIR *(the signature)***

Two columns. Each column: heading, image, body — in that vertical order.  
Observed: the reference site s14 ("The Project" / "The Goal") and s16 ("Development" / "Deliverables")  
Cells: 6 · Columns: x121, x630 · Image height approx 270px  
Vertical order per column: heading (y2583), image (y2647), body (y2917)  
Fill order: c1 heading, c2 heading, c1 image, c2 image, c1 body, c2 body — ROW MAJOR, because the cells are laid out in rows of two  
Verified: NO  
**Caution:** Google's "Two column image and captions" preset produces image-then-caption and its DOM order is COLUMN major. It is not this block. Do not substitute it.

## **BFS-07 · KANSAS — FOUR UP COURSE CARD**

Four columns, six rows. The richest pattern on either site.  
Observed: BLP s13, the four-class series  
Cells: 24 · Columns: x121, x375, x630, x885  
Vertical order per column: label ("Class \#1"), subheading (topic), image, button (material link), date, body  
Verified: NO  
Note: KANSAS is UTAH extended. Same grammar — heading above image — with an action and a date added. A four-part series renders as one block, not four.

## **BFS-08 · IOWA — PROFILE ROW**

Four columns alternating image and text, used for people.  
Observed: BLP s18 — image, name, "Open Hours", dates, email  
Cells: 11 (uneven; one profile carries an extra date line)  
Verified: NO  
Note: the unevenness is real content, not a defect. Do not pad it for symmetry.

## **BFS-09 · GEORGIA — ACTION BUTTON**

One button, centred, standing alone between sections.  
Observed: the reference site s19 "Book Your Next Meeting" · BLP s4, s11, s19 (Zoom links)  
Cells: 1 · Verified: NO  
Note: on the reference site it sits directly above the calendar embed. Button then embed is a pair.

## **BFS-10 · VERMONT — CONTACT ROW**

Three columns of text: name, email, and a third field.  
Observed: BLP s22  
Cells: 3 · Verified: NO

## **BFS-11 · ALASKA — DRIVE DOCUMENT EMBED**

A Drive file rendered inline, usually as the left media of OREGON.  
Observed: the reference site s12 — Joe\_Brazil\_Legacy\_Securing\_History-merged.pdf  
Verified: NO — embed target resolves from the iframe src

## **BFS-12 · HAWAII — CUSTOM EMBED**

Third-party embed by code. On the reference site, a Google Calendar appointment scheduler.  
Observed: the reference site s20, paired beneath GEORGIA  
Verified: YES as a mechanism (RCRC dashboard)  
**Retrieval note:** Sites wraps custom embeds in a cross-origin gstatic shim, so the iframe src reveals nothing. The original embed code survives on a **data-code** attribute on the cell. Without reading that attribute the block cannot be catalogued.

## **VERIFICATION STATE**

Verified 2 of 12\. Partial 1\. That is the honest position, and it is the queue.  
Priority order for verification, by how often the pattern appears across both sites:  
1\. NEVADA (BFS-03) rhythm spacer — done  
2\. UTAH (BFS-06) two up feature pair — the signature, four instances  
3\. GEORGIA (BFS-09) action button — four instances  
4\. OREGON (BFS-05) media left text right — two instances  
5\. OHIO (BFS-02) section heading — two instances  
6\. MAINE (BFS-01) title stack — two instances

## **WHAT VERIFIED MEANS**

Placed on a real page, read back from the page, cell map recorded, and the result written down — including the fill order and any trap. Not: "it appears in a menu and looks right."  
Each verified recipe records: the Sites UI path, cell count, column x-positions, vertical order, fill order, and the failure mode observed when it goes wrong.

UTAH — BUILD DECISION, RATIFIED BY ANDREW 2026-08-31

Automation builds UTAH from the stock preset and accepts image-on-top. Repositioning to  
the house order (heading above image) is done by hand afterwards, when it matters.

WHAT WAS TESTED, AND WHAT IT SHOWED

Two-column grid from the preset — WORKS. One menu click. Columns land at x=121 and x=630,  
width 484 each, which are the reference site's own column positions. No dragging.  
Vertical stacking by insert order — WORKS. Text box then image places the image below the  
heading. Order follows sequence, not coordinates.  
Filling cells by DOM index — WORKS. Both columns fill correctly, row-major.  
Duplicate a cell — WORKS as a button, but the copy lands BELOW, never beside. It cannot  
create a column.  
Removing a preset's image placeholder — DOES NOT WORK. Selecting a Content placeholder  
exposes no Remove control at all, unlike a Text cell which exposes Duplicate and Remove.  
The placeholder is structural to the preset.  
Dragging a cell to reorder — DOES NOT WORK. Press-move-release on the cell centre leaves  
the grid byte-identical.

WHY THE DECISION

The house order requires either removing the placeholder or reordering within the section,  
and neither has a deterministic path. Both remaining routes need a manual gesture. Blocking  
the whole cycle on one block's vertical order costs more than the order is worth right now,  
and placement is recoverable by hand later. The cycle matters more than the block.

WHAT THIS MEANS IN PRACTICE

The automation produces image, heading, body. The house pattern is heading, image, body.  
Every UTAH block placed by machine therefore carries a known, recorded deviation that a  
human corrects. This is a deviation, not a redefinition: the catalogue still records UTAH  
as heading-above-image, because that is the design. Do not quietly rewrite the pattern to  
match what the tool can currently do.

REOPEN THIS IF: Sites exposes a cell-level Remove on image placeholders, a reorder control  
appears, or a preset ships with text above media.