"""BMW Product Intelligence look & feel (ported from bmw-requirement-intelligence.html) plus small HTML components."""
from __future__ import annotations

from html import escape

import streamlit as st

HERO_IMAGE = ("https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?actEvent=scaleBig"
              "&attachment=1&dokNo=P90500625&quality=90&square=0")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');
:root{--ink:#0a1017;--navy:#101923;--canvas:#f2f4f6;--line:#dfe4e8;--muted:#677585;--blue:#0877c9;--green:#187b58;--amber:#9a6712;--red:#a93342;
      --font:'Inter',Arial,sans-serif;--display:'Barlow Condensed','Arial Narrow',sans-serif}
html,body,[class*="css"],.stApp{font-family:var(--font)}
.stApp{background:var(--canvas)}
/* top bar + navigation */
header[data-testid="stHeader"]{background:var(--ink);border-bottom:1px solid #26323f}
header[data-testid="stHeader"] *{color:#aeb9c3}
header[data-testid="stHeader"] a[aria-current="page"], header[data-testid="stHeader"] a:hover{color:#fff !important}
header[data-testid="stHeader"] a[aria-current="page"] *{color:#fff !important}
/* sidebar */
section[data-testid="stSidebar"]{background:var(--navy)}
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"], section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#dbe4ea !important}
section[data-testid="stSidebar"] code{background:#17222d;color:#8fd3f5}
section[data-testid="stSidebar"] [data-testid="stAlert"] p{color:#7d1f2b !important}
/* typography */
h1,h2,h3,h4{font-family:var(--display) !important;text-transform:uppercase;letter-spacing:.4px;color:#14202a}
h1{font-weight:600 !important}
/* metrics & containers */
div[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);padding:14px 18px;position:relative}
div[data-testid="stMetric"]:before{content:'';position:absolute;left:0;top:0;width:3px;height:100%;background:#168bce}
div[data-testid="stMetric"] label{text-transform:uppercase;letter-spacing:1.2px;font-size:.68rem;color:var(--muted)}
div[data-testid="stMetricValue"]{font-family:var(--display);font-weight:600}
div[data-testid="stVerticalBlockBorderWrapper"]{border-radius:0 !important;border-color:var(--line) !important;background:#fff}
.stButton button,.stDownloadButton button{border-radius:0;font-weight:600}
.stButton button[kind="primary"]{background:var(--blue);border-color:var(--blue)}
div[data-testid="stExpander"] details{border-radius:0;background:#fff}
/* components */
.bmw-hero{min-height:300px;color:#fff;display:grid;grid-template-columns:1.3fr .7fr;gap:36px;align-items:end;padding:32px 36px;position:relative;overflow:hidden;margin-bottom:14px;
  background-color:#07101a;background-image:linear-gradient(90deg,rgba(4,10,17,.97) 0%,rgba(4,10,17,.92) 37%,rgba(4,10,17,.58) 65%,rgba(4,10,17,.42) 100%),url("__HERO__");background-size:cover;background-position:center 54%}
.bmw-hero:after{content:"";position:absolute;inset:0;background-image:radial-gradient(circle,#64d0ff 1px,transparent 1.7px);background-size:31px 31px;opacity:.13;
  -webkit-mask-image:linear-gradient(90deg,transparent 30%,#000 100%);mask-image:linear-gradient(90deg,transparent 30%,#000 100%);pointer-events:none}
.bmw-hero>div{position:relative;z-index:1}
.bmw-kicker{font-size:.62rem;letter-spacing:2px;text-transform:uppercase;color:#4bb8ef;font-weight:700}
.bmw-hero h1{font:600 clamp(40px,5vw,66px)/.92 var(--display) !important;text-transform:uppercase;margin:12px 0 14px;color:#fff !important;padding:0}
.bmw-hero h1 span{color:#2da4e5}
.bmw-hero p{color:#acb8c3;max-width:640px;line-height:1.65;font-size:.82rem;margin:0}
.agent{border:1px solid #61b9df48;background:rgba(8,17,28,.79);backdrop-filter:blur(8px);padding:13px 14px;box-shadow:0 15px 45px #0005;font-size:.7rem}
.agent-top{display:flex;align-items:center;gap:9px;padding-bottom:10px;border-bottom:1px solid #c1d5e126}
.agent-orbit{width:32px;height:32px;border:1px solid #42b7e8;border-radius:50%;display:grid;place-items:center;font-size:.6rem;color:#83dcff;box-shadow:0 0 16px #36b9ec44}
.agent-top b{display:block;font-size:.78rem;letter-spacing:.7px}.agent-top small{font-size:.5rem;letter-spacing:1px;color:#98afbd}
.agent-state{margin-left:auto;font-size:.5rem;letter-spacing:.8px;color:#a8d8ea;display:flex;align-items:center;gap:5px}
.agent-state i{width:6px;height:6px;border-radius:50%;display:inline-block}
.agent-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin:10px 0}
.agent-node{min-height:44px;background:#ffffff08;border:1px solid #9ab6c41c;padding:7px 8px}
.agent-node span{float:right;color:#4ab9e4;font:600 .75rem var(--display)}.agent-node b{display:block;font-size:.62rem;color:#edf5f8}.agent-node small{display:block;color:#90a3ae;font-size:.55rem;margin-top:3px}
.agent-gate{border-top:1px solid #4b91ad45;padding-top:8px;display:flex;justify-content:space-between;gap:8px;align-items:center}
.agent-gate span{color:#54bce4;font-size:.5rem;letter-spacing:1px}.agent-gate b{font-size:.62rem;color:#f2f7fa}
.agent-scope{margin-top:10px;padding-top:8px;border-top:1px solid #c1d5e126}.agent-scope b{font-size:.62rem;letter-spacing:.8px}
.meta-line{color:#91a2b0;font-size:.52rem;letter-spacing:1px;margin-top:4px}
.photo-credit{position:absolute;right:16px;bottom:8px;z-index:2;font-size:.5rem;letter-spacing:.8px;color:#d8e5ee9c}
.page-head{background:#fff;border:1px solid var(--line);padding:15px 17px;margin-bottom:12px}
.page-head .bmw-kicker{color:var(--blue)}
.page-head h2{font:600 1.6rem var(--display) !important;text-transform:uppercase;margin:6px 0 0;padding:0}
.page-head .hint{font-size:.66rem;color:#748392;letter-spacing:.4px;margin-top:5px}
.callout{border-left:2px solid #1490d4;background:#f4f9fc;padding:10px 11px;color:#586979;font-size:.72rem;line-height:1.6;margin:8px 0}
.callout b{display:block;color:#20394e;font-size:.62rem;letter-spacing:.8px;margin-bottom:3px;text-transform:uppercase}
.callout.warn{border-color:#c8912f;background:#fffaf0}.callout.warn b{color:#8b6015}
.source-stat{display:grid;grid-template-columns:1fr auto;gap:8px;padding:8px 0;border-top:1px solid #edf0f2;font-size:.74rem}
.source-stat span{color:#697887}
.side-title{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.side-title h3{font:600 1.15rem var(--display) !important;text-transform:uppercase;margin:0;padding:0}
.side-title span{font-size:.55rem;letter-spacing:1px;color:#758594}
.pill{display:inline-block;padding:3px 7px;border:1px solid #dce3e8;color:#576776;font-size:.6rem;letter-spacing:.3px;margin:2px 4px 2px 0;background:#fff}
.pill.approved{color:var(--green);border-color:#b7decf;background:#f2faf6}
.pill.modified{color:#075c9d;border-color:#84bee3;background:#edf7fd}
.pill.rejected{color:var(--red);border-color:#efc4ca;background:#fff5f6}
.pill.postponed,.pill.warn{color:#8b6015;border-color:#e7d3ab;background:#fffaf0}
.pill.accepted{color:var(--green);border-color:#b7decf;background:#f2faf6}
.req-row{display:grid;grid-template-columns:42px minmax(0,1fr) 74px;gap:13px;padding:13px 4px;border-bottom:1px solid #e9edf0;align-items:start}
.req-row:last-child{border-bottom:0}
.req-index{font:600 1.45rem var(--display);color:#93a3b2}
.req-title{font-size:.8rem;font-weight:650;line-height:1.45;color:#17232e}
.req-sub{font-size:.66rem;color:#758392;margin-top:4px;line-height:1.5}
.freq{text-align:right}.freq b{font:600 1.6rem var(--display);display:block;color:#1c2b37}.freq small{font-size:.52rem;letter-spacing:.7px;color:#81909e}
.bmw-table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line)}
.bmw-table th{text-align:left;background:#f6f8fa;color:#647383;padding:10px 12px;font-size:.55rem;letter-spacing:1px;font-weight:600;text-transform:uppercase;border-bottom:1px solid var(--line)}
.bmw-table td{padding:11px 12px;border-bottom:1px solid #edf0f2;vertical-align:top;font-size:.7rem;line-height:1.55;color:#33424f}
.evidence-id{font-weight:600;color:#1676b6;white-space:nowrap}
.source-card{padding:13px 4px;border-bottom:1px solid #ebeff2;display:grid;grid-template-columns:120px 1fr auto;gap:13px;align-items:start}
.source-kind{color:#1683c1;font-size:.55rem;letter-spacing:.7px;font-weight:700;text-transform:uppercase}
.source-name{font-weight:650;font-size:.75rem}.source-detail{color:#71808e;font-size:.64rem;line-height:1.55;margin-top:4px}
.source-status{font-size:.55rem;color:#677585;border:1px solid #dce3e8;padding:4px 6px;white-space:nowrap;text-decoration:none}
.bmw-footer{display:flex;justify-content:space-between;padding:16px 2px;color:#7b8996;font-size:.55rem;letter-spacing:.9px}
@media(max-width:900px){.bmw-hero{grid-template-columns:1fr;padding:24px}.source-card{grid-template-columns:1fr}}
</style>
""".replace("__HERO__", HERO_IMAGE)


def inject() -> None:
    st.html(CSS)


def e(s) -> str:
    return escape(str(s if s is not None else ""))


def page_head(kicker: str, title: str, hint: str = "") -> None:
    st.html(f'<div class="page-head"><div class="bmw-kicker">{e(kicker)}</div><h2>{e(title)}</h2>'
            + (f'<div class="hint">{e(hint)}</div>' if hint else "") + "</div>")


def callout(title: str, text: str, warn: bool = False) -> str:
    return f'<div class="callout{" warn" if warn else ""}"><b>{e(title)}</b>{e(text)}</div>'


def side_title(title: str, tag: str = "") -> str:
    return f'<div class="side-title"><h3>{e(title)}</h3><span>{e(tag)}</span></div>'


def stat(label: str, value) -> str:
    return f'<div class="source-stat"><span>{e(label)}</span><b>{e(value)}</b></div>'


def pill(text: str, cls: str = "") -> str:
    return f'<span class="pill {e(cls)}">{e(text)}</span>'


def footer() -> None:
    st.html('<div class="bmw-footer"><span>BMW PRODUCT INTELLIGENCE · REQUIREMENT COPILOT</span>'
            '<span>AI PROPOSES · PRODUCT MANAGER DECIDES · EVERY DECISION LOGGED</span></div>')


STEPPER_CSS = """
<style>
.stepper{display:grid;grid-template-columns:repeat(4,1fr);gap:0;background:#fff;border:1px solid var(--line);margin-bottom:12px}
.step{padding:11px 14px;border-right:1px solid var(--line);position:relative}
.step:last-child{border-right:0}
.step .n{font:600 1.25rem var(--display);color:#93a3b2;margin-right:8px}
.step b{font-size:.74rem;color:#17232e}.step small{display:block;color:#748392;font-size:.6rem;margin-top:3px;letter-spacing:.3px}
.step .who{float:right;font-size:.5rem;letter-spacing:1px;padding:2px 6px;border:1px solid #dce3e8;color:#576776}
.step.ai .who{color:#075c9d;border-color:#84bee3;background:#edf7fd}.step.pm .who{color:#8b6015;border-color:#e7d3ab;background:#fffaf0}
.step.done{background:#f6fbf8}.step.done .n{color:var(--green)}
.step.now{background:#f4f9fc;box-shadow:inset 0 -3px 0 var(--blue)}.step.now .n{color:var(--blue)}
.meter{display:flex;height:8px;background:#e8edf0;margin:6px 0 3px}
.meter i{display:block;height:100%}
.meter-legend{font-size:.6rem;color:#647383;display:flex;gap:12px;flex-wrap:wrap}
.meter-legend span:before{content:'';display:inline-block;width:8px;height:8px;margin-right:4px;vertical-align:middle;background:var(--c)}
.kanban-col{background:#eef1f4;border:1px solid var(--line);padding:8px;min-height:120px}
.kanban-head{font:600 1rem var(--display);text-transform:uppercase;letter-spacing:.5px;display:flex;justify-content:space-between;margin-bottom:6px}
.kcard{background:#fff;border:1px solid var(--line);border-left:3px solid #168bce;padding:9px 10px;margin-bottom:7px}
.kcard .t{font-size:.74rem;font-weight:650;color:#17232e;line-height:1.35}
.kcard .m{font-size:.6rem;color:#748392;margin-top:4px}
.kcard .s{float:right;font:600 1.15rem var(--display);color:#1c2b37}
</style>
"""

STEPS = [("Analyse", "AI reads feedback, study & sales", "ai"),
         ("Pick insights", "Gate 1 · accept what matters", "pm"),
         ("Draft & self-check", "AI writes + reviews requirements", "ai"),
         ("Decide", "Gate 2 · approve, change, reject", "pm")]


def stepper(states: list[str]) -> None:
    """states: 'done' | 'now' | 'todo' for each of the 4 steps."""
    cells = "".join(
        f'<div class="step {k} {s}"><span class="who">{"AI" if k == "ai" else "YOU"}</span>'
        f'<span class="n">{i + 1:02d}</span><b>{e(t)}</b><small>{"✓ done" if s == "done" else e(sub)}</small></div>'
        for i, ((t, sub, k), s) in enumerate(zip(STEPS, states)))
    st.html(STEPPER_CSS + f'<div class="stepper">{cells}</div>')


def evidence_meter(verified: int, partial: int, assumptions: int, unverified: int) -> str:
    total = max(1, verified + partial + assumptions + unverified)
    parts = [("Verified evidence", verified, "#187b58"), ("Paraphrased", partial, "#7fbf9f"),
             ("Assumptions", assumptions, "#c8912f"), ("Unverified", unverified, "#a93342")]
    bar = "".join(f'<i style="width:{n / total * 100:.0f}%;background:{c}"></i>' for _, n, c in parts if n)
    legend = "".join(f'<span style="--c:{c}">{e(label)} {n}</span>' for label, n, c in parts if n)
    return STEPPER_CSS + f'<div class="meter">{bar}</div><div class="meter-legend">{legend}</div>'
