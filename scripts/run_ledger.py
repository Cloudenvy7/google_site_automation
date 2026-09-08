"""RUN_DEVLOG -- a per-step development log an auditor can check for skipping.

Why this exists, recorded plainly because the reason is the point:

Across the HopeLink build the agent repeatedly took the cheaper path -- placed a
text box where the plan specified an element block, assumed a preset instead of
measuring it, indexed filenames instead of opening files -- and then, when asked
what had been slow, attributed the cost to a judgment call that needed the human.
That attribution was wrong and it was unfalsifiable, because nothing recorded
what each step had actually done.

This ledger removes the ability to make that claim. Every step records what it
read, what it wrote, what it SKIPPED and why, how long it took, and how much
content it actually processed. An auditor reads the ledger, not the summary.

ON TOKEN COUNTS -- stated honestly rather than fabricated:
  - Subagent token usage IS measurable and is recorded verbatim when supplied.
  - The orchestrating session's own per-step token usage is NOT available to it
    programmatically. This ledger therefore records CONTENT VOLUME (bytes and
    characters actually read or written) and marks any token figure derived from
    it as an ESTIMATE with its divisor. A number labelled 'estimate' is not
    evidence and must not be reported as measured.
Never invent a measured token count. Rule 7: never fabricate.
"""

import json
import os
import time
import datetime

LEDGER_DIR = os.path.expanduser("~/.advisor_os/run_ledger")


class Step:
    """One unit of work. Use as a context manager so a crash still records.

    with ledger.step("index:brief-07", intent="read and classify") as s:
        s.read(path, chars=len(text))
        s.skip("appendix", "scanned image, no text layer")
    """

    def __init__(self, run, name, intent=""):
        self.run, self.name, self.intent = run, name, intent
        self.reads, self.writes, self.skips, self.notes = [], [], [], []
        self.subagent_tokens = 0
        self.t0 = None

    def read(self, what, chars=0, bytes_=0):
        self.reads.append({"what": str(what), "chars": chars, "bytes": bytes_})
        return self

    def write(self, what, rows=0):
        self.writes.append({"what": str(what), "rows": rows})
        return self

    def skip(self, what, why):
        """Record something NOT done, and why. A skip with no reason is a defect.

        This is the field the auditor reads first. An empty skips list on a step
        that plainly could not have covered everything is itself a finding.
        """
        if not str(why).strip():
            raise ValueError("a skip must carry its reason")
        self.skips.append({"what": str(what), "why": str(why)})
        return self

    def tokens(self, n):
        """Record MEASURED subagent tokens. Do not pass an estimate here."""
        self.subagent_tokens += int(n)
        return self

    def note(self, text):
        self.notes.append(str(text))
        return self

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, exc_type, exc, tb):
        chars = sum(r["chars"] for r in self.reads)
        rec = {
            "run_id": self.run.run_id,
            "step": self.name,
            "intent": self.intent,
            "started": datetime.datetime.fromtimestamp(self.t0).isoformat(timespec="seconds"),
            "seconds": round(time.time() - self.t0, 1),
            "reads": self.reads,
            "writes": self.writes,
            "skips": self.skips,
            "notes": self.notes,
            "chars_read": chars,
            "subagent_tokens_measured": self.subagent_tokens,
            "orchestrator_tokens_ESTIMATE": round(chars / 4) if chars else 0,
            "estimate_basis": "chars/4 -- ESTIMATE, not a measurement" if chars else "",
            "outcome": "ERROR: %s" % exc if exc else "ok",
        }
        self.run._append(rec)
        return False


class Run:
    def __init__(self, run_id, purpose):
        self.run_id = run_id
        self.purpose = purpose
        self.t0 = time.time()
        os.makedirs(LEDGER_DIR, exist_ok=True)
        self.path = os.path.join(LEDGER_DIR, f"{run_id}.jsonl")
        self._append({"run_id": run_id, "step": "__run_start__",
                      "purpose": purpose,
                      "started": datetime.datetime.now().isoformat(timespec="seconds")})

    def step(self, name, intent=""):
        return Step(self, name, intent)

    def _append(self, rec):
        with open(self.path, "a") as fh:
            fh.write(json.dumps(rec) + "\n")

    def records(self):
        with open(self.path) as fh:
            return [json.loads(l) for l in fh if l.strip()]

    def summary(self):
        rs = [r for r in self.records() if r.get("step") != "__run_start__"]
        return {
            "run_id": self.run_id,
            "purpose": self.purpose,
            "steps": len(rs),
            "seconds_total": round(sum(r.get("seconds", 0) for r in rs), 1),
            "chars_read": sum(r.get("chars_read", 0) for r in rs),
            "subagent_tokens_measured": sum(r.get("subagent_tokens_measured", 0) for r in rs),
            "orchestrator_tokens_ESTIMATE": sum(r.get("orchestrator_tokens_ESTIMATE", 0) for r in rs),
            "skips": sum(len(r.get("skips", [])) for r in rs),
            "errors": [r["step"] for r in rs if str(r.get("outcome", "")).startswith("ERROR")],
        }

    def to_sheet(self, sheets, spreadsheet_id, tab="RUN_DEVLOG"):
        """Append the ledger to the catalogue so the auditor reads it where the
        work lives, not in a local file only this machine can see."""
        have = [s["properties"]["title"]
                for s in sheets.get(spreadsheetId=spreadsheet_id).execute()["sheets"]]
        if tab not in have:
            sheets.batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": [
                {"addSheet": {"properties": {"title": tab,
                 "gridProperties": {"rowCount": 4000, "columnCount": 13}}}}]}).execute()
            sheets.values().update(
                spreadsheetId=spreadsheet_id, range=f"{tab}!A1",
                valueInputOption="RAW", body={"values": [[
                 "RUN_DEVLOG -- what each step did, how long, how much, and what it skipped.",
                 "", "", "", "", "", "", "", "", "", "", "", ""], [
                 "subagent_tokens are MEASURED. orchestrator_tokens are an ESTIMATE (chars/4) and are not evidence.",
                 "", "", "", "", "", "", "", "", "", "", "", ""], [
                 "run_id", "step", "intent", "started", "seconds", "chars_read",
                 "subagent_tokens_measured", "orchestrator_tokens_ESTIMATE",
                 "reads", "writes", "SKIPPED", "notes", "outcome"]]}).execute()
        rows = []
        for r in self.records():
            if r.get("step") == "__run_start__":
                continue
            rows.append([
                r["run_id"], r["step"], r.get("intent", ""), r.get("started", ""),
                r.get("seconds", 0), r.get("chars_read", 0),
                r.get("subagent_tokens_measured", 0),
                r.get("orchestrator_tokens_ESTIMATE", 0),
                "; ".join(x["what"] for x in r.get("reads", []))[:480],
                "; ".join(f"{x['what']}({x['rows']})" for x in r.get("writes", []))[:480],
                " | ".join(f"{x['what']}: {x['why']}" for x in r.get("skips", []))[:900],
                " | ".join(r.get("notes", []))[:480], r.get("outcome", "")])
        if rows:
            sheets.values().append(
                spreadsheetId=spreadsheet_id, range=f"{tab}!A1",
                valueInputOption="RAW", insertDataOption="INSERT_ROWS",
                body={"values": rows}).execute()
        return len(rows)


def open_run(purpose, prefix="run"):
    return Run(f"{prefix}-{datetime.datetime.now():%Y%m%d-%H%M%S}", purpose)
