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
"""

import sys, time, json
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


def insert_for(preset):
    if preset == "Text box":
        return lambda ws: B.insert_menu(ws, "Text box")[0]
    label = f"Add layout: {preset}"
    return lambda ws: B.insert_layout(ws, label)[0]


def build(ws, rows, label, expect_id):
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
    label, expect_id, path = sys.argv[1], sys.argv[2], sys.argv[3]
    rows = json.load(open(path))
    site = open("/tmp/hl_site.txt").read().strip()
    ws, _ = S.attach()
    try:
        H.guard_2_viewport(ws)
        C.send_ws_cmd(ws, "Page.navigate",
                      {"url": f"https://sites.google.com/u/1/d/{site}/edit"})
        for _ in range(60):
            time.sleep(1)
            if S.find_control(ws, "Publish", exact=True):
                break
        time.sleep(5)
        pid, results = build(ws, rows, label, None if expect_id == "-" else expect_id)
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
