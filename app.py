"""Streamlit entry point for Truck Ready HVAC.

Minimal, focused UI around the single closed loop:
jobs + stock → pre-departure checklist → offline export (JSON + PDF).

Supports demo data and real contractor CSV uploads.
"""

from __future__ import annotations

import streamlit as st

from truck_ready.core import build_pre_departure_checklist
from truck_ready.export import checklist_to_json_string
from truck_ready.io import CSVLoadError, load_inventory_csv, load_jobs_csv
from truck_ready.pdf import checklist_to_pdf_bytes
from truck_ready.seed import demo_inventory, demo_jobs

st.set_page_config(
    page_title="Truck Ready HVAC",
    page_icon="TR",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Truck Ready HVAC")
st.caption(
    "Pre-departure parts checklist — stage the right parts, "
    "finish more jobs first visit."
)

with st.sidebar:
    st.header("Data Source")
    source = st.radio(
        "Load from",
        options=["Demo company", "Upload CSVs"],
        index=0,
    )

    jobs = None
    inventory = None
    load_error: str | None = None

    if source == "Demo company":
        if st.button("Load Demo Company", type="primary", use_container_width=True):
            st.session_state.pop("checklist", None)
        jobs = demo_jobs()
        inventory = demo_inventory()
    else:
        inv_file = st.file_uploader(
            "Inventory CSV",
            type=["csv"],
            help="See docs/CSV_FORMAT.md for required columns.",
        )
        jobs_file = st.file_uploader(
            "Jobs CSV",
            type=["csv"],
            help="job_type is enough to start; required_parts is optional.",
        )
        if inv_file is not None and jobs_file is not None:
            try:
                inventory = load_inventory_csv(inv_file)
                jobs = load_jobs_csv(jobs_file)
            except CSVLoadError as exc:
                load_error = str(exc)
        elif inv_file is not None or jobs_file is not None:
            st.info("Upload both inventory.csv and jobs.csv to generate a checklist.")

    st.divider()
    st.markdown(
        """
        **Closed loop**
        1. Jobs + truck stock
        2. Parts availability
        3. Pre-departure checklist
        4. Offline export (JSON + PDF)
        """
    )
    st.caption("CSV column reference: docs/CSV_FORMAT.md")

if load_error:
    st.error(f"Could not load CSVs: {load_error}")
    st.stop()

if jobs is None or inventory is None:
    # First paint or incomplete upload — fall back to demo so the UI is never empty.
    jobs = demo_jobs()
    inventory = demo_inventory()

if (
    "checklist" not in st.session_state
    or st.session_state.get("_jobs_id") != id(jobs)
    or st.session_state.get("_inv_id") != id(inventory)
):
    checklist = build_pre_departure_checklist(
        jobs=jobs,
        inventory=inventory,
        tech_id="TCH-01",
    )
    st.session_state["checklist"] = checklist
    st.session_state["_jobs_id"] = id(jobs)
    st.session_state["_inv_id"] = id(inventory)

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
                f"**{item.sku}** — {item.name}  \n"
                f"Qty: `{item.quantity}` | Urgency: `{item.urgency.value}` | "
                f"Jobs: {', '.join(item.related_jobs)}"
            )

with tab_missing:
    if not checklist.items_missing:
        st.success("No missing parts. Truck is ready.")
    else:
        for item in checklist.items_missing:
            st.error(
                f"**{item.sku}** — {item.name}  \n"
                f"Need: `{item.quantity}` more | {item.notes} | "
                f"Jobs: {', '.join(item.related_jobs)}"
            )

with tab_reorder:
    if not checklist.reorder_suggestions:
        st.write("No reorder suggestions right now.")
    else:
        for item in checklist.reorder_suggestions:
            st.warning(
                f"**{item.sku}** — {item.name}  \n"
                f"Suggested qty: `{item.quantity}` | {item.notes}"
            )

with tab_export:
    st.markdown(
        "Download a self-contained checklist the tech can use offline or print."
    )
    col_json, col_pdf = st.columns(2)

    with col_json:
        json_payload = checklist_to_json_string(checklist)
        st.download_button(
            label="Download Offline Checklist (JSON)",
            data=json_payload,
            file_name="truck_ready_checklist.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_pdf:
        pdf_bytes = checklist_to_pdf_bytes(checklist)
        st.download_button(
            label="Download Printable Checklist (PDF)",
            data=pdf_bytes,
            file_name="truck_ready_checklist.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )

    with st.expander("Preview JSON"):
        st.code(json_payload, language="json")
