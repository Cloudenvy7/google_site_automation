"""Translate a PAGE_WIREFRAME row into placed Site blocks, deterministically.

Identity is GEOMETRIC, not attribute-based. Sites re-renders cells as the page
grows, so a data-* tag stamped before an insert is gone afterwards and old cells
look new -- which sent two paragraphs into one cell. Blocks are always appended,
so the new block owns exactly the cells below the previous bottom edge.

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
    """Place one block and fill only the cells it created, addressed by DOM index."""
    before = cell_count(ws)
    if not insert_fn(ws):
        return f"{block_type}:INSERT_FAILED", []
    time.sleep(3.0)

    fresh = cells_from(ws, before)
    texts = [c for c in cols if c and not str(c).startswith("[")]
    targets = [c for c in fresh if c["label"] == "Text" and c["empty"]]

    if not texts:
        return f"{block_type}:PLACED", fresh
    if len(targets) < len(texts):
        return f"{block_type}:ONLY_{len(targets)}_EMPTY_FOR_{len(texts)}_TEXTS", fresh

    out = []
    for cell, txt in zip(targets, texts):
        out.append(fill_index(ws, cell["i"], txt))
    return f"{block_type}:" + "+".join(out), fresh
