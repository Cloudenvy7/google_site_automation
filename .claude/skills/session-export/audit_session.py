#!/usr/bin/env python3
"""Build an AUDIT LEDGER from a session transcript: what was promised, what was
claimed done, and what evidence sat underneath the claim.

WHAT THIS IS NOT
It is not a verdict and it is not an eval. It has no expected answer. It is a
shortlist with the evidence attached, for a human or a fresh session to judge
against the artifacts. Treating it as the record of what happened rebuilds the
exact problem it exists to catch -- a summary written by the thing being audited.

**The ledger is the claim. git, the files, the Sheet and the Site are the truth.**
Every check runs ledger -> reality, never the other way.

THE FAILURE THAT PRODUCED IT (2026-09-08, found 2026-09-13)
A session said, at 11:21 UTC, "Both repos clean and pushed, everything green.
Yes -- we're done." That was TRUE when written. Work then resumed five hours
later and produced four commits -- 8505b45, c2291f7, ac6553a, 770f586 -- none of
which were pushed. 991 lines sat on a disposable worktree branch for five days.

Nobody lied. The claim EXPIRED, and nothing re-checked it. So the first and most
important section of this ledger is mechanical and needs no model at all:
everything that happened after the last completion claim is work no summary
covers.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from export_session import resolve, blocks, NOISE   # noqa: E402

INTENT = re.compile(
    r"\b(I'?ll |I am going to |I'm going to |Let me |Next,? I|"
    r"going to (?:add|build|write|fix|run|push|create|verify))", re.I)
DONE = re.compile(
    r"\b(done|pushed|committed|fixed|verified|confirmed|landed|"
    r"complete[d]?|shipped|all pass|green)\b", re.I)
BLOCKED = re.compile(
    r"\b(could ?n'?t|cannot|can'?t|blocked|failed|not working|refused|"
    r"still (?:open|broken|outstanding|does ?n'?t)|did ?n'?t|stopped|unable)\b", re.I)

# Tool calls that change something. Everything else is a read.
# Claims that assert the whole working state is settled -- as opposed to a claim
# about one artifact. Only these can EXPIRE, because only these are invalidated by
# any later work. Narrow deliberately: the first version of this check used "the
# last claim of any kind" and missed the very failure it was written for, because
# the last claim in that session was "9 files, verified as real images" -- true,
# local, and not a statement about the repo at all.
SETTLED = re.compile(
    r"(both repos?[^.]{0,40}(pushed|clean)|"
    r"(everything|all)[^.]{0,30}(pushed|committed|green|clean|done)|"
    r"we'?re done|all (?:pushed|committed|clean)|"
    r"nothing (?:is )?(?:unpushed|uncommitted)|repos? clean)", re.I)

MUTATING = {"Write", "Edit", "NotebookEdit", "MultiEdit"}
# The two that decide whether work left the machine.
GIT_COMMIT = re.compile(r"\bgit\s+(?:-[^\s]+\s+)*commit\b", re.I)
GIT_PUSH = re.compile(r"\bgit\s+(?:-[^\s]+\s+)*push\b", re.I)
WRITE_BASH = re.compile(
    r"\b(git\s+(commit|push|merge|rebase|reset|mv|rm)|>\s*\S|>>\s*\S|"
    r"\bmv\b|\brm\b|\bcp\b|\btee\b|\bmkdir\b|pip install)", re.I)


def sentences(text):
    for s in re.split(r'(?<=[.!?])\s+|\n', text or ""):
        s = s.strip()
        if 12 < len(s) < 260:
            yield s


def harvest(path):
    """One pass. Every record keeps its index so the ledger can cite position."""
    events = []
    for i, raw in enumerate(open(path, errors="replace")):
        try:
            d = json.loads(raw)
        except Exception:
            continue
        if d.get("type") not in ("user", "assistant"):
            continue
        msg = d.get("message")
        if not isinstance(msg, dict):
            continue
        role, ts = msg.get("role"), (d.get("timestamp") or "")[:19]
        for b in blocks(msg):
            t = b.get("type")
            if t == "text":
                txt = (b.get("text") or "").strip()
                if not txt:
                    continue
                if role == "user":
                    if any(txt.startswith(n) for n in NOISE):
                        continue
                    events.append({"i": i, "ts": ts, "kind": "ask", "text": txt})
                else:
                    for s in sentences(txt):
                        if INTENT.search(s):
                            k = "intent"
                        elif DONE.search(s):
                            k = "claim"
                        elif BLOCKED.search(s):
                            k = "blocked"
                        else:
                            continue
                        events.append({"i": i, "ts": ts, "kind": k, "text": s})
            elif t == "tool_use":
                name = b.get("name", "?")
                inp = b.get("input") or {}
                cmd = str(inp.get("command", ""))
                mutating = name in MUTATING or bool(WRITE_BASH.search(cmd))
                target = inp.get("file_path") or inp.get("path") or (cmd[:160] if cmd else "")
                events.append({"i": i, "ts": ts, "kind": "tool", "name": name,
                               "text": str(target), "mutating": mutating,
                               "commit": bool(GIT_COMMIT.search(cmd)),
                               "push": bool(GIT_PUSH.search(cmd)),
                               "cmd": cmd})
            elif t == "tool_result":
                c = b.get("content")
                s = c if isinstance(c, str) else json.dumps(c)
                events.append({"i": i, "ts": ts, "kind": "result",
                               "text": (s or "")[:400]})
    return events


def build(path, evidence_chars=400):
    ev = harvest(path)
    claims = [e for e in ev if e["kind"] == "claim"]
    intents = [e for e in ev if e["kind"] == "intent"]
    blocked = [e for e in ev if e["kind"] == "blocked"]
    tools = [e for e in ev if e["kind"] == "tool"]
    mut = [e for e in tools if e.get("mutating")]

    out = ["# Audit ledger", "",
           f"- **Source:** `{path}`",
           f"- **Span:** {ev[0]['ts'] if ev else '?'} → {ev[-1]['ts'] if ev else '?'} (UTC)",
           f"- **Intents:** {len(intents)}  **Completion claims:** {len(claims)}  "
           f"**Blocked/failed:** {len(blocked)}",
           f"- **Tool calls:** {len(tools)} ({len(mut)} mutating)",
           "",
           "> This ledger records what the session **claimed**. It is not the record",
           "> of what happened. Check every line against git, the files, the Sheet and",
           "> the Site — ledger → reality, never the reverse.",
           ""]

    # ---- 1. The mechanical check. No model needed. This is the eval candidate.
    commits = [e for e in tools if e.get("commit")]
    pushes = [e for e in tools if e.get("push")]
    settled = [c for c in claims if SETTLED.search(c["text"])]

    out += ["---", "", "## 1. Did the work leave the machine?",
            "", "*Mechanical, and the only section that needs no judgement. A "
            "settlement claim is falsified by any commit after it that was never "
            "pushed. The claim is usually true when written — nothing re-checks it.*",
            "",
            f"Session totals: **{len(commits)} commits**, **{len(pushes)} pushes**.", ""]

    if commits:
        last_push_i = max([p["i"] for p in pushes], default=-1)
        stranded = [c for c in commits if c["i"] > last_push_i]
        if stranded:
            out += [f"### ⚠️ {len(stranded)} commits after the last push",
                    "", "These never left the machine during this session.", "",
                    "| Time | Commit command |", "|---|---|"]
            for e in stranded:
                c = re.sub(r"\s+", " ", e["cmd"])[:150].replace("|", "\\|")
                out.append(f"| {e['ts'][11:]} | `{c}` |")
            out += ["", "**Verify:** `git log --oneline --all --not --remotes`", ""]
        else:
            out += ["✅ Every commit was followed by a push.", ""]

    if not settled:
        out += ["*No claim asserted the whole state was settled.*", ""]
    for c in settled:
        after_c = [e for e in commits if e["i"] > c["i"]]
        after_p = [e for e in pushes if e["i"] > c["i"]]
        other = len([e for e in mut if e["i"] > c["i"]]) - len(after_c) - len(after_p)
        out += [f"**Claim — `{c['ts']}`**", "", f"> {c['text']}", ""]
        if after_c and not after_p:
            out += [f"⚠️ **{len(after_c)} commits and 0 pushes after this claim.** "
                    f"It was true when written; it is false now.", ""]
        elif after_c:
            out += [f"{len(after_c)} commits and {len(after_p)} pushes after this "
                    f"claim — check the last commit is on the remote.", ""]
        elif other > 0:
            out += [f"{other} other mutating actions after this claim, no commits. "
                    f"Check for uncommitted work.", ""]
        else:
            out += ["✅ Nothing changed after it.", ""]

    # ---- 2. Claims with their evidence
    out += ["---", "", "## 2. Completion claims, with the evidence under each",
            "", "*A claim whose turn contains no tool result rests on nothing "
            "but assertion.*", ""]
    for n, c in enumerate(claims, 1):
        near = [e for e in ev if e["kind"] == "result" and c["i"] - 2 <= e["i"] <= c["i"] + 2]
        tcalls = [e for e in tools if c["i"] - 2 <= e["i"] <= c["i"] + 2]
        flag = "" if near else "  ⚠️ **no tool result in this turn — unverified assertion**"
        out += [f"**{n}. `{c['ts']}`**{flag}", "", f"> {c['text']}", ""]
        if tcalls:
            out.append("Tools in the same turn: " +
                       ", ".join(f"`{t['name']}`" for t in tcalls[:6]))
            out.append("")
        if near:
            s = near[0]["text"][:evidence_chars].strip()
            out += ["<details><summary>evidence</summary>", "",
                    "```", s, "```", "", "</details>", ""]

    # ---- 3. Intents with no later claim
    out += ["---", "", "## 3. Intents with no later completion claim", "",
            "*Stated, then never reported on. Some resolved silently; each needs "
            "checking against the artifact.*", ""]
    orphans = []
    for it in intents:
        later = [c for c in claims if c["i"] > it["i"] and c["i"] - it["i"] < 40]
        if not later:
            orphans.append(it)
    if orphans:
        for o in orphans:
            out.append(f"- `{o['ts'][11:]}` {o['text'][:190]}")
    else:
        out.append("Every intent has a later completion claim.")
    out.append("")

    # ---- 4. Stated limits
    out += ["---", "", "## 4. Stated failures, blocks and limits", "",
            "*These are the honest ones. Confirm each is still true or now fixed.*", ""]
    for b in blocked[:60]:
        out.append(f"- `{b['ts'][11:]}` {b['text'][:190]}")
    if len(blocked) > 60:
        out.append(f"- *… {len(blocked) - 60} more*")
    out.append("")

    # ---- 5. What to run
    out += ["---", "", "## 5. Verification — run these against reality", "",
            "The ledger cannot answer any of these. Only the artifacts can.", "",
            "```bash",
            "git log --oneline --all --not --remotes   # anything unpushed?",
            "git status --short                        # anything uncommitted?",
            "bash evals/run.sh                         # does the suite still pass?",
            "```", "",
            "Then, per claim in §1 and §2: does the file exist, is the commit on the",
            "remote, does the Site or Sheet actually hold what was claimed?", "",
            "**Anything that can be turned into a deterministic check should be.**",
            "An audit finds it once; a check catches it forever.", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("session", help="link, session id, uuid, or path")
    ap.add_argument("--out")
    ap.add_argument("--evidence-chars", type=int, default=400)
    a = ap.parse_args()

    matches, how = resolve(a.session)
    if not matches:
        print(f"Could not resolve {a.session!r}. Try --list on export_session.py.",
              file=sys.stderr)
        return 2
    if len(matches) > 1:
        print(f"{a.session!r} matches {len(matches)}. Pass one path:", file=sys.stderr)
        for s in matches:
            print("  " + s["path"], file=sys.stderr)
        return 3

    md = build(matches[0]["path"], a.evidence_chars)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, "w").write(md)
        print(f"Wrote {a.out} ({len(md)/1000:.0f} KB)  via {how}")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
