"""Write cells into a Google Sheet through the browser, verifying each one.

Sheets is finicky about how text arrives: typing character-by-character into a
grid cell silently failed on some cells while the formula bar showed the right
text. Clipboard paste is what actually commits. Every write is read back from
the formula bar before moving on, because a write that looks fine and did
nothing is the failure mode that matters here.
"""

import json
import sys
import time

import chrome_automation as C
import sites_automation as S


def open_tab_on(sheet_id, tab_name):
    ws = S.open_tab(f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit")
    time.sleep(14)
    tabs = json.loads(S.eval_js(ws, r"""
    (function(){var o=[];document.querySelectorAll('.docs-sheet-tab').forEach(function(e){
     var r=e.getBoundingClientRect();o.push({name:(e.innerText||'').trim(),
     x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)});});
     return JSON.stringify(o);})()""") or "[]")
    for t in tabs:
        if t["name"].lower().startswith(tab_name.lower()):
            S.click_at(ws, t["x"], t["y"])
            time.sleep(3)
            return ws
    raise SystemExit(f"tab {tab_name!r} not found in {[t['name'] for t in tabs]}")


def _name_box(ws):
    return json.loads(S.eval_js(ws, """(function(){
     var e=document.querySelector('#t-name-box');var r=e.getBoundingClientRect();
     return JSON.stringify({x:Math.round(r.left+r.width/2),
                            y:Math.round(r.top+r.height/2)});})()"""))


def select(ws, cell):
    nb = _name_box(ws)
    S.click_at(ws, nb["x"], nb["y"])
    time.sleep(0.7)
    S.select_all(ws)
    S.type_chars(ws, cell)
    S.press_enter(ws)
    time.sleep(2.2)
    return S.eval_js(ws, "(document.querySelector('#t-name-box')||{}).value")


def read(ws):
    return (S.eval_js(ws, "(document.querySelector('#t-formula-bar-input')||{}).innerText")
            or "").strip()


def write_cells(ws, pairs, overwrite=True):
    ok = True
    for cell, val in pairs:
        if select(ws, cell) != cell:
            print(f"  ABORT {cell}: could not select")
            ok = False
            break
        if not overwrite and read(ws):
            print(f"  SKIP {cell}: already populated")
            continue
        C.type_text(ws, val)
        time.sleep(1.2)
        S.press_enter(ws)
        time.sleep(2.2)
        select(ws, cell)
        back = read(ws)
        good = back.strip() == val.strip()
        print(f"  {cell}: {'OK  ' if good else 'MISMATCH'} {back[:56]}")
        ok = ok and good
    return ok


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    ws = open_tab_on(cfg["sheet"], cfg["tab"])
    print("all verified:", write_cells(ws, [tuple(p) for p in cfg["cells"]]))
    ws.close()
