"""Build a Site page from its PAGE_WIREFRAME rows. One row, one Sites block."""
import time, sites_automation as S, build_page as BP, wireframe_build as W

def _menu(item):
    def f(ws):
        ok,_,_ = BP.insert_menu(ws, item); return ok
    return f

def _layout(label):
    def f(ws):
        ok,_,_ = BP.insert_layout(ws, label); return ok
    return f

def build_row(ws, row):
    """row = [order, section, block_type, c1_media, c1_head, c1_body,
              c2_media, c2_head, c2_body, notes]"""
    r = (row + [""]*10)[:10]
    bt = r[2]
    BP.append_point(ws)

    if bt == "spacer":
        ok,_,_ = BP.insert_menu(ws, "Spacer"); return "OK" if ok else "FAIL"

    if bt in ("paragraph", "calendar_button"):
        item = "Text box" if bt == "paragraph" else "Button"
        st, fresh = W.build_section(ws, bt, [r[4]], _menu(item))
        return st

    if bt == "layout_2col":
        # DOM order for this layout is COLUMN-MAJOR: the whole left column, then
        # the whole right column. Row-major ordering put c2's heading in c1.
        cols = [r[4], r[5], r[7], r[8]]   # c1_head, c1_body, c2_head, c2_body
        st, fresh = W.build_section(ws, bt, cols,
                                    _layout("Add layout: Two column image and captions"))
        return st

    if bt == "image":
        return "SKIPPED_NO_ASSET" if r[3].startswith("[") else "IMAGE_TODO"
    if bt == "drive_file_embed":
        return "DEFERRED_PICKER"
    if bt == "embedded_website":
        return "DEFERRED_EMBED_DIALOG"
    return "NO_RECIPE:"+bt
