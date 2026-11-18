"""Compact KPI strip, built in JS inside an iframe (replaces the st.metric cards)."""
import json

import streamlit as st
import streamlit.components.v1 as components

HTML = r"""
<div id="strip"></div>
<style>
  @font-face{font-family:"Ronzino";src:url("/app/static/fonts/Ronzino-Regular.otf") format("opentype");
             font-weight:400;font-style:normal;font-display:swap}
  @font-face{font-family:"Ronzino";src:url("/app/static/fonts/Ronzino-Medium.otf") format("opentype");
             font-weight:500;font-style:normal;font-display:swap}
  @font-face{font-family:"Ronzino";src:url("/app/static/fonts/Ronzino-Bold.otf") format("opentype");
             font-weight:700;font-style:normal;font-display:swap}
  *{box-sizing:border-box}
  html,body{margin:0;overflow:hidden;background:transparent;
            font-family:"Ronzino",system-ui,sans-serif;
            --line:#dfe4e8; --txt:#20262b; --mut:#6b7781; --acc:#ea7b00;
            --good:#1a7f4b; --warn:#d2691e; --wash:rgba(234,123,0,.07)}
  body.dark{--line:#3a454d; --txt:#e9ecef; --mut:#9aa5ad; --acc:#f59b2a;
            --good:#4cc38a; --warn:#f5a04a; --wash:rgba(245,155,42,.10)}
  @media (prefers-color-scheme: dark){
    body.auto{--line:#3a454d; --txt:#e9ecef; --mut:#9aa5ad; --acc:#f59b2a;
              --good:#4cc38a; --warn:#f5a04a; --wash:rgba(245,155,42,.10)}}
  /* one line, never truncated: if the tiles do not fit, fit() below scales the whole
     strip down uniformly instead of letting the text ellipsis */
  #strip{display:flex;flex-wrap:nowrap;align-items:stretch;gap:6px;padding:2px;
         transform-origin:left top}
  .group{display:flex;flex-direction:column;gap:3px;min-width:0;flex:0 0 auto}
  .group.spaced{margin-right:32px}
  .group-title{font-size:10.5px;font-weight:500;letter-spacing:.07em;
               text-transform:uppercase;color:var(--mut);white-space:nowrap;
               padding:0 2px;line-height:1.2}
  .group-row{display:flex;flex-wrap:nowrap;gap:6px;align-items:stretch;flex:1 1 auto;
             min-height:0}
  /* narrow group: content-sized, then +15% via padding + type scale */
  .group.narrow .tile{flex:0 0 auto;width:max-content;
                      padding:calc(7px * 1.15) calc(8px * 1.15) calc(8px * 1.15) calc(11px * 1.15)}
  .group.narrow .lab{font-size:calc(10.5px * 1.15)}
  .group.narrow .val{font-size:calc(27px * 1.15);margin-top:calc(2px * 1.15)}
  .group.narrow .val .u{font-size:calc(12px * 1.15)}
  .group.narrow .note{font-size:calc(11.5px * 1.15)}
  .tile{position:relative;flex:1 1 auto;min-width:0;border:1px solid var(--line);
        border-radius:7px;padding:7px 10px 8px 13px;color:var(--txt);line-height:1.2;
        overflow:hidden;background:linear-gradient(170deg,var(--wash),transparent 70%);
        transition:transform .12s ease, box-shadow .12s ease, border-color .12s ease}
  .tile::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--a)}
  .tile:hover{transform:translateY(-1px);border-color:var(--a);
              box-shadow:0 2px 10px rgba(0,0,0,.10)}
  .lab{font-size:10.5px;font-weight:500;letter-spacing:.07em;
       text-transform:uppercase;color:var(--mut);white-space:nowrap}
  .val{font-size:27px;font-weight:700;letter-spacing:-.015em;margin-top:2px;
       font-variant-numeric:tabular-nums;white-space:nowrap}
  .val.dim{color:var(--mut);margin-top:0}
  .val .u{font-size:12px;font-weight:500;color:var(--mut);margin-left:4px;letter-spacing:0}
  .note{font-size:11.5px;font-weight:500;color:var(--mut);white-space:pre-line}
  .note.good{color:var(--good)} .note.warn{color:var(--warn)}
</style>
<script>
const ITEMS = __DATA__;
document.body.className = __THEME__;
const esc = (s) => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const accent = (t) => t.tone === 'good' ? 'var(--good)' : t.tone === 'warn' ? 'var(--warn)' : 'var(--acc)';
const valLine = (value, unit, dim) => value == null ? '' :
  `<div class="val${dim ? ' dim' : ''}">${esc(value)}${
    unit ? '<span class="u">' + esc(unit) + '</span>' : ''}</div>`;
const tileHtml = (t) => `
  <div class="tile" style="--a:${accent(t)}" title="${esc(t.hint || t.label)}">
    <div class="lab">${esc(t.label)}</div>
    ${valLine(t.value, t.unit, false)}
    ${valLine(t.value2, t.unit2, true)}
    ${t.note ? `<div class="note ${t.tone || ''}">${esc(t.note)}</div>` : ''}
  </div>`;
const strip = document.getElementById('strip');
strip.innerHTML = ITEMS.map(item => {
  if (item.group != null) {
    const cls = 'group' + (item.narrow ? ' narrow' : '') + (item.spaced ? ' spaced' : '');
    const title = item.group
      ? `<div class="group-title">${esc(item.group)}</div>`
      : '';
    return `<div class="${cls}">${title}<div class="group-row">${
      (item.tiles || []).map(tileHtml).join('')
    }</div></div>`;
  }
  return tileHtml(item);
}).join('');

// scale the strip down when the tiles cannot fit side by side at full size, so a
// narrow window shrinks the cards instead of clipping the numbers inside them
let fitting = false;
function fit(){
  if(fitting) return;
  fitting = true;
  strip.style.transform = 'none';
  strip.style.width = 'max-content';
  const need = strip.offsetWidth, have = document.documentElement.clientWidth;
  if(need > have && need > 0){
    strip.style.transform = 'scale(' + (have / need).toFixed(4) + ')';
  } else {
    strip.style.width = '100%';
  }
  fitting = false;
}
fit();
document.fonts.ready.then(fit);                      // metrics re-measure once Ronzino lands
if(window.ResizeObserver) new ResizeObserver(fit).observe(document.documentElement);
</script>
"""


def render_metrics(items, theme=None, height=None):
    """items: tiles and optional groups.

    Tile: {label, value, unit, value2?, unit2?, note?, tone: ''|'good'|'warn', hint}
    Group: {group: title|None, tiles: [Tile], narrow?: bool, spaced?: bool}
    """
    if theme is None:
        try:
            theme = st.context.theme.type or "auto"
        except Exception:
            theme = "auto"
    payload = json.dumps(items).replace("</", "<\\/")
    html = HTML.replace("__DATA__", payload).replace("__THEME__", json.dumps(theme))
    # fixed: an iframe cannot grow itself, and height="content" reserves 150px here
    # +18px when a group title sits above the first tiles
    h = height or 140  # room for group title / dual value lines / two-line notes
    if hasattr(st, "iframe"):
        st.iframe(html, height=h)
    else:
        components.html(html, height=h)
