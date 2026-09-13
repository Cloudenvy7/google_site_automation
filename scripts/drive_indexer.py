"""Stage 1 — index a Drive folder into a catalogue's DRIVE_INVENTORY tab.

Metadata only. Nothing is opened, downloaded, moved, renamed or shared. The crawl
reads names, paths, owners, sharing scope and dates, and assigns a provisional
sensitivity tier from those alone.

The tier is a FIRST PASS, not a guarantee. A file called "Notes.docx" holding
camper medical details is GREEN to this script. That is why the tier column is
reviewed by a human before stage 3 selection, and why the default on any doubt is
never GREEN.

Runs against a Shared Drive via the service account, or any folder the account
can see. Re-runnable: a second run rewrites the tab, preserving nothing, because
the inventory is a snapshot of the cabinet and not a place to keep decisions.
Decisions live in MANIFEST.
"""

import json
import sys

import google.oauth2.service_account as sa
from googleapiclient.discovery import build
import config

SCOPES = ["https://www.googleapis.com/auth/drive",
          "https://www.googleapis.com/auth/spreadsheets"]

HEADERS = ["file_id", "name", "mime_type", "size", "web_link", "full_path", "depth",
           "kind", "created", "modified", "owner_email", "sharing", "sensitivity_tier",
           "tier_reason", "site_candidate", "proposed_page", "review_status"]

# Order matters: the first list to match wins, most restrictive first.
TIERS = [
    ("RED", ("camper", "medical", "allergy", "emergency contact", "incident",
             "minor", "guardian", "waiver", "release", "consent", "student record")),
    ("ORANGE", ("payroll", "i-9", "i9", "background check", " hr ", "resume", "ssn",
                "salary", "offer letter", "donor", "w-9", "tax id", "bank")),
    ("YELLOW", ("executive session", "legal", "contract", "budget", "invoice",
                "confidential", "grant financial", "personnel", "board minutes")),
    ("BLUE", ("logo", "flyer", "brochure", "press release", "public", "marketing",
              "published", "annual report")),
]


def tier_for(name, path):
    """Provisional tier from name and path only. Never opens the file."""
    s = (name + " " + path).lower()
    for tier, words in TIERS:
        for w in words:
            if w in s:
                return tier, f"keyword in name/path: {w.strip()}"
    return "GREEN", "no sensitivity signal in name or path"


def crawl(dr, root_id, root_name, max_depth=6):
    rows, seen = [], set()

    def walk(fid, path, depth):
        if depth > max_depth or fid in seen:
            return
        seen.add(fid)
        token = None
        while True:
            r = dr.files().list(
                q=f"'{fid}' in parents and trashed=false",
                includeItemsFromAllDrives=True, supportsAllDrives=True,
                pageSize=200, pageToken=token, orderBy="folder,name",
                fields=("nextPageToken,files(id,name,mimeType,size,createdTime,"
                        "modifiedTime,owners(emailAddress),webViewLink,shared)")
            ).execute()
            for f in r.get("files", []):
                is_folder = f["mimeType"].endswith(".folder")
                full = path + "/" + f["name"]
                tier, why = tier_for(f["name"], path)
                rows.append([
                    f["id"], f["name"], f["mimeType"].split(".")[-1], f.get("size", ""),
                    f.get("webViewLink", ""), full, str(depth),
                    "folder" if is_folder else "file",
                    f.get("createdTime", "")[:10], f.get("modifiedTime", "")[:10],
                    (f.get("owners") or [{}])[0].get("emailAddress", ""),
                    "shared" if f.get("shared") else "private",
                    tier, why, "", "", "Pending",
                ])
                if is_folder:
                    walk(f["id"], full, depth + 1)
            token = r.get("nextPageToken")
            if not token:
                break

    walk(root_id, "/" + root_name, 0)
    return rows


def main(folder_id, catalogue_id):
    # Resolved here, not at import -- see indexer_v3.py.
    creds = sa.Credentials.from_service_account_file(
        config.service_account_path(), scopes=SCOPES)
    dr = build("drive", "v3", credentials=creds)
    sh = build("sheets", "v4", credentials=creds).spreadsheets()

    root = dr.files().get(fileId=folder_id, fields="name",
                          supportsAllDrives=True).execute()
    rows = crawl(dr, folder_id, root["name"])

    sh.values().clear(spreadsheetId=catalogue_id,
                      range="DRIVE_INVENTORY!A:Q").execute()
    sh.values().update(spreadsheetId=catalogue_id, range="DRIVE_INVENTORY!A1",
                       valueInputOption="RAW",
                       body={"values": [HEADERS] + rows}).execute()

    counts = {}
    for r in rows:
        counts[r[12]] = counts.get(r[12], 0) + 1
    print(f"indexed {len(rows)} items under /{root['name']}")
    for t in ("RED", "ORANGE", "YELLOW", "GREEN", "BLUE"):
        if counts.get(t):
            print(f"   {counts[t]:>5}  {t}")
    print("\nTiers are provisional. Review the sensitivity_tier column before stage 3.")
    return rows


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: drive_indexer.py <drive_folder_id> <catalogue_spreadsheet_id>")
        raise SystemExit(2)
    main(sys.argv[1], sys.argv[2])
