"""Coverage is proven, not claimed. Pure Python; no Google, no browser.

WHY THIS EXISTS (2026-09-07)
The v3 verifier compared the agent's reported chars_read against a re-derived
extractor count -- but the packet had HANDED the agent that number. An agent
that read nothing could echo it and pass. The check proved the extractor was
deterministic; it proved nothing about reading. And the one v3 measurement on
record (3 files, 259,926 chars, 34,146 tokens) is roughly HALF the raw token
content of the text, which is consistent with a partial read that nobody could
have detected. Andrew: "need to make sure everything was read so that the
information system architect is making the decisions based on all the
information."

THE MOVE, same shape as v3's "state lives in the sheet": do not ask the model to
be disciplined; remove its opportunity to be otherwise, then MEASURE.

  1. CHUNK. Long text is split into fixed pieces small enough that a cheap
     model reads one whole without paging. The agent is never handed 245,000
     characters with "please page through it."
  2. MARK. A random token -- ⟦CHK:a3f9c1⟧ -- is planted every MARK_EVERY
     characters, regenerated per run. The agent must return every marker it
     encountered. It cannot guess them. Missing markers are an exact map of
     what went unread.
  3. REFUSE. GUARD 9 (harness.py) refuses to commit a row whose markers do not
     cover the file. Coverage becomes arithmetic in the orchestrator, computed
     from what the agent returned, never from what the agent claimed.

WHAT MARKERS DO NOT PROVE, stated so nobody oversells them: a marker proves the
text was IN the agent's context, not that it was comprehended. An agent allowed
to grep could harvest markers without reading. Two things close that:
  - The indexing agent runs with Read-only tools (no Grep, no Bash). Then the
    only way to see a marker is to read the chunk it sits in.
  - The canary eval (evals/canary_partial_read.py) plants a distinctive fact
    near the END of a long file and asserts it reaches the row. Markers prove
    presence; the canary proves comprehension. Both run.
"""

import json
import re
import secrets

CHUNK_CHARS = 12_000     # ~3k tokens. One Read call, no offset/limit games.
MARK_EVERY = 1_500       # ~8 markers per chunk; any unread stretch drops one.
MARK_RE = re.compile(r"⟦CHK:([0-9a-f]{6})⟧")

NO_TEXT_STATUSES = ("IMAGE_DOWNLOADED_VIEW_IT", "CANNOT_READ", "SHORTCUT",
                    "OPENED_NO_TEXT_LAYER", "ERROR")


def new_marker():
    return f"⟦CHK:{secrets.token_hex(3)}⟧"


def plant(text, chunk_chars=CHUNK_CHARS, mark_every=MARK_EVERY):
    """Split text into chunks and plant markers. Returns (chunks, expected).

    chunks   : list of {"i": n, "text": str, "markers": [..], "chars": int}
               where chars is the ORIGINAL character count of that slice.
    expected : the flat ordered list of every marker planted.

    Markers sit on their own line so they survive whitespace normalisation and
    so a reader sees them as scaffolding, not content. Every chunk gets at
    least one marker, even a tiny final one -- an unmarked chunk would be a
    chunk nobody could prove was read.
    """
    chunks, expected = [], []
    if not text:
        text = ""
    pos, i = 0, 0
    while pos < len(text) or (pos == 0 and i == 0):
        raw = text[pos:pos + chunk_chars]
        out, marks = [], []
        p = 0
        while True:
            seg = raw[p:p + mark_every]
            m = new_marker()
            marks.append(m)
            out.append(m + "\n" + seg)
            p += mark_every
            if p >= len(raw):
                break
        chunks.append({"i": i, "text": "\n".join(out), "markers": marks,
                       "chars": len(raw)})
        expected.extend(marks)
        pos += chunk_chars
        i += 1
        if not raw:
            break
    return chunks, expected


def markers_in(text):
    """Every marker present in a piece of text, in order. Used by tests and by
    the eval's negative control; the production path uses what the AGENT
    returned, not what is on disk."""
    return [f"⟦CHK:{h}⟧" for h in MARK_RE.findall(text or "")]


HEX_RE = re.compile(r"(?:CHK\s*:?\s*)?([0-9a-fA-F]{6})")


def marker_id(m):
    """Normalise a marker to its 6-hex identity.

    CORRECTION 2026-09-07, from the first live canary run: the agent read the
    whole file (both canaries found) and GUARD 9 still refused it -- "61
    markers never planted" -- because the agent had transcribed the tokens
    without the ⟦ ⟧ brackets and exact string equality failed. A guard that
    refuses correct work is as broken as one that passes bad work. The
    identity of a marker is its random hex, not its punctuation; brackets,
    spacing and case are presentation. Fabrication is still caught: an
    unknown hex id is unknown however it is dressed.
    """
    s = str(m or "").strip()
    mm = MARK_RE.search(s) or HEX_RE.search(s)
    return mm.group(1).lower() if mm else s.lower()


def coverage(expected, returned):
    """Compare planted markers to returned ones. Pure arithmetic on marker ids.

    Returns {"total", "seen", "missing": [..], "pct", "ok", "unknown": [..]}.
    'unknown' is anything returned that was never planted -- a fabricated
    marker is itself a finding.
    """
    exp = list(dict.fromkeys(marker_id(m) for m in (expected or [])))
    ret = {marker_id(m) for m in (returned or []) if str(m).strip()}
    seen = [m for m in exp if m in ret]
    missing = [m for m in exp if m not in ret]
    unknown = sorted(ret - set(exp))
    total = len(exp)
    pct = 100.0 if total == 0 else round(100.0 * len(seen) / total, 1)
    return {"total": total, "seen": len(seen), "missing": missing,
            "pct": pct, "ok": (not missing) and (not unknown), "unknown": unknown}


def orchestrator_chars(chunks):
    """The ONLY legitimate source for chars_read: what the orchestrator sliced.
    Never the agent's number."""
    return sum(int(c.get("chars", 0)) for c in chunks or [])


def write_chunks(chunks, workdir, file_id):
    """Write chunk files; return their paths in order."""
    import os
    paths = []
    for c in chunks:
        p = os.path.join(workdir, f"{file_id}.c{c['i']:03d}.txt")
        with open(p, "w") as fh:
            fh.write(c["text"])
        paths.append(p)
    return paths


if __name__ == "__main__":
    import sys
    t = sys.stdin.read()
    ch, exp = plant(t)
    print(json.dumps({"chunks": len(ch), "markers": len(exp),
                      "chars": orchestrator_chars(ch)}))
