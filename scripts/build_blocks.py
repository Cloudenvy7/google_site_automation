"""Build uniform Image-and-caption blocks on a Google Sites page.

One block per workshop row: the same layout preset every time, so every entry
renders at the same size and shape regardless of whether its picture came from
a real flyer or a screenshot of the event page.

Each block is verified before moving on -- heading and body read back from the
target cell, image count checked for an increase. A block that fails stops the
run rather than leaving a half-built page that looks finished.
"""

import json
import sys
import time

import sites_automation as S
import drive_upload as D


def img_count(ws):
    return S.eval_js(ws, "document.querySelectorAll('img').length") or 0


def open_page(site, page_label="test."):
    ws = S.open_tab(f"https://sites.google.com/u/1/d/{site}/edit")
    for _ in range(50):
        time.sleep(1)
        if S.find_control(ws, "Publish", exact=True):
            break
    time.sleep(3)
    if S.find_control(ws, "Exit preview", exact=True):
        S.click_control(ws, "Exit preview", exact=True)
        time.sleep(2)
    S.click_control(ws, "Pages", exact=True)
    time.sleep(2.5)
    S.click_control(ws, page_label, exact=True)
    time.sleep(4)
    return ws


def select_last_section(ws):
    """Put the caret in the last section so Insert appends.

    Sites inserts a new layout relative to the current selection, not at the
    end of the page. Building three batches without doing this produced a page
    whose block order had nothing to do with the order they were added in.
    """
    S.eval_js(ws, "window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1.5)
    pt = S.eval_js(ws, """
    (function(){
      var s=document.querySelectorAll('[role="gridcell"]');
      if(!s.length) return null;
      var last=s[s.length-1]; last.scrollIntoView({block:'center'});
      var r=last.getBoundingClientRect();
      return JSON.stringify({x:Math.round(r.left+r.width/2),
                             y:Math.round(r.top+r.height/2)});
    })()""")
    if pt:
        import json as _j
        p = _j.loads(pt)
        S.click_at(ws, p["x"], p["y"])
        time.sleep(1.2)


def add_block(ws, heading, body, image_path=None):
    # 1. place the layout, appended after the current last section
    select_last_section(ws)
    S.click_control(ws, "Insert", exact=True)
    time.sleep(2)
    tile = S.wait_for_control(ws, "Add layout: Image and caption", exact=True)
    if not tile:
        return "LAYOUT_TILE_NOT_FOUND"
    S.click_at(ws, tile["x"], tile["y"])
    time.sleep(4)

    # 2. captions
    status = S.fill_layout(ws, heading, body)
    if status != "FILLED":
        return f"CAPTION_{status}"

    if not image_path:
        return "OK_NO_IMAGE"

    # 3. image, through the intercepted native file chooser
    before = img_count(ws)

    def do_click():
        # Scroll the placeholder into view first. Off-screen coordinates click
        # nothing and the Upload menu never opens -- the failure looks like a
        # missing menu item rather than a scroll problem.
        S.eval_js(ws, """
        (function(){var e=document.querySelector('[aria-label="Content placeholder"]');
         if(e) e.scrollIntoView({block:'center'});})()""")
        time.sleep(1.5)
        c = S.wait_for_control(ws, "Insert content", exact=True, attempts=10)
        if not c:
            print("    no Insert content placeholder")
            return
        S.click_at(ws, c["x"], c["y"])
        time.sleep(2.5)
        u = S.find_control(ws, "Upload", exact=True)
        if not u:
            print("    no Upload menu item")
            return
        S.click_at(ws, u["x"], u["y"])

    res = D.upload_via_file_chooser(ws, do_click, [image_path], timeout=25)
    if res != "FILES_SET":
        return f"UPLOAD_{res}"
    time.sleep(14)

    if img_count(ws) <= before:
        return "IMAGE_COUNT_DID_NOT_RISE"
    return "OK"


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    ws = open_page(cfg["site"], cfg.get("page", "test."))
    for b in cfg["blocks"]:
        print(f"\n--- {b['heading'][:55]}")
        st = add_block(ws, b["heading"], b["body"], b.get("image"))
        print(f"    => {st}")
        if not st.startswith("OK"):
            print("    STOPPING: block failed, page left mid-build")
            break
        page = S.eval_js(ws, "document.body.innerText") or ""
        print(f"    heading present in DOM: {b['heading'][:40] in page}")
    ws.close()
