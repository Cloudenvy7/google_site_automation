"""Merge Pass B subagent output into DRIVE_INVENTORY, asserting coverage first.

The orchestrator does NOT edit a subagent's finding to make it tidier
(Indexer Spec v2.0, step 5). It merges verbatim, and it refuses to write at all
if coverage is short -- a missing row is exactly the failure this pass exists to
end, and quietly writing 54 of 59 rows would hide it.
"""

import glob
import json
import sys
import datetime

sys.path.insert(0, ".")
import google.oauth2.service_account as sa
from googleapiclient.discovery import build
import run_ledger as RL

SA = "/home/tyler/Projects/Blackfox Studios/service_account.json"
HL = "1RZnHy1Lq2rFzkimVZRqhcAvlveTo-H7SL7sosevCqSY"
COLS = ["file_id", "name", "mime_type", "size", "web_link", "full_path", "depth",
        "kind", "created", "modified", "owner_email", "sharing",
        "sensitivity_tier", "tier_reason", "opened", "not_opened_reason",
        "doc_type", "what_it_says", "key_entities", "key_dates", "priority",
        "priority_reason", "site_candidate", "proposed_section", "extracted_to",
        "chars_read", "indexed_by", "indexed_at", "review_status"]


def main(write=False):
    creds = sa.Credentials.from_service_account_file(SA, scopes=[
        "https://www.googleapis.com/auth/spreadsheets"])
    sh = build("sheets", "v4", credentials=creds).spreadsheets()

    expected = {}
    for p in sorted(glob.glob("/tmp/slice_0*.json")):
        for f in json.load(open(p)):
            expected[f["file_id"]] = f

    got, dupes = {}, []
    for p in sorted(glob.glob("/tmp/idxout_*.json")):
        rows = json.load(open(p))
        for r in rows:
            fid = r.get("file_id")
            if fid in got:
                dupes.append(fid)
            got[fid] = (r, p.split("_")[-1].split(".")[0])

    missing = [fid for fid in expected if fid not in got]
    extra = [fid for fid in got if fid not in expected]

    print(f"expected {len(expected)} files, got {len(got)} rows")
    if dupes:
        print(f"  DUPLICATES: {len(dupes)}")
    if extra:
        print(f"  UNEXPECTED ids: {len(extra)}")
    if missing:
        print(f"  MISSING {len(missing)}:")
        for fid in missing:
            print(f"    {expected[fid]['name'][:66]}")
        print("\nCOVERAGE ASSERTION FAILED -- refusing to write.")
        print("A short index is the failure this pass exists to end.")
        return 1
    print("COVERAGE ASSERTION: PASS")

    unread = [(r["name"], r.get("not_opened_reason", ""))
              for r, _ in got.values() if str(r.get("opened", "")).lower() != "yes"]
    # One row is a known-cleared discrepancy, resolved on CONTENT not char count:
    # the .xlsm agent hand-parsed a subset of the workbook XML while the patched
    # extractor reads more parts. Same file, different extraction depth -- verified
    # by matching Atharva Ubale's 2026-08-12 threaded comment and all seven items.
    noreason = [n for n, why in unread if not str(why).strip()]
    if noreason:
        print(f"\nREFUSING: {len(noreason)} unread file(s) carry no reason: {noreason[:5]}")
        return 1

    prio = {}
    for r, _ in got.values():
        prio[str(r.get("priority", "?")).upper()] = prio.get(str(r.get("priority", "?")).upper(), 0) + 1
    chars = sum(int(r.get("chars_read") or 0) for r, _ in got.values())
    print(f"\nopened: {len(got) - len(unread)}/{len(got)}   chars read: {chars:,}")
    print(f"priority: {dict(sorted(prio.items()))}")
    if unread:
        print("not opened, each with a reason:")
        for n, why in unread:
            print(f"    {n[:50]:52} {why[:74]}")

    if not write:
        print("\n(dry run -- pass --write to update the sheet)")
        return 0

    now = datetime.datetime.now().isoformat(timespec="seconds")
    out = [COLS]
    for fid, (r, slc) in got.items():
        base = expected[fid]
        out.append([
            fid, base["name"], base["mime"], base["size"], "", base["path"], "",
            "file", "", "", "", "", base["tier"], "",
            r.get("opened", ""), r.get("not_opened_reason", ""),
            r.get("doc_type", ""), r.get("what_it_says", ""),
            r.get("key_entities", ""), r.get("key_dates", ""),
            r.get("priority", ""), r.get("priority_reason", ""),
            r.get("site_candidate", ""), r.get("proposed_section", ""), "",
            r.get("chars_read", 0), f"pass-b-agent-{slc}", now, "indexed"])
    sh.values().clear(spreadsheetId=HL, range="DRIVE_INVENTORY!A1:AC200").execute()
    sh.values().update(spreadsheetId=HL, range="DRIVE_INVENTORY!A1",
                       valueInputOption="RAW", body={"values": out}).execute()
    sid = [s["properties"]["sheetId"]
           for s in sh.get(spreadsheetId=HL).execute()["sheets"]
           if s["properties"]["title"] == "DRIVE_INVENTORY"][0]
    sh.batchUpdate(spreadsheetId=HL, body={"requests": [
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1},
         "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                  "backgroundColor": {"red": .85, "green": .89, "blue": .95}}},
         "fields": "userEnteredFormat(textFormat,backgroundColor)"}},
        {"updateSheetProperties": {"properties": {"sheetId": sid,
         "gridProperties": {"frozenRowCount": 1, "frozenColumnCount": 2}},
         "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount"}}]}).execute()
    print(f"\nDRIVE_INVENTORY rewritten: {len(out) - 1} rows on the v2.0 schema")
    return 0


if __name__ == "__main__":
    sys.exit(main(write="--write" in sys.argv))
