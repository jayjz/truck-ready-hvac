"""Streamlit entry point for Truck Ready HVAC.

Minimal, focused UI around the single closed loop:
jobs + stock → pre-departure checklist → offline export.
"""

from __future__ import annotations

import streamlit as st

from truck_ready.core import build_pre_departure_checklist
from truck_ready.export import checklist_to_json_string
from truck_ready.seed import demo_inventory, demo_jobs

st.set_page_config(
    page_title="Truck Ready HVAC",
    page_icon="TR",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Truck Ready HVAC")
st.caption("Pre-departure parts checklist — stage the right parts, finish more jobs first visit.")

with st.sidebar:
    st.header("Demo Controls")
    use_demo = st.button("Load Demo Company", type="primary", use_container_width=True)
    st.divider()
    st.markdown(
        """
        **Closed loop**
        1. Jobs + truck stock
        2. Parts availability
        3. Pre-departure checklist
        4. Offline export
        """
    )

if use_demo or "checklist" not in st.session_state:
    jobs = demo_jobs()
    inventory = demo_inventory()
    checklist = build_pre_departure_checklist(jobs=jobs, inventory=inventory, tech_id="TCH-01")
    st.session_state["checklist"] = checklist
    st.session_state["jobs"] = jobs
    st.session_state["inventory"] = inventory

checklist = st.session_state["checklist"]

# KPI row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Jobs Covered", len(checklist.jobs_covered))
col2.metric("Readiness Score", f"{checklist.overall_readiness_score:.0%}")
col3.metric("Ready to Stage", len(checklist.items_to_stage))
col4.metric("Missing / Pick Up", len(checklist.items_missing))

st.info(checklist.summary)

tab_stage, tab_missing, tab_reorder, tab_export = st.tabs(
    ["Stage These", "Missing — Pick Up", "Reorder Suggestions", "Offline Export"]
)

with tab_stage:
    if not checklist.items_to_stage:
        st.success("Nothing to stage — or no parts mapped yet.")
    else:
        for item in checklist.items_to_stage:
            st.markdown(
                f"**{item.sku}** — {item.name}  
"
                f"Qty: `{item.quantity}` | Urgency: `{item.urgency.value}` | Jobs: {', '.join(item.related_jobs)}"
            )

with tab_missing:
    if not checklist.items_missing:
        st.success("No missing parts. Truck is ready.")
    else:
        for item in checklist.items_missing:
            st.error(
                f"**{item.sku}** — {item.name}  
"
                f"Need: `{item.quantity}` more | {item.notes} | Jobs: {', '.join(item.related_jobs)}"
            )

with tab_reorder:
    if not checklist.reorder_suggestions:
        st.write("No reorder suggestions right now.")
    else:
        for item in checklist.reorder_suggestions:
            st.warning(
                f"**{item.sku}** — {item.name}  
"
                f"Suggested qty: `{item.quantity}` | {item.notes}"
            )

with tab_export:
    st.markdown("Download a self-contained JSON checklist the tech can open offline.")
    json_payload = checklist_to_json_string(checklist)
    st.download_button(
        label="Download Offline Checklist (JSON)",
        data=json_payload,
        file_name="truck_ready_checklist.json",
        mime="application/json",
        use_container_width=True,
    )
    with st.expander("Preview JSON"):
        st.code(json_payload, language="json")
