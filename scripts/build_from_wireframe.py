"""Build a Site page from the PAGE_WIREFRAME tab. One row = one block.

Two guards exist because their absence destroyed a finished page on 2026-08-30:

1. FORCE THE VIEWPORT. A screenshot had left Emulation.setDeviceMetricsOverride
   at 1400px. clearDeviceMetricsOverride returns ok and does nothing, so every
   later coordinate was computed against a layout the editor was not using --
   the Pages panel had collapsed and the page click silently missed.
   Set the metrics explicitly at the start of every run. Never assume.

2. ASSERT THE PAGE BEFORE DELETING. clear_page ran after a page click that
   returned true but had landed nowhere, so it cleared whatever was open --
   Home -- and rebuilt Team's content onto it. A destructive step must confirm
   its target, not trust the click that preceded it. The URL carries the page
   id; read it back and refuse if it is not the intended one.

usage:
  build_from_wireframe.py <page> <expected_page_id|-> <rows.json> <site> [--u N]

  <page> is the page's id or its editor URL (sites.google.com/u/<N>/d/<site>/p/<id>/edit),
  or, the old way, its exact label in the Pages panel. An id or URL opens the page
  directly and GUARD 1 checks the id; a label is clicked in the panel, which on
  2026-11-04 found only Home on a seven-page Site. Prefer the id.
  <site> is the Site's id or its editor URL (sites.google.com/u/<N>/d/<id>/edit).
  If omitted, ADVISOR_SITE_ID is used; with neither, it refuses rather than guess.
  --u N picks the signed-in Google account; otherwise the /u/<N>/ in a pasted
  URL, then ADVISOR_U_INDEX, then 0. Naming the Site in the command also lets
  the build hook check it against the preflight stamp.
"""

import re, sys, time, json
import config
import chrome_automation as C
import sites_automation as S
import wireframe_build as W
import build_page as B
import harness as H

# The guards are NOT reimplemented here. They live in harness.py so there is one
# definition of each and no second copy to drift. Re-deriving a guard locally is
# how the first one got lost.
force_viewport = H.guard_2_viewport
page_id = lambda ws: H.guard_1_assert_page(ws, None)


def select_page(ws, label, expect_id):
    """Open a page and prove it before anything destructive touches it.

    The click is not the proof. GUARD 1 reads the page id back from the live URL
    and refuses if it is not the intended target.
    """
    S.click_control(ws, "Pages", exact=True)
    time.sleep(2.5)
    if not S.click_control(ws, label, exact=True):
        raise H.Refusal(f"GUARD 1: page control {label!r} not found -- nothing cleared")
    time.sleep(6)
    return H.guard_1_assert_page(ws, expect_id)


# 2026-11-04 on the RCRC Finance Site: select_page found Home's label and no
# other, run after run, while site_survey.py saw all seven on the same editor.
# The label path also needs the exact aria-label, trailing period and all, which
# the survey prints without the period. The page id is already in hand (the
# person pastes the page's URL to confirm it), and it is the thing GUARD 1
# checks anyway, so open the page by id and drop the panel click.
PAGE_ID = re.compile(r"^1[A-Za-z0-9_-]{25,60}$")


def page_ref(value, site):
    """Return the page id if `value` is a page id or page editor URL, else None.

    A URL for another Site is refused, so a pasted address cannot point the
    build somewhere other than the Site the stamp was checked for.
    """
    v = value.strip()
    if "sites.google.com" in v:
        if "/p/" not in v:
            raise H.Refusal("GUARD 1: that page URL has no /p/<page id>/ in it. Open the page "
                            "in the editor and copy that address -- nothing cleared")
        url_site = v.split("/d/", 1)[1].split("/", 1)[0] if "/d/" in v else None
        if url_site and url_site != site:
            raise H.Refusal(f"GUARD 1: the page URL is on Site {url_site}, but the build is for "
                            f"{site} -- nothing cleared")
        return v.split("/p/", 1)[1].split("/", 1)[0].split("?", 1)[0]
    return v if PAGE_ID.match(v) else None


def open_page_by_id(ws, site, u, pid):
    """Open a page straight from its id, then prove it before anything is cleared."""
    C.send_ws_cmd(ws, "Page.navigate",
                  {"url": f"https://sites.google.com/u/{u}/d/{site}/p/{pid}/edit"})
    for _ in range(60):
        time.sleep(1)
        if S.find_control(ws, "Publish", exact=True):
            break
    time.sleep(5)
    H.guard_2_viewport(ws)
    if S.find_control(ws, "Exit preview", exact=True):
        S.click_control(ws, "Exit preview", exact=True); time.sleep(2)
    got = H.guard_1_assert_page(ws, None)
    if got != pid:
        raise H.Refusal(f"GUARD 1: asked for page {pid}, the editor opened {got}. "
                        "If that is Home, build Home by its label instead -- nothing cleared")
    return got


def insert_for(preset):
    if preset == "Text box":
        return lambda ws: B.insert_menu(ws, "Text box")[0]
    label = f"Add layout: {preset}"
    return lambda ws: B.insert_layout(ws, label)[0]


def build(ws, rows, label, expect_id, opened_id=None):
    if opened_id:
        pid = opened_id                       # open_page_by_id already asserted it
    else:
        H.guard_2_viewport(ws)
        if S.find_control(ws, "Exit preview", exact=True):
            S.click_control(ws, "Exit preview", exact=True); time.sleep(2)
        pid = select_page(ws, label, expect_id)
    print(f"  page confirmed: {label} -> {pid}")

    removed = B.clear_page(ws)
    print(f"  cleared {removed} sections")
    time.sleep(2)

    results = []
    for r in rows:
        order, preset, cells = r["order"], r["preset"], r["cells"]
        B.append_point(ws)
        status, fresh = W.build_section(ws, preset, cells, insert_for(preset))
        print(f"  [{order:>2}] {preset:<32} {status}")
        results.append({"order": order, "preset": preset, "status": status})
    return pid, results


def main():
    args = sys.argv[1:]
    u_arg = None
    if "--u" in args:
        i = args.index("--u")
        u_arg = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    if len(args) < 3:
        print(__doc__); raise SystemExit(1)
    label, expect_id, path = args[0], args[1], args[2]
    site_arg = args[3] if len(args) > 3 else None
    try:
        site = config.site_id(site_arg)
        # The account index can come from either pasted URL; the Site's wins.
        u_src = site_arg if (site_arg and "/u/" in site_arg) else (label if "/u/" in label else site_arg)
        u = config.u_index(u_arg, u_src or None)
    except config.ConfigError as e:
        print(f"\n  REFUSED -- {e}\n  Nothing was modified.")
        raise SystemExit(2)
    expect = None if expect_id == "-" else expect_id
    try:
        pid_in = page_ref(label, site)
    except H.Refusal as e:
        print(f"\n  REFUSED -- {e}\n  Nothing was modified.")
        raise SystemExit(2)
    if pid_in and expect and expect != pid_in:
        print(f"\n  REFUSED -- GUARD 1: page {pid_in} given, but expected id is {expect}.\n"
              "  Nothing was modified.")
        raise SystemExit(2)
    rows = json.load(open(path))
    print(f"  site {site}  (account /u/{u}/)")
    ws, _ = S.attach()
    try:
        H.guard_2_viewport(ws)
        if pid_in:
            print(f"  opening page {pid_in} by id")
            opened = open_page_by_id(ws, site, u, pid_in)
            pid, results = build(ws, rows, label, pid_in, opened_id=opened)
        else:
            C.send_ws_cmd(ws, "Page.navigate",
                          {"url": f"https://sites.google.com/u/{u}/d/{site}/edit"})
            for _ in range(60):
                time.sleep(1)
                if S.find_control(ws, "Publish", exact=True):
                    break
            time.sleep(5)
            pid, results = build(ws, rows, label, expect)
        ok = sum(1 for r in results if "FAILED" not in r["status"]
                 and "NOT_VERIFIED" not in r["status"] and "ONLY_" not in r["status"])
        print(f"\n  {ok}/{len(results)} blocks clean on page {pid}")
        json.dump({"page_id": pid, "results": results},
                  open(path.replace(".json", ".result.json"), "w"), indent=1)
    except H.Refusal as e:
        print(f"\n  REFUSED -- {e}")
        print("  Nothing was modified. A refusal is a finding, not an error to route around.")
        raise SystemExit(2)
    finally:
        ws.close()


if __name__ == "__main__":
    main()
