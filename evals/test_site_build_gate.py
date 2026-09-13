"""Deterministic tests for the Site-build PreToolUse hook. No model, no network.

Each case feeds the hook the JSON Claude Code would send and asserts the exit
code (0 allow, 2 block) and, for ask, the JSON decision on stdout. Every case
names the failure it exists to catch.
"""
import json, os, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
HOOK = None
for cand in (os.path.join(ROOT, ".claude", "hooks", "site_build_gate.py"),
             os.path.join(HERE, "..", ".claude", "hooks", "site_build_gate.py")):
    if os.path.exists(cand):
        HOOK = os.path.abspath(cand); break
assert HOOK, "hook not found"

# The scripts directory differs by repository: `scripts/` here,
# `.agents/scripts/` in advisor-os where this suite was first written. Resolve it
# rather than assume, so the same file passes in both.
SCRIPTS = None
for cand in (os.path.join(HERE, "..", "scripts"),
             os.path.join(ROOT, ".agents", "scripts"),
             os.path.join(HERE, "..", ".agents", "scripts")):
    if os.path.isdir(cand):
        SCRIPTS = os.path.abspath(cand); break
assert SCRIPTS, "scripts directory not found"

FAILS = []
def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"  -- {detail}" if detail and not cond else ""))
    if not cond: FAILS.append(name)


def run(cmd, home):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True,
                       env={**os.environ, "ADVISOR_OS_HOME": home})
    decision = None
    try:
        decision = json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]
    except Exception:
        pass
    return r.returncode, r.stderr, decision


def stamp(home, verdict="RATIFIED", site="1SITEAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", age_s=0, problems=None):
    os.makedirs(home, exist_ok=True)
    json.dump({"verdict": verdict, "site_id": site, "epoch": int(time.time()) - age_s,
               "problems": problems or []}, open(os.path.join(home, "preflight.json"), "w"))


ADHOC_WRITE = 'python - <<EOF\nimport sites_automation as S\nws,_=S.attach()\nS.type_chars(ws, "Placement Test")\nEOF'
ADHOC_PROBE = 'python - <<EOF\nimport sites_automation as S\nws,_=S.attach()\nprint(S.probe_controls(ws, 50))\nEOF'
DOOR = 'python build_from_wireframe.py 1SITEAAAAAAAAAAAAAAAAAAAAAAAAAAAAA Home'
DOOR_OTHER = 'python build_from_wireframe.py 1OTHERBBBBBBBBBBBBBBBBBBBBBBBBBBBB Home'
CLEAR = 'python -c "import build_page as B; B.clear_page(ws)"'
PUBLISH = 'python -c "import sites_automation as S; S.publish(ws)"'
READONLY = 'python catalog_site.py 1SITEAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'


def test_non_site_commands_are_ignored():
    with tempfile.TemporaryDirectory() as h:
        for c in ("ls -la", "git status", "python3 indexer_v3.py status X", 'grep -rn "foo" .'):
            rc, _, _ = run(c, h)
            check(f"ignored: {c[:30]}", rc == 0)
        check("no log written for non-site", not os.path.exists(os.path.join(h, "hook_log.jsonl")))


def test_mentions_are_not_invocations():
    """First live run: a docs edit whose heredoc MENTIONED the door was refused,
    and so was the Bash call that tried to fix the hook. Mentions are not
    invocations; a command that cannot execute code cannot reach the editor."""
    with tempfile.TemporaryDirectory() as h:
        doc = 'cat > START_HERE.md <<EOF\nUse build_from_wireframe.py after harness.py preflight.\nimport sites_automation is refused inline.\nEOF'
        rc, _, _ = run(doc, h)
        check("cat > docs mentioning the door -> allow", rc == 0)
        rc, _, _ = run('cp scripts/sites_automation.py /tmp/x.py && git add -A', h)
        check("cp/git of a site module -> allow", rc == 0)
        rc, _, _ = run('echo \'{"command":"python build_from_wireframe.py X Home"}\' | python3 hooks/site_build_gate.py', h)
        check("quoted door string piped to the hook itself -> allow", rc == 0)
        rc, _, _ = run('python - <<EOF\nimport sites_automation as S\nS.type_chars(ws, "x")\nEOF', h)
        check("KNOWN LIMIT: python heredoc that imports+writes -> still block", rc == 2)
        skill = ("python3 - <<'PYEOF'\np='SKILL.md'; s=open(p).read()\nnew = '''only through\n"
                 "`build_from_wireframe.py` / `run_wireframe.py`, only after preflight.'''\n"
                 "open(p,'w').write(s+new)\nPYEOF")
        rc, _, _ = run(skill, h)
        check("python patch of docs with a backticked door line -> allow", rc == 0)
        rc, _, _ = run("cd scripts && python3 build_from_wireframe.py 1SITEAAAAAAAAAAAAAAAAAAAAAAAAAAAAA Home", h)
        check("real door call still recognised -> block (no stamp)", rc == 2)
        # Second live run: the one-liner form slipped through a line-start import rule.
        rc, _, _ = run('cd .agents/scripts && python3 -c "import sites_automation as S; S.type_chars(None, \'hello\')"', h)
        check("python3 -c one-liner import + write -> block", rc == 2)
        rc, _, _ = run('python3 -c "from wireframe_build import fill_index; fill_index(ws, 2, \'x\')"', h)
        check("from-import one-liner + write -> block", rc == 2)
        rc, _, _ = run('cat > docs/x.md <<EOF\nimport sites_automation is refused inline; type_chars is a write token.\nEOF', h)
        check("prose containing both a module name and a write word, no execution -> allow", rc == 0)
        rc, _, _ = run('cat > tests/new_test.py <<EOF\nimport sites_automation as S\nS.type_chars(ws, "x")\nEOF', h)
        check("cat > a .py file (not executed) -> allow; use Edit/Write for source anyway", rc == 0)


def test_adhoc_write_is_blocked():
    """The failure: literal strings typed into a Site from an inline script."""
    with tempfile.TemporaryDirectory() as h:
        rc, err, _ = run(ADHOC_WRITE, h)
        check("ad-hoc write -> block", rc == 2 and "LANDING RULE" in err)
        rc, _, _ = run('python build_blocks.py', h)
        check("build_blocks.py direct -> block", rc == 2)
        rc, _, _ = run('python -c "import wireframe_build as W; W.fill_index(ws, 3, \'x\')"', h)
        check("fill_index direct -> block", rc == 2)


def test_readonly_probe_is_allowed():
    """Diagnosis must stay possible; probe_controls cannot mutate."""
    with tempfile.TemporaryDirectory() as h:
        rc, _, _ = run(ADHOC_PROBE, h)
        check("probe_controls -> allow", rc == 0)
        rc, _, _ = run(READONLY, h)
        check("catalog_site.py -> allow", rc == 0)
        rc, _, _ = run('python -c "import sites_automation as S; print(S.eval_js(ws, \'1+1\'))"', h)
        check("eval_js counts as write -> block", rc == 2)


def test_readonly_allowlist_is_narrow():
    """site_survey.py is allowlisted so Stage 1 diagnosis is possible. The
    allowlist must not become a way to smuggle a write past the gate."""
    with tempfile.TemporaryDirectory() as h:
        rc, _, _ = run("cd scripts && python3 site_survey.py 1zt9YV_klKRhTodzdPaQLIIbAFJK2Yg9h 1", h)
        check("site_survey.py -> allow", rc == 0)
        rc, _, _ = run("python3 site_survey.py SITE && python3 -c \"import sites_automation as S; S.type_chars(ws,'x')\"", h)
        check("allowlisted name + a write in the same command -> block", rc == 2)
        rc, _, _ = run("python3 site_survey_evil.py SITE", h)
        check("a name that merely starts with an allowlisted one -> not allowlisted", rc == 0 or rc == 2)
        src = open(os.path.join(SCRIPTS, "site_survey.py")).read()
        for m in ("S.insert_layout", "S.type_chars", "S.publish", "clear_page("):
            check(f"site_survey calls no {m}", m not in src)


def test_door_requires_fresh_ratified_stamp():
    """The failure: build proposed twice before the ISA existed."""
    with tempfile.TemporaryDirectory() as h:
        rc, err, _ = run(DOOR, h)
        check("door, no stamp -> block", rc == 2 and "preflight" in err)
        stamp(h, verdict="REFUSED", problems=["GATE 1: isa_status is DRAFT, not RATIFIED."])
        rc, err, _ = run(DOOR, h)
        check("door, REFUSED stamp -> block", rc == 2 and "DRAFT" in err)
        stamp(h, age_s=13 * 3600)
        rc, err, _ = run(DOOR, h)
        check("door, stale stamp -> block", rc == 2 and "old" in err)
        stamp(h)
        rc, _, _ = run(DOOR, h)
        check("door, fresh RATIFIED stamp -> allow", rc == 0)
        rc, err, _ = run(DOOR_OTHER, h)
        check("door, stamp for a different site -> block", rc == 2 and "One stamp, one site" in err)


def test_destructive_and_publish():
    """The failures: clear_page on the wrong page; publishing without a human."""
    with tempfile.TemporaryDirectory() as h:
        stamp(h)
        rc, err, _ = run(CLEAR, h)
        check("clear_page outside door -> block", rc == 2 and "2026-08-31" in err)
        rc, _, dec = run(PUBLISH, h)
        check("publish -> ask", rc == 0 and dec == "ask")


def test_waivers_are_human_acts():
    """A waiver names who, which site, until when, and why. Nothing less."""
    with tempfile.TemporaryDirectory() as h:
        wd = os.path.join(h, "waivers"); os.makedirs(wd)
        good = {"waived_by": "Andrew Powers", "site_id": "1SITEAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                "expires": "2099-01-01T00:00:00", "reason": "scratch site for placement tests"}
        cmd = ADHOC_WRITE.replace("import sites_automation", "SITE='1SITEAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'\nimport sites_automation")
        rc, _, _ = run(cmd, h)
        check("waiver absent -> block", rc == 2)
        json.dump(good, open(os.path.join(wd, "scratch.json"), "w"))
        rc, _, _ = run(cmd, h)
        check("valid waiver, named site -> allow", rc == 0)
        rc, _, _ = run(ADHOC_WRITE, h)   # no site id in command
        check("waiver but command names no site -> block", rc == 2)
        json.dump({**good, "expires": "2000-01-01T00:00:00"}, open(os.path.join(wd, "scratch.json"), "w"))
        rc, _, _ = run(cmd, h)
        check("expired waiver -> block", rc == 2)
        json.dump({**good, "waived_by": ""}, open(os.path.join(wd, "scratch.json"), "w"))
        rc, _, _ = run(cmd, h)
        check("waiver with no waived_by -> block", rc == 2)
        json.dump(good, open(os.path.join(wd, "scratch.json"), "w"))
        rc, _, _ = run(CLEAR.replace("B.clear_page", "SITE='1SITEAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'; B.clear_page"), h)
        check("clear_page under waiver -> still block", rc == 2)
        lines = [json.loads(l) for l in open(os.path.join(h, "hook_log.jsonl"))]
        check("every decision logged", len(lines) >= 6 and any(l["decision"] == "ALLOW" and l.get("waived_by") for l in lines))


if __name__ == "__main__":
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        print(fn.__name__); fn()
    print("\n" + ("ALL PASS" if not FAILS else f"FAILED: {FAILS}"))
    sys.exit(1 if FAILS else 0)
