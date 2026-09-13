# Architecture principles

Each principle carries the failure that produced it. A rule without its
reasoning is cargo — the next session cannot evaluate it and will either discard
it or obey it blindly.

Derived from the HopeLink Ride Ready build (2026-08-28 to 09-01). The principles
are general; the evidence is specific.

---

## On structure

**One reader question = one page.** The structure is the list of things people
come to find out, not a filing scheme and not the folder tree.

**Order pages by frequency of the question, not importance of the content.**
An architecture ordered by importance optimises for the rare visit and taxes the
common one. HopeLink's most important page sits third because it is read once,
while the briefs are read weekly.

**Separate by AUDIENCE before separating by TIME.**
*Failure:* the ISA put two meeting tracks on one page and argued chronology —
a reader wants to know what happened in order. Andrew: *"There are two separate
team meetings that might have the same type of people but they're not on the
same page because we only need one team to look at one."* The tracks were not two
views of one thing; they were two audiences. Merging them made every reader
scroll past half a page that was never for them, every week. Chronology is how a
person reads *within* a page; audience decides which page they open.

**Do not rebuild an index that already exists.** If a sheet already indexes the
material, embed it. Rebuilding it as hand-placed rows duplicates a structure,
goes stale on the next addition, and costs one placement per row.

**Group a long flat list into themes, each with an authored paragraph.**
Fifteen undifferentiated documents is a shelf, not an argument. A reader should
be able to read only the theme paragraphs and understand the programme.

**Home is never empty.** README plus executive summary at a high-school-freshman
reading level, under five minutes, ending with a map of every other page.

## On what to leave out

**Exclusions are recorded, and the significant ones are visible on the site.**
An absence should read as a decision, not a gap. HopeLink excludes raw
transcripts because verbatim speech is where criticism of people lives, and the
briefs stay candid only while the room stays candid — so Home says so.

**Do not publish the folder tree.** The site usually exists so that nobody has to
navigate folders. Reproducing the tree reproduces the problem.

**Refusal is a valid deliverable.** The council proposes with reasoning; the
human ratifies.

## On blocks

**Design only with blocks that are verified buildable.** Designing around a block
that cannot be placed is designing a site that cannot be built.

**The architecture removes blockers rather than solving them.**
*Evidence:* the first render pass wanted 33 external link rows, because it was
placing documents with no architecture telling it not to. Grouping and embedding
removed the need entirely. That is the clearest argument for writing the
architecture before the render.

**Measure the preset; do not trust its name.**
*Failure:* "Four column image and captions" was assumed to hold a name and a role
per column. It holds ONE caption per column. Eight values went into four slots,
two people vanished, and the build reported success.

## On evidence

**A goal you cannot quote is a goal you invented.** Every charter goal carries
the client's own sentence.

**Affiliation is evidenced, never inferred from a name.**
*Failure:* a consultant was placed inside the client organisation because the
architecture had no evidence column. Email domains in a message thread settled it
correctly.

**Never state a scope, constraint or decision as the client's unless you can
point to where they said it.** Archive first, memory second, assertion last.

## On sequence

**The ISA is written at Stage 0** — before the folder is indexed, not between
analysis and build.
*Failure:* build was proposed twice with no ISA. Andrew, twice: *"the whole point
of this was the right the information systems architecture now before spending a
second building."*

**Analysis completes before rendering is considered; rendering completes before
building starts.** Andrew: *"block rules should only be considered after all the
content and themes and philosophy has been considered — I don't want the system
rushing to build until a full analysis has been done."*

**Ask at most five questions; ten is the ceiling.** Fifteen was too many.

**A harness written after the build is an audit.** Guardrails ship at the
beginning; their authority comes from arriving early.
