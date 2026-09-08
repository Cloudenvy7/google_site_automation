"""Build one Site page by walking SITE_CONTENT_BLOCKS in block_order.

Returns a per-block status so SITE_SYNC_LOG records what actually landed. Most
recipes in 13_BLOCK_RECIPES are marked untested; this is what tests them, so a
failure is a finding rather than an error to swallow.
"""

import json
import time
import sites_automation as S


def cells(ws):
    return S.eval_js(ws, "document.querySelectorAll('[role=\"gridcell\"]').length") or 0


def append_point(ws):
    """Move the insertion point to the end of the page WITHOUT putting a caret
    in a text cell.

    The previous version clicked the centre of the last gridcell. When that cell
    was a Text cell the click placed the caret inside it, so the next block's
    text typed into the PREVIOUS block -- producing merged paragraphs and, when
    two blocks fought over one cell, character-interleaved text like
    "The PDreovjeelcotpmnet". Click the empty canvas BELOW the last section, then
    press Escape to drop any lingering caret.
    """
    S.eval_js(ws, "window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1.4)
    pt = S.eval_js(ws, """
    (function(){
      var cells=document.querySelectorAll('[role="gridcell"]');
      if(!cells.length) return null;
      var maxB=0, left=250, right=1400;
      cells.forEach(function(c){
        var r=c.getBoundingClientRect();
        if(r.width<20) return;
        if(r.bottom>maxB) maxB=r.bottom;
      });
      // a point just under the last section, inside the canvas but in no cell
      var y=Math.round(maxB+28);
      var el=document.elementFromPoint(Math.round((left+right)/2), y);
      var inCell = el && el.closest && el.closest('[role="gridcell"]');
      return JSON.stringify({x:Math.round((left+right)/2), y:y,
                             in_cell: !!inCell});
    })()""")
    if pt:
        p = json.loads(pt)
        if not p.get("in_cell"):
            S.click_at(ws, p["x"], p["y"])
            time.sleep(0.6)
    # drop any caret so typing cannot land in a previous block
    for kind in ("rawKeyDown", "keyUp"):
        __import__("chrome_automation").send_ws_cmd(ws, "Input.dispatchKeyEvent", {
            "type": kind, "key": "Escape", "code": "Escape",
            "windowsVirtualKeyCode": 27, "nativeVirtualKeyCode": 27})
    time.sleep(0.6)


def insert_menu(ws, item):
    """Insert > <item>. Returns True if the gridcell count rose."""
    before = cells(ws)
    if not S.click_control(ws, "Insert", exact=True):
        return False, before, before
    time.sleep(2)
    m = S.wait_for_control(ws, item, exact=True, attempts=8, role="menuitem")
    if not m:
        return False, before, before
    S.click_at(ws, m["x"], m["y"])
    time.sleep(3.5)
    after = cells(ws)
    return after > before, before, after


def clear_page(ws, max_sections=60):
    """Delete every section. Generated pages are rebuilt wholesale, not diffed --
    Sites exposes no block IDs, so there is no way to reconcile in place."""
    removed = 0
    for _ in range(max_sections):
        btn = S.find_control(ws, "Delete section", exact=True, role="button")
        if not btn:
            break
        S.eval_js(ws, """(function(){var b=document.querySelector('[aria-label="Delete section"]');
         if(b) b.scrollIntoView({block:'center'});})()""")
        time.sleep(0.8)
        btn = S.find_control(ws, "Delete section", exact=True, role="button")
        if not btn:
            break
        S.click_at(ws, btn["x"], btn["y"])
        time.sleep(1.6)
        removed += 1
    return removed


def fill_layout_now(ws, text):
    """Fill THIS layout's captions immediately after placing it.

    Filling in a later batch is what scrambled the first build: the helper takes
    the first empty cell in DOM order, which wanders across every unfilled block
    on the page. Filling straight away means only one block has empty cells.
    """
    parts = [p.strip() for p in text.split("|")] if "|" in text else [text]
    out = []
    for p in parts:
        if not p:
            continue
        out.append(S.fill_next_empty_caption(ws, p))
    return "+".join(out) if out else "NO_TEXT"


def insert_layout(ws, label):
    """Layout tiles are divs, not menuitems, so they need their own lookup."""
    before = cells(ws)
    if not S.click_control(ws, "Insert", exact=True):
        return False, before, before
    time.sleep(2)
    t = S.wait_for_control(ws, label, exact=True, attempts=8, role="div")
    if not t:
        return False, before, before
    S.click_at(ws, t["x"], t["y"])
    time.sleep(3.5)
    a = cells(ws)
    return a > before, before, a


def build_block(ws, block_type, text=""):
    append_point(ws)

    if block_type == "paragraph":
        ok, b, a = insert_menu(ws, "Text box")
        if not ok:
            return "TEXTBOX_NOT_PLACED"
        if text:
            if not (S.eval_js(ws, "document.querySelectorAll('[contenteditable=\"true\"]').length") or 0):
                return "PLACED_BUT_NOT_EDITABLE"
            S.type_chars(ws, text)
            time.sleep(1.5)
            if text[:40] not in (S.eval_js(ws, "document.body.innerText") or ""):
                return "TEXT_NOT_VERIFIED"
        return "OK"

    if block_type == "spacer":
        ok, b, a = insert_menu(ws, "Spacer")
        return "OK" if ok else "SPACER_NOT_PLACED"

    if block_type == "calendar_button":
        ok, b, a = insert_menu(ws, "Button")
        if not ok:
            return "BUTTON_NOT_PLACED"
        return "OK_LABEL_PENDING"          # label needs the button's own dialog

    if block_type in ("image", "image_x2", "image_x3"):
        return "SKIPPED_NO_ASSET"          # no image chosen yet - do not invent one

    if block_type in ("paragraph_x2", "paragraph_x3"):
        ok, b, a = insert_layout(ws, "Add layout: Two column image and captions")
        if not ok:
            return "MULTICOL_NOT_PLACED"
        return "LAYOUT:" + fill_layout_now(ws, text)

    if block_type == "drive_file_embed":
        return "DEFERRED_PICKER"           # Drive picker is a separate interaction
    if block_type == "embedded_website":
        return "DEFERRED_EMBED_DIALOG"

    return f"NO_RECIPE:{block_type}"
