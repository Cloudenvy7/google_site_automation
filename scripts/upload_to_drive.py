"""Upload local files into a Drive folder through the browser, and report ids.

WHY THE BROWSER AND NOT THE API
The target folder is reachable by andrew@blackfoxstudios.org and returns 404 to
the service account -- link-sharing grants people, not service accounts. Rather
than ask for a third sharing action, use the session that already has access.
Drive builds no file input until you click New, and that opens a NATIVE OS
dialog no DOM scripting can reach; CDP's file-chooser interception is the way
in, which is what drive_upload.py exists for.

WHAT IT VERIFIES
Drive's own listing, read back after the upload: every requested filename must
appear with a file id. An upload that "succeeded" and put nothing in the folder
is the failure this checks for, and the ids are needed anyway to write the
sheet's Flyer Embed URL column.

usage:
  upload_to_drive.py <folder_id> <dir> [u_index]
"""

import json
import os
import sys
import time

import chrome_automation as C
import drive_upload as D
import sites_automation as S

# Read BOTH innerText and aria-label. Drive leaves aria-label empty on these
# rows -- the same trap that made the New menu look like a menu of [''].
LIST_JS = r"""
(function(){
  var o=[], seen={};
  document.querySelectorAll('[data-id]').forEach(function(e){
    var id=e.getAttribute('data-id')||'';
    if(id.length < 20 || seen[id]) return;
    var t=((e.innerText||'')+' '+(e.getAttribute('aria-label')||''))
            .replace(/\s+/g,' ').trim();
    if(!t) return;
    seen[id]=1; o.push({id:id, label:t.slice(0,160)});
  });
  return JSON.stringify(o);
})()"""


def listing(ws):
    try:
        return json.loads(S.eval_js(ws, LIST_JS) or "[]")
    except (TypeError, ValueError):
        return []


def by_text(ws, prefix, roles='[role="menuitem"],[role="button"]'):
    """Find a visible control whose INNERTEXT starts with `prefix`.

    Drive leaves aria-label empty on these, so sites_automation.probe_controls
    -- which reads aria-label -- reports a menu of ['']. The item is plainly
    there as text ("File upload Alt+C then U"). Match what the DOM actually
    carries rather than concluding the control does not exist.
    """
    raw = S.eval_js(ws, """
    (function(){
      var want=%s, hit=null;
      document.querySelectorAll('%s').forEach(function(e){
        if(hit) return;
        var r=e.getBoundingClientRect();
        if(r.width<2||r.height<2) return;
        var t=(e.innerText||'').replace(/\\s+/g,' ').trim();
        if(t.toLowerCase().indexOf(want.toLowerCase())===0)
          hit={x:Math.round(r.left+r.width/2), y:Math.round(r.top+r.height/2), t:t};
      });
      return hit?JSON.stringify(hit):null;
    })()""" % (json.dumps(prefix), roles))
    return json.loads(raw) if raw else None


def open_new_menu(ws):
    """Click New, then File upload."""
    n = by_text(ws, "New") or S.find_control(ws, "New", exact=True)
    if not n:
        print("   no 'New' button")
        return False
    S.click_at(ws, n["x"], n["y"])
    time.sleep(2.5)
    for label in ("File upload", "Upload files"):
        it = by_text(ws, label)
        if it:
            print(f"   click {it['t'][:34]!r} @({it['x']},{it['y']})")
            S.click_at(ws, it["x"], it["y"])
            return True
    print("   no 'File upload' item found by text")
    return False


def _row_for(ws, base):
    """The folder row matching this filename, or None.

    Returns the row rather than a bool so a SKIP still yields the file id. The
    first version returned a bool, and a rerun over an already-full folder wrote
    an empty _drive_ids.json -- destroying the ids the sheet's Flyer Embed URL
    column needs. A second run must never leave less than the first.
    """
    stem = os.path.splitext(base)[0][:46]
    for e in listing(ws):
        if base[:46] in e["label"] or stem in e["label"]:
            return e
    return None


def _present(ws, base):
    return _row_for(ws, base) is not None


def _reset_menu(ws):
    """Escape any menu left open.

    Two chooser cycles back to back otherwise find the New menu already open,
    and the click meant to open it closes it instead -- which surfaces as
    'no File upload item found by text', i.e. as a missing control rather than
    as the state problem it is.
    """
    for t in ("keyDown", "keyUp"):
        C.send_ws_cmd(ws, "Input.dispatchKeyEvent",
                      {"type": t, "key": "Escape", "windowsVirtualKeyCode": 27})
    time.sleep(1)


def main(folder_id, src_dir, u=1):
    """Upload one file per chooser cycle, verifying each before the next.

    WHY ONE AT A TIME (2026-09-13, after this sat recorded as broken since 09-08)
    The original handed all nine paths to a single DOM.setFileInputFiles call.
    Every observable step reported success: the menu item was found and clicked,
    Page.fileChooserOpened fired, setFileInputFiles returned no error, and the
    script printed "files handed to Drive". Drive ingested NOTHING. Nine files,
    zero landed, no error anywhere.

    Handing over a single path lands it every time. Same folder, same account,
    same session, same code path -- only the count differs.

    So the 09-08 note that "the chooser arms and Drive never ingests" was right
    about the symptom and wrong about the cause. It is not the handoff. It is the
    MULTI-FILE handoff, and the difference matters because the first reading
    implicates CDP interception, which works fine.

    The failure mode is the dangerous kind -- silent success -- which is why each
    file is confirmed present before the next is attempted, rather than uploading
    nine and counting at the end.
    """
    src_dir = os.path.expanduser(src_dir)
    paths = sorted(os.path.join(src_dir, f) for f in os.listdir(src_dir)
                   if not f.startswith("_") and
                   os.path.splitext(f)[1].lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp"))
    if not paths:
        print(f"no images in {src_dir}"); return 1
    print(f"{len(paths)} file(s) to upload from {src_dir}")

    ws, _ = S.attach(f"https://drive.google.com/drive/u/{u}/folders/{folder_id}")
    time.sleep(9)
    print(f"folder already lists {len(listing(ws))} item(s)\n")

    # ONE FILE PER CHOOSER CYCLE. See the docstring for why.
    found, missing = {}, []
    for path in paths:
        base = os.path.basename(path)
        row = _row_for(ws, base)
        if row:
            found[base] = row["id"]          # record the id even when skipping
            print(f"  SKIP  {row['id'][:24]}  {base[:48]}")
            continue

        _reset_menu(ws)
        res = D.upload_via_file_chooser(ws, lambda: open_new_menu(ws), [path], timeout=30)
        if res != "FILES_SET":
            print(f"  FAILED ({res})  {base[:42]}")
            missing.append(base)
            continue

        # Confirm THIS file before attempting the next. The failure being
        # guarded against reports success and delivers nothing, so a count at
        # the end cannot tell a working run from a silent one.
        landed = False
        for _ in range(12):                       # up to 60s per file
            time.sleep(5)
            if _present(ws, base):
                landed = True
                break
        if landed:
            row = _row_for(ws, base)
            if row:
                found[base] = row["id"]
            print(f"  OK    {found.get(base, '?')[:24]}  {base[:50]}")
        else:
            print(f"  LOST (handed over, never appeared)  {base[:40]}")
            missing.append(base)

    out = os.path.join(src_dir, "_drive_ids.json")
    json.dump(found, open(out, "w"), indent=1)
    print(f"\n{len(found)} landed, {len(missing)} failed -> {out}")
    return 0 if not missing else 4


def probe(folder_id, u=1):
    """What Drive's New menu actually exposes. probe_controls reads aria-label;
    Drive labels these by innerText, so an aria-only probe reports ['']."""
    ws, _ = S.attach(f"https://drive.google.com/drive/u/{u}/folders/{folder_id}")
    time.sleep(9)
    n = S.find_control(ws, "New", exact=True)
    print("New button:", n)
    if n:
        S.click_at(ws, n["x"], n["y"])
        time.sleep(3)
    raw = S.eval_js(ws, r"""
    (function(){
      var o=[];
      document.querySelectorAll('[role="menuitem"],[role="button"]').forEach(function(e){
        var r=e.getBoundingClientRect();
        if(r.width<2||r.height<2) return;
        var t=(e.innerText||'').replace(/\s+/g,' ').trim();
        var a=e.getAttribute('aria-label')||'';
        if(!t && !a) return;
        o.push({role:e.getAttribute('role'), text:t.slice(0,44), aria:a.slice(0,44),
                x:Math.round(r.left+r.width/2), y:Math.round(r.top+r.height/2)});
      });
      return JSON.stringify(o.slice(0,40));
    })()""")
    for it in json.loads(raw or "[]"):
        print(f"  {it['role']:>9} ({it['x']:>5},{it['y']:>5})  text={it['text']!r}  aria={it['aria']!r}")
    return 0


def show(folder_id, u=1):
    """What the folder actually contains, read from the live listing."""
    ws, _ = S.attach(f"https://drive.google.com/drive/u/{u}/folders/{folder_id}")
    time.sleep(12)
    rows = listing(ws)
    print(f"rows with a data-id: {len(rows)}")
    for e in rows[:20]:
        print(f"   {e['id'][:24]} | {e['label'][:80]}")
    txt = (S.eval_js(ws, '(document.body.innerText||"").replace(/\\s+/g," ")') or "")
    print()
    for p in ("White Center", "SBCAP", "SIBA", "Launchpad", "Harnessing"):
        print(f"   page text mentions {p!r}: {p in txt}")
    return 0


if __name__ == "__main__":
    if "--list" in sys.argv:
        sys.exit(show(sys.argv[1], int(sys.argv[3]) if len(sys.argv) > 3 else 1))
    if "--probe" in sys.argv:
        sys.exit(probe(sys.argv[1], int(sys.argv[3]) if len(sys.argv) > 3 else 1))
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    sys.exit(main(sys.argv[1], sys.argv[2],
                  int(sys.argv[3]) if len(sys.argv) > 3 else 1))
