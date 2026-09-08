"""Deterministic tests for the coverage guardrail. No model, no network.

These run on every commit that touches the indexer, the harness, the skills or
CLAUDE.md (.githooks/pre-commit). They test the CONFIGURATION that steers the
agent, which the playbook says deserves the regression testing that code gets.

Each test names the failure it exists to catch.
"""
import json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
for cand in (os.path.join(HERE, "..", "scripts"), os.path.join(HERE, "..", ".agents", "scripts")):
    if os.path.isdir(cand):
        sys.path.insert(0, os.path.abspath(cand)); break

import coverage as cv
import harness as H
import indexer_v3 as I

FAILS = []
def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"  -- {detail}" if detail and not cond else ""))
    if not cond: FAILS.append(name)


def test_every_chunk_is_marked():
    """A chunk with no marker is a chunk nobody could prove was read."""
    for n in (0, 1, 1499, 1500, 1501, 12000, 12001, 40000):
        ch, exp = cv.plant("a" * n)
        check(f"chunk marked n={n}", all(c["markers"] for c in ch) and len(exp) >= 1)
        check(f"orchestrator chars n={n}", cv.orchestrator_chars(ch) == n)


def test_full_read_passes_partial_refuses():
    """The failure: an agent reads part of a file and reports it read."""
    ch, exp = cv.plant("b" * 50000)
    full = [m for c in ch for m in cv.markers_in(c["text"])]
    check("full read -> ok", H.guard_9_coverage("f", exp, full)["ok"])
    for frac in (0.0, 0.5, 0.9, 0.97):
        part = full[: int(len(full) * frac)]
        try:
            H.guard_9_coverage("f", exp, part); ok = False
        except H.Refusal:
            ok = True
        check(f"partial read {int(frac*100)}% -> Refusal", ok)


def test_fabricated_marker_refuses():
    """The failure: an agent invents a plausible-looking marker."""
    ch, exp = cv.plant("c" * 5000)
    full = [m for c in ch for m in cv.markers_in(c["text"])]
    try:
        H.guard_9_coverage("f", exp, full + ["⟦CHK:deadbe⟧"]); ok = False
    except H.Refusal as e:
        ok = "never planted" in str(e)
    check("fabricated marker -> Refusal", ok)


def test_no_text_files_are_exempt_only_with_reason():
    """Images/video/scanned PDFs cannot have markers. They pass GUARD 9 only
    because check_results already demands opened=no + a reason (GUARD 7)."""
    check("image exempt", H.guard_9_coverage("i", ["x"], [], status="IMAGE_DOWNLOADED_VIEW_IT")["exempt"])
    with tempfile.TemporaryDirectory() as d:
        pk = I.build_packet([{"file_id": "img1", "name": "photo.png", "mime": "image/png",
                               "extractor_status": "IMAGE_DOWNLOADED_VIEW_IT", "text": ""}], d)
        acc, ref = I.check_results(pk, [{"file_id": "img1", "name": "photo.png",
                                         "opened": "no", "not_opened_reason": ""}])
        check("image opened=no without reason -> refused", not acc and ref and "no reason" in ref[0][1])
        acc, ref = I.check_results(pk, [{"file_id": "img1", "name": "photo.png",
                                         "opened": "yes", "markers_seen": []}])
        check("image opened=yes (viewed) -> accepted", len(acc) == 1 and not ref)


def test_chars_read_never_comes_from_the_agent():
    """The v3.0 hole: chars_read was the agent's echo of a number it was handed."""
    with tempfile.TemporaryDirectory() as d:
        pk = I.build_packet([{"file_id": "d1", "name": "doc", "mime": "document",
                               "extractor_status": "OPENED", "text": "z" * 7000}], d)
        exp = json.load(open(os.path.join(d, f"expected_{pk['nonce']}.json")))
        full = []
        for p in pk["files"][0]["chunks"]:
            full += cv.markers_in(open(p).read())
        acc, ref = I.check_results(pk, [{"file_id": "d1", "name": "doc", "opened": "yes",
                                         "markers_seen": full, "chars_read": 999999}])
        check("agent's chars_read overwritten", acc and acc[0][0]["chars_read"] == 7000 and not ref)
        check("packet carries no char count", "chars" not in pk["files"][0] and "markers" not in json.dumps(pk))
        check("expected file exists and is not in packet", os.path.exists(os.path.join(d, f"expected_{pk['nonce']}.json")))


def test_missing_row_is_refused():
    """The failure: 54 of 59 rows written and reported as success."""
    with tempfile.TemporaryDirectory() as d:
        pk = I.build_packet([{"file_id": "a", "name": "A", "extractor_status": "OPENED", "text": "q" * 100},
                             {"file_id": "b", "name": "B", "extractor_status": "OPENED", "text": "q" * 100}], d)
        fa = cv.markers_in(open(pk["files"][0]["chunks"][0]).read())
        acc, ref = I.check_results(pk, [{"file_id": "a", "name": "A", "opened": "yes", "markers_seen": fa}])
        check("file with no row -> refused", len(acc) == 1 and any("no row" in r[1] for r in ref))


def test_marker_presentation_does_not_matter():
    """The first live canary: agent read everything, returned markers without
    brackets, guard refused. Identity is the hex, not the punctuation."""
    ch, exp = cv.plant("d" * 20000)
    full = [m for c in ch for m in cv.markers_in(c["text"])]
    stripped = [m.replace("⟦", "").replace("⟧", "") for m in full]          # CHK:a3f9c1
    bare = [m[5:11] for m in full]                                          # a3f9c1
    upper = [m.upper() for m in full]
    spaced = ["CHK : " + m[5:11] for m in full]
    for label, form in (("no brackets", stripped), ("bare hex", bare),
                        ("upper", upper), ("spaced", spaced)):
        check(f"marker form '{label}' -> ok", H.guard_9_coverage("f", exp, form)["ok"])
    try:
        H.guard_9_coverage("f", exp, bare[:-1] + ["ffffff"]); ok = False
    except H.Refusal: ok = True
    check("unknown hex still refused", ok)
    try:
        H.guard_9_coverage("f", exp, bare[:-2]); ok = False
    except H.Refusal: ok = True
    check("two missing still refused", ok)


def test_prompt_and_eval_share_one_text():
    """The eval must test the prompt production uses, not a copy that drifts."""
    check("AGENT_PROMPT mentions markers", "⟦CHK:" in I.AGENT_PROMPT and "markers_seen" in I.AGENT_PROMPT)
    check("AGENT_PROMPT forbids partial reads", "IN FULL" in I.AGENT_PROMPT and "Do not stop early" in I.AGENT_PROMPT)


def test_baseline_monotone():
    """Borrowed from Ruflo's audit-tool-descriptions: a count that may never
    rise. Today's counts must be <= the committed baseline."""
    bp = os.path.join(HERE, "baseline.json")
    base = json.load(open(bp))
    counts = {"guard9_bypass_paths": 0,       # no code path writes DONE without check_results
              "agent_supplied_chars_read": 0}  # see test above
    src = open(os.path.join(os.path.dirname(I.__file__), "indexer_v3.py")).read()
    counts["agent_supplied_chars_read"] = src.count('r.get("chars_read"')
    counts["guard9_bypass_paths"] = 0 if "check_results(packet, results)" in src else 1
    for k, v in counts.items():
        check(f"baseline {k}: {v} <= {base[k]}", v <= base[k])


if __name__ == "__main__":
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        print(fn.__name__); fn()
    print("\n" + ("ALL PASS" if not FAILS else f"FAILED: {FAILS}"))
    sys.exit(1 if FAILS else 0)
