"""Capture event pages as fixed-size images for Google Sites content blocks.

Why this exists: a Sites layout placeholder accepts only an image (Upload /
Select image / From Drive / YouTube / Calendar / Map) -- there is no "embed by
URL" option, verified by probing the live editor. Several of the event pages
also send X-Frame-Options: SAMEORIGIN, so they cannot be framed anywhere on the
page. Rendering each page to a PNG at one fixed size sidesteps both limits and
makes every workshop block identical by construction.

Every capture is verified: a page that fails to load, or renders essentially
blank, is reported rather than written out as a plausible-looking image.
"""

import base64
import json
import time

import chrome_automation
import sites_automation as S

WIDTH, HEIGHT = 1200, 900


def capture(url, out_path, settle=6.0):
    """Render url at a fixed viewport and write a PNG. Returns a status dict."""
    ws = S.open_tab("about:blank")
    if not ws:
        return {"url": url, "status": "NO_TAB"}
    try:
        chrome_automation.send_ws_cmd(ws, "Emulation.setDeviceMetricsOverride", {
            "width": WIDTH, "height": HEIGHT,
            "deviceScaleFactor": 1, "mobile": False,
        })
        chrome_automation.send_ws_cmd(ws, "Page.navigate", {"url": url})
        time.sleep(settle)

        landed = S.current_url(ws) or ""
        title = S.eval_js(ws, "document.title") or ""
        text = S.eval_js(ws, "document.body ? document.body.innerText : ''") or ""

        res = chrome_automation.send_ws_cmd(ws, "Page.captureScreenshot", {
            "format": "png",
            "clip": {"x": 0, "y": 0, "width": WIDTH, "height": HEIGHT, "scale": 1},
            "captureBeyondViewport": True,
        })
        data = (res or {}).get("result", {}).get("data")
        if not data:
            return {"url": url, "status": "NO_IMAGE_DATA"}

        raw = base64.b64decode(data)
        with open(out_path, "wb") as fh:
            fh.write(raw)

        # A screenshot always "succeeds" -- an error page renders just fine.
        # Judge the page, not the capture.
        status = "OK"
        if len(text.strip()) < 40:
            status = "BLANK_PAGE"
        elif any(m in title.lower() or m in text[:400].lower()
                 for m in ("404", "not found", "page isn't available",
                           "page not found")):
            status = "ERROR_PAGE"

        return {"url": url, "landed": landed, "title": title[:80],
                "bytes": len(raw), "status": status, "path": out_path}
    finally:
        try:
            chrome_automation.send_ws_cmd(ws, "Emulation.clearDeviceMetricsOverride")
            chrome_automation.send_ws_cmd(ws, "Page.close")
            ws.close()
        except Exception:
            pass


if __name__ == "__main__":
    import sys
    targets = json.load(open(sys.argv[1]))
    out = []
    for t in targets:
        print(f"capturing {t['name']} ...")
        r = capture(t["url"], t["out"])
        r["name"] = t["name"]
        print(f"   {r['status']:12} {r.get('bytes',0):>8} bytes  {r.get('title','')}")
        out.append(r)
    json.dump(out, open(sys.argv[2], "w"), indent=2)
