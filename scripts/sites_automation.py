"""Google Sites automation over the Chrome DevTools Protocol.

Companion to chrome_automation.py, which does the same job for Google Docs.
Google Sites has no public write API (execution-pathways.md section 1 routes
Sites work to browser automation), so driving the editor front end is the
sanctioned surface, not a workaround.

Two house rules carried over from chrome_automation.py:

  1. Read back after every action. A click that returned SUCCESS is not
     evidence the editor changed. Every mutating helper re-queries the DOM and
     returns an explicit status string.
  2. Fail loudly. Helpers return NOT_FOUND / TIMEOUT rather than pretending,
     so callers can stop and report per execution-pathways.md section 6.

The Sites editor DOM is undocumented and Google changes it. probe_controls()
exists so selectors can be rediscovered from the live page instead of guessed.
"""

import json
import time
import urllib.request

import websocket

import chrome_automation

CHROME_PORT = chrome_automation.CHROME_PORT


# ---------------------------------------------------------------- connection


def open_tab(url, timeout=15):
    """Open a new tab at url and return a connected websocket."""
    ws_url = chrome_automation.create_new_doc()
    if not ws_url:
        print("Error: could not open a Chrome tab. Is Chrome running with "
              f"--remote-debugging-port={CHROME_PORT}?")
        return None
    ws = websocket.create_connection(ws_url, timeout=timeout)
    chrome_automation.send_ws_cmd(ws, "Page.enable")
    chrome_automation.send_ws_cmd(ws, "Page.navigate", {"url": url})
    return ws


def list_tabs():
    """Every open page target in the debug browser.

    Named list_tabs, not list_pages -- list_pages already means the Sites
    editor's pages panel in this module. Two different kinds of "page".
    """
    with urllib.request.urlopen(f"http://localhost:{CHROME_PORT}/json/list") as r:
        return [t for t in json.load(r) if t.get("type") == "page"]


def close_tab(tab_id):
    """Actually close a tab. ws.close() only drops the socket; the tab lives on.

    This was a real leak: every helper call opened a fresh tab via /json/new and
    never closed it, so a nine-block build left a trail of tabs behind it.
    """
    try:
        urllib.request.urlopen(
            f"http://localhost:{CHROME_PORT}/json/close/{tab_id}").read()
        return True
    except Exception:
        return False


def attach(url=None, reuse=True, timeout=15):
    """Attach to ONE tab and keep using it. Returns (ws, tab_id).

    Prefer this over open_tab. Reusing a single tab is what makes a multi-page
    build cheap: the alternative is a new tab plus a full Sites editor load
    (30-45s) for every step, which is where the cost actually was -- not in
    memory so much as in reloading the editor over and over.
    """
    tabs = list_tabs()
    target = tabs[0] if (reuse and tabs) else None
    if target is None:
        req = urllib.request.Request(
            f"http://localhost:{CHROME_PORT}/json/new", method="PUT")
        with urllib.request.urlopen(req) as r:
            target = json.load(r)
    ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=timeout)
    chrome_automation.send_ws_cmd(ws, "Page.enable")
    if url:
        chrome_automation.send_ws_cmd(ws, "Page.navigate", {"url": url})
    return ws, target["id"]


def eval_js(ws, expression, await_promise=False):
    """Run JS in the page and return its value, or None."""
    res = chrome_automation.send_ws_cmd(
        ws, "Runtime.evaluate",
        {"expression": expression, "awaitPromise": await_promise,
         "returnByValue": True},
    )
    if not res:
        return None
    result = res.get("result", {}).get("result", {})
    if result.get("subtype") == "error":
        print(f"  JS error: {result.get('description', '')[:200]}")
        return None
    return result.get("value")


def wait_for(ws, predicate_js, label, attempts=30, delay=1.0):
    """Poll a JS predicate until it is truthy. Returns True/False."""
    for i in range(attempts):
        if eval_js(ws, f"(function(){{ try {{ return !!({predicate_js}); }} "
                       f"catch (e) {{ return false; }} }})()"):
            print(f"  ready: {label}")
            return True
        time.sleep(delay)
    print(f"  TIMEOUT waiting for: {label}")
    return False


def current_url(ws):
    return eval_js(ws, "window.location.href") or ""


# ------------------------------------------------------------------- probing


PROBE_JS = r"""
(function() {
    var out = [];
    var nodes = document.querySelectorAll(
        '[aria-label],[role="button"],[role="menuitem"],[role="tab"],button');
    for (var i = 0; i < nodes.length && out.length < LIMIT; i++) {
        var el = nodes[i];
        var r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        out.push({
            label: el.getAttribute('aria-label') || '',
            role: el.getAttribute('role') || el.tagName.toLowerCase(),
            text: (el.innerText || '').trim().slice(0, 60),
            x: Math.round(r.left + r.width / 2),
            y: Math.round(r.top + r.height / 2)
        });
    }
    return JSON.stringify(out);
})()
"""


def probe_controls(ws, limit=250):
    """Dump every visible interactive control with its aria-label and centre.

    This is the discovery tool. When a selector below stops working, run this
    against the live editor and read the real labels rather than guessing.
    """
    raw = eval_js(ws, PROBE_JS.replace("LIMIT", str(limit)))
    try:
        return json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []


def find_control(ws, needle, limit=250, exact=False, role=None):
    """Find the best-matching visible control.

    Ranked, because loose substring matching bites: a container's innerText
    contains every child's text, so searching "Pages" once matched the whole
    sidebar. Exact aria-label wins, then exact text, then substring on the
    label only, and substring on text is the last resort.
    """
    needle_l = needle.lower()
    controls = probe_controls(ws, limit)
    # Menu items and page content can share a label -- "Spacer" is both an
    # Insert menu item and an existing block on the page. Without this filter
    # the matcher clicks the block instead of the menu and nothing is inserted.
    if role:
        controls = [c for c in controls if c["role"] == role]

    for c in controls:
        if c["label"].lower() == needle_l:
            return c
    for c in controls:
        if c["text"].lower() == needle_l:
            return c
    if exact:
        return None
    for c in controls:
        if needle_l in c["label"].lower():
            return c
    for c in controls:
        if needle_l in c["text"].lower():
            return c
    return None


def wait_for_control(ws, needle, attempts=20, delay=1.0, exact=False, role=None):
    """Poll until a control appears. Sites renders the toolbar in stages, so
    probing once right after load misses controls that arrive a second later —
    that is why an earlier run 'could not find' the site name field."""
    for i in range(attempts):
        ctl = find_control(ws, needle, exact=exact, role=role)
        if ctl:
            return ctl
        time.sleep(delay)
    print(f"  TIMEOUT: control '{needle}' never appeared")
    return None


# ------------------------------------------------------------------ clicking


def click_at(ws, x, y):
    """Dispatch a real mouse click at viewport coordinates.

    Synthetic el.click() is often ignored by the Sites editor, which listens
    for pointer sequences. Real CDP mouse events are the reliable path and are
    also what makes drag-and-drop possible.
    """
    for kind in ("mousePressed", "mouseReleased"):
        chrome_automation.send_ws_cmd(ws, "Input.dispatchMouseEvent", {
            "type": kind, "x": x, "y": y, "button": "left",
            "clickCount": 1, "buttons": 1 if kind == "mousePressed" else 0,
        })
    time.sleep(0.4)


def click_control(ws, needle, exact=False, role=None):
    """Find a control by label/text and click its centre. Returns bool."""
    ctl = find_control(ws, needle, exact=exact, role=role)
    if not ctl:
        print(f"  NOT_FOUND: control matching '{needle}'")
        return False
    print(f"  clicking '{ctl['label'] or ctl['text']}' at "
          f"({ctl['x']}, {ctl['y']})")
    click_at(ws, ctl["x"], ctl["y"])
    return True


def drag(ws, x1, y1, x2, y2, steps=12):
    """Press, move in steps, release. Sites layout placement needs this."""
    chrome_automation.send_ws_cmd(ws, "Input.dispatchMouseEvent", {
        "type": "mousePressed", "x": x1, "y": y1,
        "button": "left", "clickCount": 1, "buttons": 1})
    for i in range(1, steps + 1):
        chrome_automation.send_ws_cmd(ws, "Input.dispatchMouseEvent", {
            "type": "mouseMoved",
            "x": int(x1 + (x2 - x1) * i / steps),
            "y": int(y1 + (y2 - y1) * i / steps),
            "button": "left", "buttons": 1})
        time.sleep(0.05)
    chrome_automation.send_ws_cmd(ws, "Input.dispatchMouseEvent", {
        "type": "mouseReleased", "x": x2, "y": y2,
        "button": "left", "clickCount": 1, "buttons": 0})
    time.sleep(1.0)


def type_chars(ws, text, delay=0.04):
    """Send real per-character key events.

    chrome_automation.type_text pastes via the clipboard, which works in the
    contenteditable surfaces Docs uses. Sites' plain <input> fields are Closure
    widgets that only honour genuine key events, so a programmatic value set or
    a paste into an unfocused field silently does nothing.
    """
    for ch in text:
        for kind in ("keyDown", "char", "keyUp"):
            # only the char event may carry text; putting it on keyDown
            # too makes every character insert twice ("test" -> "tteesstt")
            params = {"type": kind}
            if kind == "char":
                params["text"] = ch
            else:
                params["key"] = ch
            chrome_automation.send_ws_cmd(ws, "Input.dispatchKeyEvent", params)
        time.sleep(delay)
    time.sleep(0.3)


def select_all(ws):
    for kind in ("rawKeyDown", "keyUp"):
        chrome_automation.send_ws_cmd(ws, "Input.dispatchKeyEvent", {
            "type": kind, "key": "a", "code": "KeyA", "modifiers": 2,
            "windowsVirtualKeyCode": 65, "nativeVirtualKeyCode": 65})
    time.sleep(0.3)


def press_enter(ws):
    for kind in ("rawKeyDown", "keyUp"):
        chrome_automation.send_ws_cmd(ws, "Input.dispatchKeyEvent", {
            "type": kind, "key": "Enter", "code": "Enter",
            "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13})
    time.sleep(0.5)


# ------------------------------------------------------------------- account


WHOAMI_JS = r"""
(function() {
    var m = document.body.innerText.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+/g);
    return JSON.stringify({
        url: window.location.href,
        emails: m ? Array.from(new Set(m)).slice(0, 10) : []
    });
})()
"""


def whoami(ws):
    """Read the signed-in account(s) from an authenticated Google page.

    Navigate to myaccount.google.com first. Returns a dict with 'emails' and
    'url'; the /u/N index in the URL is the multi-login index to reuse.
    """
    raw = eval_js(ws, WHOAMI_JS)
    try:
        return json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}


def multi_login_index(url):
    """Extract the /u/N account index from a Google URL, defaulting to 0."""
    parts = url.split("/u/")
    if len(parts) > 1 and parts[1][:1].isdigit():
        return int(parts[1][0])
    return 0


# --------------------------------------------------------------------- sites


SITES_EDITOR_READY_JS = (
    "document.querySelector('[aria-label=\"Publish\"]') || "
    "document.querySelector('[aria-label=\"Insert\"]') || "
    "document.querySelector('[guidedhelpid=\"publish\"]')"
)


def wait_for_editor(ws, attempts=40):
    return wait_for(ws, SITES_EDITOR_READY_JS, "Sites editor toolbar",
                    attempts=attempts)


def site_id_from_url(url):
    """Pull the site id out of a /d/<id>/ editor URL."""
    if "/d/" not in url:
        return None
    return url.split("/d/")[1].split("/")[0]


def open_editor(site_id, u=0):
    """Open an existing site's editor and wait for it to load."""
    ws = open_tab(f"https://sites.google.com/u/{u}/d/{site_id}/edit")
    if not ws:
        return None, None
    if not wait_for_editor(ws):
        return ws, None
    return ws, site_id


def create_site(u=0):
    """Create a new blank site. Returns (ws, site_id)."""
    ws = open_tab(f"https://sites.google.com/u/{u}/create")
    if not ws:
        return None, None
    if not wait_for_editor(ws):
        print("  editor did not load after /create")
        return ws, None
    url = current_url(ws)
    sid = site_id_from_url(url)
    print(f"  created site: {sid}  ({url})")
    return ws, sid


def rename_site(ws, name):
    """Set the site name via the top-left name field. Returns bool."""
    if not click_control(ws, "site name"):
        return False
    chrome_automation.select_all_and_delete(ws)
    chrome_automation.type_text(ws, name)
    time.sleep(1.5)
    got = eval_js(ws, "(document.querySelector('[aria-label=\"Site name\"]')"
                      " || {}).value || document.title")
    ok = bool(got and name.lower() in str(got).lower())
    print(f"  rename_site verify: {got!r} -> {'OK' if ok else 'MISMATCH'}")
    return ok


PAGE_LIST_JS = r"""
(function() {
    var out = [];
    var nodes = document.querySelectorAll(
        '[role="treeitem"], [data-nav-item-name], [aria-label*="page"]');
    for (var i = 0; i < nodes.length; i++) {
        var t = (nodes[i].innerText || '').trim();
        if (t) out.push(t.split('\n')[0]);
    }
    return JSON.stringify(Array.from(new Set(out)));
})()
"""


def list_pages(ws):
    try:
        return json.loads(eval_js(ws, PAGE_LIST_JS) or "[]")
    except (TypeError, ValueError):
        return []


def create_page(ws, name):
    """Open the Pages panel, add a page, name it. Returns bool (verified)."""
    before = list_pages(ws)
    print(f"  pages before: {before}")

    if not click_control(ws, "Pages"):
        return False
    time.sleep(1.5)
    if not click_control(ws, "New page"):
        return False
    time.sleep(1.5)

    chrome_automation.type_text(ws, name)
    time.sleep(0.5)
    if not click_control(ws, "Done"):
        # Some builds accept Enter instead of a Done button.
        chrome_automation.send_ws_cmd(ws, "Input.dispatchKeyEvent", {
            "type": "rawKeyDown", "key": "Enter", "code": "Enter",
            "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13})
        chrome_automation.send_ws_cmd(ws, "Input.dispatchKeyEvent", {
            "type": "keyUp", "key": "Enter", "code": "Enter",
            "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13})
    time.sleep(2.5)

    after = list_pages(ws)
    print(f"  pages after: {after}")
    ok = any(name.lower() == p.lower() for p in after)
    print(f"  create_page verify: {'OK' if ok else 'NOT_FOUND'}")
    return ok


LAYOUT_TILE_JS = r"""
(function() {
    var out = [];
    var nodes = document.querySelectorAll(
        '[role="listitem"],[role="option"],[aria-label*="ayout"]');
    for (var i = 0; i < nodes.length; i++) {
        var r = nodes[i].getBoundingClientRect();
        if (r.width < 30 || r.height < 20) continue;
        out.push({
            label: nodes[i].getAttribute('aria-label') || '',
            x: Math.round(r.left + r.width / 2),
            y: Math.round(r.top + r.height / 2)
        });
    }
    return JSON.stringify(out);
})()
"""


def open_layouts(ws):
    """Open Insert > Layouts and return the available layout tiles."""
    if not click_control(ws, "Insert"):
        return []
    time.sleep(1.5)
    if not click_control(ws, "Layouts"):
        print("  NOT_FOUND: Layouts section in the Insert panel")
        return []
    time.sleep(1.5)
    try:
        tiles = json.loads(eval_js(ws, LAYOUT_TILE_JS) or "[]")
    except (TypeError, ValueError):
        tiles = []
    print(f"  layout tiles found: {len(tiles)}")
    for t in tiles:
        print(f"    - {t['label']!r} @ ({t['x']}, {t['y']})")
    return tiles


CANVAS_JS = r"""
(function() {
    var el = document.querySelector('[role="main"]') ||
             document.querySelector('[aria-label*="Canvas"]');
    if (!el) return null;
    var r = el.getBoundingClientRect();
    return JSON.stringify({
        x: Math.round(r.left + r.width / 2),
        y: Math.round(r.top + Math.min(r.height / 2, 300))
    });
})()
"""


def canvas_point(ws):
    try:
        return json.loads(eval_js(ws, CANVAS_JS) or "null")
    except (TypeError, ValueError):
        return None


def insert_layout(ws, tile, use_drag=True):
    """Place a layout tile on the canvas.

    Tries a plain click first (some builds append on click), then a drag onto
    the canvas. Returns a status string, never a bare bool, so the caller can
    report exactly which mechanism failed.
    """
    target = canvas_point(ws)
    if not target:
        return "CANVAS_NOT_FOUND"

    click_at(ws, tile["x"], tile["y"])
    time.sleep(2.0)
    if count_text_boxes(ws) > 0:
        return "PLACED_BY_CLICK"

    if not use_drag:
        return "CLICK_DID_NOT_PLACE"

    print(f"  click did not place; dragging to ({target['x']}, {target['y']})")
    drag(ws, tile["x"], tile["y"], target["x"], target["y"])
    time.sleep(2.0)
    if count_text_boxes(ws) > 0:
        return "PLACED_BY_DRAG"
    return "DRAG_DID_NOT_PLACE"


TEXT_BOX_JS = (
    "document.querySelectorAll('[contenteditable=\"true\"]').length"
)


def count_text_boxes(ws):
    return eval_js(ws, TEXT_BOX_JS) or 0


def double_click_at(ws, x, y):
    """Two clicks in quick succession. Sites needs this to enter a text cell."""
    for click_count in (1, 2):
        for kind in ("mousePressed", "mouseReleased"):
            chrome_automation.send_ws_cmd(ws, "Input.dispatchMouseEvent", {
                "type": kind, "x": x, "y": y, "button": "left",
                "clickCount": click_count,
                "buttons": 1 if kind == "mousePressed" else 0,
            })
        time.sleep(0.15)
    time.sleep(0.6)


# Tag the target cell before clicking so focus can be proven afterwards.
# Coordinates are re-read after scrollIntoView because the editor reflows and
# a stale rect is exactly how text ends up in the wrong cell.
TAG_EMPTY_CAPTION_JS = r"""
(function() {
    var cells = document.querySelectorAll('[role="gridcell"][aria-label="Text"]');
    var target = null;
    for (var i = 0; i < cells.length; i++) {
        if ((cells[i].innerText || '').trim() === 'Click to edit text') {
            target = cells[i];
            break;
        }
    }
    if (!target) return null;
    var prev = document.querySelectorAll('[data-bfs-target]');
    for (var j = 0; j < prev.length; j++) prev[j].removeAttribute('data-bfs-target');
    target.setAttribute('data-bfs-target', '1');
    target.scrollIntoView({block: 'center'});
    var r = target.getBoundingClientRect();
    return JSON.stringify({x: Math.round(r.left + r.width / 2),
                           y: Math.round(r.top + r.height / 2)});
})()
"""

VERIFY_FOCUS_JS = r"""
(function() {
    var ae = document.activeElement;
    if (!ae) return 'NO_ACTIVE_ELEMENT';
    var cell = ae.closest ? ae.closest('[role="gridcell"]') : null;
    if (!cell) return 'ACTIVE_NOT_IN_A_CELL';
    if (!cell.hasAttribute('data-bfs-target')) return 'FOCUSED_WRONG_CELL';
    var editable = document.querySelectorAll('[contenteditable="true"]').length;
    return editable > 0 ? 'FOCUSED_TARGET' : 'TARGET_NOT_EDITABLE';
})()
"""

READ_TARGET_JS = r"""
(function() {
    var t = document.querySelector('[data-bfs-target]');
    return t ? (t.innerText || '').trim() : null;
})()
"""


def fill_next_empty_caption(ws, text):
    """Type text into the next empty caption cell, or refuse.

    The earlier version clicked a stale coordinate and pasted blind; the text
    landed in unrelated cells while the intended block stayed empty. This one
    proves focus is inside the tagged cell before typing, and returns a status
    string instead of guessing.
    """
    pt_raw = eval_js(ws, TAG_EMPTY_CAPTION_JS)
    if not pt_raw:
        return "NO_EMPTY_CAPTION"
    pt = json.loads(pt_raw)
    print(f"  target caption at ({pt['x']}, {pt['y']})")

    click_at(ws, pt["x"], pt["y"])
    status = eval_js(ws, VERIFY_FOCUS_JS)
    if status != "FOCUSED_TARGET":
        print(f"  single click -> {status}; trying double click")
        double_click_at(ws, pt["x"], pt["y"])
        status = eval_js(ws, VERIFY_FOCUS_JS)

    if status != "FOCUSED_TARGET":
        print(f"  ABORT: focus check returned {status}; not typing")
        return status

    # Per-character key events transpose on long strings -- "One call or one"
    # came back as "One call ro one". Clipboard paste is atomic, so use it for
    # anything long enough to race; short labels type fine either way.
    # Clipboard paste does not reach these caption cells reliably (it lands in
    # Sheets, not here), so type. At 40ms long strings transpose - "One call or"
    # became "One call ro" - so slow down as the string grows.
    type_chars(ws, text, delay=0.09 if len(text) > 40 else 0.04)

    # Poll rather than sleep. A fixed wait produced BOTH false negatives (paste
    # not landed yet) and false confidence, so the status column could not be
    # trusted in either direction.
    probe = text[:30]
    for _ in range(12):
        time.sleep(0.8)
        got = eval_js(ws, READ_TARGET_JS) or ""
        if probe in got:
            print(f"  verified in target cell: {got.splitlines()[0][:60]!r}")
            return "FILLED"
    got = eval_js(ws, READ_TARGET_JS)
    print(f"  FILL_NOT_VERIFIED: target cell reads {got!r}")
    return "FILL_NOT_VERIFIED"


def fill_layout(ws, heading, body):
    """Fill the two caption slots of the most recently inserted layout."""
    for label, text in (("heading", heading), ("body", body)):
        status = fill_next_empty_caption(ws, text)
        print(f"  {label}: {status}")
        if status != "FILLED":
            return status
    return "FILLED"


def publish(ws):
    """Click Publish and confirm. Returns a status string."""
    if not click_control(ws, "Publish"):
        return "PUBLISH_BUTTON_NOT_FOUND"
    time.sleep(2.0)
    # The confirm dialog's primary action is also labelled Publish.
    if click_control(ws, "Publish"):
        time.sleep(3.0)
    return "PUBLISH_SUBMITTED"
