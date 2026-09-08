"""Read a Google Site's editor and catalogue it as a repeatable template.

The published HTML is useless for this: Sites compiles every block into generic
divs, so a Layouts preset and a hand-placed image beside a text box look
identical. The editor exposes aria-labels and a grid, which is where the block
vocabulary actually lives.

Embeds are recorded with their CONTENTS, not just their presence. "There is an
embed here" cannot be repeated; "this section embeds Drive file X" can.
"""

import json
import time

import sites_automation as S

# What each cell contributes to the template, per section, in document order.
EXTRACT_JS = r"""
(function(){
  function ident(cell){
    // An embed's identity is the thing inside it, not the frame.
    // Sites wraps custom embeds in a cross-origin gstatic shim, so the iframe
    // src tells you nothing. The ORIGINAL embed code survives on data-code,
    // and that is the only thing that makes the block repeatable.
    var all = cell.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
      var dc = all[i].getAttribute && all[i].getAttribute('data-code');
      if (dc) {
        var m = dc.match(/src=["']([^"']+)["']/);
        return {embed_kind: 'custom_embed',
                embed_code: dc.replace(/\s+/g,' ').slice(0,300),
                embed_target: m ? m[1].slice(0,200) : ''};
      }
    }
    var f = cell.querySelector('iframe');
    if (f) {
      var src = f.getAttribute('src') || f.getAttribute('data-src') || '';
      var id  = '';
      var m = src.match(/[-\w]{25,}/);
      if (m) id = m[0];
      return {embed_src: src.slice(0,300), embed_id: id,
              embed_title: (f.getAttribute('title')||'').slice(0,120)};
    }
    // Drive-backed blocks carry their target in data attributes or alt text.
    var img = cell.querySelector('img');
    if (img) {
      return {img_src: (img.getAttribute('src')||'').slice(0,300),
              img_alt: (img.getAttribute('alt')||'').slice(0,120)};
    }
    var a = cell.querySelector('a[href]');
    if (a) return {link: a.href.slice(0,300), link_text:(a.innerText||'').trim().slice(0,80)};
    return {};
  }

  var out = [];
  var seen = new Set();
  document.querySelectorAll('[role="gridcell"]').forEach(function(c){
    var r = c.getBoundingClientRect();
    if (r.width < 20 || r.height < 10) return;
    var key = Math.round(r.top+window.scrollY)+':'+Math.round(r.left);
    if (seen.has(key)) return;
    seen.add(key);
    var o = {
      label: c.getAttribute('aria-label') || '',
      text : (c.innerText||'').trim().replace(/\s+/g,' ').slice(0,110),
      top  : Math.round(r.top + window.scrollY),
      left : Math.round(r.left),
      w    : Math.round(r.width),
      h    : Math.round(r.height)
    };
    var extra = ident(c);
    for (var k in extra) o[k] = extra[k];
    out.push(o);
  });
  out.sort(function(a,b){ return (a.top-b.top) || (a.left-b.left); });
  return JSON.stringify(out);
})()
"""


def read_page(ws):
    """Return the ordered cell list for whatever page is open."""
    try:
        return json.loads(S.eval_js(ws, EXTRACT_JS) or "[]")
    except (TypeError, ValueError):
        return []


def group_into_sections(cells, gap=60):
    """Cells sharing a horizontal band are one section; a vertical gap starts a new one."""
    sections, cur, last = [], [], None
    for c in cells:
        if last is not None and c["top"] - last > gap:
            sections.append(cur)
            cur = []
        cur.append(c)
        last = c["top"]
    if cur:
        sections.append(cur)
    return sections


def describe(section):
    """Name the arrangement so it can be repeated, not just described."""
    labels = [c["label"] or "?" for c in section]
    cols = sorted(set(c["left"] for c in section))
    kinds = sorted(set(labels))
    has_media = any(k in ("Image", "Document", "Content placeholder") or
                    c.get("embed_src") for k, c in zip(labels, section))
    if len(cols) >= 2 and has_media and "Text" in kinds:
        shape = f"{len(cols)}-col media+text"
    elif len(cols) >= 2:
        shape = f"{len(cols)}-col"
    else:
        shape = "1-col"
    return shape, kinds
