"""The Build Harness -- the mechanical subset of the gates, guards and ledgers.

Governed by "TEMPLATE - Build Harness and Guardrails v2.0", which is instantiated
at STAGE 0 -- before the folder is indexed and before the client is asked
anything. Read that document for the reasoning; this file only enforces.

A harness written after the build is an audit. It cannot prevent anything,
because by the time it exists the drift has already happened. These checks are
meant to run from the first day of a site's work, against a catalogue that was
copied from the template with 00_HARNESS and WAIVERS already in it.

The distinction that matters: every failure this guards against PASSED ITS OWN
VERIFICATION. A builder that confirms "the block is on the page" passes while
the page is scrambled, incomplete, or built on top of something it destroyed.
So these checks do not ask whether the artifact looks right. They ask whether
the method was followed, which is the thing the artifact cannot show you.

Nothing here decides anything. Every check either passes or raises Refusal, and
a Refusal is a finding for the human, not an error to work around.
"""

import json
import os
import re
import time
import config

# Browser modules are imported lazily. GUARD 9 and the gates are used by the
# indexer and by the eval suite, which must load without a browser stack.
try:
    import chrome_automation as C
    import sites_automation as S
except Exception:          # websocket-client absent, or no display
    C = S = None

VIEWPORT = (1920, 1080)
BLOCKING_FLAGS = ("UNKNOWN", "NOT ESTABLISHED", "NOT_ESTABLISHED", "TBD",
                  "NOT RECORDED", "ROSTER NOT ESTABLISHED")


class Refusal(Exception):
    """A gate or guard refused. This is a valid deliverable, not a crash.

    Refusal is a feature (Cycle, THE GATE). The council proposes with
    reasoning; the human ratifies. An agent that routes around a Refusal has
    reproduced the failure the Refusal exists to prevent.
    """


REQUIRED_TABS = ("00_HARNESS", "WAIVERS", "00_README", "DRIVE_INVENTORY",
                 "CHARTER", "MANIFEST", "PAGE_PLAN", "SITE_PAGES",
                 "SITE_CONTENT_BLOCKS", "SITE_ASSETS", "SITE_SYNC_LOG")

STAGE_0_KEYS = ("site_name", "drive_folder_id", "isa_doc_id", "harness_version")


# --------------------------------------------------------------------------
# STAGE 0 -- the harness is instantiated before any other stage runs.
# --------------------------------------------------------------------------

def stage_0_instantiated(tabs):
    """Refuse to treat a catalogue as ready if it was not built from the template.

    A catalogue missing a tab is not a smaller catalogue; it is a broken one --
    later stages read columns by name and fail silently when a name moves. The
    two harness tabs are required exactly like the rest: 00_HARNESS carries the
    gate checklist, WAIVERS is the only legitimate way past a flagged gap.
    """
    missing = [t for t in REQUIRED_TABS if t not in tabs]
    if missing:
        raise Refusal("STAGE 0: catalogue is missing %s. Copy the template; "
                      "do not hand-assemble." % ", ".join(missing))
    kv = {str(r[0]).strip().lower(): (r[1].strip() if len(r) > 1 else "")
          for r in tabs["00_README"] if r}
    blank = [k for k in STAGE_0_KEYS if not kv.get(k)]
    if blank:
        raise Refusal("STAGE 0: 00_README has no value for %s. Fill the Stage 0 "
                      "keys before indexing." % ", ".join(blank))
    return True


def harness_checklist(tabs):
    """Read 00_HARNESS. A blank status is a stop, not an omission.

    The checklist is the human-readable half of this file. It exists so the
    gates are answerable by someone reading the sheet, without running anything.
    """
    rows = tabs.get("00_HARNESS", [])
    hdr = next((i for i, r in enumerate(rows) if r and r[0] == "id"), None)
    if hdr is None:
        raise Refusal("STAGE 0: 00_HARNESS has no header row. Copy the template.")
    open_rows = []
    for r in rows[hdr + 1:]:
        r = list(r) + [""] * 8
        if not str(r[0]).strip():
            continue
        if str(r[5]).strip().upper() not in ("PASS", "WAIVED", "N/A"):
            open_rows.append((r[0], r[2]))
    if open_rows:
        raise Refusal(
            "00_HARNESS: %d gate(s) not yet PASS/WAIVED. The build does not "
            "start:\n  - %s" % (len(open_rows),
            "\n  - ".join(f"{i}: {w[:78]}" for i, w in open_rows[:12])))
    return True


# --------------------------------------------------------------------------
# GATES -- preconditions. They fire before a stage and block it.
# --------------------------------------------------------------------------

def gate_1_architecture(readme_rows):
    """GATE 1 -- no page is built for a site with no ratified ISA.

    Failure: build proposed twice before the HopeLink ISA existed. "The whole
    point of this was the right the information systems architecture now before
    spending a second building."
    """
    kv = {str(r[0]).strip().lower(): (r[1].strip() if len(r) > 1 else "")
          for r in readme_rows if r}
    doc = kv.get("isa_doc_id", "")
    status = kv.get("isa_status", "").upper()
    if not doc:
        raise Refusal("GATE 1: catalogue 00_README names no isa_doc_id. "
                      "Write the Information Systems Architecture first.")
    if status != "RATIFIED":
        raise Refusal(f"GATE 1: isa_status is {status or 'blank'}, not RATIFIED. "
                      "Ratification is a human act.")
    return doc


def gate_2_landing(wireframe_rows, source_values):
    """GATE 2 -- THE LANDING RULE. Nothing renders that is not already a cell.

    Failure: the Team page shipped 6 of 15 people because names were typed from
    an agent's recall of a conversation instead of read from a tab. The page
    looked finished. Only the sheet could have shown the absence.

    source_values is the flattened set of every value present in the
    catalogue's evidence tabs. A wireframe value absent from it never landed.
    """
    norm = {_norm(v) for v in source_values if str(v).strip()}
    orphans = []
    for r in wireframe_rows:
        for cell in r.get("cells", []):
            c = _norm(cell)
            if not c:
                continue
            if not any(c in s or s in c for s in norm):
                orphans.append(cell)
    if orphans:
        raise Refusal(
            "GATE 2 (Landing Rule): %d value(s) would render without existing "
            "in the catalogue first. Gather them into a tab before building:\n  - %s"
            % (len(orphans), "\n  - ".join(o[:88] for o in orphans[:12])))
    return True


def gate_3_flags(rows, label="rows"):
    """GATE 3 -- a flagged gap blocks its own block.

    Failure: 'ROSTER NOT ESTABLISHED' was written into the catalogue honestly
    and then the page was built around it. A flag that stops nothing is
    decoration. Resolving it means searching the archive, not deleting the flag.
    """
    blocked = [r for r in rows
               if any(f in " ".join(str(x).upper() for x in r) for f in BLOCKING_FLAGS)]
    if blocked:
        raise Refusal(
            "GATE 3: %d %s carry an unresolved flag and block their dependent "
            "blocks. Resolve, or record a human waiver:\n  - %s"
            % (len(blocked), label,
               "\n  - ".join(" | ".join(str(x)[:40] for x in r[:3]) for r in blocked[:10])))
    return True


def gate_6_index_complete(inventory_rows):
    """GATE 6 -- the index is complete before the Charter is written.

    An index of filenames is a directory listing, not an index. The architecture
    is built ON the index; if the index does not know what is in the cabinet, the
    architecture is guessing and every later stage inherits the guess.

    Failure: an 85-row inventory in which site_candidate and proposed_section
    were 0/85 populated, because the spec said "metadata only; nothing is
    opened". Eighteen briefs holding the full project roster were never opened.
    The Team page then shipped 6 of 15 people, and the shortfall was attributed
    to a judgment call needing the advisor. It was not; nobody had looked.

    Importance is an OUTPUT of the index, not an input to it -- so "it looked
    unimportant" is never a reason for leaving a file unread.
    """
    if not inventory_rows:
        raise Refusal("GATE 6: DRIVE_INVENTORY is empty. Stage 1 has not run.")
    hdr = [str(c).strip() for c in inventory_rows[0]]
    need = ("opened", "doc_type", "what_it_says", "key_entities",
            "priority", "priority_reason", "extracted_to")
    absent = [c for c in need if c not in hdr]
    if absent:
        raise Refusal("GATE 6: DRIVE_INVENTORY is on the pre-v2.0 schema, missing "
                      "%s. A metadata-only index does not advance to Charter."
                      % ", ".join(absent))
    ix = {c: hdr.index(c) for c in need}
    ix["kind"] = hdr.index("kind") if "kind" in hdr else None
    unread, thin, unlanded = [], [], []
    for r in inventory_rows[1:]:
        r = list(r) + [""] * len(hdr)
        if ix["kind"] is not None and str(r[ix["kind"]]).strip().lower() == "folder":
            continue
        name = str(r[1])[:52]
        if str(r[ix["opened"]]).strip().lower() != "yes":
            if not str(r[hdr.index("not_opened_reason")]).strip() \
                    if "not_opened_reason" in hdr else True:
                unread.append(name)
            continue
        if not all(str(r[ix[c]]).strip()
                   for c in ("doc_type", "what_it_says", "key_entities",
                             "priority", "priority_reason")):
            thin.append(name)
        elif str(r[ix["priority"]]).strip().upper() in ("P1", "P2") \
                and not str(r[ix["extracted_to"]]).strip():
            unlanded.append(name)
    problems = []
    if unread:
        problems.append("%d file(s) not opened and carrying no reason: %s"
                        % (len(unread), ", ".join(unread[:6])))
    if thin:
        problems.append("%d opened file(s) missing doc_type/what_it_says/"
                        "key_entities/priority: %s" % (len(thin), ", ".join(thin[:6])))
    if unlanded:
        problems.append("%d P1/P2 file(s) whose content landed in no tab -- indexed "
                        "but not gathered: %s" % (len(unlanded), ", ".join(unlanded[:6])))
    if problems:
        raise Refusal("GATE 6: the index is not complete.\n  - " + "\n  - ".join(problems))
    return True


def gate_4_charter(plan_rows, goal_col="charter_goal_id"):
    """GATE 4 -- the Cycle's Binding Rule, made executable.

    Every rendered row traces to the sentence the client said that put it there.
    Mirrors the substrate rule that every relation cites a source_event_id.
    """
    missing = [r for r in plan_rows if not str(r.get(goal_col, "")).strip()]
    if missing:
        raise Refusal(
            "GATE 4: %d row(s) cite no %s and are not renderable. Attach the "
            "goal or exclude the row and record the exclusion."
            % (len(missing), goal_col))
    return True


def gate_5_ratified(rows, stage):
    """GATE 5 -- Charter, Manifest and Page Plan are ratified before Render."""
    who = [r for r in rows if str(r.get("ratified_by", "")).strip()]
    if not who:
        raise Refusal(f"GATE 5: {stage} carries no ratified_by. "
                      "The council proposes; the human ratifies.")
    return True


# --------------------------------------------------------------------------
# GUARDS -- runtime invariants. They fire during execution and abort it.
# --------------------------------------------------------------------------

def guard_2_viewport(ws):
    """GUARD 2 -- own the environment; never inherit it.

    Failure: a screenshot left Emulation.setDeviceMetricsOverride at 1400px and
    never cleared it. clearDeviceMetricsOverride RETURNS OK AND DOES NOTHING, so
    the override survived, the editor rendered narrow, the Pages panel collapsed,
    a page click missed silently, and a destructive routine deleted a finished
    page. Set metrics explicitly and verify; a diagnostic must not change the
    system it is diagnosing.
    """
    C.send_ws_cmd(ws, "Emulation.setDeviceMetricsOverride", {
        "width": VIEWPORT[0], "height": VIEWPORT[1],
        "deviceScaleFactor": 1, "mobile": False})
    time.sleep(1)
    got = S.eval_js(ws, "window.innerWidth")
    if got != VIEWPORT[0]:
        raise Refusal(f"GUARD 2: viewport is {got}, expected {VIEWPORT[0]}. "
                      "Coordinates would be computed against the wrong layout.")
    return got


def guard_1_assert_page(ws, expected_id):
    """GUARD 1 -- assert the target before destroying it.

    Failure: a page-selection click returned success and landed nowhere;
    clear_page then deleted 18 sections from a finished Home page. A click
    returning true is not evidence that the click worked. The URL is the only
    statement the environment makes about which page is actually open.
    """
    url = S.current_url(ws) or ""
    got = url.split("/p/")[1].split("/")[0].split("?")[0] if "/p/" in url else "HOME"
    if expected_id and got != expected_id:
        raise Refusal(f"GUARD 1: open page is {got}, expected {expected_id}. "
                      "Refusing to modify. Nothing was cleared.")
    return got


def guard_7_no_fabrication(value, source_evidence):
    """GUARD 7 -- never invent a value to fill a cell.

    A blank with a reason outranks a plausible guess. Four HSI staff have no
    stated role anywhere in the folder, so the page says 'Programme team' and
    the roster records role_evidence = NOT RECORDED.
    """
    if str(value).strip() and not str(source_evidence).strip():
        raise Refusal(f"GUARD 7: {value!r} has no source evidence. "
                      "State what is missing rather than filling the cell.")
    return True


def guard_9_coverage(name, expected_markers, returned_markers, status="OPENED"):
    """GUARD 9 -- coverage is proven, not claimed.

    Failure (2026-09-07): verify_index_integrity.py compared the agent's
    reported chars_read to a re-derived extractor count -- but the packet had
    handed the agent that very number. An agent that read nothing could echo
    it and pass. The check proved the extractor was deterministic and proved
    nothing about reading. The one v3 run on record cost about half the tokens
    its text should have needed, and nothing could say whether it had read
    the rest.

    So the orchestrator plants unforgeable markers through the text
    (coverage.py) and the agent must hand them back. Coverage is arithmetic
    on what was RETURNED, never on what was claimed. A file with no text layer
    (image, video, scanned PDF) is exempt only because it carries opened=no
    and a reason -- GUARD 7's rule, not a loophole.

    Returns the coverage dict on success. Raises Refusal on any missing or
    fabricated marker. A Refusal here is not an error to route around: it is
    the statement that this row was not read, and the row must not be written.
    """
    import coverage as _cv
    if status in _cv.NO_TEXT_STATUSES:
        return {"total": 0, "seen": 0, "missing": [], "pct": 100.0,
                "ok": True, "unknown": [], "exempt": status}
    cov = _cv.coverage(expected_markers, returned_markers)
    if cov["unknown"]:
        raise Refusal(f"GUARD 9: {name!r} returned {len(cov['unknown'])} marker(s) "
                      f"that were never planted. A fabricated marker is a finding, "
                      f"not a rounding error. Refusing to commit.")
    if cov["missing"]:
        raise Refusal(f"GUARD 9: {name!r} coverage {cov['pct']}% -- "
                      f"{cov['seen']}/{cov['total']} markers returned, "
                      f"{len(cov['missing'])} unread stretch(es). The file was not "
                      f"read in full. Refusing to commit; re-run the packet.")
    return cov


# --------------------------------------------------------------------------
# PREFLIGHT -- run every gate that can be checked from the catalogue alone.
# --------------------------------------------------------------------------

def preflight(tabs, wireframe_rows, evidence_tabs, strict=True):
    """Run the gates. Returns [] when clear, else a list of Refusal messages.

    strict=False collects every failure instead of stopping at the first, so a
    human sees the whole picture rather than fixing one gate at a time.
    """
    problems = []
    checks = [
        ("GATE 1", lambda: gate_1_architecture(tabs.get("00_README", []))),
        ("GATE 2", lambda: gate_2_landing(
            wireframe_rows,
            [c for t in evidence_tabs for r in tabs.get(t, []) for c in r])),
        ("GATE 3", lambda: gate_3_flags(
            [r for t in evidence_tabs for r in tabs.get(t, [])], "evidence rows")),
    ]
    for name, fn in checks:
        try:
            fn()
        except Refusal as e:
            problems.append(str(e))
            if strict:
                break
    return problems


def _norm(v):
    return re.sub(r"[^a-z0-9]+", " ", str(v).lower()).strip()


# --------------------------------------------------------------------------
# PREFLIGHT STAMP -- the bridge between the gates and the PreToolUse hook.
# --------------------------------------------------------------------------

ADVISOR_HOME = os.environ.get("ADVISOR_OS_HOME", os.path.expanduser("~/.advisor_os"))
STAMP_PATH = os.path.join(ADVISOR_HOME, "preflight.json")
STAMP_MAX_AGE_H = 12


def _tabs_from_sheet(catalogue_id):
    """Read every tab of a catalogue into {tab: rows}. Only the preflight talks
    to Google; the hook reads the stamp it leaves behind and stays offline."""
    import google.oauth2.service_account as sa
    from googleapiclient.discovery import build
    key = config.service_account_path()
    c = sa.Credentials.from_service_account_file(
        key, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    sh = build("sheets", "v4", credentials=c).spreadsheets()
    titles = [x["properties"]["title"] for x in sh.get(spreadsheetId=catalogue_id).execute()["sheets"]]
    out = {}
    for t in titles:
        out[t] = sh.values().get(spreadsheetId=catalogue_id, range=f"'{t}'").execute().get("values", [])
    return out


def write_stamp(catalogue_id, site_id, verdict, problems, meta):
    os.makedirs(ADVISOR_HOME, exist_ok=True)
    stamp = {"catalogue_id": catalogue_id, "site_id": site_id, "verdict": verdict,
             "problems": problems, "stamped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "epoch": int(time.time()), **meta}
    with open(STAMP_PATH, "w") as fh:
        json.dump(stamp, fh, indent=1)
    return stamp


def preflight_stamp(catalogue_id, site_id):
    """Run the Stage-0 checks and the ratification gates against a live
    catalogue, and leave a stamp the Site-build hook can read.

    WHY A STAMP. A PreToolUse hook fires on every Bash call and must be fast and
    offline. It cannot read a spreadsheet each time, and it must not be the
    thing that decides ratification -- that is a human act recorded in the
    catalogue. So the preflight reads the catalogue ONCE, applies the gates, and
    writes what it found. The hook then answers one question: is there a fresh
    stamp, for this site, that says RATIFIED? Anything else is a refusal.

    The stamp expires (STAMP_MAX_AGE_H) so a ratification cannot be inherited
    across days without being re-checked against the sheet.
    """
    tabs = _tabs_from_sheet(catalogue_id)
    problems, meta = [], {}
    checks = [
        ("STAGE 0", lambda: stage_0_instantiated(tabs)),
        ("00_HARNESS", lambda: harness_checklist(tabs)),
        ("GATE 1", lambda: gate_1_architecture(tabs.get("00_README", []))),
    ]
    def keyed(rows):
        """gate_5 reads dict rows; a sheet tab arrives as lists. Key by header.
        (First live preflight reported GATE 5 'could not evaluate' for this.)"""
        if not rows:
            return []
        hdr = [str(h).strip() for h in rows[0]]
        return [dict(zip(hdr, r)) for r in rows[1:] if any(str(c).strip() for c in r)]
    for t in ("CHARTER", "MANIFEST", "PAGE_PLAN"):
        checks.append((f"GATE 5 {t}", lambda t=t: gate_5_ratified(keyed(tabs.get(t, [])), t)))
    for name, fn in checks:
        try:
            fn()
        except Refusal as e:
            problems.append(str(e))
        except Exception as e:
            problems.append(f"{name}: could not evaluate ({type(e).__name__}: {e})")
    kv = {str(r[0]).strip().lower(): (r[1].strip() if len(r) > 1 else "")
          for r in tabs.get("00_README", []) if r}
    meta = {"site_name": kv.get("site_name", ""), "isa_status": kv.get("isa_status", ""),
            "isa_doc_id": kv.get("isa_doc_id", ""), "tabs": sorted(tabs.keys())}
    verdict = "RATIFIED" if not problems else "REFUSED"
    stamp = write_stamp(catalogue_id, site_id, verdict, problems, meta)
    print(f"preflight : {verdict}   catalogue {catalogue_id}   site {site_id}")
    print(f"stamp     : {STAMP_PATH}  (valid {STAMP_MAX_AGE_H}h)")
    for p in problems:
        print(f"   - {p[:160]}")
    if problems:
        print("\nThe Site-build hook will refuse builds for this site until these are resolved\n"
              "in the catalogue and preflight is re-run. Ratification is a human act.")
    return stamp


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4 and sys.argv[1] == "preflight":
        st = preflight_stamp(sys.argv[2], sys.argv[3])
        sys.exit(0 if st["verdict"] == "RATIFIED" else 2)
    print(__doc__)
    print("Gates:", [n for n in dir() if n.startswith("gate_")])
    print("Guards:", [n for n in dir() if n.startswith("guard_")])
    print("\nusage: harness.py preflight <catalogue_sheet_id> <site_id>")
