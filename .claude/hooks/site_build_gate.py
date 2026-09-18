#!/usr/bin/env python3
"""PreToolUse hook -- the deterministic layer for Google Sites builds.

Stdlib only. Fast. Offline. Fires on every Bash call whether or not the agent
chose to call the harness -- which is the whole point. A skill is advisory;
harness.py only runs if the code calls it. This runs regardless.

WHAT IT ENFORCES, and the failure behind each:

  USE THE DOOR.   Any command that reaches the Sites editor must go through the
                  sanctioned entry point (build_from_wireframe.py / run_wireframe.py),
                  which enforces the Landing Rule and asserts the page id. Inline
                  scripts that import sites_automation and type literal strings
                  are refused. Failure: 2026-09-07, an agent placed "Placement
                  Test" blocks by hand -- harmless that day, and exactly the path
                  by which content that is not a cell reaches a page.
  RATIFIED FIRST. The door opens only on a fresh preflight stamp (harness.py
                  preflight) that says RATIFIED. Failure: build proposed twice
                  before the first client ISA existed.
  NO BLIND DELETE. clear_page outside the door is refused. Failure: 2026-08-31,
                  clear_page ran on the wrong page and destroyed a finished Home.
  PUBLISH ASKS.   Publishing is outward-facing; the human confirms.
  WAIVERS ARE HUMAN ACTS. A waiver file with waived_by, site_id, expires and
                  reason permits builds on that one site. Every use is logged.
  EVERY DECISION IS LOGGED to ~/.advisor_os/hook_log.jsonl.

WHAT IT CANNOT SEE: the DOM. It reads the command text. Read-only probes
(probe_controls, whoami, list_pages...) are allowed so diagnosis stays
possible; anything that can mutate the editor -- including eval_js -- counts as
a write and must go through the door or carry a waiver.
"""
import glob
import hashlib
import json
import os
import re
import sys
import time

HOME = os.environ.get("ADVISOR_OS_HOME", os.path.expanduser("~/.advisor_os"))
STAMP = os.path.join(HOME, "preflight.json")
LOG = os.path.join(HOME, "hook_log.jsonl")
WAIVERS = os.path.join(HOME, "waivers")
STAMP_MAX_AGE_S = 12 * 3600

# A command can only reach the editor if it EXECUTES something. cat/tee/cp/git
# writing a file that merely mentions these modules cannot. Found on the first
# live run: a docs edit whose heredoc mentioned build_from_wireframe.py was
# refused, and so was the Bash call that tried to fix this hook -- which is why
# the fix went in through the Edit tool. The rule that fell out of it: edit
# files with Edit/Write; run things with Bash. The hook matches only Bash.
# The path token may not begin with a quote or backtick: a documentation line
# that starts `build_from_wireframe.py` is a mention, not a call.
_B = r"(?:^|&&|\|\||;|\|)\s*(?:[^\s`'\"]*python[0-9.]*\s+(?:-[a-zA-Z]+\s+)?)?[^\s`'\"]*"
EXECUTES = re.compile(r"(\bpython[0-9.]*\b|" + _B + r"\.py\b|\bbash\s+\S+\.sh|\bsh\s+\S+\.sh|\bnode\b)", re.M)
DOOR = re.compile(_B + r"(build_from_wireframe|run_wireframe)\.py\b", re.M)
_MODS = r"(sites_automation|wireframe_build|build_page|build_blocks|chrome_automation)"
# An import IN CODE CONTEXT: followed by `as`, `import`, `;`, `,`, `)` or end of
# line. Prose reads "import sites_automation is refused" -- code never does.
# (Second live run: tightening to line-start imports let the one-liner form
# `python3 -c "import sites_automation as S; ..."` straight through.)
SITES_TOUCH = re.compile(
    r"\b(?:import|from)\s+" + _MODS + r"\b\s*(?:as\b|import\b|;|,|\)|$)"
    r"|" + _B + r"(sites_automation|wireframe_build|build_page|build_blocks|build_from_wireframe|run_wireframe|"
    r"catalog_site|extract_site_template|capture_page_images)\.py\b"
    r"|(attach|open_tab|open_editor)\([^)]*sites\.google\.com", re.M)
# Catch-all, whatever the syntax: an executing command that names a site module
# AND a write token is a write.
LOOSE_TOUCH = re.compile(_MODS)
# The allowlist trusts these FILES, not the command that names them. Each is
# read-only by construction and lives in git where a change shows up in review.
# site_survey.py added 2026-09-08: Stage 1 of any build is "look before you
# touch", and nothing offered a way to do that -- catalog_site and
# extract_site_template are libraries with no entry point, so the only route was
# an inline probe, which this hook refuses (correctly, since it cannot tell a
# probe from a write). site_survey self-checks that it calls no mutator.
READ_ONLY_TOOLS = re.compile(
    _B + r"(catalog_site|extract_site_template|capture_page_images|site_survey|harness)\.py\b", re.M)
DESTRUCTIVE = re.compile(r"(clear_page|delete_page|remove_section)", re.I)
PUBLISH = re.compile(r"(\bpublish\s*\(|S\.publish|\"Publish\"|'Publish')")
WRITE_TOKENS = re.compile(
    r"(insert_layout|insert_menu|type_chars|fill_index|fill_layout|fill_next_empty|build_section|"
    r"build_block|click_control|click_at|double_click_at|drag\(|press_enter|select_all|"
    r"create_site|create_page|rename_site|eval_js|send_ws_cmd|Input\.|DOM\.setFileInputFiles|"
    r"setInterceptFileChooser)", re.I)
SITE_ID = re.compile(r"\b(1[A-Za-z0-9_-]{25,60})\b")


def log(decision, reason, cmd, extra=None):
    try:
        os.makedirs(HOME, exist_ok=True)
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "decision": decision,
               "reason": reason[:200], "cmd_sha": hashlib.sha256(cmd.encode()).hexdigest()[:12],
               "cmd_head": cmd.strip().splitlines()[0][:100] if cmd.strip() else ""}
        if extra:
            rec.update(extra)
        with open(LOG, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
    except Exception:
        pass


def allow(reason, cmd, extra=None):
    log("ALLOW", reason, cmd, extra)
    sys.exit(0)


def ask(reason, cmd):
    log("ASK", reason, cmd)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": "ask",
                                             "permissionDecisionReason": reason}}))
    sys.exit(0)


def block(reason, cmd, extra=None):
    log("BLOCK", reason, cmd, extra)
    sys.stderr.write("SITE BUILD GATE -- refused.\n" + reason + "\n")
    sys.exit(2)


def stamp():
    try:
        s = json.load(open(STAMP))
        s["age_s"] = int(time.time()) - int(s.get("epoch", 0))
        return s
    except Exception:
        return None


def waiver_for(cmd):
    """A human-written waiver for a NAMED site mentioned in the command."""
    ids = set(SITE_ID.findall(cmd))
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    for p in sorted(glob.glob(os.path.join(WAIVERS, "*.json"))):
        try:
            w = json.load(open(p))
        except Exception:
            continue
        if not str(w.get("waived_by", "")).strip() or not str(w.get("reason", "")).strip():
            continue
        if str(w.get("expires", "")) < now:
            continue
        if w.get("site_id") in ids:
            return w, p
    return None, None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if data.get("tool_name") != "Bash":
        sys.exit(0)
    cmd = str((data.get("tool_input") or {}).get("command", ""))
    if not EXECUTES.search(cmd):
        sys.exit(0)                                   # cannot run code; cannot reach the editor
    if not SITES_TOUCH.search(cmd) and not (
            LOOSE_TOUCH.search(cmd) and (WRITE_TOKENS.search(cmd) or DESTRUCTIVE.search(cmd)
                                         or PUBLISH.search(cmd))):
        sys.exit(0)                                   # not our business; stay silent and fast

    if PUBLISH.search(cmd):
        ask("Publishing a Google Site is outward-facing. Confirm this publish.", cmd)

    if DOOR.search(cmd):
        st = stamp()
        if not st:
            block("No preflight stamp. Run:\n"
                  "  harness.py preflight <catalogue_sheet_id> <site_id>\n"
                  "It reads the catalogue, applies STAGE 0 / 00_HARNESS / GATE 1 / GATE 5, and leaves a stamp.\n"
                  "Ratification is a human act recorded in the catalogue; this hook only checks it was done.", cmd)
        if st.get("verdict") != "RATIFIED":
            block(f"Preflight stamp says {st.get('verdict')} for site {st.get('site_id')}:\n  - " +
                  "\n  - ".join(str(p)[:140] for p in st.get("problems", [])[:6]) +
                  "\nResolve these in the catalogue, then re-run preflight.", cmd)
        if st["age_s"] > STAMP_MAX_AGE_S:
            block(f"Preflight stamp is {st['age_s']//3600}h old (limit {STAMP_MAX_AGE_S//3600}h). "
                  "Re-run harness.py preflight so ratification is re-checked against the sheet.", cmd)
        ids = set(SITE_ID.findall(cmd))
        if ids and st.get("site_id") not in ids:
            block(f"Preflight stamp is for site {st.get('site_id')}, but this command names "
                  f"{sorted(ids)}. One stamp, one site. Re-run preflight for this site.", cmd)
        allow("door + fresh RATIFIED stamp", cmd, {"site_id": st.get("site_id")})

    if READ_ONLY_TOOLS.search(cmd) and not WRITE_TOKENS.search(cmd):
        allow("read-only tool", cmd)

    w, wp = waiver_for(cmd)
    if w:
        if DESTRUCTIVE.search(cmd):
            block("clear_page / delete outside the door is refused even under a waiver. "
                  "Destructive steps must assert their target (GUARD 1); only the door does that.", cmd)
        allow("WAIVED by human", cmd, {"waived_by": w["waived_by"], "site_id": w["site_id"],
                                      "reason": w["reason"][:120], "waiver": os.path.basename(wp)})

    if DESTRUCTIVE.search(cmd):
        block("clear_page / delete outside the sanctioned build path. This destroyed a finished Home "
              "page on 2026-08-31 when a page click silently missed. Use build_from_wireframe.py, "
              "which asserts the page id from the URL before anything is cleared.", cmd)

    if WRITE_TOKENS.search(cmd):
        block("This command can write to a Google Site outside the sanctioned build path.\n"
              "THE LANDING RULE: information lands in the sheet before it lands on the page. "
              "Content typed from a script is content that is not a cell.\n"
              "Use build_from_wireframe.py (reads PAGE_WIREFRAME; enforces GATE 2; asserts the page id), "
              "after harness.py preflight.\n"
              "For scratch testing on a named site, a human may place a waiver at\n"
              f"  {WAIVERS}/<name>.json  with waived_by, site_id, expires, reason.", cmd)

    allow("read-only probe (no write tokens)", cmd)


if __name__ == "__main__":
    main()
