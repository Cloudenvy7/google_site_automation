"""Translate a PAGE_WIREFRAME row into placed Site blocks, deterministically.

Identity is a DIFF of the cell list across the insert. Sites re-renders cells
as the page grows, so a data-* tag stamped before an insert is gone afterwards
and old cells look new -- which sent two paragraphs into one cell.

CORRECTION 2026-09-07, found by testing on a live page. This file used to say
"blocks are always appended, so the new block owns the cells from the old count
onward." That is FALSE. Insertion goes to the current insertion point, and when
append_point does not land at the bottom the block is inserted ABOVE existing
content -- observed on a real page, where a two-column block placed at DOM
indices 1..6 and pushed the previous block's cells from 10..14 down to 15..20.
Reading "from the old count onward" then addresses OTHER BLOCKS' cells.

It did not corrupt anything, because the occupancy check refused to write into
non-empty cells and returned ONLY_0_EMPTY_FOR_4_TEXTS. That refusal is the only
reason this was a finding rather than another scrambled page -- and it is also
what the "paragraph path is broken" symptom actually was.

So the new block's cells are found by diffing the cell signature list before and
after the insert: common prefix, common suffix, and whatever lies between is
what the insert created. That holds wherever Sites chose to put it.

The failure this replaces: filling used a global "first empty caption" search.
Every write verified against the cell it wrote to, and the page still came out
scrambled, because the cell it wrote to was not the cell that belonged to the
block just placed. Sites reflows as blocks are added, so DOM order is not a
stable address.

The fix is to mark every cell that exists BEFORE an insert, then treat whatever
is unmarked afterwards as this block's own cells. Those are sorted left to right
and filled from col_1, col_2, col_3. A column address cannot wander.
"""

import json
import time

import sites_automation as S


# A freshly inserted Text box renders its style picker INSIDE the gridcell, so
# the cell's innerText reads "Normal text\nTitle\nHeading..." and an emptiness
# test against the cell wrongly concludes the box is already occupied -- which
# is why three text boxes placed and none of them filled. Read the cell's own
# [contenteditable] instead; the picker is not one.
CELLTEXT = """(function(c){
  var e=c.querySelector('[contenteditable]');
  var t=((e?e.innerText:c.innerText)||'').trim();
  if(t==='Click to edit text') t='';
  if(/^Normal text\\n/.test(t)) t='';
  return t;})"""

COUNT = "document.querySelectorAll('[role=\"gridcell\"]').length"


def cell_count(ws):
    return S.eval_js(ws, COUNT) or 0


def cells_from(ws, start_index):
    """Cells at or after start_index in DOM order.

    Identity is the DOM INDEX, not geometry and not a data-* tag:
      - tags do not survive Sites re-rendering (two paragraphs merged into one)
      - y coordinates are viewport-relative because the editor scrolls an inner
        container, so window.scrollY is 0 and a saved 'floor' goes stale
    Blocks are always appended, so the new block owns the cells from the old
    count onward. Coordinates are re-read at click time, never cached.
    """
    raw = S.eval_js(ws, f"""
    (function(){{
      var CELLTEXT={CELLTEXT};
      var all=document.querySelectorAll('[role="gridcell"]');
      var o=[];
      for(var i={start_index}; i<all.length; i++){{
        var c=all[i], r=c.getBoundingClientRect();
        if(r.width<20) continue;
        o.push({{i:i, label:c.getAttribute('aria-label')||'',
                 x:Math.round(r.left),
                 empty: {CELLTEXT}(c)===''}});
      }}
      return JSON.stringify(o);
    }})()""")
    try:
        return json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []


def cell_signatures(ws):
    """(label, text) per gridcell, in DOM order -- the input to the insert diff."""
    raw = S.eval_js(ws, f"""
    (function(){{
      var CELLTEXT={CELLTEXT};
      var all=document.querySelectorAll('[role="gridcell"]');
      var o=[];
      for(var i=0;i<all.length;i++){{
        o.push([all[i].getAttribute('aria-label')||'', CELLTEXT(all[i])]);
      }}
      return JSON.stringify(o);
    }})()""")
    try:
        return [tuple(x) for x in json.loads(raw or "[]")]
    except (TypeError, ValueError):
        return []


def inserted_range(before, after):
    """Indices the insert created, by common-prefix/common-suffix diff.

    Do NOT assume the block landed at the end. It lands at the insertion point,
    which is above existing content whenever append_point misses.
    """
    n, m = len(before), len(after)
    if m <= n:
        return []
    p = 0
    while p < n and before[p] == after[p]:
        p += 1
    sfx = 0
    while sfx < (n - p) and before[n - 1 - sfx] == after[m - 1 - sfx]:
        sfx += 1
    return list(range(p, m - sfx))


def fill_index(ws, i, text):
    """Fill cell i (DOM order). Scrolls it into view and re-reads its position."""
    pt = S.eval_js(ws, f"""
    (function(){{
      var CELLTEXT={CELLTEXT};
      var c=document.querySelectorAll('[role="gridcell"]')[{i}];
      if(!c) return null;
      var t=CELLTEXT(c);
      if(t!=='') return JSON.stringify({{busy:t.slice(0,24)}});
      c.scrollIntoView({{block:'center'}});
      var r=c.getBoundingClientRect();
      return JSON.stringify({{x:Math.round(r.left+r.width/2),
                              y:Math.round(r.top+Math.min(r.height/2,40))}});
    }})()""")
    if not pt:
        return "CELL_GONE"
    p = json.loads(pt)
    if "busy" in p:
        return "REFUSED_OCCUPIED"

    S.click_at(ws, p["x"], p["y"])
    time.sleep(0.9)
    S.type_chars(ws, text, delay=0.11)

    probe = text[:28]
    for _ in range(14):
        time.sleep(0.7)
        got = S.eval_js(ws, f"""(function(){{
          var CELLTEXT={CELLTEXT};
          var c=document.querySelectorAll('[role="gridcell"]')[{i}];
          return c?CELLTEXT(c):'';}})()""") or ""
        if probe in got:
            return "FILLED"
    return "NOT_VERIFIED"


def build_section(ws, block_type, cols, insert_fn):
    """Place one block and fill only the cells that insert created.

    The cells are located by diffing the page before and after, never by
    "everything after the old count" -- see the correction in the module
    docstring. Fill order is COLUMN-MAJOR: entire left column, then the next.
    """
    before = cell_signatures(ws)
    if not insert_fn(ws):
        return f"{block_type}:INSERT_FAILED", []
    time.sleep(3.0)

    after = cell_signatures(ws)
    idx = inserted_range(before, after)
    if not idx:
        return f"{block_type}:NO_NEW_CELLS", []

    geom = {c["i"]: c for c in cells_from(ws, 0)}
    fresh = [geom[i] for i in idx if i in geom]

    texts = [c for c in cols if c and not str(c).startswith("[")]
    targets = [c for c in fresh if c["label"] == "Text" and c["empty"]]

    if not texts:
        return f"{block_type}:PLACED", fresh
    if len(targets) < len(texts):
        return (f"{block_type}:ONLY_{len(targets)}_EMPTY_FOR_{len(texts)}_TEXTS"
                f"@{idx[0]}-{idx[-1]}", fresh)

    out = []
    for cell, txt in zip(targets, texts):
        out.append(fill_index(ws, cell["i"], txt))
    return f"{block_type}:" + "+".join(out), fresh
