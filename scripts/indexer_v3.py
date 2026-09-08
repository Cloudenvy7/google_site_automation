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

v3.1 -- 2026-09-07 -- COVERAGE IS PROVEN, NOT CLAIMED (Indexer Spec v2.1).
v3.0 handed the agent whole files and the agent's own chars_read. An agent that
read nothing could echo the number and pass every check. Now the orchestrator
chunks the text, plants unforgeable markers (coverage.py), keeps the expected
list to itself, and GUARD 9 refuses any row whose returned markers do not cover
the file. chars_read is computed HERE from the slices, never taken from the
agent. The agent runs with Read-only tools so the only way to see a marker is
to read the chunk it sits in. Ratified by Andrew Powers, 2026-09-07.

usage:
  indexer_v3.py seed   <root_folder_id> <spreadsheet_id>   # crawl, write PENDING rows
  indexer_v3.py next   <spreadsheet_id> [n]                # extract, chunk, mark; emit a packet
  indexer_v3.py prompt <packet.json>                       # print the agent prompt for this packet
  indexer_v3.py agent  <packet.json> [model]               # run `claude -p` on the packet (Read/Write only)
  indexer_v3.py commit <spreadsheet_id> <results.json>     # GUARD 9, then write rows, mark DONE
  indexer_v3.py status <spreadsheet_id>                    # progress, and what is left
"""

import json
import os
import subprocess
import sys
import datetime

import secrets

import google.oauth2.service_account as sa
from googleapiclient.discovery import build

import coverage as cv
import harness as H

HERE = os.path.dirname(os.path.abspath(__file__))
SA = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", os.environ.get("ADVISOR_SA",
                    "/home/tyler/Projects/Blackfox Studios/service_account.json"))
SCOPES = ["https://www.googleapis.com/auth/drive.readonly",
          "https://www.googleapis.com/auth/spreadsheets"]
TAB = "DRIVE_INDEX"
WORK = os.environ.get("INDEX_WORK", os.path.expanduser("~/.advisor_os/index_work"))
READER = os.environ.get("READER", os.path.join(HERE, "read_drive_file.py"))
FOLDER_MIME = "application/vnd.google-apps.folder"

# v3.1 appends three columns. Existing tabs get their header extended in place;
# nothing already written moves. chars_read keeps its name and CHANGES MEANING:
# it is now the orchestrator's count of what it sliced, never the agent's claim.
COLS = ["file_id", "name", "mime_type", "size", "full_path", "web_link",
        "status", "opened", "not_opened_reason", "doc_type", "what_it_says",
        "key_entities", "key_dates", "priority", "priority_reason",
        "site_candidate", "proposed_section", "extracted_to", "chars_read",
        "indexed_by", "indexed_at", "attempts",
        "chunks_total", "chunks_verified", "coverage_pct"]
LAST_COL = "Y"

AGENT_PROMPT = """You are an indexing agent. Read {packet} -- a JSON packet listing files whose text has ALREADY been extracted and split into chunk files for you. Do not download anything. You have only the Read and Write tools.

For EACH entry in "files":
1. Read EVERY path listed in its "chunks", in order, each one IN FULL -- one Read call per chunk, no offset/limit. Do not stop early. Do not skip a chunk because the file "looks unimportant"; importance is an OUTPUT of the index, not an input.
2. Each chunk contains scaffolding tokens shaped like ⟦CHK:xxxxxx⟧. Record every one you encounter, in the order you meet them, in "markers_seen". They are how the orchestrator proves you read the whole file. Do not search for them, do not guess them, do not invent any. If you did not read a chunk, its markers must NOT appear -- and say so in what_it_says.
3. If "extractor_status" is not OPENED, the file gets opened="no" and the reason from the chunk text.
4. If "localpath" is an image, Read it (look at it) before writing the row. An image is not opened until someone has looked at it.

Then Write ONE JSON array to {results} -- exactly one object per entry in "files", with these keys:
  file_id, name, opened ("yes"/"no"), not_opened_reason, doc_type,
  what_it_says (2-3 sentences written from READING it; never the filename restated),
  key_entities (people and organisations named), key_dates (dates the content is about),
  priority ("P1" governs the architecture / "P2" substantive / "P3" supporting / "P4" noise),
  priority_reason, site_candidate ("yes"/"no"), proposed_section,
  markers_seen (array of the ⟦CHK:...⟧ tokens you actually encountered), indexed_by.

Never leave not_opened_reason blank when opened is "no". Never report a file as read that you did not read in full."""


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
    meta = sh.get(spreadsheetId=sid).execute()["sheets"]
    have = {m["properties"]["title"]: m["properties"] for m in meta}
    if TAB not in have:
        sh.batchUpdate(spreadsheetId=sid, body={"requests": [{"addSheet": {
            "properties": {"title": TAB,
                           "gridProperties": {"rowCount": 20000,
                                              "columnCount": len(COLS)}}}}]}).execute()
        sh.values().update(spreadsheetId=sid, range=f"{TAB}!A1",
                           valueInputOption="RAW", body={"values": [COLS]}).execute()
        return
    # v3.0 tab: extend the header for the three v3.1 columns without touching rows.
    hdr = sh.values().get(spreadsheetId=sid, range=f"{TAB}!1:1").execute().get("values", [[]])[0]
    if len(hdr) < len(COLS):
        cols_now = have[TAB]["gridProperties"].get("columnCount", 0)
        if cols_now < len(COLS):
            sh.batchUpdate(spreadsheetId=sid, body={"requests": [{"appendDimension": {
                "sheetId": have[TAB]["sheetId"], "dimension": "COLUMNS",
                "length": len(COLS) - cols_now}}]}).execute()
        sh.values().update(spreadsheetId=sid, range=f"{TAB}!A1",
                           valueInputOption="RAW", body={"values": [COLS]}).execute()


def read_rows(sh, sid):
    v = sh.values().get(spreadsheetId=sid,
                        range=f"{TAB}!A1:{LAST_COL}20000").execute().get("values", [])
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
            "PENDING", "", "", "", "", "", "", "", "", "", "", "", 0, "", "", 0,
            0, 0, ""]
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

def extract(fid, mime, workdir):
    """Run the deterministic extractor. Returns (status, text, localpath)."""
    try:
        res = subprocess.run([sys.executable, READER, fid, mime, workdir],
                             capture_output=True, text=True, timeout=900)
        raw = res.stdout
    except Exception as e:
        raw = f"STATUS::ERROR\nCHARS::0\nTEXT::\n(extractor failed: {e})"
    status = next((l.split("::", 1)[1] for l in raw.splitlines()
                   if l.startswith("STATUS::")), "ERROR")
    local = next((l.split("::", 1)[1] for l in raw.splitlines()
                  if l.startswith("LOCALPATH::")), "")
    text = raw.split("TEXT::\n", 1)[1] if "TEXT::\n" in raw else ""
    return status, text, local


def build_packet(entries, workdir, nonce=None):
    """Chunk + mark every entry; write chunk files; keep the expected markers
    OUT of the packet. Pure apart from file writes -- the eval uses this too,
    so production and test share one code path.

    entries: [{file_id, name, mime, path, extractor_status, text, localpath}]
    returns: packet dict (what the agent sees)
    side-effect: {workdir}/expected_{nonce}.json (what only the orchestrator sees)
    """
    nonce = nonce or secrets.token_hex(4)
    os.makedirs(workdir, exist_ok=True)
    files, expected = [], {}
    for e in entries:
        chunks, marks = cv.plant(e.get("text") or "")
        paths = cv.write_chunks(chunks, workdir, e["file_id"])
        expected[e["file_id"]] = {"markers": marks,
                                  "chars": cv.orchestrator_chars(chunks),
                                  "chunks": len(chunks),
                                  "status": e.get("extractor_status", "OPENED"),
                                  "name": e.get("name", "")}
        files.append({"file_id": e["file_id"], "name": e.get("name", ""),
                      "mime": e.get("mime", ""), "path": e.get("path", ""),
                      "extractor_status": e.get("extractor_status", "OPENED"),
                      "chunks": paths, "localpath": e.get("localpath", "")})
    packet = {"nonce": nonce, "workdir": workdir,
              "results": os.path.join(workdir, f"results_{nonce}.json"),
              "files": files}
    with open(os.path.join(workdir, f"expected_{nonce}.json"), "w") as fh:
        json.dump(expected, fh, indent=1)
    with open(os.path.join(workdir, f"packet_{nonce}.json"), "w") as fh:
        json.dump(packet, fh, indent=1)
    return packet


def next_packet(sid, n=4):
    """Emit the next n unfinished files: extracted, chunked, marked.

    Extraction happens HERE, not in the model. The agent receives paths to
    chunk files on disk and nothing about their size -- v3.0 put the char
    count in the packet, which is how an agent could echo it back as
    chars_read without reading.
    """
    _, sh = svc()
    _, rows = read_rows(sh, sid)
    todo = [(rn, r) for rn, r in rows.values()
            if (r[6] if len(r) > 6 else "") not in ("DONE", "SKIPPED")]
    todo.sort(key=lambda x: int(x[1][21]) if len(x[1]) > 21 and str(x[1][21]).isdigit() else 0)
    entries = []
    for rn, r in todo[:n]:
        status, text, local = extract(r[0], r[2], WORK)
        entries.append({"file_id": r[0], "name": r[1], "mime": r[2], "path": r[4],
                        "extractor_status": status, "text": text, "localpath": local})
    packet = build_packet(entries, WORK)
    pk = os.path.join(WORK, f"packet_{packet['nonce']}.json")
    print(f"remaining : {len(todo)}")
    print(f"packet    : {len(packet['files'])} file(s) -> {pk}")
    exp = json.load(open(os.path.join(WORK, f"expected_{packet['nonce']}.json")))
    for f in packet["files"]:
        e = exp[f["file_id"]]
        print(f"   {f['extractor_status']:26} {e['chars']:>9,}ch  {e['chunks']:>3} chunk(s)  {f['name'][:50]}")
    if not packet["files"]:
        print("\nNothing left. Run: indexer_v3.py status <sid>")
    else:
        print(f"\nNext: indexer_v3.py agent {pk}   (or: prompt {pk} to run it yourself)")
    return pk


def prompt_for(packet_path):
    p = json.load(open(packet_path))
    return AGENT_PROMPT.format(packet=packet_path, results=p["results"])


def run_agent(packet_path, model="haiku", extra_instruction=""):
    """Run the indexing agent non-interactively with READ-ONLY reach.

    --allowedTools Read,Write is the deterministic half of GUARD 9: with no
    Grep and no Bash, the only way to see a marker is to read the chunk it
    sits in. Returns (results_list_or_None, usage_dict, raw_stdout).
    """
    p = json.load(open(packet_path))
    prompt = prompt_for(packet_path) + ("\n\n" + extra_instruction if extra_instruction else "")
    cmd = ["claude", "-p", prompt, "--model", model,
           "--allowedTools", "Read,Write", "--output-format", "json",
           ]
    t0 = datetime.datetime.now()
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    secs = (datetime.datetime.now() - t0).total_seconds()
    usage = {"seconds": round(secs, 1), "model": model}
    try:
        j = json.loads(res.stdout)
        u = j.get("usage") or {}
        usage.update({"input_tokens": u.get("input_tokens"),
                      "output_tokens": u.get("output_tokens"),
                      "cache_read": u.get("cache_read_input_tokens"),
                      "cost_usd": j.get("total_cost_usd"),
                      "turns": j.get("num_turns"), "is_error": j.get("is_error")})
    except Exception:
        usage["parse_error"] = True
    results = json.load(open(p["results"])) if os.path.exists(p["results"]) else None
    return results, usage, res.stdout[-2000:]


def check_results(packet, results):
    """GUARD 9 over every returned row. Pure -- no Google, no browser.

    Returns (accepted, refused):
      accepted: [(row_dict, coverage_dict, expected_entry)]
      refused : [(name, reason)]
    chars_read on every accepted row is REPLACED with the orchestrator's count.
    """
    workdir, nonce = packet["workdir"], packet["nonce"]
    expected = json.load(open(os.path.join(workdir, f"expected_{nonce}.json")))
    by_id = {f["file_id"] for f in packet["files"]}
    accepted, refused = [], []
    seen = set()
    for r in results or []:
        fid = r.get("file_id")
        name = r.get("name") or fid
        if fid not in by_id:
            refused.append((name, "not in this packet")); continue
        if fid in seen:
            refused.append((name, "duplicate row")); continue
        seen.add(fid)
        e = expected[fid]
        if str(r.get("opened", "")).lower() != "yes" and not str(r.get("not_opened_reason", "")).strip():
            refused.append((name, "opened=no with no reason")); continue
        try:
            cov = H.guard_9_coverage(name, e["markers"], r.get("markers_seen") or [],
                                     status=e["status"])
        except H.Refusal as x:
            refused.append((name, str(x))); continue
        r = dict(r)
        r["chars_read"] = e["chars"]                       # orchestrator's number
        r["chunks_total"] = e["chunks"]
        r["chunks_verified"] = e["chunks"] if cov["ok"] else 0
        r["coverage_pct"] = cov["pct"]
        accepted.append((r, cov, e))
    for fid in by_id - seen:
        refused.append((expected[fid]["name"] or fid, "no row returned for this file"))
    return accepted, refused


# ---------------------------------------------------------------- commit

def commit(sid, results_path, packet_path=None):
    """GUARD 9, then write finished rows back. One file per row.

    Refuses: a row with no returned markers covering its file; a fabricated
    marker; opened=no without a reason; a file in the packet with no row.
    A refused file stays PENDING and is re-issued by the next `next`.
    """
    import run_ledger as RL
    results = json.load(open(results_path))
    if packet_path is None:
        # results_<nonce>.json sits beside packet_<nonce>.json
        nonce = os.path.basename(results_path).replace("results_", "").replace(".json", "")
        packet_path = os.path.join(os.path.dirname(results_path), f"packet_{nonce}.json")
    packet = json.load(open(packet_path))
    accepted, refused = check_results(packet, results)

    _, sh = svc()
    ensure_tab(sh, sid)
    _, rows = read_rows(sh, sid)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    run = RL.open_run(f"index commit {packet['nonce']}", prefix="index")
    data = []
    for r, cov, e in accepted:
        fid = r["file_id"]
        if fid not in rows:
            refused.append((r.get("name", fid), "not in the index -- seed first")); continue
        rn, old = rows[fid]
        att = int(old[21]) + 1 if len(old) > 21 and str(old[21]).isdigit() else 1
        with run.step(f"index:{r.get('name','')[:40]}", intent="GUARD 9 + write row") as st:
            st.read(r.get("name", fid), chars=e["chars"])
            st.note(f"coverage {cov['pct']}% ({cov['seen']}/{cov['total']} markers)")
            if str(r.get("opened", "")).lower() != "yes":
                st.skip(r.get("name", fid), r.get("not_opened_reason", ""))
            st.write(f"{TAB} row {rn}", rows=1)
        data.append({"range": f"{TAB}!G{rn}:{LAST_COL}{rn}", "values": [[
            "DONE", r.get("opened", ""), r.get("not_opened_reason", ""),
            r.get("doc_type", ""), r.get("what_it_says", ""),
            r.get("key_entities", ""), r.get("key_dates", ""),
            r.get("priority", ""), r.get("priority_reason", ""),
            r.get("site_candidate", ""), r.get("proposed_section", ""),
            r.get("extracted_to", ""), r["chars_read"],
            r.get("indexed_by", "haiku-packet"), now, att,
            r["chunks_total"], r["chunks_verified"], r["coverage_pct"]]]})
    for n, why in refused:
        with run.step(f"refused:{str(n)[:40]}", intent="GUARD 9") as st:
            st.skip(n, why)
    if refused:
        print("REFUSED (row stays PENDING; re-issued by the next packet):")
        for n, why in refused:
            print(f"   {str(n)[:50]}: {why[:150]}")
    if data:
        sh.values().batchUpdate(spreadsheetId=sid, body={
            "valueInputOption": "RAW", "data": data}).execute()
    print(f"committed : {len(data)} row(s) marked DONE   refused: {len(refused)}")
    print(f"ledger    : {run.summary() if hasattr(run, 'summary') else 'written'}")
    return len(data), len(refused)


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
    print(f"chars read  : {chars:,}   (orchestrator-counted; v3.1)")
    short = [r for r in done if len(r) > 24 and str(r[24]) not in ("", "100", "100.0")
             and str(r[7]).lower() == "yes"]
    if short:
        print(f"COVERAGE < 100% on {len(short)} DONE row(s) -- should be impossible under GUARD 9:")
        for r in short[:5]:
            print(f"    {r[1][:50]}  {r[24]}%")
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
    elif cmd == "prompt": print(prompt_for(sys.argv[2]))
    elif cmd == "agent":
        res, usage, tail = run_agent(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "haiku")
        print(json.dumps({"rows": None if res is None else len(res), "usage": usage}, indent=1))
        if res is None:
            print("agent produced no results file; stdout tail:\n" + tail); sys.exit(3)
    elif cmd == "commit": commit(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif cmd == "status": status(sys.argv[2])
    else: print(__doc__); sys.exit(1)
