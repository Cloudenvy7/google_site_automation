#!/usr/bin/env python3
"""Export a Claude Code session transcript to readable markdown.

WHY THIS EXISTS
A dead session was rebuilt by hand -- copying the visible conversation into a
Google Doc -- twice, so a fresh session could check what the work claimed against
what was built. The transcript was on disk the whole time, and holds more than was
ever on screen: the tool results, and sometimes the thinking.

The reason not to just `cat` the file: a single session here is 15 MB, roughly
4 million tokens. It does not fit in any context window. Copying only what was
visible was, accidentally, the right filter. This makes that filter explicit and
gives you the layers underneath it.

RESOLVING A SESSION
The id in a claude.ai/code/session_XXXX link is NOT stored as a field. It shows
up only in `cwd` and `gitBranch`, because a worktree session is named after it.
About half of these sessions are not worktree sessions, so that lookup cannot be
the only one. Order tried:

  1. an explicit path
  2. a session UUID (filename, or the `sessionId` field)
  3. a link id, matched against directory / cwd / gitBranch
  4. failing those -- list candidates and let the human choose

It never guesses between two matches. Picking the wrong transcript and saying
nothing is worse than asking.
"""

import argparse
import glob
import json
import os
import re
import sys

PROJECTS = os.path.expanduser("~/.claude/projects")

# Who the human is, for the speaker label. Hardcoding a name is how a tool built
# on one machine announces that it was built on one machine -- the same defect
# this repo spent 2026-09-13 removing from seven other files.
USER_LABEL = os.environ.get("SESSION_EXPORT_USER") or os.environ.get("USER") or "User"

LEVELS = ("talk", "tools", "thinking", "full")

# User-role records that are machinery, not the human speaking. A compaction
# summary is injected in the user role and reads exactly like something they
# typed -- which is why this filter exists and why it matters.
NOISE = ("[SYSTEM", "<local-command", "<task-notification", "<command-name",
         "<system-reminder", "Caveat:")


def sessions():
    """Every transcript on this machine, with enough metadata to choose by."""
    out = []
    for f in glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")):
        meta = {"path": f, "title": None, "first": None, "last": None,
                "cwd": None, "branch": None, "turns": 0,
                "size": os.path.getsize(f)}
        try:
            for line in open(f, errors="replace"):
                if '"aiTitle"' in line and not meta["title"]:
                    try: meta["title"] = json.loads(line).get("aiTitle")
                    except Exception: pass
                    continue
                try: d = json.loads(line)
                except Exception: continue
                ts = d.get("timestamp")
                if ts:
                    meta["first"] = meta["first"] or ts
                    meta["last"] = ts
                meta["cwd"] = meta["cwd"] or d.get("cwd")
                meta["branch"] = meta["branch"] or d.get("gitBranch")
                if d.get("type") in ("user", "assistant"):
                    meta["turns"] += 1
        except OSError:
            continue
        out.append(meta)
    out.sort(key=lambda m: m["last"] or "", reverse=True)
    return out


def resolve(token):
    """Return (matches, how). Never collapses an ambiguous result to one."""
    if token and os.path.exists(token):
        return [{"path": token}], "path"

    all_s = sessions()

    # A UUID -- the filename, or the sessionId field.
    m = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                  token or "", re.I)
    if m:
        u = m.group(0).lower()
        hit = [s for s in all_s if u in os.path.basename(s["path"]).lower()]
        if hit:
            return hit, "uuid"

    # A link id: session_01ABC..., or the bare id.
    m = re.search(r"(?:session[_-])?([0-9A-Za-z]{20,30})", token or "")
    if m:
        sid = m.group(1)
        hit = [s for s in all_s
               if sid in s["path"] or sid in (s["cwd"] or "")
               or sid in (s["branch"] or "")]
        if hit:
            return hit, "link id"

    return [], "unresolved"


DEFAULT_OUT_DIR = os.path.expanduser("~/.advisor_os/session_exports")


def _in_git_repo(path):
    """Walk up looking for .git. Cheap, no subprocess, works on a bare path."""
    d = os.path.dirname(os.path.abspath(path)) or os.getcwd()
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def resolve_out(out):
    """Where to write, defaulting OUTSIDE any repository.

    A transcript holds whatever was discussed -- client names, financials, folder
    ids. The client agreed to Google when they put their files in Drive; they
    never agreed to GitHub. So the default lands in ~/.advisor_os/, and aiming at
    a working tree gets a warning rather than silence.

    It warns rather than refuses: there are legitimate reasons to write into a
    repo that gitignores the path. Silence is the thing worth preventing.
    """
    if not out:
        return None
    if not os.path.dirname(out):
        os.makedirs(DEFAULT_OUT_DIR, exist_ok=True)
        return os.path.join(DEFAULT_OUT_DIR, out)
    repo = _in_git_repo(out)
    if repo:
        sys.stderr.write(
            "\n  !! WARNING: writing into a git working tree:\n"
            "     %s\n"
            "     Transcripts and ledgers must not be committed -- they carry\n"
            "     whatever was discussed. Confirm .gitignore covers this path,\n"
            "     or pass a bare filename to use %s\n\n"
            % (repo, DEFAULT_OUT_DIR))
    return out


def blocks(msg):
    c = msg.get("content")
    if isinstance(c, str):
        return [{"type": "text", "text": c}]
    return [b for b in (c or []) if isinstance(b, dict)]


def render(path, level, subagents=False, result_chars=800):
    lines, stats = [], {"user": 0, "assistant": 0, "tools": 0, "thinking": 0,
                        "thinking_redacted": 0}
    title = None
    for raw in open(path, errors="replace"):
        try: d = json.loads(raw)
        except Exception: continue
        if d.get("type") == "ai-title" and not title:
            title = d.get("aiTitle")
        if d.get("type") not in ("user", "assistant"):
            continue
        msg = d.get("message")
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        ts = (d.get("timestamp") or "")[:19].replace("T", " ")

        for b in blocks(msg):
            t = b.get("type")

            if t == "text":
                txt = (b.get("text") or "").strip()
                if not txt:
                    continue
                if role == "user":
                    if any(txt.startswith(n) for n in NOISE):
                        continue
                    stats["user"] += 1
                    lines.append(f"\n---\n\n### 🧑 {USER_LABEL} · {ts}\n\n{txt}\n")
                else:
                    stats["assistant"] += 1
                    lines.append(f"\n### 🤖 Claude · {ts}\n\n{txt}\n")

            elif t == "thinking" and level in ("thinking", "full"):
                # Not every session stores the thinking text. Where it is absent
                # the block survives as a signature with an empty body -- so it
                # must be counted as redacted, not as recovered. Counting it as
                # recovered is how an export claims to hold reasoning it does not.
                th = (b.get("thinking") or "").strip()
                if th:
                    stats["thinking"] += 1
                    lines.append(f"\n<details><summary>💭 thinking · {ts}</summary>\n\n```\n{th}\n```\n\n</details>\n")
                else:
                    stats["thinking_redacted"] += 1

            elif t == "tool_use" and level in ("tools", "thinking", "full"):
                stats["tools"] += 1
                args = json.dumps(b.get("input", {}), indent=1)
                if level != "full" and len(args) > result_chars:
                    args = args[:result_chars] + f"\n... [{len(args) - result_chars} more chars]"
                lines.append(f"\n**🔧 {b.get('name','?')}**\n\n```json\n{args}\n```\n")

            elif t == "tool_result" and level in ("tools", "thinking", "full"):
                c = b.get("content")
                s = c if isinstance(c, str) else json.dumps(c, indent=1)
                s = (s or "").strip()
                if not s:
                    continue
                if level != "full" and len(s) > result_chars:
                    s = s[:result_chars] + f"\n... [{len(s) - result_chars} more chars — use --level full]"
                lines.append(f"\n<details><summary>↩️ result</summary>\n\n```\n{s}\n```\n\n</details>\n")

    head = [f"# {title or os.path.basename(path)}",
            "",
            f"- **Source:** `{path}`",
            f"- **Level:** `{level}`",
            f"- **Turns:** {stats['user']} from {USER_LABEL}, {stats['assistant']} from Claude",
            f"- **Tool calls rendered:** {stats['tools']}   **Thinking blocks:** {stats['thinking']}",
            (f"- **⚠️ {stats['thinking_redacted']} thinking blocks carry no text** in this"
             f" session and cannot be recovered — only a signature was stored."
             if stats["thinking_redacted"] else ""),
            "",
            "> Exported from the local Claude Code transcript. At levels other than",
            "> `full`, tool arguments and results are truncated — the marker says by",
            "> how much. Nothing else is dropped or summarised.",
            ""]

    if subagents:
        sub = os.path.join(os.path.dirname(path),
                           os.path.basename(path)[:-6], "subagents", "*.jsonl")
        found = sorted(glob.glob(sub))
        if found:
            lines.append(f"\n\n---\n\n# Subagent transcripts ({len(found)})\n")
            for s in found:
                lines.append(f"\n## `{os.path.basename(s)}`\n")
                lines.append(render(s, level, subagents=False, result_chars=result_chars)[0])

    return "\n".join(head + lines), stats


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("session", nargs="?", help="link, session id, uuid, or path")
    ap.add_argument("--level", default="tools", choices=LEVELS,
                    help="talk | tools (default) | thinking | full")
    ap.add_argument("--out", help="write here instead of stdout")
    ap.add_argument("--subagents", action="store_true", help="append subagent transcripts")
    ap.add_argument("--list", action="store_true", help="list sessions and stop")
    ap.add_argument("--all", action="store_true",
                    help="if the token matches several, export them all, oldest first")
    ap.add_argument("--result-chars", type=int, default=800)
    a = ap.parse_args()
    a.out = resolve_out(a.out)   # every write path, not just the first

    if a.list or not a.session:
        rows = sessions()
        print(f"{len(rows)} sessions under {PROJECTS}\n")
        for s in rows:
            print(f"  {(s['last'] or '?')[:10]}  {s['size']/1e6:6.1f} MB  {s['turns']:4d} turns  "
                  f"{(s['title'] or '(untitled)')[:52]}")
            print(f"      {s['path']}")
        if not a.session:
            print("\nGive a link, a session id, a uuid, or a path.")
        return 0

    matches, how = resolve(a.session)
    if not matches:
        print(f"Could not resolve {a.session!r}.\n"
              f"A claude.ai/code link id only appears in a worktree session's path, so\n"
              f"about half of these will not match one. Run with --list and pick.",
              file=sys.stderr)
        return 2
    if len(matches) > 1 and a.all:
        matches.sort(key=lambda m: m.get("first") or "")
        parts, tot = [], {"user": 0, "assistant": 0, "tools": 0, "thinking": 0,
                          "thinking_redacted": 0}
        for mt in matches:
            md, st = render(mt["path"], a.level, a.subagents, a.result_chars)
            parts.append(md)
            for k in tot: tot[k] += st.get(k, 0)
        md = ("\n\n\n---\n\n"
              f"*{len(matches)} transcripts matched via {how}, concatenated oldest first.*\n\n---\n\n"
              ).join(parts)
        stats = tot
        path = f"{len(matches)} transcripts"
        if a.out:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            open(a.out, "w").write(md)
            print(f"Wrote {a.out}  ({len(md)/1000:.0f} KB, ~{len(md)//4000}k tokens)\n"
                  f"  {path} via {how}\n"
                  f"  {stats['user']} {USER_LABEL} / {stats['assistant']} Claude turns, "
                  f"{stats['tools']} tool calls, {stats['thinking']} thinking blocks")
        else:
            sys.stdout.write(md)
        return 0
    if len(matches) > 1:
        print(f"{a.session!r} matches {len(matches)} transcripts via {how}. "
              f"Choose one and pass its path, or re-run with --all:\n", file=sys.stderr)
        for s in matches:
            print(f"  {(s.get('last') or '?')[:10]}  {(s.get('title') or '(untitled)')[:50]}\n"
                  f"      {s['path']}", file=sys.stderr)
        return 3

    path = matches[0]["path"]
    md, stats = render(path, a.level, a.subagents, a.result_chars)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, "w").write(md)
        print(f"Wrote {a.out}  ({len(md)/1000:.0f} KB, ~{len(md)//4000}k tokens)\n"
              f"  resolved via {how}: {path}\n"
              f"  {stats['user']} {USER_LABEL} / {stats['assistant']} Claude turns, "
              f"{stats['tools']} tool calls, {stats['thinking']} thinking blocks")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
