"""Streamlit entry point for Truck Ready HVAC — redesigned UI.

Thin presentation layer only. All domain logic lives in truck_ready.*
Drop-in replacement for the original app.py — zero backend changes.
"""

from __future__ import annotations

import streamlit as st
import hashlib

from truck_ready.core import build_pre_departure_checklist, check_all_jobs
from truck_ready.export import checklist_to_json_string
from truck_ready.io import CSVLoadError, load_inventory_csv, load_jobs_csv
from truck_ready.models import ChecklistItem, Urgency
from truck_ready.pdf import checklist_to_pdf_bytes
from truck_ready.seed import demo_inventory, demo_jobs

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Truck Ready HVAC",
    page_icon="TR",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');

    /* ── Root variables ── */
    :root {
        --bg-base:        #0d1117;
        --bg-surface:     #161b22;
        --bg-elevated:    #1c2330;
        --bg-hover:       #21282f;
        --border:         #30363d;
        --border-subtle:  #21262d;

        --text-primary:   #e6edf3;
        --text-secondary: #8b949e;
        --text-muted:     #484f58;

        --accent-blue:    #1f6feb;
        --accent-blue-bg: #0d1f38;

        --green:          #3fb950;
        --green-bg:       #0d2818;
        --green-border:   #1a4428;

        --red:            #f85149;
        --red-bg:         #2d1216;
        --red-border:     #4a1e22;

        --orange:         #e3b341;
        --orange-bg:      #2d2007;
        --orange-border:  #4a3408;

        --critical:       #ff6b6b;
        --critical-bg:    rgba(255,107,107,0.12);
        --high:           #ffa94d;
        --high-bg:        rgba(255,169,77,0.12);
        --medium:         #74c0fc;
        --medium-bg:      rgba(116,192,252,0.12);
        --low:            #8b949e;
        --low-bg:         rgba(139,148,158,0.10);

        --font-ui:   'IBM Plex Sans', sans-serif;
        --font-mono: 'IBM Plex Mono', monospace;

        --radius-sm: 4px;
        --radius-md: 8px;
        --radius-lg: 12px;
    }

    /* ── Global reset ── */
    html, body, [class*="css"] {
        font-family: var(--font-ui) !important;
        background-color: var(--bg-base) !important;
        color: var(--text-primary) !important;
    }

    /* Hide Streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
    .block-container {
        padding: 1.5rem 2rem 3rem !important;
        max-width: 1400px !important;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: var(--bg-surface) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] * {
        color: var(--text-primary) !important;
    }
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stFileUploader label {
        color: var(--text-secondary) !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    /* ── Buttons ── */
    .stButton > button {
        background-color: var(--accent-blue) !important;
        color: #fff !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        font-family: var(--font-ui) !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.55rem 1.1rem !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button:hover {
        background-color: #388bfd !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(31,111,235,0.35) !important;
    }
    .stDownloadButton > button {
        border-radius: var(--radius-md) !important;
        font-family: var(--font-ui) !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        transition: all 0.15s ease !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent !important;
        border-bottom: 1px solid var(--border) !important;
        gap: 0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        color: var(--text-secondary) !important;
        font-family: var(--font-ui) !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        padding: 0.65rem 1.2rem !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0 !important;
        transition: all 0.15s ease;
    }
    .stTabs [aria-selected="true"] {
        color: var(--text-primary) !important;
        border-bottom: 2px solid var(--accent-blue) !important;
        background-color: transparent !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding: 1.5rem 0 !important;
    }

    /* ── Metrics ── */
    [data-testid="stMetric"] {
        background-color: var(--bg-surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-lg) !important;
        padding: 1.1rem 1.3rem !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.07em;
    }
    [data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
        font-family: var(--font-mono) !important;
        font-size: 1.9rem !important;
        font-weight: 600 !important;
    }

    /* ── Expanders ── */
    [data-testid="stExpander"] {
        background-color: var(--bg-surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
    }
    [data-testid="stExpander"] summary {
        color: var(--text-secondary) !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
    }

    /* ── Code blocks ── */
    .stCodeBlock {
        border-radius: var(--radius-md) !important;
    }

    /* ── Divider ── */
    hr { border-color: var(--border) !important; }

    /* ── Info / Error / Warning alerts ── */
    [data-testid="stAlert"] {
        border-radius: var(--radius-md) !important;
        font-size: 0.88rem !important;
    }

    /* ── File uploader ── */
    [data-testid="stFileUploader"] {
        background-color: var(--bg-surface) !important;
        border: 1px dashed var(--border) !important;
        border-radius: var(--radius-md) !important;
        padding: 0.5rem !important;
    }

    /* ── Custom component styles ── */
    .tr-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        padding: 0 0 1.5rem 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 1.75rem;
    }
    .tr-header-brand {
        display: flex;
        align-items: center;
        gap: 0.9rem;
    }
    .tr-logo {
        width: 42px;
        height: 42px;
        background: linear-gradient(135deg, var(--accent-blue), #58a6ff);
        border-radius: var(--radius-md);
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-weight: 600;
        font-size: 0.95rem;
        color: #fff;
        letter-spacing: -0.03em;
        flex-shrink: 0;
    }
    .tr-header-text h1 {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        margin: 0 0 0.1rem 0 !important;
        padding: 0 !important;
        line-height: 1.2 !important;
    }
    .tr-header-text p {
        font-size: 0.8rem;
        color: var(--text-secondary);
        margin: 0;
    }
    .tr-header-meta {
        text-align: right;
    }
    .tr-header-meta .ts {
        font-family: var(--font-mono);
        font-size: 0.72rem;
        color: var(--text-muted);
    }
    .tr-header-meta .tech-badge {
        display: inline-block;
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 0.2rem 0.7rem;
        font-size: 0.72rem;
        font-family: var(--font-mono);
        color: var(--text-secondary);
        margin-top: 0.3rem;
    }

    /* Readiness banner */
    .tr-readiness-bar {
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1rem 1.4rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1.2rem;
    }
    .tr-readiness-score {
        font-family: var(--font-mono);
        font-size: 2.2rem;
        font-weight: 700;
        color: var(--text-primary);
        white-space: nowrap;
    }
    .tr-readiness-label {
        font-size: 0.72rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.3rem;
    }
    .tr-progress-track {
        flex: 1;
        height: 8px;
        background: var(--bg-elevated);
        border-radius: 99px;
        overflow: hidden;
    }
    .tr-progress-fill {
        height: 100%;
        border-radius: 99px;
        transition: width 0.6s ease;
    }
    .tr-summary-text {
        font-size: 0.85rem;
        color: var(--text-secondary);
        margin-top: 0.3rem;
    }

    /* Section headers inside tabs */
    .tr-section-label {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--text-muted);
        margin-bottom: 0.6rem;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid var(--border-subtle);
    }

    /* Checklist item card */
    .tr-item {
        display: flex;
        align-items: flex-start;
        gap: 0.9rem;
        padding: 0.85rem 1rem;
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        margin-bottom: 0.5rem;
        transition: border-color 0.12s ease, background 0.12s ease;
    }
    .tr-item:hover {
        background: var(--bg-hover);
        border-color: #3d444d;
    }
    .tr-item-checkbox {
        width: 18px;
        height: 18px;
        border: 2px solid var(--border);
        border-radius: 4px;
        flex-shrink: 0;
        margin-top: 2px;
    }
    .tr-item-body { flex: 1; min-width: 0; }
    .tr-item-top {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        flex-wrap: wrap;
        margin-bottom: 0.3rem;
    }
    .tr-sku {
        font-family: var(--font-mono);
        font-size: 0.78rem;
        font-weight: 600;
        color: var(--text-primary);
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        border-radius: var(--radius-sm);
        padding: 0.1rem 0.45rem;
        white-space: nowrap;
    }
    .tr-name {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-primary);
    }
    .tr-item-meta {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
    }
    .tr-qty {
        font-family: var(--font-mono);
        font-size: 0.75rem;
        color: var(--text-secondary);
    }
    .tr-qty strong {
        color: var(--text-primary);
        font-weight: 600;
    }
    .tr-note {
        font-size: 0.75rem;
        color: var(--text-muted);
    }
    .tr-job-tag {
        display: inline-block;
        font-family: var(--font-mono);
        font-size: 0.68rem;
        color: var(--accent-blue);
        background: var(--accent-blue-bg);
        border: 1px solid rgba(31,111,235,0.3);
        border-radius: 3px;
        padding: 0.05rem 0.35rem;
        white-space: nowrap;
    }

    /* Urgency badges */
    .tr-urgency {
        display: inline-block;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        border-radius: 3px;
        padding: 0.12rem 0.45rem;
        white-space: nowrap;
    }
    .urg-critical { color: var(--critical); background: var(--critical-bg); }
    .urg-high     { color: var(--high);     background: var(--high-bg); }
    .urg-medium   { color: var(--medium);   background: var(--medium-bg); }
    .urg-low      { color: var(--low);      background: var(--low-bg); }

    /* Action indicator stripe */
    .tr-item.action-stage   { border-left: 3px solid var(--green); }
    .tr-item.action-missing { border-left: 3px solid var(--red); }
    .tr-item.action-reorder { border-left: 3px solid var(--orange); }

    /* Empty state */
    .tr-empty {
        text-align: center;
        padding: 2.5rem 1rem;
        color: var(--text-muted);
        font-size: 0.85rem;
    }
    .tr-empty-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
        opacity: 0.4;
    }

    /* Job card in sidebar */
    .tr-job-card {
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 0.7rem 0.85rem;
        margin-bottom: 0.5rem;
    }
    .tr-job-card .jid {
        font-family: var(--font-mono);
        font-size: 0.7rem;
        color: var(--accent-blue);
        margin-bottom: 0.15rem;
    }
    .tr-job-card .jname {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.1rem;
    }
    .tr-job-card .jtype {
        font-size: 0.72rem;
        color: var(--text-muted);
    }
    .tr-job-card .jtech {
        display: inline-block;
        font-family: var(--font-mono);
        font-size: 0.65rem;
        color: var(--text-secondary);
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: 3px;
        padding: 0.05rem 0.35rem;
        margin-top: 0.3rem;
    }
    .tr-job-score {
        display: inline-block;
        font-family: var(--font-mono);
        font-size: 0.68rem;
        font-weight: 600;
        border-radius: 3px;
        padding: 0.1rem 0.4rem;
        float: right;
        margin-top: 0.1rem;
    }
    .score-ready  { color: var(--green);  background: var(--green-bg); }
    .score-warn   { color: var(--orange); background: var(--orange-bg); }
    .score-danger { color: var(--red);    background: var(--red-bg); }

    /* Export section */
    .tr-export-card {
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.4rem 1.6rem;
    }
    .tr-export-card h4 {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        margin: 0 0 0.25rem 0 !important;
    }
    .tr-export-card p {
        font-size: 0.78rem;
        color: var(--text-secondary);
        margin: 0 0 1rem 0;
    }

    /* Sidebar section labels */
    .sb-label {
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--text-muted);
        margin: 1.2rem 0 0.5rem 0;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-base); }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _urgency_badge(urgency: Urgency) -> str:
    cls = {
        Urgency.CRITICAL: "urg-critical",
        Urgency.HIGH: "urg-high",
        Urgency.MEDIUM: "urg-medium",
        Urgency.LOW: "urg-low",
    }[urgency]
    return f'<span class="tr-urgency {cls}">{urgency.value}</span>'


def _job_tags(jobs: list[str]) -> str:
    return " ".join(f'<span class="tr-job-tag">{j}</span>' for j in jobs)


def _render_checklist_item(item: ChecklistItem, action_class: str) -> str:
    badge = _urgency_badge(item.urgency)
    tags = _job_tags(item.related_jobs)
    note_html = f'<span class="tr-note">{item.notes}</span>' if item.notes else ""
    return f"""
    <div class="tr-item {action_class}">
        <div class="tr-item-checkbox"></div>
        <div class="tr-item-body">
            <div class="tr-item-top">
                <span class="tr-sku">{item.sku}</span>
                <span class="tr-name">{item.name}</span>
                {badge}
            </div>
            <div class="tr-item-meta">
                <span class="tr-qty">Qty: <strong>{item.quantity}</strong></span>
                {tags}
                {note_html}
            </div>
        </div>
    </div>
    """


def _readiness_color(score: float) -> str:
    if score >= 0.8:
        return "var(--green)"
    if score >= 0.5:
        return "var(--orange)"
    return "var(--red)"

def _hash_data(data) -> str:
    """Generate a deterministic hash for Pydantic model lists."""
    return hashlib.md5(str(data).encode("utf-8")).hexdigest()

# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="sb-label">Data Source</p>', unsafe_allow_html=True)
    source = st.radio(
        "Load from",
        options=["Demo Company", "Upload CSVs"],
        index=0,
        label_visibility="collapsed",
    )

    jobs = None
    inventory = None
    load_error: str | None = None

    if source == "Demo Company":
        if st.button("Reload Demo Data", use_container_width=True):
            st.session_state.pop("checklist", None)
            st.session_state.pop("_jobs_id", None)
            st.session_state.pop("_inv_id", None)
        jobs = demo_jobs()
        inventory = demo_inventory()
    else:
        st.markdown(
            '<p style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">'
            "Upload two CSVs — see docs/CSV_FORMAT.md for column specs.</p>",
            unsafe_allow_html=True,
        )
        inv_file = st.file_uploader("Inventory CSV", type=["csv"], key="inv_up")
        jobs_file = st.file_uploader("Jobs CSV", type=["csv"], key="jobs_up")

        if inv_file is not None and jobs_file is not None:
            try:
                inventory = load_inventory_csv(inv_file)
                jobs = load_jobs_csv(jobs_file)
            except CSVLoadError as exc:
                load_error = str(exc)
        elif inv_file is not None or jobs_file is not None:
            st.info("Upload both files to generate a checklist.")

        # --- NEW: CSV Template Downloads ---
        st.markdown('<p class="sb-label">Templates</p>', unsafe_allow_html=True)
        st.download_button(
            label="Download Inventory Template",
            data="sku,name,quantity,reorder_point,unit_cost,category\n",
            file_name="inventory_template.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            label="Download Jobs Template",
            data="job_id,job_type,customer_name,scheduled_date,assigned_tech,notes,required_parts\n",
            file_name="jobs_template.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # Fallback so UI is never empty
    if jobs is None or inventory is None:
        jobs = demo_jobs()
        inventory = demo_inventory()

    # --- UPDATED: Deterministic Hashing ---
    current_jobs_hash = _hash_data(jobs)
    current_inv_hash = _hash_data(inventory)

    # Build or reuse cached checklist using content hashes instead of id()
    if (
        "checklist" not in st.session_state
        or st.session_state.get("_jobs_hash") != current_jobs_hash
        or st.session_state.get("_inv_hash") != current_inv_hash
    ):
        checklist = build_pre_departure_checklist(
            jobs=jobs,
            inventory=inventory,
            tech_id="TCH-01",
        )
        st.session_state["checklist"] = checklist
        st.session_state["_jobs_hash"] = current_jobs_hash
        st.session_state["_inv_hash"] = current_inv_hash
        st.session_state["_jobs_obj"] = jobs
        st.session_state["_inv_obj"] = inventory

    checklist = st.session_state["checklist"]
    _jobs_for_sidebar = st.session_state.get("_jobs_obj", jobs)
    _inv_for_sidebar = st.session_state.get("_inv_obj", inventory)

    # Per-job breakdown
    st.markdown('<p class="sb-label">Jobs Today</p>', unsafe_allow_html=True)
    job_results = check_all_jobs(_jobs_for_sidebar, _inv_for_sidebar)
    for job, result in zip(_jobs_for_sidebar, job_results):
        score_pct = result.availability_score
        if score_pct >= 0.8:
            score_cls = "score-ready"
        elif score_pct >= 0.5:
            score_cls = "score-warn"
        else:
            score_cls = "score-danger"

        jtype_display = job.job_type.replace("_", " ")
        tech_html = (
            f'<span class="jtech">{job.assigned_tech}</span>'
            if job.assigned_tech
            else ""
        )
        st.markdown(
            f"""
            <div class="tr-job-card">
                <span class="tr-job-score {score_cls}">{score_pct:.0%}</span>
                <div class="jid">{job.job_id}</div>
                <div class="jname">{job.customer_name}</div>
                <div class="jtype">{jtype_display}</div>
                {tech_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<p class="sb-label">About</p>', unsafe_allow_html=True)
    st.markdown(
        """
        <p style="font-size:0.75rem;color:var(--text-muted);line-height:1.6;margin:0;">
        Jobs + truck stock &rarr; pre-departure checklist &rarr; offline export.<br>
        Stage once. Fix it first visit.
        </p>
        """,
        unsafe_allow_html=True,
    )


# ── Error gate ──────────────────────────────────────────────────────────────────
if load_error:
    st.error(f"CSV load error: {load_error}")
    st.stop()


# ── Page header ─────────────────────────────────────────────────────────────────
generated_ts = checklist.generated_at.strftime("%Y-%m-%d %H:%M UTC")
tech_display = checklist.tech_id or "Unassigned"

st.markdown(
    f"""
    <div class="tr-header">
        <div class="tr-header-brand">
            <div class="tr-logo">TR</div>
            <div class="tr-header-text">
                <h1>Truck Ready HVAC</h1>
                <p>Pre-departure parts checklist &mdash; stage the right parts, finish more jobs first visit.</p>
            </div>
        </div>
        <div class="tr-header-meta">
            <div class="ts">{generated_ts}</div>
            <div class="tech-badge">Tech: {tech_display}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── Readiness banner ─────────────────────────────────────────────────────────────
score = checklist.overall_readiness_score
score_color = _readiness_color(score)
score_pct_int = int(score * 100)

st.markdown(
    f"""
    <div class="tr-readiness-bar">
        <div>
            <div class="tr-readiness-label">Fleet Readiness</div>
            <div class="tr-readiness-score" style="color:{score_color};">{score_pct_int}%</div>
        </div>
        <div style="flex:1;">
            <div class="tr-readiness-label">Score across {len(checklist.jobs_covered)} job(s)</div>
            <div class="tr-progress-track">
                <div class="tr-progress-fill" style="width:{score_pct_int}%;background:{score_color};"></div>
            </div>
            <div class="tr-summary-text">{checklist.summary}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── KPI strip ────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Jobs Covered", len(checklist.jobs_covered))
k2.metric("Ready to Stage", len(checklist.items_to_stage))
k3.metric("Missing / Pick Up", len(checklist.items_missing))
k4.metric("Reorder Needed", len(checklist.reorder_suggestions))

st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)


# ── Main tabs ────────────────────────────────────────────────────────────────────
stage_count = len(checklist.items_to_stage)
missing_count = len(checklist.items_missing)
reorder_count = len(checklist.reorder_suggestions)

tab_stage, tab_missing, tab_reorder, tab_export = st.tabs(
    [
        f"Stage These  ({stage_count})",
        f"Missing — Pick Up  ({missing_count})",
        f"Reorder  ({reorder_count})",
        "Offline Export",
    ]
)


# ── Tab: Stage ───────────────────────────────────────────────────────────────────
with tab_stage:
    st.markdown(
        '<p class="tr-section-label">Parts already on truck — load before departure</p>',
        unsafe_allow_html=True,
    )
    if not checklist.items_to_stage:
        st.markdown(
            '<div class="tr-empty">'
            '<div class="tr-empty-icon">[OK]</div>'
            "<div>No parts to stage — checklist is clear.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        html_rows = "".join(
            _render_checklist_item(item, "action-stage")
            for item in checklist.items_to_stage
        )
        st.markdown(html_rows, unsafe_allow_html=True)


# ── Tab: Missing ─────────────────────────────────────────────────────────────────
with tab_missing:
    st.markdown(
        '<p class="tr-section-label">Parts not on truck — pick up before rolling</p>',
        unsafe_allow_html=True,
    )
    if not checklist.items_missing:
        st.markdown(
            '<div class="tr-empty">'
            '<div class="tr-empty-icon">[OK]</div>'
            "<div>No missing parts. Truck is ready to roll.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        html_rows = "".join(
            _render_checklist_item(item, "action-missing")
            for item in checklist.items_missing
        )
        st.markdown(html_rows, unsafe_allow_html=True)


# ── Tab: Reorder ─────────────────────────────────────────────────────────────────
with tab_reorder:
    st.markdown(
        '<p class="tr-section-label">Parts below reorder point or absent from inventory</p>',
        unsafe_allow_html=True,
    )
    if not checklist.reorder_suggestions:
        st.markdown(
            '<div class="tr-empty">'
            '<div class="tr-empty-icon">[OK]</div>'
            "<div>Stock levels are healthy. No reorders needed.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        html_rows = "".join(
            _render_checklist_item(item, "action-reorder")
            for item in checklist.reorder_suggestions
        )
        st.markdown(html_rows, unsafe_allow_html=True)


# ── Tab: Export ──────────────────────────────────────────────────────────────────
with tab_export:
    json_payload = checklist_to_json_string(checklist)
    pdf_bytes = checklist_to_pdf_bytes(checklist)

    col_json, col_pdf = st.columns(2, gap="medium")

    with col_json:
        st.markdown(
            """
            <div class="tr-export-card">
                <h4>Offline JSON</h4>
                <p>Self-contained payload — works on any device, zero signal required.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.download_button(
            label="Download truck_ready_checklist.json",
            data=json_payload,
            file_name="truck_ready_checklist.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_pdf:
        st.markdown(
            """
            <div class="tr-export-card">
                <h4>Printable PDF</h4>
                <p>Print-ready checklist with checkboxes — hand to the tech before departure.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.download_button(
            label="Download truck_ready_checklist.pdf",
            data=pdf_bytes,
            file_name="truck_ready_checklist.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    with st.expander("Preview JSON payload"):
        st.code(json_payload, language="json")
