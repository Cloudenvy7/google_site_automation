"""Resumable Drive indexer -- Stage 1, built to run on a client's own Claude Pro
account under Claude Code, on Haiku, over a large Drive, without skipping.

WHY v3 EXISTS
v2's Pass B spent ~796,000 tokens across 9 parallel Opus subagents to index 59
files. It was complete and it was correct, and it is unusable on a $20 Pro
account against a Drive with years of history. But completeness is not the thing
to trade away -- an index that skips is the failure the whole method exists to
prevent. So the cost has to come out of the ARCHITECTURE, not out of the coverage.

Four changes carry all of it:

1. STATE LIVES IN THE SHEET, NOT IN CONTEXT. Every file gets a PENDING row before
   any reading starts. Progress is durable across sessions, models, usage limits
   and crashes. Resume is just "select where status != DONE".

2. ONE FILE IS COMMITTED AT A TIME. An interruption loses at most one file's work.
   v2 held nine agents' findings in flight and would have lost all of it.

3. THE EXPENSIVE PART IS NOT THE MODEL. Text extraction is deterministic and free
   -- it runs here, in Python. Only the JUDGMENT (what is this, what does it say,
   who is named, how important) needs a model, and it receives extracted text
   rather than a whole Drive.

4. SMALL PACKETS TO A CHEAP MODEL. Work is handed out in packets of a few files.
   A Haiku subagent reads a packet's text files off disk, returns compact JSON,
   and exits. Its context never grows past the packet, which is what parallel
   fan-out was really buying in v2 -- and checkpointing buys it far cheaper.

The no-skipping rule is unchanged: every file gets a row, every unread file
carries a reason, and coverage is asserted before the index is declared complete.

usage:
  indexer_v3.py seed   <root_folder_id> <spreadsheet_id>   # crawl, write PENDING rows
  indexer_v3.py next   <spreadsheet_id> [n]                # emit a work packet
  indexer_v3.py commit <spreadsheet_id> <results.json>     # write rows back, mark DONE
  indexer_v3.py status <spreadsheet_id>                    # progress, and what is left
"""

import json
import os
import subprocess
import sys
import datetime

import google.oauth2.service_account as sa
from googleapiclient.discovery import build

SA = os.environ.get("ADVISOR_SA",
                    "/home/tyler/Projects/Blackfox Studios/service_account.json")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly",
          "https://www.googleapis.com/auth/spreadsheets"]
TAB = "DRIVE_INDEX"
WORK = "/tmp/index_work"
FOLDER_MIME = "application/vnd.google-apps.folder"

COLS = ["file_id", "name", "mime_type", "size", "full_path", "web_link",
        "status", "opened", "not_opened_reason", "doc_type", "what_it_says",
        "key_entities", "key_dates", "priority", "priority_reason",
        "site_candidate", "proposed_section", "extracted_to", "chars_read",
        "indexed_by", "indexed_at", "attempts"]


def svc():
    c = sa.Credentials.from_service_account_file(SA, scopes=SCOPES)
    return (build("drive", "v3", credentials=c),
            build("sheets", "v4", credentials=c).spreadsheets())


# ---------------------------------------------------------------- seed

def true_root(dr, fid):
    """Walk up to the real project root.

    v2 recorded a root that was a SIBLING of the folders holding the files.
    Listing it returned 2 files out of 61, and a crawl from there would have
    reported complete. Resolve and print the ancestry so the operator can see
    which folder is actually being indexed rather than trusting an id.
    """
    m = dr.files().get(fileId=fid, fields="id,name,parents,driveId,mimeType",
                       supportsAllDrives=True).execute()
    chain = [m["name"]]
    p = m.get("parents")
    while p:
        try:
            up = dr.files().get(fileId=p[0], fields="id,name,parents",
                                supportsAllDrives=True).execute()
        except Exception:
            break
        chain.append(up["name"])
        p = up.get("parents")
    return m, " / ".join(reversed(chain))


def crawl(dr, root, drive_id):
    files, folders, stack = {}, {}, [(root, "")]
    while stack:
        fid, path = stack.pop()
        if fid in folders:
            continue
        folders[fid] = path
        tok = None
        while True:
            kw = dict(q=f"'{fid}' in parents and trashed=false",
                      fields="nextPageToken,files(id,name,mimeType,size,webViewLink)",
                      pageSize=1000, pageToken=tok,
                      supportsAllDrives=True, includeItemsFromAllDrives=True)
            if drive_id:
                # Without corpora+driveId a shared-drive listing silently
                # under-returns. That looks exactly like a complete crawl.
                kw.update(corpora="drive", driveId=drive_id)
            r = dr.files().list(**kw).execute()
            for f in r.get("files", []):
                p = f"{path}/{f['name']}"
                if f["mimeType"] == FOLDER_MIME:
                    stack.append((f["id"], p))
                else:
                    files[f["id"]] = {"name": f["name"], "mime": f["mimeType"],
                                      "size": f.get("size") or "", "path": p,
                                      "link": f.get("webViewLink", "")}
            tok = r.get("nextPageToken")
            if not tok:
                break
    return files, folders


def ensure_tab(sh, sid):
    have = [s["properties"]["title"] for s in sh.get(spreadsheetId=sid).execute()["sheets"]]
    if TAB not in have:
        sh.batchUpdate(spreadsheetId=sid, body={"requests": [{"addSheet": {
            "properties": {"title": TAB,
                           "gridProperties": {"rowCount": 20000,
                                              "columnCount": len(COLS)}}}}]}).execute()
        sh.values().update(spreadsheetId=sid, range=f"{TAB}!A1",
                           valueInputOption="RAW", body={"values": [COLS]}).execute()


def read_rows(sh, sid):
    v = sh.values().get(spreadsheetId=sid,
                        range=f"{TAB}!A1:V20000").execute().get("values", [])
    if not v:
        return [], {}
    hdr = v[0]
    return v, {r[0]: (i + 2, r) for i, r in enumerate(v[1:]) if r}


def sibling_check(dr, meta, drive_id, n_files):
    """Refuse a root that is probably a leaf of the real project folder.

    v2 was handed the id of "Hopelink Project Site Folder" and crawled it as the
    project root. That folder is a SIBLING of the folders holding the material;
    listing it returns 2 files out of 61. The crawl succeeded, reported no error,
    and would have produced a 2-row index that looked finished.

    On a client's Drive nobody is watching closely enough to catch that. So the
    seeder refuses when the parent has other folders and the chosen root holds
    little -- the operator must confirm the root or pass the parent instead.
    """
    parents = meta.get("parents") or []
    if not parents:
        return True
    kw = dict(q=f"'{parents[0]}' in parents and trashed=false and "
                f"mimeType='{FOLDER_MIME}'",
              fields="files(id,name)", pageSize=100,
              supportsAllDrives=True, includeItemsFromAllDrives=True)
    if drive_id:
        kw.update(corpora="drive", driveId=drive_id)
    try:
        sibs = [f for f in dr.files().list(**kw).execute().get("files", [])
                if f["id"] != meta["id"]]
    except Exception:
        return True
    if sibs and n_files < 10:
        up = dr.files().get(fileId=parents[0], fields="id,name",
                            supportsAllDrives=True).execute()
        print(f"\n*** REFUSING TO SEED ***")
        print(f"'{meta['name']}' holds only {n_files} file(s), and its parent "
              f"'{up['name']}' has {len(sibs)} other folder(s):")
        for x in sibs[:8]:
            print(f"      {x['name']}")
        print(f"\nThis id looks like a LEAF, not the project root. Indexing it would "
              f"produce a\nsmall index that reports success -- the exact failure this "
              f"check exists to stop.")
        print(f"\nIf the real root is '{up['name']}', seed that instead:")
        print(f"   indexer_v3.py seed {up['id']} <spreadsheet_id>")
        print(f"If '{meta['name']}' really is what you want, re-run with --yes")
        return False
    return True


def seed(root, sid, force=False):
    dr, sh = svc()
    meta, ancestry = true_root(dr, root)
    print(f"root      : {meta['name']}")
    print(f"ancestry  : {ancestry}")
    print(f"driveId   : {meta.get('driveId') or '(my drive)'}")
    files, folders = crawl(dr, root, meta.get("driveId"))
    print(f"crawl     : {len(files)} files, {len(folders)} folders")
    if not force and not sibling_check(dr, meta, meta.get("driveId"), len(files)):
        sys.exit(2)
    ensure_tab(sh, sid)
    _, existing = read_rows(sh, sid)
    new = [[fid, v["name"], v["mime"], v["size"], v["path"], v["link"],
            "PENDING", "", "", "", "", "", "", "", "", "", "", "", 0, "", "", 0]
           for fid, v in files.items() if fid not in existing]
    if new:
        sh.values().append(spreadsheetId=sid, range=f"{TAB}!A1",
                           valueInputOption="RAW", insertDataOption="INSERT_ROWS",
                           body={"values": new}).execute()
    print(f"seeded    : {len(new)} new PENDING rows "
          f"({len(existing)} already present -- seed is idempotent)")
    print(f"\nEvery file now has a row before any reading starts. If this run dies "
          f"here,\nnothing is lost: the work list survives in the sheet.")


# ---------------------------------------------------------------- next

def next_packet(sid, n=4):
    """Emit the next n unfinished files, with their text already extracted.

    Extraction happens HERE, not in the model. The packet the agent receives is
    paths to text on disk -- so a 300,000-character transcript costs the model
    only what it actually reads, and costs the orchestrator nothing.
    """
    _, sh = svc()
    _, rows = read_rows(sh, sid)
    todo = [(rn, r) for rn, r in rows.values()
            if (r[6] if len(r) > 6 else "") not in ("DONE", "SKIPPED")]
    todo.sort(key=lambda x: int(x[1][21]) if len(x[1]) > 21 and str(x[1][21]).isdigit() else 0)
    os.makedirs(WORK, exist_ok=True)
    packet = []
    for rn, r in todo[:n]:
        fid, name, mime = r[0], r[1], r[2]
        out = f"{WORK}/{fid}.txt"
        try:
            res = subprocess.run([sys.executable, os.environ.get("READER","/tmp/read_drive_file.py"),
                                  fid, mime, WORK],
                                 capture_output=True, text=True, timeout=900)
            txt = res.stdout
        except Exception as e:
            txt = f"STATUS::ERROR\nCHARS::0\nTEXT::\n(extractor failed: {e})"
        open(out, "w").write(txt)
        status = next((l.split("::", 1)[1] for l in txt.splitlines()
                       if l.startswith("STATUS::")), "ERROR")
        chars = next((int(l.split("::", 1)[1]) for l in txt.splitlines()
                      if l.startswith("CHARS::")), 0)
        local = next((l.split("::", 1)[1] for l in txt.splitlines()
                      if l.startswith("LOCALPATH::")), "")
        packet.append({"file_id": fid, "name": name, "mime": mime,
                       "path": r[4], "text_file": out, "extractor_status": status,
                       "chars": chars, "localpath": local})
    json.dump(packet, open("/tmp/packet.json", "w"), indent=1)
    print(f"remaining : {len(todo)}")
    print(f"packet    : {len(packet)} file(s) -> /tmp/packet.json")
    for p in packet:
        print(f"   {p['extractor_status']:26} {p['chars']:>8,}ch  {p['name'][:56]}")
    if not packet:
        print("\nNothing left. Run: indexer_v3.py status <sid>")


# ---------------------------------------------------------------- commit

def commit(sid, results_path):
    """Write finished rows back. One file per row, committed immediately.

    Refuses a row that claims opened=no without a reason -- the ledger rule, at
    the point of writing rather than at the end where it is too late.
    """
    _, sh = svc()
    _, rows = read_rows(sh, sid)
    res = json.load(open(results_path))
    now = datetime.datetime.now().isoformat(timespec="seconds")
    data, bad = [], []
    for r in res:
        fid = r.get("file_id")
        if fid not in rows:
            bad.append((fid, "not in the index -- seed first")); continue
        if str(r.get("opened", "")).lower() != "yes" and not str(
                r.get("not_opened_reason", "")).strip():
            bad.append((r.get("name", fid), "opened=no with no reason")); continue
        rn, old = rows[fid]
        att = int(old[21]) + 1 if len(old) > 21 and str(old[21]).isdigit() else 1
        data.append({"range": f"{TAB}!G{rn}:V{rn}", "values": [[
            "DONE", r.get("opened", ""), r.get("not_opened_reason", ""),
            r.get("doc_type", ""), r.get("what_it_says", ""),
            r.get("key_entities", ""), r.get("key_dates", ""),
            r.get("priority", ""), r.get("priority_reason", ""),
            r.get("site_candidate", ""), r.get("proposed_section", ""),
            r.get("extracted_to", ""), r.get("chars_read", 0),
            r.get("indexed_by", "haiku-packet"), now, att]]})
    if bad:
        print("REFUSED:")
        for n, why in bad:
            print(f"   {n}: {why}")
    if data:
        sh.values().batchUpdate(spreadsheetId=sid, body={
            "valueInputOption": "RAW", "data": data}).execute()
    print(f"committed : {len(data)} row(s) marked DONE")


# ---------------------------------------------------------------- status

def status(sid):
    _, sh = svc()
    v, rows = read_rows(sh, sid)
    if not rows:
        print("no index yet -- run seed"); return
    done = [r for _, r in rows.values() if len(r) > 6 and r[6] == "DONE"]
    todo = [r for _, r in rows.values() if not (len(r) > 6 and r[6] == "DONE")]
    unread = [r for r in done if len(r) > 7 and str(r[7]).lower() != "yes"]
    chars = sum(int(r[18]) for r in done
                if len(r) > 18 and str(r[18]).isdigit())
    pr = {}
    for r in done:
        if len(r) > 13 and r[13]:
            pr[r[13]] = pr.get(r[13], 0) + 1
    total = len(rows)
    print(f"total files : {total}")
    print(f"done        : {len(done)}  ({100*len(done)//max(total,1)}%)")
    print(f"remaining   : {len(todo)}")
    print(f"chars read  : {chars:,}")
    print(f"priority    : {dict(sorted(pr.items()))}")
    print(f"unread (with reason): {len(unread)}")
    for r in unread[:8]:
        print(f"    {r[1][:44]:46} {str(r[8])[:60]}")
    if todo:
        print(f"\nnext up:")
        for r in todo[:5]:
            print(f"    {r[1][:66]}")
        print("\nRESUMABLE: rerun `next` then `commit`. Nothing already DONE is redone.")
    else:
        print("\nCOVERAGE: every file has a DONE row.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "seed":    seed(sys.argv[2], sys.argv[3], "--yes" in sys.argv)
    elif cmd == "next":  next_packet(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 4)
    elif cmd == "commit": commit(sys.argv[2], sys.argv[3])
    elif cmd == "status": status(sys.argv[2])
    else: print(__doc__); sys.exit(1)
