"""Build the workshops page: one Image-and-caption block per workshop row.

Composes the proven pieces rather than adding new ones:
  wireframe_build.build_section  placement + caption fill, targeted by DIFFING
                                 the cell list across the insert
  drive_upload.upload_via_file_chooser   image bytes disk -> Chrome
  harness.guard_2_viewport / guard_1_assert_page   own the environment, assert
                                 the target before touching it

WHY NOT build_blocks.py, which already does this
It fills captions with S.fill_layout ("next empty caption in DOM order") and
targets images with querySelector('[aria-label="Content placeholder"]') -- the
FIRST placeholder on the page. Both are the same defect: a global search for
"the next empty thing" is not an address, and on a page with nine blocks it
wanders. That is what scrambled three pages in August. Here every cell is
addressed by the DOM index the insert-diff returned for THIS block.

The image slot is likewise addressed by index. A filled slot stops advertising
itself as a Content placeholder, so "the first placeholder" happens to work
while you fill strictly in order -- and stops working the moment you do not.
Do not rely on an accident.

usage:
  build_workshops.py <sheet_id> <site_id> <page_id> <image_dir> [--limit N]
"""

import json
import os
import sys
import time

import google.oauth2.service_account as sa
from googleapiclient.discovery import build as gbuild

import build_page as B
import drive_upload as D
import harness as H
import sites_automation as S
import wireframe_build as W
import config

SA = config.service_account_path()
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sept", "Oct", "Nov", "Dec"]


# ----------------------------------------------------------------- the sheet

def rows(sheet_id):
    """Workshops joined to Hours Log on Related Workshop, in date order.

    Hours live only in Hours Log; the Workshops tab has attendees but not hours.
    A workshop with no matching log row keeps its own attendee count and says
    nothing about hours rather than inventing a number.
    """
    c = sa.Credentials.from_service_account_file(
        SA, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    sh = gbuild("sheets", "v4", credentials=c).spreadsheets()

    def tab(name):
        v = sh.values().get(spreadsheetId=sheet_id, range=f"'{name}'").execute()["values"]
        h = v[0]
        return [dict(zip(h, r + [""] * (len(h) - len(r)))) for r in v[1:] if any(r)]

    log = {}
    for r in tab("Hours Log"):
        k = (r.get("Related Workshop") or "").strip()
        if k:
            log[k] = r
    out = []
    for w in tab("Workshops"):
        t = (w.get("Workshop Title") or "").strip()
        if not t:
            continue
        w["_log"] = log.get(t, {})
        out.append(w)
    return sorted(out, key=lambda r: (r.get("Date") or "9999"))


def pretty_date(start, end=""):
    def part(d):
        y, m, dd = d.split("-")
        return MONTHS[int(m) - 1], str(int(dd)), y
    if not start:
        return ""
    m1, d1, y1 = part(start)
    if not end:
        return f"{m1} {d1}, {y1}"
    m2, d2, y2 = part(end)
    if (m1, y1) == (m2, y2):
        return f"{m1} {d1}-{d2}, {y1}"
    return f"{m1} {d1} - {m2} {d2}, {y2}"


def caption(r):
    """heading, body. Every value comes from a cell; nothing is composed from
    memory of a conversation (GUARD 7, and the reason the Team page shipped
    with six of fifteen people)."""
    head = (r.get("Workshop Title") or "").strip()
    bits = [pretty_date((r.get("Date") or "").strip(), (r.get("End Date") or "").strip())]
    hours = (r["_log"].get("Hours") or "").strip()
    if hours:
        bits.append(f"{hours} hour" + ("s" if hours not in ("1", "1.0") else ""))
    att = (r["_log"].get("Attendees") or r.get("Attendee Count") or "").strip()
    if att:
        bits.append(f"{att} attended")
    return head, " · ".join(b for b in bits if b)


# ----------------------------------------------------------------- the image

def upload_into(ws, cell_index, path):
    """Put `path` into the image slot at DOM index `cell_index`.

    Addressed by index, not by "the first Content placeholder". Coordinates are
    re-read immediately before the click and the cell is scrolled into view
    first -- an off-screen click does nothing and presents as a missing Upload
    menu item, which cost a run in August.
    """
    before = S.eval_js(ws, "document.querySelectorAll('img').length") or 0

    def do_click():
        # Scroll the TARGET cell into view, then pick the "Insert content"
        # control that lies within its rectangle. The control is not a DOM
        # descendant of the gridcell -- looking for it inside the cell finds
        # nothing, the click lands on the cell itself, no menu opens, and the
        # failure presents as NO_FILE_CHOOSER_EVENT. Geometry is the join here;
        # a global "first Insert content" would wander once there are nine.
        S.eval_js(ws, f"""
        (function(){{
          var c=document.querySelectorAll('[role="gridcell"]')[{cell_index}];
          if(c) c.scrollIntoView({{block:'center'}});
        }})()""")
        time.sleep(1.8)
        box = S.eval_js(ws, f"""
        (function(){{
          var c=document.querySelectorAll('[role="gridcell"]')[{cell_index}];
          if(!c) return null;
          var r=c.getBoundingClientRect();
          return JSON.stringify({{l:r.left,t:r.top,rt:r.right,b:r.bottom}});
        }})()""")
        if not box:
            print(f"      cell {cell_index} vanished"); return
        bx = json.loads(box)
        cands = [c for c in S.probe_controls(ws, 400)
                 if c["label"] in ("Insert content", "Upload image", "Add image")]
        inside = [c for c in cands
                  if bx["l"] - 8 <= c["x"] <= bx["rt"] + 8 and bx["t"] - 8 <= c["y"] <= bx["b"] + 8]
        target = inside[0] if inside else (
            min(cands, key=lambda c: abs(c["y"] - (bx["t"] + bx["b"]) / 2)) if cands else None)
        if not target:
            print(f"      no 'Insert content' control near cell {cell_index}; "
                  f"saw {sorted({c['label'] for c in cands})}")
            return
        print(f"      click 'Insert content' @({target['x']},{target['y']})")
        S.click_at(ws, target["x"], target["y"])
        time.sleep(3.0)
        u = S.find_control(ws, "Upload", exact=True)
        if not u:
            menu = sorted({c["label"] for c in S.probe_controls(ws, 400)
                           if c["role"] in ("menuitem", "button")})
            print(f"      no Upload menu item; nearby menu {menu[:10]}")
            return
        print(f"      click 'Upload' @({u['x']},{u['y']})")
        S.click_at(ws, u["x"], u["y"])

    res = D.upload_via_file_chooser(ws, do_click, [path], timeout=40)
    if res != "FILES_SET":
        # One retry. The interceptor is armed per attempt, and a menu that was
        # already open when the first attempt began swallows the click that
        # should have opened the chooser.
        S.eval_js(ws, "document.activeElement && document.activeElement.blur()")
        time.sleep(2)
        res = D.upload_via_file_chooser(ws, do_click, [path], timeout=40)
    if res != "FILES_SET":
        return f"UPLOAD_{res}"
    for _ in range(20):                       # poll; do not sleep a fixed guess
        time.sleep(1.5)
        if (S.eval_js(ws, "document.querySelectorAll('img').length") or 0) > before:
            return "OK"
    return "IMAGE_COUNT_DID_NOT_RISE"


# ----------------------------------------------------------------- the build

def insert_tile(ws):
    ok, _, _ = B.insert_layout(ws, "Image and caption")
    return ok


def read_cells(ws):
    """i, label and TEXT per gridcell. wireframe_build.cells_from reports
    emptiness but not content, and reconciling a half-built page needs to know
    which workshop a block already holds."""
    raw = S.eval_js(ws, r"""
    (function(){
      var cs=document.querySelectorAll('[role="gridcell"]'); var o=[];
      for(var i=0;i<cs.length;i++){
        var c=cs[i], e=c.querySelector('[contenteditable]');
        var t=((e?e.innerText:c.innerText)||'').replace(/\s+/g,' ').trim();
        if(t==='Click to edit text') t='';
        if(/^Normal text /.test(t)) t='';
        o.push({i:i, label:c.getAttribute('aria-label')||'', text:t});
      }
      return JSON.stringify(o);
    })()""")
    try:
        return json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []


def page_blocks(ws):
    """Every Image-and-caption block on the page: (media, heading, body).

    WHY THIS EXISTS (2026-09-08, the hard way)
    The first run filled a block's captions and then failed on the image. The
    script stopped, correctly, leaving the page mid-build. The RERUN then read
    that block as "not empty", appended a fresh one, and produced a duplicate.
    Stopping cleanly is worthless if the next run cannot see what the last one
    did -- the same lesson as the indexer: state lives in the artifact, and the
    artifact here is the page. So read the page and reconcile against it rather
    than assuming a blank slate.
    """
    cells = read_cells(ws)
    by_i = {c["i"]: c for c in cells}
    out = []
    def lab(c):
        return (c.get("label") or "").strip().lower()

    for c in cells:
        # Match on substance, not an exact string. A filled slot's aria-label
        # is not the same as an empty one's, and an exact-match list silently
        # dropped the second block on a two-block page -- the reconciler then
        # could not see a duplicate it had itself created.
        media = "placeholder" in lab(c) or lab(c) == "image" or lab(c).startswith("image")
        if not media:
            continue
        h, b = by_i.get(c["i"] + 1), by_i.get(c["i"] + 2)
        if not h or not b or lab(h) != "text" or lab(b) != "text":
            continue
        out.append({"media_i": c["i"], "has_image": "placeholder" not in lab(c),
                    "head_i": h["i"], "head": h["text"],
                    "body_i": b["i"], "body": b["text"]})
    return out


def main(sheet_id, site_id, page_id, img_dir, limit=None):
    ws, _ = S.attach(f"https://sites.google.com/u/1/d/{site_id}/p/{page_id}/edit")
    for _ in range(60):
        time.sleep(1)
        if S.find_control(ws, "Publish", exact=True):
            break
    else:
        print("editor never loaded"); return 1

    H.guard_2_viewport(ws)
    H.guard_1_assert_page(ws, page_id)        # refuses if we are not on the target
    print(f"page asserted : {page_id}\ncells before  : {W.cell_count(ws)}\n")

    ws_rows = rows(sheet_id)[: int(limit)] if limit else rows(sheet_id)
    results = []

    # Reconcile against what is already on the page, so a rerun after a partial
    # run completes it instead of duplicating it.
    existing = page_blocks(ws)
    claimed, dupes = {}, []
    for blk in existing:
        if not blk["head"]:
            continue
        if blk["head"] in claimed:
            dupes.append(blk)
        else:
            claimed[blk["head"]] = blk
    if claimed:
        print(f"already on the page: {len(claimed)} block(s) "
              f"({sum(1 for b in claimed.values() if b['has_image'])} with an image)")
    if dupes:
        print(f"DUPLICATES: {len(dupes)} block(s) repeat a heading already present.")
        for d in dupes:
            print(f"   cells {d['media_i']}-{d['body_i']}  {d['head'][:56]}")
        print("   Not deleted: removing a section is destructive and the harness "
              "refuses it outside the door. Delete by hand, or leave and re-run.")
    print()

    for n, r in enumerate(ws_rows, 1):
        head, body = caption(r)
        img = os.path.join(img_dir, (r.get("Block Image File") or "").strip())
        have_img = os.path.isfile(img)
        print(f"--- {n}/{len(ws_rows)}  {head[:58]}")
        print(f"    {body}")

        blk = claimed.get(head)
        if blk:
            ph, st, place = blk["media_i"], "ALREADY_FILLED", f"existing @{blk['media_i']}"
            if blk["body"] != body:                       # sheet changed under us
                st = W.fill_index(ws, blk["body_i"], body)
                place += " (body refreshed)"
            if blk["has_image"]:
                print(f"    {place}  captions={st}  image=ALREADY_PRESENT")
                results.append({"n": n, "title": head, "captions": st,
                                "image": "ALREADY_PRESENT", "placement": place})
                continue
        else:
            empty = next((b for b in existing
                          if not b["has_image"] and not b["head"] and not b["body"]), None)
            if empty:                                     # the shipped empty block
                st = "+".join([W.fill_index(ws, empty["head_i"], head),
                               W.fill_index(ws, empty["body_i"], body)])
                ph, place = empty["media_i"], f"existing empty @{empty['media_i']}"
                existing.remove(empty)
            else:
                B.append_point(ws)
                st, fresh = W.build_section(ws, "layout_media_text", [head, body], insert_tile)
                ph = next((c["i"] for c in fresh if c["label"] == "Content placeholder"), None)
                place = f"appended @{fresh[0]['i'] if fresh else '?'}"
                st = st.split(":", 1)[1] if ":" in st else st

        ist = "NO_IMAGE_FILE"
        if have_img and ph is not None and ("FILLED" in st or st == "ALREADY_FILLED"):
            ist = upload_into(ws, ph, img)
        print(f"    {place}  captions={st}  image={ist}")
        results.append({"n": n, "title": head, "captions": st, "image": ist,
                        "placement": place})
        if ("FILLED" not in st and st != "ALREADY_FILLED") or (have_img and ist != "OK"):
            print("\nSTOPPING: this block did not land cleanly. The page is left "
                  "mid-build; re-running reconciles rather than duplicating.")
            break
        existing = page_blocks(ws)                        # indices shift as we go
        claimed = {b["head"]: b for b in existing if b["head"]}

    print(f"\ncells after   : {W.cell_count(ws)}")
    print(f"images on page: {S.eval_js(ws, 'document.querySelectorAll(\"img\").length')}")
    json.dump(results, open(os.path.join(img_dir, "_build_report.json"), "w"), indent=1)
    ok = sum(1 for r in results if "FILLED" in r["captions"]
             and r["image"] in ("OK", "NO_IMAGE_FILE"))
    print(f"blocks landed : {ok}/{len(ws_rows)}")
    return 0 if ok == len(ws_rows) else 4


def probe(site_id, page_id, cell_index=None):
    """Report what the reconciler sees, and what sits near a media cell.
    Diagnostics live in the file that owns the problem -- an inline probe that
    names a site module is refused by the hook, and rightly."""
    ws, _ = S.attach(f"https://sites.google.com/u/1/d/{site_id}/p/{page_id}/edit")
    for _ in range(60):
        time.sleep(1)
        if S.find_control(ws, "Publish", exact=True):
            break
    H.guard_2_viewport(ws)
    print("cells:")
    for c in read_cells(ws):
        print(f"  {c['i']:>3} | {c['label'][:22]:24} | {c['text'][:60]}")
    print("\nblocks the reconciler sees:")
    for b in page_blocks(ws):
        print(f"  media@{b['media_i']} img={b['has_image']}  head@{b['head_i']}={b['head'][:44]!r}")
    if cell_index is None:
        return 0
    i = int(cell_index)
    S.eval_js(ws, f"(function(){{var c=document.querySelectorAll('[role=\"gridcell\"]')[{i}];"
                  f"if(c) c.scrollIntoView({{block:'center'}});}})()")
    time.sleep(2)
    box = json.loads(S.eval_js(ws, f"""
      (function(){{var c=document.querySelectorAll('[role="gridcell"]')[{i}];
       var r=c.getBoundingClientRect();
       return JSON.stringify({{l:r.left,t:r.top,rt:r.right,b:r.bottom}});}})()"""))
    print(f"\ncell {i} rect: {box}")
    print("controls overlapping that rect:")
    for c in S.probe_controls(ws, 400):
        if box["l"] - 30 <= c["x"] <= box["rt"] + 30 and box["t"] - 30 <= c["y"] <= box["b"] + 30:
            print(f"  {c['role']:>10} ({c['x']:>5},{c['y']:>5})  {c['label'][:56]!r}")
    return 0


if __name__ == "__main__":
    if "--probe" in sys.argv:
        a = sys.argv.index("--probe")
        sys.exit(probe(sys.argv[2], sys.argv[3],
                       sys.argv[a + 1] if len(sys.argv) > a + 1 else None))
    if len(sys.argv) < 5:
        print(__doc__); sys.exit(1)
    lim = sys.argv[sys.argv.index("--limit") + 1] if "--limit" in sys.argv else None
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3],
                  os.path.expanduser(sys.argv[4]), lim))
