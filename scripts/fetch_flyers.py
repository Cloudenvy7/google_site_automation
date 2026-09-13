"""Fetch the workshop flyer images to local disk through the authenticated browser.

Writes files. Touches no Google Site -- this is the step BEFORE a build, not a
build. It needs no waiver for that reason.

WHY IT EXISTS
The nine flyers referenced by the Workshops tab's `Flyer Embed URL` are readable
by nobody except a signed-in account that has been granted them:
  - the service account gets HTTP 404 (never granted the folder)
  - an anonymous request gets HTTP 200 and a ~912KB text/html SIGN-IN PAGE
That second one is the whole lesson. Nothing errors. A naive downloader writes
912KB of HTML to `flyer.png`, the build uploads it, and the page shows a broken
image while every check says fine. So every fetch here is verified as a real
image by magic bytes, not by status code.

WHY IT FETCHES FROM A drive.google.com TAB
The thumbnail endpoint is on drive.google.com. A fetch issued from a
sites.google.com page is cross-origin and CORS-blocked. Same-origin from a Drive
tab, with the session cookies, is the path that works.

usage:
  fetch_flyers.py <spreadsheet_id> <outdir> [u_index]
"""

import http.cookiejar
import json
import os
import sys
import time
import urllib.request

import google.oauth2.service_account as sa
from googleapiclient.discovery import build

import chrome_automation as C
import sites_automation as S
import config

SA = config.service_account_path()

# A real image announces itself in its first bytes. Content-Type is not enough:
# the sign-in page is served as text/html with HTTP 200, and a truncated or
# error-page body can still carry a plausible header.
MAGIC = {b"\x89PNG\r\n\x1a\n": "png", b"\xff\xd8\xff": "jpeg",
         b"GIF87a": "gif", b"GIF89a": "gif", b"RIFF": "webp"}

# WHY NOT A PAGE-CONTEXT fetch(): tried first, and it fails on all nine with
# "TypeError: Failed to fetch" even from a same-origin drive.google.com tab.
# Drive serves a strict Content-Security-Policy and the thumbnail endpoint is
# not in its connect-src, so the page may not fetch it. A CSP refusal surfaces
# as a bare TypeError, which reads exactly like a network error -- another
# healthy-looking failure.
#
# So: take the session cookies out of the browser over CDP and do the HTTP
# request from Python, where no CSP applies. The bytes still come from an
# authenticated session; they just do not travel through a page that is
# forbidden to ask for them.


def sheet_rows(sheet_id):
    c = sa.Credentials.from_service_account_file(
        SA, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    sh = build("sheets", "v4", credentials=c).spreadsheets()
    v = sh.values().get(spreadsheetId=sheet_id, range="'Workshops'").execute()["values"]
    hdr = v[0]
    return [dict(zip(hdr, r + [""] * (len(hdr) - len(r)))) for r in v[1:] if any(r)]


def looks_like_image(raw):
    for sig, kind in MAGIC.items():
        if raw.startswith(sig):
            return kind
    return None


def browser_cookies(ws, host="drive.google.com", debug=False):
    """Cookies the browser would send to `host`, straight out of it over CDP.

    Domain matching has to be done properly. The first version kept every
    cookie whose domain merely contained "google.com" and collapsed duplicates
    by name with last-wins -- so an `accounts.google.com`-scoped value could
    overwrite the `.google.com` one that actually authenticates Drive, and the
    request came back 302 to ServiceLogin. A sign-in redirect is the same
    healthy-looking failure as the sign-in page: HTTP says 302, not 401.

    Rule: a cookie applies to `host` if its domain equals the host or the host
    ends with the dotted domain. Where a name appears more than once, the more
    specific domain wins.
    """
    C.send_ws_cmd(ws, "Network.enable")
    res = C.send_ws_cmd(ws, "Network.getAllCookies") or {}
    jar = (res.get("result") or {}).get("cookies") or []
    best = {}
    for c in jar:
        dom = (c.get("domain") or "").lstrip(".")
        if not (host == dom or host.endswith("." + dom)):
            continue
        prev = best.get(c["name"])
        if prev is None or len(dom) > len(prev[0]):
            best[c["name"]] = (dom, c["value"])
    if debug:
        for n, (d, _) in sorted(best.items()):
            print(f"    {n[:34]:36} <- {d}")
    return "; ".join(f"{n}={v}" for n, (_, v) in best.items())


def cookie_jar(ws):
    """Every browser cookie, as a real CookieJar.

    A single Cookie header is not enough, and the redirect chain is why:
        drive.google.com/thumbnail
          -> lh3.googleusercontent.com/d/<id>
          -> work.fife.usercontent.google.com/rd-d/...
          -> accounts.google.com/ServiceLogin        <- sign-in
    The image is served from a DIFFERENT domain than the one we asked. A fixed
    header carries drive.google.com's cookies to usercontent.google.com, which
    is not authenticated by them, so Google bounces the request to sign-in and
    returns HTTP 200 with a 912KB login page. A jar sends each domain its own
    cookies across every hop, which is what the browser itself does.
    """
    C.send_ws_cmd(ws, "Network.enable")
    res = C.send_ws_cmd(ws, "Network.getAllCookies") or {}
    jar = http.cookiejar.CookieJar()
    n = 0
    for c in (res.get("result") or {}).get("cookies") or []:
        dom = c.get("domain") or ""
        if "google" not in dom:
            continue
        jar.set_cookie(http.cookiejar.Cookie(
            version=0, name=c["name"], value=c["value"],
            port=None, port_specified=False,
            domain=dom, domain_specified=dom.startswith("."),
            domain_initial_dot=dom.startswith("."),
            path=c.get("path", "/"), path_specified=True,
            secure=bool(c.get("secure")),
            expires=int(c["expires"]) if c.get("expires", -1) and c.get("expires", -1) > 0 else None,
            discard=bool(c.get("session")), comment=None, comment_url=None, rest={}))
        n += 1
    return jar, n


def fetch_one(opener, url):
    """Return (bytes, note). bytes is None when it is not a real image."""
    req = urllib.request.Request(url, headers={
        "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"),
        "Accept": "image/avif,image/webp,image/png,image/*,*/*;q=0.8",
    })
    try:
        with opener.open(req, timeout=60) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
    except Exception as e:
        return None, f"http error: {type(e).__name__}: {str(e)[:70]}"
    kind = looks_like_image(raw)
    if not kind:
        head = raw[:300].decode("utf8", "replace").replace("\n", " ")
        hint = ("SIGN-IN PAGE" if ("accounts.google" in head or "signin" in head)
                else "not an image")
        return None, f"{hint} -- {len(raw)/1024:.0f}KB, ctype={ctype[:24]}"
    return raw, f"{kind}, {len(raw)/1024:.0f}KB"


def main(sheet_id, outdir, u=1):
    os.makedirs(outdir, exist_ok=True)
    rows = sheet_rows(sheet_id)
    # Same-origin tab so the cookies apply and CORS does not block the fetch.
    ws, _ = S.attach(f"https://drive.google.com/drive/u/{u}/my-drive")
    if not ws:
        print("no tab; is Chrome running with --remote-debugging-port=9222?")
        return 1
    time.sleep(6)
    jar, n = cookie_jar(ws)
    if not n:
        print("no google cookies in the browser -- is it signed in?")
        return 2
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    print(f"session     : {n} cookies from the live browser, sent per-domain\n")

    report, ok, bad = [], 0, 0
    for r in rows:
        title = r.get("Workshop Title", "")
        url = (r.get("Flyer Embed URL") or "").strip()
        name = (r.get("Block Image File") or "").strip()
        if not url or not name:
            print(f"  NO SOURCE      {title[:52]}")
            report.append({"title": title, "status": "NO_SOURCE"}); bad += 1
            continue
        # Ask for a larger render than the sheet's w1000; same asset, more pixels.
        big = url.replace("sz=w1000", "sz=w1600")
        raw, note = fetch_one(opener, big + f"&authuser={u}")
        if raw is None:
            raw, note = fetch_one(opener, big)                  # default account retry
        if raw is None:
            print(f"  FAILED         {title[:46]}  {note}")
            report.append({"title": title, "status": "FAILED", "note": note}); bad += 1
            continue
        path = os.path.join(outdir, name)
        with open(path, "wb") as fh:
            fh.write(raw)
        print(f"  OK  {note:22} {name[:58]}")
        report.append({"title": title, "status": "OK", "path": path,
                       "bytes": len(raw), "note": note}); ok += 1

    json.dump(report, open(os.path.join(outdir, "_fetch_report.json"), "w"), indent=1)
    print(f"\nfetched {ok}/{ok + bad} as verified images -> {outdir}")
    if bad:
        print("Rows that failed need a fallback (screenshot the registration URL, "
              "as in August) or a sharing fix. They are NOT silently skipped.")
    return 0 if bad == 0 else 4


def diag(sheet_id, u=1):
    """Trace one row end to end: which cookies apply, and where the URL lands.
    Diagnostics live in this file because the Site-build hook refuses an inline
    probe that names a site module -- edit files, run files."""
    ws, _ = S.attach(f"https://drive.google.com/drive/u/{u}/my-drive")
    time.sleep(5)
    print("cookies applicable to drive.google.com:")
    ck = browser_cookies(ws, debug=True)
    row = sheet_rows(sheet_id)[0]
    url = row["Flyer Embed URL"].replace("sz=w1000", "sz=w1600")
    print(f"\nurl: {url[:100]}")

    class Trace(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            print(f"  {code} -> {newurl[:120]}")
            return urllib.request.HTTPRedirectHandler.redirect_request(
                self, req, fp, code, msg, headers, newurl)

    op = urllib.request.build_opener(Trace)
    for label, uu in (("authuser", url + f"&authuser={u}"), ("plain", url)):
        print(f"\n[{label}]")
        try:
            r = urllib.request.Request(uu, headers={"Cookie": ck, "User-Agent": "Mozilla/5.0"})
            with op.open(r, timeout=45) as resp:
                b = resp.read()
                print(f"  {resp.status} {resp.headers.get('Content-Type')} "
                      f"{len(b)/1024:.0f}KB magic={b[:8]!r} -> {looks_like_image(b)}")
        except Exception as e:
            print(f"  {type(e).__name__}: {str(e)[:110]}")
    return 0


if __name__ == "__main__":
    if "--diag" in sys.argv:
        sys.exit(diag(sys.argv[1], int(sys.argv[3]) if len(sys.argv) > 3 else 1))
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(sys.argv[1], sys.argv[2],
                  int(sys.argv[3]) if len(sys.argv) > 3 else 1))
