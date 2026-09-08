import json
import urllib.request
import websocket
import time

CHROME_PORT = 9222
_cmd_id = 0

def send_ws_cmd(ws, method, params=None):
    global _cmd_id
    _cmd_id += 1
    cmd = {
        "id": _cmd_id,
        "method": method,
        "params": params or {}
    }
    ws.send(json.dumps(cmd))
    while True:
        try:
            msg = ws.recv()
            res = json.loads(msg)
            if res.get("id") == _cmd_id:
                return res
        except websocket.WebSocketTimeoutException:
            print(f"Error: Command {method} (ID: {_cmd_id}) timed out.")
            return None
        except Exception as e:
            print(f"Error receiving response: {e}")
            return None

def create_new_doc():
    url_new = f"http://localhost:{CHROME_PORT}/json/new"
    print("Opening a new blank tab in Chrome...")
    try:
        req = urllib.request.Request(url_new, method="PUT")
        with urllib.request.urlopen(req) as response:
            new_tab = json.loads(response.read().decode('utf-8'))
            ws_url = new_tab.get("webSocketDebuggerUrl")
            print(f"Created tab WebSocket URL: {ws_url}")
            return ws_url
    except Exception as e:
        print("Failed to create new tab in Chrome:", e)
        return None

def open_existing_doc(doc_id):
    ws_url = create_new_doc()
    if not ws_url:
        return None
        
    print(f"Connecting and navigating to docs.google.com/document/d/{doc_id}/edit...")
    ws = websocket.create_connection(ws_url, timeout=10)
    nav_cmd = {
        "id": 9999,
        "method": "Page.navigate",
        "params": {"url": f"https://docs.google.com/document/d/{doc_id}/edit"}
    }
    ws.send(json.dumps(nav_cmd))
    ws.recv() # Wait for navigate ack
    ws.close()
    return ws_url

def extract_google_doc_text_via_chrome(doc_id):
    ws_url = create_new_doc()
    if not ws_url:
        print("Error: Could not open Chrome tab for Google Doc text extraction.")
        return None
        
    print(f"Connecting to Chrome tab to extract text for Doc {doc_id}...")
    ws = websocket.create_connection(ws_url, timeout=15)
    try:
        url = f"https://docs.google.com/document/d/{doc_id}/edit"
        send_ws_cmd(ws, "Page.navigate", {"url": url})
        
        # Wait for the document to load
        time.sleep(5.0)
        
        js_extract = """
        (function() {
            const url = new URL(window.location.href);
            url.pathname = url.pathname.replace('/edit', '/export');
            url.search = '';
            url.searchParams.set('format', 'txt');
            return fetch(url.toString()).then(res => res.text());
        })()
        """
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": js_extract, "awaitPromise": True})
        val = res.get("result", {}).get("result", {}).get("value")
        
        # Close the tab
        send_ws_cmd(ws, "Page.close")
        return val
    except Exception as e:
        print(f"Error during Google Doc Chrome text extraction: {e}")
        try:
            send_ws_cmd(ws, "Page.close")
        except:
            pass
        return None
    finally:
        ws.close()

def wait_for_doc_to_load(ws, doc_id):
    print("Waiting for document tab to load and editor to initialize...")
    for attempt in range(25):
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": "window.location.href"})
        val = res.get("result", {}).get("result", {}).get("value") or ""
        print(f"Polling tab URL: {val}")
        if doc_id in val:
            break
        time.sleep(1.0)
    else:
        print("Timeout waiting for URL navigation.")
        return False
        
    check_editor_js = """
    (function() {
        var el = document.querySelector('.chapter-item-label-and-buttons-container') || document.querySelector('[aria-label^="Show tabs & outlines"]') || document.querySelector('[aria-label="Add tab"]');
        return !!el;
    })()
    """
    for attempt in range(20):
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": check_editor_js})
        val = res.get("result", {}).get("result", {}).get("value") if res else False
        if val:
            print("Google Doc editor initialized and ready!")
            time.sleep(2.0)
            return True
        print("Waiting for editor outline elements to load...")
        time.sleep(1.5)
        
    print("Timeout waiting for editor outline elements to load.")
    return False

def ensure_sidebar_open(ws):
    ensure_sidebar_js = """
    (function() {
        var addTabBtn = document.querySelector('[aria-label="Add tab"]');
        if (!addTabBtn || addTabBtn.offsetWidth === 0 || addTabBtn.offsetHeight === 0) {
            var showSidebarBtn = document.querySelector('[aria-label^="Show tabs & outlines"]');
            if (showSidebarBtn) {
                showSidebarBtn.click();
                return "CLICKED_SHOW_SIDEBAR";
            }
            return "SHOW_SIDEBAR_BUTTON_NOT_FOUND";
        }
        return "SIDEBAR_ALREADY_OPEN";
    })()
    """
    res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": ensure_sidebar_js})
    status = res.get("result", {}).get("result", {}).get("value")
    print(f"Ensure sidebar status: {status}")
    if status == "CLICKED_SHOW_SIDEBAR":
        time.sleep(2.0)
    return status

def add_tab(ws):
    ensure_sidebar_open(ws)
    
    add_tab_js = """
    (function() {
        var addTabBtn = document.querySelector('[aria-label="Add tab"]');
        if (addTabBtn) {
            addTabBtn.click();
            return "SUCCESS";
        }
        return "ADD_TAB_BUTTON_NOT_FOUND";
    })()
    """
    get_tabs_js = """
    (function() {
        const results = [];
        const containers = document.querySelectorAll('.chapter-item-label-and-buttons-container');
        for (let c of containers) {
            results.push(c.innerText.trim());
        }
        return JSON.stringify(results);
    })()
    """
    for attempt in range(5):
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": get_tabs_js})
        existing_tabs = json.loads(res.get("result", {}).get("result", {}).get("value") or "[]")
        print(f"Add Tab: Existing tabs = {existing_tabs}")
        
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": add_tab_js})
        val = res.get("result", {}).get("result", {}).get("value")
        print(f"Add tab attempt {attempt+1} result: {val}")
        time.sleep(2.0)
        
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": get_tabs_js})
        new_tabs = json.loads(res.get("result", {}).get("result", {}).get("value") or "[]")
        
        for t in new_tabs:
            if t not in existing_tabs:
                print(f"Successfully added tab: '{t}'")
                return t
    return None

def rename_tab(ws, current_name, target_name):
    ensure_sidebar_open(ws)
    print(f"Renaming tab '{current_name}' to '{target_name}'...")
    click_options_js = """
    (function() {
        const containers = document.querySelectorAll('.chapter-item-label-and-buttons-container');
        let container = null;
        for (let c of containers) {
            if (c.innerText.trim() === 'CURRENT_NAME') {
                container = c;
                break;
            }
        }
        if (!container) return "CONTAINER_NOT_FOUND";
        
        const optionsBtn = container.parentElement.querySelector('[aria-label="Tab options"]');
        if (optionsBtn) {
            optionsBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
            optionsBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
            optionsBtn.click();
            return "SUCCESS";
        }
        return "OPTIONS_NOT_FOUND";
    })()
    """.replace('CURRENT_NAME', current_name)
    
    click_rename_js = """
    (function() {
        const menuItems = document.querySelectorAll('.goog-menuitem, [role="menuitem"]');
        for (let item of menuItems) {
            if (item.innerText.includes('Rename')) {
                item.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                item.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                item.click();
                return "CLICKED_RENAME";
            }
        }
        return "RENAME_NOT_FOUND";
    })()
    """
    
    submit_rename_js = """
    (function() {
        const inputs = document.querySelectorAll('input.goog-control');
        for (let input of inputs) {
            if (input.value === 'CURRENT_NAME') {
                input.focus();
                input.select();
                input.value = "TARGET_NAME";
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                
                var enterDown = new KeyboardEvent('keydown', {
                    bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13
                });
                var enterUp = new KeyboardEvent('keyup', {
                    bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13
                });
                input.dispatchEvent(enterDown);
                input.dispatchEvent(enterUp);
                
                input.blur();
                return "RENAME_SUBMITTED";
            }
        }
        return "INPUT_NOT_FOUND";
    })()
    """.replace('CURRENT_NAME', current_name).replace('TARGET_NAME', target_name)
    
    for attempt in range(5):
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": click_options_js})
        val = res.get("result", {}).get("result", {}).get("value")
        print(f"Click tab options result: {val}")
        if val != "SUCCESS":
            time.sleep(1.0)
            continue
        time.sleep(0.5)
        
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": click_rename_js})
        val = res.get("result", {}).get("result", {}).get("value")
        print(f"Click Rename result: {val}")
        if val != "CLICKED_RENAME":
            time.sleep(1.0)
            continue
        time.sleep(0.5)
        
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": submit_rename_js})
        val = res.get("result", {}).get("result", {}).get("value")
        print(f"Submit rename result: {val}")
        time.sleep(1.5)
        
        # Verify rename
        get_tabs_js = """
        (function() {
            const results = [];
            const containers = document.querySelectorAll('.chapter-item-label-and-buttons-container');
            for (let c of containers) {
                results.push(c.innerText.trim());
            }
            return JSON.stringify(results);
        })()
        """
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": get_tabs_js})
        tabs = json.loads(res.get("result", {}).get("result", {}).get("value") or "[]")
        if target_name in tabs:
            print(f"Rename verified! Tab '{target_name}' is active.")
            return True
            
    return False

def add_subtab(ws, parent_name):
    ensure_sidebar_open(ws)
    print(f"Adding subtab under parent tab '{parent_name}'...")
    click_options_js = """
    (function() {
        const containers = document.querySelectorAll('.chapter-item-label-and-buttons-container');
        let container = null;
        for (let c of containers) {
            if (c.innerText.trim() === 'PARENT_NAME') {
                container = c;
                break;
            }
        }
        if (!container) return "PARENT_CONTAINER_NOT_FOUND";
        
        const optionsBtn = container.parentElement.querySelector('[aria-label="Tab options"]');
        if (optionsBtn) {
            optionsBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
            optionsBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
            optionsBtn.click();
            return "SUCCESS";
        }
        return "OPTIONS_NOT_FOUND";
    })()
    """.replace('PARENT_NAME', parent_name)
    
    get_tabs_js = """
    (function() {
        const fontResults = [];
        const containers = document.querySelectorAll('.chapter-item-label-and-buttons-container');
        for (let c of containers) {
            fontResults.push(c.innerText.trim());
        }
        return JSON.stringify(fontResults);
    })()
    """
    
    click_subtab_js = """
    (function() {
        const menuItems = document.querySelectorAll('.goog-menuitem, [role="menuitem"]');
        for (let item of menuItems) {
            if (item.innerText.includes('Add subtab')) {
                item.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                item.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                item.click();
                return "CLICKED_ADD_SUBTAB";
            }
        }
        return "ADD_SUBTAB_NOT_FOUND";
    })()
    """
    
    for attempt in range(5):
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": get_tabs_js})
        existing_tabs = json.loads(res.get("result", {}).get("result", {}).get("value") or "[]")
        
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": click_options_js})
        val = res.get("result", {}).get("result", {}).get("value")
        print(f"Click parent options result: {val}")
        if val != "SUCCESS":
            time.sleep(1.0)
            continue
        time.sleep(0.5)
        
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": click_subtab_js})
        val = res.get("result", {}).get("result", {}).get("value")
        print(f"Click Add subtab result: {val}")
        if val != "CLICKED_ADD_SUBTAB":
            time.sleep(1.0)
            continue
        time.sleep(2.0)
        
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": get_tabs_js})
        new_tabs = json.loads(res.get("result", {}).get("result", {}).get("value") or "[]")
        
        for t in new_tabs:
            if t not in existing_tabs:
                print(f"Successfully added subtab: '{t}'")
                return t
    return None

def select_tab(ws, name):
    ensure_sidebar_open(ws)
    print(f"Selecting tab '{name}'...")
    select_tab_js = """
    (function() {
        const containers = document.querySelectorAll('.chapter-item-label-and-buttons-container');
        for (let c of containers) {
            if (c.innerText.trim() === 'TAB_NAME') {
                c.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                c.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                c.click();
                return "SELECTED";
            }
        }
        return "NOT_FOUND";
    })()
    """.replace('TAB_NAME', name)
    
    res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": select_tab_js})
    print("Select result:", res.get("result", {}).get("result", {}).get("value"))
    time.sleep(1.0)

def focus_editor(ws):
    focus_js = """
    (function() {
        var iframe = document.querySelector(".docs-texteventtarget-iframe");
        var el = iframe ? (iframe.contentDocument || iframe.contentWindow.document).querySelector("[contenteditable=true]") : document.querySelector("[contenteditable=true]");
        if (el) {
            el.focus();
            return "SUCCESS";
        }
        return "EDITOR_NOT_FOUND";
    })()
    """
    res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": focus_js})
    print("Focus editor result:", res.get("result", {}).get("result", {}).get("value"))
    time.sleep(1.0)

def select_all_and_delete(ws):
    print("Selecting all and deleting...")
    send_ws_cmd(ws, "Input.dispatchKeyEvent", {
        "type": "keyDown",
        "modifiers": 2,
        "key": "Control",
        "code": "ControlLeft",
        "windowsVirtualKeyCode": 17,
        "nativeVirtualKeyCode": 17,
    })
    send_ws_cmd(ws, "Input.dispatchKeyEvent", {
        "type": "keyDown",
        "modifiers": 2,
        "key": "a",
        "code": "KeyA",
        "windowsVirtualKeyCode": 65,
        "nativeVirtualKeyCode": 65,
    })
    send_ws_cmd(ws, "Input.dispatchKeyEvent", {
        "type": "keyUp",
        "modifiers": 2,
        "key": "a",
        "code": "KeyA",
        "windowsVirtualKeyCode": 65,
        "nativeVirtualKeyCode": 65,
    })
    send_ws_cmd(ws, "Input.dispatchKeyEvent", {
        "type": "keyUp",
        "modifiers": 0,
        "key": "Control",
        "code": "ControlLeft",
        "windowsVirtualKeyCode": 17,
        "nativeVirtualKeyCode": 17,
    })
    time.sleep(0.5)
    send_ws_cmd(ws, "Input.dispatchKeyEvent", {
        "type": "rawKeyDown",
        "key": "Backspace",
        "code": "Backspace",
        "windowsVirtualKeyCode": 8,
        "nativeVirtualKeyCode": 8,
    })
    send_ws_cmd(ws, "Input.dispatchKeyEvent", {
        "type": "keyUp",
        "key": "Backspace",
        "code": "Backspace",
        "windowsVirtualKeyCode": 8,
        "nativeVirtualKeyCode": 8,
    })
    time.sleep(1.0)

def type_text(ws, text):
    print("Pasting text via clipboard emulation...")
    js_escaped = text.replace('\\', '\\\\').replace('\'', '\\\'').replace('\n', '\\n').replace('\r', '\\r')
    js_copy = f"""
    (function() {{
        const el = document.createElement('textarea');
        el.value = '{js_escaped}';
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        return true;
    }})()
    """
    send_ws_cmd(ws, "Runtime.evaluate", {"expression": js_copy})
    time.sleep(0.2)
    
    send_ws_cmd(ws, "Input.dispatchKeyEvent", {
        "type": "rawKeyDown",
        "key": "Control",
        "code": "ControlLeft",
        "windowsVirtualKeyCode": 17,
        "modifiers": 2
    })
    send_ws_cmd(ws, "Input.dispatchKeyEvent", {
        "type": "rawKeyDown",
        "key": "v",
        "code": "KeyV",
        "windowsVirtualKeyCode": 86,
        "modifiers": 2
    })
    send_ws_cmd(ws, "Input.dispatchKeyEvent", {
        "type": "char",
        "text": "v",
        "modifiers": 2
    })
    send_ws_cmd(ws, "Input.dispatchKeyEvent", {
        "type": "keyUp",
        "key": "v",
        "code": "KeyV",
        "windowsVirtualKeyCode": 86,
        "modifiers": 2
    })
    send_ws_cmd(ws, "Input.dispatchKeyEvent", {
        "type": "keyUp",
        "key": "Control",
        "code": "ControlLeft",
        "windowsVirtualKeyCode": 17,
        "modifiers": 2
    })
    time.sleep(1.0)

def rename_doc(ws, target_name):
    print(f"Renaming document to '{target_name}'...")
    wait_title_js = """
    (function() {
        var input = document.querySelector("input.docs-title-input");
        return !!input;
    })()
    """
    for attempt in range(15):
        res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": wait_title_js})
        if res and res.get("result", {}).get("result", {}).get("value"):
            break
        time.sleep(1.0)
    else:
        print("Error: Document title input field not loaded.")
        return False

    rename_js = f"""
    (function() {{
        var label = document.querySelector(".docs-title-input-label");
        var input = document.querySelector("input.docs-title-input");
        if (!input) return "INPUT_NOT_FOUND";
        if (label) {{
            label.click();
        }}
        input.focus();
        input.select();
        input.value = "{target_name}";
        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        var enterDown = new KeyboardEvent('keydown', {{
            bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13
        }});
        var enterUp = new KeyboardEvent('keyup', {{
            bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13
        }});
        input.dispatchEvent(enterDown);
        input.dispatchEvent(enterUp);
        input.blur();
        return "DISPATCHED";
    }})()
    """
    res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": rename_js})
    time.sleep(2.0)
    
    res = send_ws_cmd(ws, "Runtime.evaluate", {"expression": "document.querySelector('.docs-title-input-label') ? document.querySelector('.docs-title-input-label').innerText : ''"})
    title = res.get("result", {}).get("result", {}).get("value") or ""
    print(f"Verified label text is now: {title}")
    return target_name in title
