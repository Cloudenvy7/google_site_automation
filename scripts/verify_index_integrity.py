"""Independently re-derive every file's char count and compare to what the
indexing agent reported.

Why: subagents redirected the extractor's stdout to generic scratch paths and
overwrote each other. One agent caught it -- line 400 of what should have been a
transcript read "Zip Shuttle has a name and nothing else" -- and warned that
other slices may be silently contaminated.

That is the dangerous failure shape: the row still looks plausible, it just
describes a different file. Nothing in the row's own content reveals it.

So this does not ask the agent whether it read the right file. It re-opens every
file through the same extractor, keyed by file_id (which cannot collide), and
compares the char count to the one reported. A mismatch means the agent was
looking at something other than what it indexed.

Maker is never checker: this runs in the orchestrator, not in the agent that
produced the row.
"""

import glob
import json
import subprocess
import sys

VENV = "/home/tyler/Projects/Blackfox Studios/.venv/bin/python"
TOL = 0.02   # 2% -- pdftotext is deterministic; docs may vary by trailing bytes


def chars_for(fid, mime, outdir):
    r = subprocess.run([VENV, "/tmp/read_drive_file.py", fid, mime, outdir],
                       capture_output=True, text=True, timeout=900)
    status, chars = "", 0
    for line in r.stdout.splitlines():
        if line.startswith("STATUS::"):
            status = line.split("::", 1)[1]
        elif line.startswith("CHARS::"):
            chars = int(line.split("::", 1)[1])
            break
    return status, chars


def main():
    slices = {}
    for p in sorted(glob.glob("/tmp/slice_0*.json")):
        for f in json.load(open(p)):
            slices[f["file_id"]] = f

    rows = {}
    for p in sorted(glob.glob("/tmp/idxout_*.json")):
        for r in json.load(open(p)):
            rows[r["file_id"]] = (r, p)

    ok, suspect, unverifiable = [], [], []
    for fid, (r, src) in rows.items():
        f = slices.get(fid)
        if not f:
            suspect.append((r.get("name", fid), "id not in any slice", src))
            continue
        status, actual = chars_for(fid, f["mime"], "/tmp/verify")
        claimed = int(r.get("chars_read") or 0)
        name = f["name"][:46]
        if status in ("IMAGE_DOWNLOADED_VIEW_IT", "CANNOT_READ", "SHORTCUT",
                      "OPENED_NO_TEXT_LAYER"):
            unverifiable.append((name, status))
            continue
        if actual == 0:
            suspect.append((name, f"re-read returned 0 chars (status {status})", src))
        elif claimed == 0:
            suspect.append((name, f"agent reported 0, actual {actual}", src))
        elif abs(actual - claimed) / max(actual, 1) > TOL:
            suspect.append((name, f"claimed {claimed:,} vs actual {actual:,}", src))
        else:
            ok.append(name)

    print(f"verified   : {len(ok)}")
    print(f"unverifiable by char count (image/video/shortcut): {len(unverifiable)}")
    for n, s in unverifiable:
        print(f"    {n:48} {s}")
    print(f"SUSPECT    : {len(suspect)}")
    for n, why, src in suspect:
        print(f"    {n:48} {why}   [{src.split('/')[-1]}]")
    if suspect:
        print("\nThese rows may describe a different file than they claim.")
        print("Re-index them before the inventory is written.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
