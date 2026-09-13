"""Survey a Google Site's editor READ-ONLY. Never mutates the site.

WHY THIS EXISTS (2026-09-08)
Stage 1 of any build is "look before you touch": which account is the editor
actually loaded as, what pages exist, and what is already on the target page.
Nothing offered a way to do that. `catalog_site.py` and
`extract_site_template.py` are libraries with no entry point, so the only route
was an inline script -- which the Site-build hook refuses, correctly, because it
cannot tell a probe from a write.

So this is the sanctioned probe, and it is on the hook's READ_ONLY_TOOLS
allowlist. That allowlist trusts this FILE, so the file has to earn it:

  - It never inserts, types, uploads, clears, publishes or renames.
  - The only interaction is opening the Pages panel, which changes editor UI
    state and nothing about the site.
  - It writes a JSON report to disk if asked, never to the Site.

If a future edit adds a mutating call here, it defeats the allowlist entry
silently. That is the risk of any allowlist, and it is why this file is small
enough to read in one sitting and lives in git where a change shows up in review.

usage:
  site_survey.py <site_id> [u_index] [--page <page_id>] [--json out.json]
"""

import json
import sys
import time

import sites_automation as S
import harness as H

MUTATORS = ("insert_layout", "insert_menu", "type_chars", "fill_", "clear_page",
            "publish", "create_page", "create_site", "rename_site", "setFileInputFiles")

CELLS_JS = r"""
(function(){
  var cs=document.querySelectorAll('[role="gridcell"]'); var o=[];
  for(var i=0;i<cs.length;i++){
    var c=cs[i]; var e=c.querySelector('[contenteditable]');
    var r=c.getBoundingClientRect();
    var t=((e?e.innerText:c.innerText)||'').replace(/\s+/g,' ').trim();
    if(t==='Click to edit text') t='';
    if(/^Normal text\n/.test(t)) t='';
    o.push({i:i, label:c.getAttribute('aria-label')||'',
            x:Math.round(r.left), y:Math.round(r.top), text:t.slice(0,110)});
  }
  return JSON.stringify(o);
})()"""


def page_list(ws):
    """Page labels from the Pages panel. Opening the panel is UI state only."""
    S.click_control(ws, "Pages", exact=True)
    time.sleep(3)
    out = []
    for c in S.probe_controls(ws, 400):
        if c["role"] == "div" and c["label"].endswith(".") \
                and not c["label"].startswith("Group starting"):
            out.append(c["label"].rstrip("."))
    return out


def cells(ws):
    try:
        return json.loads(S.eval_js(ws, CELLS_JS) or "[]")
    except (TypeError, ValueError):
        return []


def survey(site_id, u=1, page_id=None):
    url = f"https://sites.google.com/u/{u}/d/{site_id}/edit"
    if page_id:
        url = f"https://sites.google.com/u/{u}/d/{site_id}/p/{page_id}/edit"
    ws, _ = S.attach(url)
    if not ws:
        return {"status": "NO_TAB"}

    ready = False
    for _ in range(60):
        time.sleep(1)
        if S.find_control(ws, "Publish", exact=True):
            ready = True
            break
    if not ready:
        # Distinguish "no access" from "slow": a permission wall has no editor.
        body = (S.eval_js(ws, "(document.body.innerText||'').slice(0,300)") or "")
        return {"status": "EDITOR_NOT_REACHABLE", "url": S.current_url(ws),
                "body_head": body.replace("\n", " ")[:240]}

    rep = {"status": "OK", "viewport": H.guard_2_viewport(ws),
           "url": S.current_url(ws),
           "open_page_id": H.guard_1_assert_page(ws, None)}

    acct = [c["label"] for c in S.probe_controls(ws, 400)
            if "Google Account" in c.get("label", "")]
    rep["account_chip"] = acct[0].replace("\n", " ")[:120] if acct else "(not found)"
    rep["can_edit_controls"] = sorted(
        {n for n in ("Insert", "Pages", "Themes", "Publish")
         if S.find_control(ws, n, exact=True)})
    rep["cells"] = cells(ws)
    rep["pages"] = page_list(ws)
    return rep


if __name__ == "__main__":
    src = open(__file__).read()
    for m in MUTATORS:                    # self-check: the allowlist entry's premise
        if f"S.{m}" in src or f"B.{m}" in src:
            print(f"REFUSING: this file calls {m}; it is on the read-only allowlist.")
            sys.exit(2)
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    site = sys.argv[1]
    u = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 1
    pid = sys.argv[sys.argv.index("--page") + 1] if "--page" in sys.argv else None
    rep = survey(site, u, pid)

    print(f"status      : {rep['status']}")
    if rep["status"] != "OK":
        print(f"url         : {rep.get('url')}")
        print(f"page says   : {rep.get('body_head','')}")
        sys.exit(3)
    print(f"account     : {rep['account_chip']}")
    print(f"url         : {rep['url']}")
    print(f"open page   : {rep['open_page_id']}")
    print(f"viewport    : {rep['viewport']}")
    print(f"edit toolbar: {rep['can_edit_controls']}")
    print(f"pages ({len(rep['pages'])})   : {rep['pages']}")
    print(f"\ncells on the open page: {len(rep['cells'])}")
    for c in rep["cells"]:
        print(f"  {c['i']:>3} | {c['label'][:20]:20} x={c['x']:>5} y={c['y']:>6} | {c['text']}")
    if "--json" in sys.argv:
        p = sys.argv[sys.argv.index("--json") + 1]
        json.dump(rep, open(p, "w"), indent=1)
        print(f"\nreport -> {p}")
