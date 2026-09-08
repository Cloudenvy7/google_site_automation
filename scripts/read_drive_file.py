"""Open one Drive file and emit its text. Used by every indexing subagent so
that 'opened' means the same thing in every row.

usage: read_drive_file.py <file_id> <mime> [outdir]
Prints: header lines, then the extracted text. Images are DOWNLOADED and the
path printed -- the agent must then view the image with the Read tool, because
an image is not opened until someone has looked at it.
"""
import io, os, socket, subprocess, sys, time
socket.setdefaulttimeout(300)
import google.oauth2.service_account as sa
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SA = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON",
                    "/home/tyler/Projects/Blackfox Studios/service_account.json")
creds = sa.Credentials.from_service_account_file(SA, scopes=[
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly"])
dr = build("drive", "v3", credentials=creds)


def retry(fn, tries=4, label=""):
    """Drive times out intermittently on large exports. A transient network
    failure must never be recorded as 'could not read' -- that would let an
    infrastructure hiccup masquerade as an indexing decision."""
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last

fid, mime = sys.argv[1], sys.argv[2]

# Normalise. v2 fed simplified labels from a hand-built inventory ("document");
# v3 crawls Drive directly and passes real MIME types
# ("application/vnd.google-apps.document"). Accept both -- a reader that returns
# CANNOT_READ because of a naming convention would record a mapping gap as an
# unreadable file, which is the failure mode this whole pass exists to remove.
_G = "application/vnd.google-apps."
if mime.startswith(_G):
    kind = mime[len(_G):]
    mime = {"document": "document", "spreadsheet": "spreadsheet",
            "presentation": "presentation", "shortcut": "shortcut",
            "folder": "folder", "drawing": "image/png",
            "form": "form", "script": "script",
            "jam": "jam", "site": "site"}.get(kind, kind)
out = sys.argv[3] if len(sys.argv) > 3 else "/tmp/idx"
os.makedirs(out, exist_ok=True)

def ooxml(fid, out):
    """Read a NATIVE Office file (.docx/.xlsx/.xlsm/.pptx).

    These are not Docs Editors files, so files().export_media returns HTTP 403
    fileNotExportable. Falling through to CANNOT_READ would record an
    infrastructure gap as an indexing decision -- an unreadable-file verdict that
    is actually a missing code path. Download the container and unzip the XML.
    """
    import re as _re, zipfile
    p2 = f"{out}/{fid}.office"
    os.makedirs(out, exist_ok=True)
    if not os.path.exists(p2):
        def _dl():
            fh = io.FileIO(p2, "wb")
            d = MediaIoBaseDownload(fh, dr.files().get_media(fileId=fid))
            done = False
            while not done: _, done = d.next_chunk()
            fh.close()
        retry(_dl)
    try:
        z = zipfile.ZipFile(p2)
        want = _re.compile(r"(word/document\.xml|xl/sharedStrings\.xml|"
                           r"xl/worksheets/sheet\d+\.xml|xl/comments\d+\.xml|"
                           r"ppt/slides/slide\d+\.xml)")
        parts = [n for n in z.namelist() if want.match(n)]
        raw = "\n".join(z.read(n).decode("utf8", "replace") for n in parts)
        txt = _re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", " ", raw)).strip()
        return ("OPENED", txt, p2)
    except Exception as ex:
        return ("CANNOT_READ", f"(Native Office file could not be unzipped: {ex})", p2)


def emit(status, text="", path=""):
    print(f"STATUS::{status}")
    if path: print(f"LOCALPATH::{path}")
    print(f"CHARS::{len(text)}")
    print("TEXT::")
    print(text)
    sys.exit(0)

try:
    if mime == "document":
        try:
            t = retry(lambda: dr.files().export_media(
                fileId=fid, mimeType="text/plain").execute()).decode("utf8", "replace")
            emit("OPENED", t)
        except Exception:
            emit(*ooxml(fid, out))   # native .docx: export 403s, unzip instead
    if mime in ("spreadsheet",) or "excel" in mime or "spreadsheetml" in mime:
        if "excel" in mime or "spreadsheetml" in mime:
            emit(*ooxml(fid, out))   # native .xlsx/.xlsm: not a Sheets file
        sh = build("sheets", "v4", credentials=creds).spreadsheets()
        t = ""
        for s in retry(lambda: sh.get(spreadsheetId=fid).execute())["sheets"]:
            tab = s["properties"]["title"]
            v = retry(lambda: sh.values().get(
                spreadsheetId=fid, range=f"{tab}!A1:AZ400").execute()).get("values", [])
            t += f"\n### TAB: {tab} ({len(v)} rows)\n"
            t += "\n".join(" | ".join(str(c) for c in r) for r in v)
        emit("OPENED", t)
    if mime == "application/pdf":
        p = f"{out}/{fid}.pdf"
        if not os.path.exists(p):
            def _dl():
                fh = io.FileIO(p, "wb")
                d = MediaIoBaseDownload(fh, dr.files().get_media(fileId=fid),
                                        chunksize=8 * 1024 * 1024)
                done = False
                while not done: _, done = d.next_chunk()
                fh.close()
            retry(_dl)
        subprocess.run(["pdftotext", "-q", p, p + ".txt"], check=False)
        t = open(p + ".txt", errors="replace").read() if os.path.exists(p + ".txt") else ""
        if len(t.strip()) < 40:
            emit("OPENED_NO_TEXT_LAYER",
                 "(PDF has no extractable text -- likely scanned or image-only. "
                 "Report opened=no, reason: scanned PDF, no text layer, needs OCR.)", p)
        emit("OPENED", t, p)
    if mime.startswith("image/"):
        ext = mime.split("/")[1]
        p = f"{out}/{fid}.{ext}"
        if not os.path.exists(p):
            def _dli():
                fh = io.FileIO(p, "wb")
                d = MediaIoBaseDownload(fh, dr.files().get_media(fileId=fid))
                done = False
                while not done: _, done = d.next_chunk()
                fh.close()
            retry(_dli)
        emit("IMAGE_DOWNLOADED_VIEW_IT", "(Use the Read tool on LOCALPATH to actually look at this image.)", p)
    if False:
        # Native uploaded Office files are NOT Docs Editors files: export_media
        # returns 403 fileNotExportable. Falling through to CANNOT_READ here
        # would record an infrastructure gap as an indexing decision -- the exact
        # failure this pass exists to end. Download and unzip the OOXML instead.
        p2 = f"{out}/{fid}.office"
        if not os.path.exists(p2):
            def _dlo():
                fh = io.FileIO(p2, "wb")
                d = MediaIoBaseDownload(fh, dr.files().get_media(fileId=fid))
                done = False
                while not done: _, done = d.next_chunk()
                fh.close()
            retry(_dlo)
        import re as _re, zipfile
        try:
            z = zipfile.ZipFile(p2)
            parts = [n for n in z.namelist() if _re.match(
                r"(word/document\.xml|xl/sharedStrings\.xml|xl/worksheets/.*\.xml|ppt/slides/slide\d+\.xml)", n)]
            raw = "\n".join(z.read(n).decode("utf8", "replace") for n in parts)
            txt = _re.sub(r"<[^>]+>", " ", raw)
            txt = _re.sub(r"\s+", " ", txt).strip()
            emit("OPENED", txt, p2)
        except Exception as ex:
            emit("CANNOT_READ", f"(Native Office file could not be unzipped: {ex})", p2)

    if mime.startswith("video/"):
        emit("CANNOT_READ", "(Video. Report opened=no, reason: video file, needs transcription.)")
    if "wordprocessingml" in mime or "presentationml" in mime:
        emit(*ooxml(fid, out))

    if mime == "shortcut":
        m = dr.files().get(fileId=fid, fields="shortcutDetails,name",
                           supportsAllDrives=True).execute()
        sd = m.get("shortcutDetails", {})
        tid, tmime = sd.get("targetId"), sd.get("targetMimeType", "")
        if tid:
            os.execv(sys.executable, [sys.executable, __file__, tid, tmime, out])
        emit("CANNOT_READ", "(Shortcut with no resolvable target.)")
    emit("CANNOT_READ", f"(Unhandled mime {mime}.)")
except Exception as e:
    emit("ERROR", f"({type(e).__name__}: {e})")
