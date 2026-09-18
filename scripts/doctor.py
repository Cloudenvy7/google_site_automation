#!/usr/bin/env python3
"""Check everything BEFORE you start, and say exactly how to fix what is wrong.

RUN THIS FIRST:   python3 scripts/doctor.py

WHY THIS EXISTS (2026-09-18)
A client setup took 1h42m. Roughly half of it went to things no instruction
covered, and the single worst was this: the Google Sheets API had never been
enabled on the project. That failure surfaced **seventy-five minutes in**, as a
confusing permissions error, after the service account, the key, the sharing and
the installs were all done. It is a two-second check.

The setup also needed a person who already knew the system sitting beside the
client. Andrew afterwards: *"If I wasn't there, there is no way that person would
be able to get that task done, and the whole point of doing a whole repo was to
make sure everything was explained."*

So this file has one rule: **every failure prints the command or click that fixes
it.** A check that tells you something is wrong without telling you what to do
has moved the problem, not solved it.

It is safe. It reads; it never writes, never uploads, never touches a Site.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IS_MAC = platform.system() == "Darwin"

OK, WARN, FAIL = "  ok  ", " warn ", " FAIL "
_results = []


def report(status, title, detail="", fix=""):
    _results.append((status, title))
    print("[%s] %s" % (status, title))
    if detail:
        for line in detail.strip().splitlines():
            print("         " + line)
    if fix and status != OK:
        print("         -> FIX:")
        for line in fix.strip().splitlines():
            print("            " + line)
    print()


# ---------------------------------------------------------------- environment
def check_python():
    v = sys.version_info
    s = "%d.%d.%d" % (v.major, v.minor, v.micro)
    if v < (3, 9):
        report(FAIL, "Python %s is too old" % s,
               "This system is proven on 3.13.5; 3.9 is the floor.",
               "macOS:  brew install python@3.12\n"
               "then:   python3 -m venv .venv && source .venv/bin/activate")
    else:
        in_venv = sys.prefix != sys.base_prefix
        report(OK if in_venv else WARN,
               "Python %s%s" % (s, "" if in_venv else "  (not in a venv)"),
               "" if in_venv else "Installing into the system Python can break other things.",
               "" if in_venv else
               "python3 -m venv .venv && source .venv/bin/activate\n"
               "pip install -r requirements.txt")


def check_deps():
    missing = []
    for mod, pkg in (("googleapiclient", "google-api-python-client"),
                     ("google.oauth2", "google-auth"),
                     ("websocket", "websocket-client")):
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        report(FAIL, "Missing Python packages: " + ", ".join(missing), "",
               "source .venv/bin/activate\npip install -r requirements.txt")
        return False
    report(OK, "Python packages installed")
    return True


def check_claude_cli():
    """Not in the original SETUP.md at all -- the client hit it at 1h26m."""
    if shutil.which("claude"):
        report(OK, "Claude Code CLI found on PATH")
        return
    report(FAIL, "Claude Code CLI ('claude') not on PATH",
           "indexer_v3.py shells out to it. Without it, Stage 1 cannot run.",
           "npm install -g @anthropic-ai/claude-code\n"
           "(needs Node.js. Takes a few minutes and prints little -- that is normal.)\n"
           "If npm is missing:  macOS  brew install node")


# ---------------------------------------------------------------- credentials
def key_path():
    for k in ("GOOGLE_SERVICE_ACCOUNT_JSON", "ADVISOR_SA"):
        v = os.environ.get(k)
        if v:
            return os.path.expanduser(v)
    for c in (os.path.join(REPO, "service_account.json"),
              os.path.expanduser("~/.advisor_os/service_account.json"),
              os.path.expanduser("~/.config/advisor_os/service_account.json")):
        if os.path.exists(c):
            return c
    return None


def check_key():
    p = key_path()
    if not p:
        report(FAIL, "No service-account key found",
               "Looked at $GOOGLE_SERVICE_ACCOUNT_JSON, ./service_account.json\n"
               "and ~/.advisor_os/service_account.json",
               "mkdir -p ~/.advisor_os\n"
               "mv ~/Downloads/<the-key-you-downloaded>.json ~/.advisor_os/service_account.json\n"
               "chmod 600 ~/.advisor_os/service_account.json\n"
               "export GOOGLE_SERVICE_ACCOUNT_JSON=~/.advisor_os/service_account.json")
        return None
    if not os.path.exists(p):
        report(FAIL, "Key path is set but nothing is there", p,
               "Fix the variable, or unset it to fall back to the searched paths.")
        return None
    try:
        k = json.load(open(p))
    except Exception as e:
        report(FAIL, "Key file will not parse as JSON", "%s\n%s" % (p, e),
               "Re-download it: Cloud Console -> IAM & Admin -> Service Accounts\n"
               "-> click the account -> KEYS -> ADD KEY -> JSON")
        return None
    if k.get("type") != "service_account" or "client_email" not in k:
        report(FAIL, "That JSON is not a service-account key", p,
               "You may have downloaded an OAuth client secret instead.\n"
               "You want: the service account -> KEYS tab -> ADD KEY -> JSON")
        return None

    # The client's downloaded filename did not match what anyone expected, and
    # nobody had opened it. Print what it IS, so the name stops mattering.
    report(OK, "Service-account key valid",
           "file        : %s\nclient_email: %s\nproject_id  : %s"
           % (p, k["client_email"], k.get("project_id", "?")))

    if os.path.abspath(p).startswith(os.path.abspath(REPO) + os.sep):
        report(WARN, "The key is INSIDE the repository",
               "Google names keys <project>-<hash>.json, which .gitignore did not\n"
               "match until 2026-09-18. The pre-commit hook now refuses credentials\n"
               "by content, but the safe place is outside the repo entirely.",
               "mkdir -p ~/.advisor_os\n"
               "mv '%s' ~/.advisor_os/service_account.json\n"
               "export GOOGLE_SERVICE_ACCOUNT_JSON=~/.advisor_os/service_account.json" % p)
    try:
        if (os.stat(p).st_mode & 0o077) and not IS_MAC:
            report(WARN, "Key is readable by other users on this machine", p,
                   "chmod 600 '%s'" % p)
    except OSError:
        pass
    return k


# ---------------------------------------------------------------- google apis
def _svc(key, api, ver, scopes):
    import google.oauth2.service_account as sa
    from googleapiclient.discovery import build
    c = sa.Credentials.from_service_account_file(key, scopes=scopes)
    return build(api, ver, credentials=c, cache_discovery=False)


def check_apis(keyfile, project):
    """The 75-minute failure. Drive was enabled; Sheets was not."""
    results = {}
    for label, api, ver, scope, probe in (
        ("Drive API", "drive", "v3",
         "https://www.googleapis.com/auth/drive.readonly",
         lambda s: s.files().list(pageSize=1, fields="files(id)").execute()),
        ("Sheets API", "sheets", "v4",
         "https://www.googleapis.com/auth/spreadsheets.readonly",
         lambda s: s.spreadsheets().get(spreadsheetId="1" + "0" * 43).execute()),
    ):
        try:
            probe(_svc(keyfile, api, ver, [scope]))
            report(OK, "%s enabled and reachable" % label)
            results[label] = True
        except Exception as e:
            msg = str(e)
            if "has not been used in project" in msg or "is disabled" in msg \
                    or "SERVICE_DISABLED" in msg or "accessNotConfigured" in msg:
                report(FAIL, "%s is NOT ENABLED on project '%s'" % (label, project or "?"),
                       "This is the failure that cost 75 minutes on 2026-09-18.\n"
                       "It shows up later as a confusing permissions error.",
                       "https://console.cloud.google.com/apis/library?project=%s\n"
                       "Search for '%s' and click ENABLE. Wait ~30s, then re-run."
                       % (project or "YOUR_PROJECT", label))
                results[label] = False
            elif "Requested entity was not found" in msg or "notFound" in msg:
                # Sheets probe uses a deliberately bogus id: a 404 proves the API
                # is switched on and answering.
                report(OK, "%s enabled and reachable" % label)
                results[label] = True
            else:
                report(WARN, "%s: could not confirm" % label, msg[:200],
                       "Re-run after the other failures above are fixed.")
                results[label] = None
    return results


def check_shared(keyfile, folder_id, catalogue_id):
    if folder_id:
        try:
            d = _svc(keyfile, "drive", "v3",
                     ["https://www.googleapis.com/auth/drive.readonly"])
            m = d.files().get(fileId=folder_id, fields="name,mimeType",
                              supportsAllDrives=True).execute()
            r = d.files().list(q="'%s' in parents and trashed=false" % folder_id,
                               fields="files(id)", pageSize=1000,
                               supportsAllDrives=True,
                               includeItemsFromAllDrives=True).execute()
            report(OK, "Drive folder shared and readable",
                   "%s  ->  %d item(s) at the top level"
                   % (m["name"], len(r.get("files", []))))
        except Exception as e:
            report(FAIL, "Cannot see that Drive folder", str(e)[:180],
                   "A 404 here almost always means LINK-SHARING instead of sharing\n"
                   "by address. Link-sharing does NOT grant service accounts.\n"
                   "Open the folder -> Share -> paste the client_email above ->\n"
                   "Viewer -> untick 'Notify people' -> Send.")
    else:
        report(WARN, "No Drive folder to check",
               "Pass --folder <id>, or set ADVISOR_FOLDER_ID.",
               "The id is the last part of drive.google.com/drive/folders/<THIS>")

    if catalogue_id:
        try:
            s = _svc(keyfile, "sheets", "v4",
                     ["https://www.googleapis.com/auth/spreadsheets.readonly"])
            meta = s.spreadsheets().get(spreadsheetId=catalogue_id).execute()
            tabs = [t["properties"]["title"] for t in meta["sheets"]]
            need = ["00_HARNESS", "WAIVERS", "DRIVE_INVENTORY", "CHARTER",
                    "MANIFEST", "PAGE_PLAN"]
            missing = [t for t in need if t not in tabs]
            if missing:
                report(FAIL, "Catalogue Sheet is missing tabs: " + ", ".join(missing),
                       "Found %d tabs. A catalogue missing a tab is not a smaller\n"
                       "catalogue, it is a broken one -- later stages read columns by\n"
                       "name and fail silently when a name moves." % len(tabs),
                       "Copy the WHOLE template Sheet (File -> Make a copy), not\n"
                       "individual tabs, and not the CSVs in catalogue_template/.")
            else:
                report(OK, "Catalogue Sheet shared and complete", "%d tabs" % len(tabs))
        except Exception as e:
            report(FAIL, "Cannot open the catalogue Sheet", str(e)[:180],
                   "Share the SHEET too, not just the folder -- this was missed at\n"
                   "1h18m on 2026-09-18. Share -> paste client_email -> EDITOR.")
    else:
        report(WARN, "No catalogue Sheet to check",
               "Pass --catalogue <id>, or set ADVISOR_CATALOGUE_ID.")


# ---------------------------------------------------------------- chrome
def check_chrome():
    port = os.environ.get("CHROME_PORT", "9222")
    try:
        with urllib.request.urlopen(
                "http://127.0.0.1:%s/json/version" % port, timeout=4) as r:
            v = json.load(r)
        report(OK, "Chrome debugging port open", v.get("Browser", "?"))
    except Exception:
        report(WARN, "Chrome is not listening on port %s" % port,
               "Only needed to BUILD a Site. Indexing does not use it.",
               "Quit Chrome completely first (%s), then:\n"
               "  ./scripts/launch_chrome.sh\n"
               "Run it from your OWN terminal -- not through an agent."
               % ("Cmd-Q" if IS_MAC else "close all windows"))


# ---------------------------------------------------------------- main
def main():
    args = sys.argv[1:]

    def opt(name, env):
        if name in args:
            return args[args.index(name) + 1]
        return os.environ.get(env)

    folder = opt("--folder", "ADVISOR_FOLDER_ID")
    catalogue = opt("--catalogue", "ADVISOR_CATALOGUE_ID")

    print("\n" + "=" * 68)
    print(" Google Sites Automation -- preflight")
    print(" %s %s | repo: %s" % (platform.system(), platform.release()[:12], REPO))
    print("=" * 68 + "\n")

    check_python()
    have_deps = check_deps()
    check_claude_cli()

    key = check_key() if have_deps else None
    if key and have_deps:
        keyfile = key_path()
        check_apis(keyfile, key.get("project_id"))
        check_shared(keyfile, folder, catalogue)
    check_chrome()

    fails = [t for s, t in _results if s == FAIL]
    warns = [t for s, t in _results if s == WARN]
    print("=" * 68)
    if fails:
        print(" %d MUST be fixed before this will work:" % len(fails))
        for t in fails:
            print("   - " + t)
    if warns:
        print(" %d worth knowing:" % len(warns))
        for t in warns:
            print("   - " + t)
    if not fails and not warns:
        print(" Everything checks out. You are ready to index.")
    elif not fails:
        print(" Nothing blocking. The warnings above are optional.")
    print("=" * 68 + "\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
