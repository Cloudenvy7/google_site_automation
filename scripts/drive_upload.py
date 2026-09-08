"""Upload local files to Google Drive through the browser.

Why not the Drive API: the connector available here can only pass file bytes
inline, and these screenshots are hundreds of KB each. Why not a DOM file
input: Drive builds none until you click "New", and that opens a *native* OS
file chooser, which no amount of DOM scripting can reach.

CDP can, though. Page.setInterceptFileChooserDialog turns the native dialog
into a Page.fileChooserOpened event carrying the input's backendNodeId, and
DOM.setFileInputFiles then hands it a path. The bytes go straight from disk to
Chrome and never pass through the agent.
"""

import json
import time

import websocket

import chrome_automation as C
import sites_automation as S


def _drain_for_event(ws, method, timeout=15.0):
    """Read frames until the named CDP event arrives (or we give up)."""
    deadline = time.time() + timeout
    ws.settimeout(2.0)
    while time.time() < deadline:
        try:
            msg = json.loads(ws.recv())
        except websocket.WebSocketTimeoutException:
            continue
        except Exception:
            break
        if msg.get("method") == method:
            return msg.get("params", {})
    return None


def upload_via_file_chooser(ws, click_fn, paths, timeout=20.0):
    """Arm the interceptor, run click_fn to trigger the picker, feed it paths."""
    C.send_ws_cmd(ws, "DOM.enable")
    C.send_ws_cmd(ws, "Page.enable")
    C.send_ws_cmd(ws, "Page.setInterceptFileChooserDialog", {"enabled": True})

    click_fn()

    params = _drain_for_event(ws, "Page.fileChooserOpened", timeout)
    if not params:
        C.send_ws_cmd(ws, "Page.setInterceptFileChooserDialog", {"enabled": False})
        return "NO_FILE_CHOOSER_EVENT"

    node = params.get("backendNodeId")
    if not node:
        return f"NO_BACKEND_NODE ({params})"

    res = C.send_ws_cmd(ws, "DOM.setFileInputFiles",
                        {"files": paths, "backendNodeId": node})
    C.send_ws_cmd(ws, "Page.setInterceptFileChooserDialog", {"enabled": False})
    if res and "error" in res:
        return f"SET_FILES_ERROR {res['error']}"
    return "FILES_SET"
