import json

import streamlit as st

from src.core.store import STATUSES, read_events
from src.ui.common import context, get_scope, ranked_requirements
from src.ui.theme import callout, e, page_head, pill, side_title, stat

vehicle, markets = get_scope()
ctx = context(vehicle, markets)
ws = ctx["ws"]

h1, h2 = st.columns([4, 1])
with h1:
    page_head("Human in the loop", "PM decision queue",
              "Approve, modify, postpone or reject each proposal, with rationale captured alongside the evidence.")
h2.download_button("Export audit JSON", json.dumps(read_events(ws["key"]), indent=2, ensure_ascii=False),
                   file_name=f"{ws['key']}_audit.json", mime="application/json")

left, right = st.columns([1.6, 0.7], gap="medium")
with left:
    pending_ins = [i for i in ws["insights"] if i["status"] == "proposed"]
    with st.container(border=True):
        st.markdown(f"### Gate 1 · insights pending ({len(pending_ins)})")
        if not ws["insights"]:
            st.caption("No insights generated yet.")
        elif not pending_ins:
            st.caption("All insights reviewed.")
        for ins in pending_ins:
            c1, c2 = st.columns([5, 1])
            c1.html(f'<div class="req-title">{e(ins["id"])} · {e(ins["title"])}</div>'
                    f'<div class="req-sub">{e(ins["evidence_basis"].replace("_", " "))} · {len(ins["evidence"])} evidence items</div>')
            if c2.button("Review", key=f"ri_{ins['id']}"):
                st.switch_page("views/insights.py")

    scored, sens = ranked_requirements(ws)
    with st.container(border=True):
        pending = [r for r in ws["requirements"] if r["status"] == "proposed"]
        st.markdown(f"### Gate 2 · requirements pending ({len(pending)})")
        if scored is None:
            st.caption("No requirements generated yet.")
        else:
            order = scored.set_index("id")
            for r in sorted(pending, key=lambda x: order.loc[x["id"], "rank"]):
                c1, c2 = st.columns([5, 1])
                flags = ""
                if r["confidence"] == "low":
                    flags += pill("low confidence", "warn")
                if not bool(sens.loc[r["id"], "robust"]):
                    flags += pill("rank sensitive", "warn")
                c1.html(f'<div class="req-title">{e(r["title"])}</div>'
                        f'<div class="req-sub">{e(r["id"])} · priority {order.loc[r["id"], "priority_score"]:.0f} · '
                        f'#{int(order.loc[r["id"], "rank"])} · {r["computed"]["voice_volume_raw"]} tagged records</div>{flags}')
                if c2.button("Review", key=f"rr_{r['id']}"):
                    st.session_state["focus_req"] = r["id"]
                    st.switch_page("views/requirements.py")
            if not pending:
                st.caption("No open proposals — every requirement has a PM decision.")

with right:
    with st.container(border=True):
        counts = {s: sum(r["status"] == s for r in ws["requirements"]) for s in STATUSES}
        st.html(side_title("Review record", "PM CONTROL") + "".join(stat(s.capitalize(), n) for s, n in counts.items())
                + callout("Before approval", "Check the requirement is customer-facing, actionable, realistic for the chosen derivative, "
                          "and grounded in evidence that applies to the selected market.")
                + callout("Decision rules", "Every decision needs a written rationale. Modifying keeps the previous wording in the version "
                          "history. All actions are appended to the audit log.", warn=True))
