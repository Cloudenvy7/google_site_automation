"""Catalogue a Google Site as a repeatable template.

Two views are required and neither is sufficient alone:

  editor    -> block TYPE and ARRANGEMENT (aria-labels, grid geometry, embeds)
  published -> IMAGE URLS

The editor lazy-renders images and paints an ar-gradient placeholder into the
cell until it scrolls into view, so reading content_image_url from the editor
reports real images as empty. That mistake was made and caught on JBL/Home.
"""

import json
import time

import sites_automation as S
import extract_site_template as X


def editor_pages(ws):
    """Page entries from the Pages panel, as (label, clean_title)."""
    S.click_control(ws, "Pages", exact=True)
    time.sleep(3)
    labels = [c["label"] for c in S.probe_controls(ws, 400)
              if c["role"] == "div" and c["label"].endswith(".")]
    out = []
    for l in labels:
        if l.startswith("Group starting"):
            continue                      # a layout artifact, not a page
        t = l.rstrip(".")
        t = t.replace("Home page, titled ", "")
        hidden = "Hidden in navigation" in t
        t = t.split(".")[0].strip()
        out.append({"label": l, "title": t, "hidden": hidden})
    return out


def walk_editor(ws, pages):
    """Click each page and record its structure. One editor session."""
    result = []
    for p in pages:
        if not S.click_control(ws, p["label"], exact=True):
            print(f"  !! could not select {p['title']}")
            continue
        time.sleep(4.5)
        url = S.current_url(ws)
        pid = url.split("/p/")[1].split("/")[0] if "/p/" in url else ""
        cells = X.read_page(ws)
        secs = X.group_into_sections(cells)
        print(f"  {p['title']:<22} id={pid[:16]:<18} cells={len(cells):<3} sections={len(secs)}")
        result.append({**p, "page_id": pid, "cells": cells, "sections": len(secs)})
    return result


def published_images(ws, base, slug):
    """Image URLs in page order, from the PUBLISHED page. Editor is unreliable."""
    import chrome_automation as C
    C.send_ws_cmd(ws, "Page.navigate", {"url": base.rstrip("/") + "/" + slug.lstrip("/")})
    time.sleep(11)
    S.eval_js(ws, "window.scrollTo(0,document.body.scrollHeight)")
    time.sleep(4)
    S.eval_js(ws, "window.scrollTo(0,0)")
    time.sleep(3)
    raw = S.eval_js(ws, r"""
    (function(){
      var o=[];
      document.querySelectorAll('img').forEach(function(e){
        var r=e.getBoundingClientRect();
        var s=e.currentSrc||e.src||'';
        if(!s || s.indexOf('data:')===0) return;
        if(e.naturalWidth<200) return;           // icons and chrome
        o.push({y:Math.round(r.top+window.scrollY),w:Math.round(r.width),
                nat:e.naturalWidth+'x'+e.naturalHeight,src:s});
      });
      o.sort(function(a,b){return a.y-b.y;});
      return JSON.stringify(o);
    })()""")
    try:
        return json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
