# INFORMATION SYSTEMS ARCHITECTURE — <SITE NAME>

v0.1 — <date>. Why this site has these pages, in this order, holding this
content. **Written before anything is built.** Grounded in the <n> Charter goals
and the <n> included items. Expressed only in verified blocks.

---

## WHAT THIS SITE IS

One paragraph. What it is *for*, and who it is *internal to*.

Then state what it is **not**, explicitly: not a public face, not a funder
report, not a deliverable handed to the client — whichever apply. Sites drift
into being all three when nobody wrote down which one they are.

Its job is to answer, without anyone having to ask a person: `<the questions>`.

## THE READER

How many people. Name them if the number is small.

**What changes about them** — turnover, rotation, onboarding, hand-off. This is
usually the real design constraint, and it is usually the reason the site exists
at all. State it as a constraint, not as background.

Readers arrive with one of `<n>` questions. The architecture is those questions,
in the order they get asked:

1. `<question>` — `<who asks it, when>`
2. …

`<n>` questions, `<n>` pages. The structure is not a filing scheme; it is a list
of the things people actually come to find out.

## WHY THIS ORDER

Pages are ordered by **frequency of the question**, not importance of the
content. Name the page that is most important but sits low, and say why:
an architecture ordered by importance optimises for the rare visit and taxes the
common one.

If two tracks/audiences exist, **separate by audience before separating by
time.** Chronology is how a person reads *within* a page; audience decides which
page they open.

## THE PAGES

For each page:

### `<n>`. `<PAGE NAME>` — "`<the reader's question>`"

What is on it, in a sentence.

**Architectural decision:** the thing you decided *not* to do here, and why.
This is the most valuable line on the page — it is where the architecture earns
its keep. (Example shape: *this page does not list eighteen links, because an
index already exists in a sheet; rebuilding it would duplicate a structure, go
stale on the next addition, and cost eighteen placements.*)

**Blocks:** `<verified block types>`. `<n>` items.
**Serves:** `GOAL-nn`.
**Expiry:** any content with a shelf life, flagged for refresh.

Notes that recur and are worth keeping:
- **Home is never empty.** README plus executive summary at a high-school-
  freshman reading level, readable in under five minutes, ending with a map of
  every other page. Someone who reads only Home can still say what the site holds.
- A **lookup surface** is not a reading surface. Minimal framing, embed, nothing else.
- Group a long flat list into themes with a short authored paragraph each.
  Fifteen undifferentiated documents is a shelf, not an argument. A reader should
  be able to read only the theme paragraphs and understand the whole.

## WHAT THIS SITE DELIBERATELY DOES NOT DO

One paragraph per exclusion, each citing the goal behind it.

Cover at minimum: what was excluded for candour or privacy; what was excluded
because publishing it would reproduce the problem the site exists to remove
(e.g. the folder tree); what the advisor ruled out by decision.

State the significant exclusions **on the site itself**, so the absence reads as
a visible decision rather than a gap.

## BLOCK VOCABULARY — VERIFIED ONLY

List the block types required, each with its verification status.

**Design only with blocks that are verified buildable.** Designing around a block
that cannot be placed is designing a site that cannot be built.

Call out what is **notably not required**, and why the architecture removed the
need. (A render pass with no architecture over it reaches for link rows; grouping
and embedding eliminate them. That is the clearest evidence the architecture
belongs before the render — it *removed* the largest blocker rather than solving
it.)

## ESTIMATED BLOCK COST

Per page, then total. Compare against the un-architected render if one exists,
and say where the difference is concentrated.

## WHAT MUST BE VERIFIED BEFORE THIS CAN BE BUILT

Ordered by priority. A block type that the architecture depends on and that has
never been placed is the highest risk item in the plan.

## OPEN QUESTIONS FOR THE ADVISOR

Numbered. Real questions, where a different answer changes the architecture.
Not confirmations.

## REVISION LOG

Corrections supersede; both versions survive; the reasoning is recorded.

> **REVISION — `<date>`, `<who>`'s correction**
> What changed, the quote or decision that changed it, **why the first version
> was wrong**, and the principle extracted from it.
