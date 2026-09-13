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


def main(folder_id, src_dir, u=1):
    src_dir = os.path.expanduser(src_dir)
    paths = sorted(os.path.join(src_dir, f) for f in os.listdir(src_dir)
                   if not f.startswith("_") and
                   os.path.splitext(f)[1].lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp"))
    if not paths:
        print(f"no images in {src_dir}"); return 1
    print(f"{len(paths)} file(s) to upload from {src_dir}")

    ws, _ = S.attach(f"https://drive.google.com/drive/u/{u}/folders/{folder_id}")
    time.sleep(9)
    before = {e["id"] for e in listing(ws)}
    print(f"folder already lists {len(before)} item(s)\n")

    res = D.upload_via_file_chooser(ws, lambda: open_new_menu(ws), paths, timeout=45)
    if res != "FILES_SET":
        print(f"UPLOAD FAILED: {res}")
        return 2
    print("files handed to Drive; waiting for the listing to settle")

    want = {os.path.basename(p) for p in paths}
    found, waited = {}, 0
    while waited < 180:
        time.sleep(6); waited += 6
        for e in listing(ws):
            for w in want:
                # Match on containment, not prefix: a row's text carries the
                # name plus type, owner and date in an order Drive chooses.
                stem = os.path.splitext(w)[0][:46]
                if w not in found and (stem in e["label"] or w[:46] in e["label"]):
                    found[w] = e["id"]
        print(f"   {len(found)}/{len(want)} visible after {waited}s")
        if len(found) == len(want):
            break

    missing = sorted(want - set(found))
    for w in sorted(found):
        print(f"  OK  {found[w]}  {w[:58]}")
    for m in missing:
        print(f"  MISSING (not in the listing)  {m[:58]}")
    out = os.path.join(src_dir, "_drive_ids.json")
    json.dump(found, open(out, "w"), indent=1)
    print(f"\n{len(found)}/{len(want)} uploaded and visible -> {out}")
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
