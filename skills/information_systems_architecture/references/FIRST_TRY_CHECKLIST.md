# First-try checklist

Every line is something that cost at least one rebuild. Read before building.

## Before you start

- [ ] Catalogue **copied** from the template — all eleven tabs, `00_HARNESS` and
      `WAIVERS` present. Never hand-assembled.
- [ ] `00_README` Stage 0 keys filled; `isa_status` is `RATIFIED`.
- [ ] ISA written **for this site** and ratified by the human.
- [ ] Charter, Manifest, Page Plan ratified. `ratified_by` and `ratified_date` set.
- [ ] Every value you are about to render **already exists as a cell**. If you
      are typing a name from memory of a conversation, stop — that is the
      failure that shipped a 15-person team page with 6 people on it.
- [ ] No dependent row carries `UNKNOWN` / `NOT ESTABLISHED` / `TBD` /
      `NOT RECORDED` without a human-signed waiver.

## Gathering information

- [ ] **Go and look before declaring a gap.** A roster, a date, a name — assume
      it is in the folder and search. Writing `NOT ESTABLISHED` and building
      around it is not a resolution.
- [ ] Attendance, membership and rosters usually live in **meeting logs**, not in
      a roster document.
- [ ] Organisation comes from **email domains** in message threads, never from
      a name or a guess.
- [ ] If a source does not state it, the cell says what is missing. A blank with
      a reason outranks a plausible guess.

## Browser build (Google Sites over CDP)

- [ ] Set the viewport **explicitly** at run start; abort if it does not take.
      `clearDeviceMetricsOverride` returns ok and does nothing — a screenshot
      that leaves a 1400px override makes every later coordinate wrong.
- [ ] A diagnostic must not change the system it is diagnosing.
- [ ] **Assert the page id from the live URL before any destructive step.** A
      click returning true is not evidence the click worked. This is what
      deleted a finished Home page.
- [ ] Address cells by **diffing the cell list across the insert** — common
      prefix, common suffix, and what lies between is what the insert created.
      **Do NOT use "everything after the old count."** Verified false on a live
      page 2026-09-07: with 21 cells present, a block landed at indices 1–6 and
      pushed existing content down. "First empty cell on the page" wanders too.
- [ ] **`append_point` is not guaranteed to reach the bottom.** Sites inserts at
      the current insertion point, so a missed append puts the new block ABOVE
      existing content. Never infer position; diff for it.
- [ ] **Re-probe the layout tile's aria-label before trusting it.** It changed
      from `Image and caption` to `Add layout: Image and caption` and every
      insert failed with a bare TIMEOUT. Google owns this DOM. Use
      `probe_controls()` rather than guessing a spelling.
- [ ] Verify text through its `contenteditable`, not the container. A new text
      box renders its style picker inside the cell, so a naive emptiness test
      reads "Normal text / Title / Heading" and skips the box.
- [ ] Verify images from the **published** page. The editor lazy-renders them as
      placeholders.
- [ ] Type at **0.11 s/char**. 0.04 and 0.05 transpose silently — "PAARGRAPH".
- [ ] Scroll a target into view before clicking. Off-screen clicks do nothing and
      the failure presents as a missing menu item.
- [ ] Clipboard paste works in Sheets grid cells and **fails** in Sites text boxes.

## Measured stock presets

| Preset | Actual shape |
|---|---|
| Text box | 1 cell, no image |
| Image and caption | image **LEFT**, text right — **not** stacked. Wrong for person cards. |
| Two column image and captions | image on top, **two** text lines under, per column. 2 img + 4 text. |
| Four column image and captions | image on top, **one** caption per column. 4 img + 4 text. |

Fill order is **column-major**: c1 line1, c1 line2, c2 line1, c2 line2.

Re-measure on any preset you have not personally placed. Names lie.

## After

- [ ] `SITE_SYNC_LOG` row written — successes, failures **and** open defects.
- [ ] Every entity on a page has a row with evidence and confidence.
- [ ] Corrections marked visibly; both versions survive.
- [ ] A separate instance audits. Maker is never checker.
