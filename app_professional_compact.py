from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# OpsPilot — compact executive dashboard.
# This is a separate file; the original dashboard files remain untouched.
st.set_page_config(
    page_title="OpsPilot | Business Operations",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- Visual system ----------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root {
      --ink:#f4f5fb; --muted:#9b9bb2; --line:#29293b;
      --paper:#090910; --panel:#11111b; --panel2:#151521;
      --purple:#8b5cf6; --purple2:#6d4aff;
    }
    html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
    .stApp { background:var(--paper); color:var(--ink); }
    .block-container { padding-top:1.35rem; padding-bottom:2.2rem; max-width:1680px; }
    [data-testid="stHeader"] { background:rgba(9,9,16,.94); }
    [data-testid="stSidebar"] {
      background:#0c0c14; border-right:1px solid #262638;
    }
    [data-testid="stSidebar"] * { color:#e8e8f4; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#9b9bb2; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:.65rem; }
    [data-testid="stSidebar"] [data-testid="stButton"] button {
      background:#151520; border:1px solid #2c2c40; color:#eeeaff;
      border-radius:11px; min-height:2.7rem;
    }
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {
      background:#6741d9; border-color:#7954ed;
    }
    h1,h2,h3 { font-family:'Manrope',sans-serif !important; color:#f5f5fb !important; letter-spacing:-.035em; }
    h1 { font-size:2.05rem !important; font-weight:800 !important; }
    h2 { font-size:1.22rem !important; font-weight:750 !important; }
    h3 { font-size:1rem !important; font-weight:700 !important; }
    p, label, .stMarkdown, [data-testid="stCaptionContainer"] { color:#b4b4c8; }
    [data-testid="stMetric"] {
      background:linear-gradient(145deg,#151521,#101019);
      border:1px solid #2b2b3e; padding:19px 20px; border-radius:17px;
      box-shadow:0 8px 24px rgba(0,0,0,.13); min-height:120px;
    }
    [data-testid="stMetricLabel"] { color:#a7a7bd !important; font-size:.8rem !important; font-weight:600 !important; }
    [data-testid="stMetricValue"] { color:#fff !important; font-family:'Manrope',sans-serif; font-weight:800 !important; font-size:1.85rem !important; }
    [data-testid="stVerticalBlockBorderWrapper"] {
      border-radius:16px; border-color:#2a2a3d !important; background:#11111b;
    }
    div[data-testid="stPlotlyChart"] {
      background:#11111b; border:1px solid #29293b; padding:9px 9px 0;
      border-radius:16px;
    }
    div[data-testid="stDataFrame"] { border:1px solid #29293b; border-radius:13px; overflow:hidden; }
    .stButton button { border-radius:10px; font-weight:650; }
    .stTextInput input { border-radius:10px; }
    [data-baseweb="select"] > div, [data-baseweb="input"] > div {
      background:#151520; border-color:#303044;
    }
    .ops-eyebrow { text-transform:uppercase; letter-spacing:.16em; color:#ad91ff; font-size:.68rem; font-weight:800; margin-bottom:.35rem; }
    .ops-subtitle { color:#9b9bb0; margin-top:-.4rem; font-size:.92rem; }
    .ops-banner {
      background:linear-gradient(115deg,#1b1730,#151523 65%,#11111b);
      border:1px solid #35294e; border-radius:16px; padding:18px 21px;
      color:#fff; margin:.8rem 0 1.1rem;
    }
    .ops-banner-title { font-family:'Manrope',sans-serif; font-size:1.08rem; font-weight:800; color:#fff; }
    .ops-banner-copy { color:#b9b5ce; font-size:.84rem; margin-top:5px; }
    .ops-status {
      display:inline-block; border-radius:999px; padding:7px 10px;
      font-size:.66rem; letter-spacing:.045em; font-weight:800;
      border:1px solid #3a3a4e; background:#171722; color:#d0cde2;
    }
    .ops-status-live { background:#142a27; color:#66dfbb; border-color:#214d43; }
    .ops-status-csv { background:#2b2415; color:#f2cb7d; border-color:#51401d; }
    .ops-status-error { background:#30191f; color:#ff9da8; border-color:#5b2934; }
    .small-muted { color:#8989a2; font-size:.77rem; }
    .section-note { color:#85859d; font-size:.8rem; margin-top:-.55rem; }
    .stAlert { border-radius:12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

EXPECTED_COLUMNS = [
    "Request ID", "Request Description", "Requester Name", "Department",
    "Request Type", "Customer Email", "AI Summary", "AI Priority",
    "Recommended Department", "Suggested Action", "Status", "Submitted At",
]
COLUMN_ALIASES = {
    "Request ID": ["Request ID", "request_id", "requestId"],
    "Request Description": ["Request Description", "Request description", "request_description"],
    "Requester Name": ["Requester Name", "Requester Name.", "requester_name"],
    "Department": ["Department", "department"],
    "Request Type": ["Request Type", "request_type"],
    "Customer Email": ["Customer Email", "customer_email"],
    "AI Summary": ["AI Summary", "AI summary", "summary"],
    "AI Priority": ["AI Priority", "AI Priority ", "priority", "Priority"],
    "Recommended Department": ["Recommended Department", "Recommended Departm", "recommended_department"],
    "Suggested Action": ["Suggested Action", "suggested_action"],
    "Status": ["Status", "status"],
    "Submitted At": ["Submitted At", "Submitted at", "submittedAt", "submitted_at"],
}
RESOLVED_STATUSES = {"resolved", "closed", "completed"}


def empty_requests():
    """Return an empty dataframe with the full expected schema."""
    return pd.DataFrame(columns=EXPECTED_COLUMNS)


def normalize_rows(payload):
    """Normalize supported n8n JSON shapes and known column aliases."""
    if isinstance(payload, dict):
        for key in ("data", "rows", "items", "results"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
        else:
            payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("The webhook response must be a JSON array of rows.")

    records = [
        item for item in payload
        if isinstance(item, dict) and any(value not in (None, "") for value in item.values())
    ]
    df = pd.DataFrame(records)
    if df.empty:
        return empty_requests()

    rename_map = {}
    for expected, aliases in COLUMN_ALIASES.items():
        if expected not in df.columns:
            for alias in aliases:
                if alias in df.columns:
                    rename_map[alias] = expected
                    break
    df = df.rename(columns=rename_map)

    for column in EXPECTED_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df[EXPECTED_COLUMNS].copy()
    for column in EXPECTED_COLUMNS:
        df[column] = df[column].fillna("").astype(str).str.strip()

    # Some sheet/webhook configurations accidentally include the header row as data.
    if not df.empty and df.iloc[0]["Request ID"].lower() in ("request id", "request_id"):
        df = df.iloc[1:].copy()

    df["AI Priority"] = df["AI Priority"].replace("", "Unassigned")
    df["Status"] = df["Status"].replace("", "New")
    return df.reset_index(drop=True)


@st.cache_data(ttl=20, show_spinner=False)
def fetch_live_data(webhook_url, header_name, header_value):
    """Fetch live requests from the existing authenticated n8n webhook."""
    response = requests.get(webhook_url, headers={header_name: header_value}, timeout=20)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError("n8n returned a response that is not valid JSON.") from exc
    return normalize_rows(payload)


def load_data():
    """Prefer the configured live n8n endpoint; use requests.csv only as fallback."""
    try:
        webhook_url = st.secrets.get("N8N_WEBHOOK_URL", "").strip()
        header_name = st.secrets.get("N8N_HEADER_NAME", "X-Copilot-Key").strip()
        header_value = st.secrets.get("N8N_HEADER_VALUE", "").strip()
    except Exception:
        webhook_url, header_name, header_value = "", "X-Copilot-Key", ""

    if webhook_url and header_name and header_value:
        try:
            return fetch_live_data(webhook_url, header_name, header_value), "live", None
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            if status in (401, 403):
                message = "n8n rejected dashboard credentials (401/403). Check Header Auth settings."
            else:
                message = f"The n8n webhook returned HTTP {status}. Check the latest workflow execution."
            return empty_requests(), "error", message
        except requests.exceptions.Timeout:
            return empty_requests(), "error", "The n8n request timed out. Try refreshing."
        except requests.exceptions.RequestException:
            return empty_requests(), "error", "Could not reach n8n. Check the published production URL."
        except Exception as exc:
            # Show the error message, but never print secret values or request headers.
            return empty_requests(), "error", f"Could not read the n8n response: {exc}"

    csv_path = Path(__file__).parent / "requests.csv"
    if csv_path.exists():
        try:
            csv_df = pd.read_csv(csv_path, dtype=str).fillna("")
            return normalize_rows(csv_df.to_dict(orient="records")), "csv", (
                "Live settings not found. Showing requests.csv (static data)."
            )
        except Exception as exc:
            return empty_requests(), "error", f"Could not read requests.csv: {exc}"

    return empty_requests(), "error", "No live settings found. Check .streamlit/secrets.toml."


def style_chart(fig, height=320):
    """Apply consistent dark chart styling without changing chart data."""
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color="#b2b2c7", size=12),
        margin=dict(l=14, r=14, t=22, b=14),
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, linecolor="#303044",
                   tickfont=dict(color="#a2a2b8"), title=None),
        yaxis=dict(showgrid=True, gridcolor="#29293b", zeroline=False, title=None,
                   tickfont=dict(color="#a2a2b8")),
        autosize=True,
    )
    return fig


def get_values(frame, column):
    """Sorted non-empty filter options; safe when data is empty."""
    if column not in frame.columns or frame.empty:
        return []
    return sorted({str(value).strip() for value in frame[column].fillna("").tolist() if str(value).strip()})


# ---------- Compact navigation ----------
if "ops_page" not in st.session_state:
    st.session_state["ops_page"] = "Dashboard"

with st.sidebar:
    st.markdown(
        '<div style="font-family:Manrope,sans-serif;font-size:1.42rem;font-weight:800;'
        'color:#fff;letter-spacing:-.06em">◈ OpsPilot</div>'
        '<div style="font-size:.68rem;letter-spacing:.09em;color:#9696ad;margin-top:-4px">'
        'BUSINESS OPERATIONS</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.caption("WORKSPACE")
    pages = [
        ("◫", "Dashboard"),
        ("▤", "Requests"),
        ("◷", "Analytics"),
    ]
    for symbol, page_name in pages:
        if st.button(
            f"{symbol}   {page_name}",
            key=f"nav_{page_name.lower()}",
            type="primary" if st.session_state["ops_page"] == page_name else "secondary",
            use_container_width=True,
        ):
            st.session_state["ops_page"] = page_name
            st.rerun()

    st.divider()
    if st.button("↻   Refresh data", key="refresh_data", use_container_width=True):
        st.cache_data.clear()
        st.session_state["ops_last_refresh"] = datetime.now().strftime("%d %b %Y, %H:%M:%S")
        st.rerun()
    st.markdown(
        '<div style="padding:10px 2px 0;color:#8989a2;font-size:.75rem">'
        '<span style="color:#5ed6b1">●</span> Workspace ready</div>',
        unsafe_allow_html=True,
    )

# Load data after the refresh control is declared.
df, source, load_error = load_data()
for column in EXPECTED_COLUMNS:
    if column not in df.columns:
        df[column] = ""
df = df[EXPECTED_COLUMNS].copy()
df["_submitted_datetime"] = pd.to_datetime(df["Submitted At"], errors="coerce", utc=True)

# ---------- Header and truthful connection state ----------
header_left, header_right = st.columns([3.1, 1.15], vertical_alignment="center")
with header_left:
    st.markdown('<div class="ops-eyebrow">OPERATIONS OVERVIEW</div>', unsafe_allow_html=True)
    st.title("Business command center")
    st.markdown(
        '<div class="ops-subtitle">Incoming requests, AI triage and operational workload — in one place.</div>',
        unsafe_allow_html=True,
    )
with header_right:
    if source == "live":
        st.markdown('<span class="ops-status ops-status-live">● LIVE · N8N CONNECTED</span>', unsafe_allow_html=True)
    elif source == "csv":
        st.markdown('<span class="ops-status ops-status-csv">● STATIC CSV DATA</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="ops-status ops-status-error">● CONNECTION ISSUE</span>', unsafe_allow_html=True)

if source == "csv":
    st.warning(load_error)
elif source == "error":
    st.error(load_error)
else:
    st.markdown(
        '<div class="ops-banner"><div class="ops-banner-title">Operational intelligence at a glance.</div>'
        '<div class="ops-banner-copy">Review request volume, understand AI triage and focus attention on the work '
        'that needs it most.</div></div>',
        unsafe_allow_html=True,
    )

# ---------- Collapsible filters ----------
with st.expander("⌘  Filters  ·  Department, priority, status and request type", expanded=False):
    filter_cols = st.columns(4)
    departments = get_values(df, "Department")
    priorities = get_values(df, "AI Priority")
    statuses = get_values(df, "Status")
    request_types = get_values(df, "Request Type")

    with filter_cols[0]:
        selected_departments = st.multiselect(
            "Department", departments, default=departments, key="filter_department"
        )
    with filter_cols[1]:
        selected_priorities = st.multiselect(
            "AI priority", priorities, default=priorities, key="filter_priority"
        )
    with filter_cols[2]:
        selected_statuses = st.multiselect(
            "Status", statuses, default=statuses, key="filter_status"
        )
    with filter_cols[3]:
        selected_types = st.multiselect(
            "Request type", request_types, default=request_types, key="filter_request_type"
        )
    st.caption("All available values are selected by default. Clear a selection to narrow the dashboard.")

filtered = df.copy()
for column, selection in [
    ("Department", selected_departments),
    ("AI Priority", selected_priorities),
    ("Status", selected_statuses),
    ("Request Type", selected_types),
]:
    if selection:
        filtered = filtered[filtered[column].isin(selection)]
    else:
        filtered = filtered.iloc[0:0]

# ---------- KPIs: calculated only from filtered records ----------
total = len(filtered)
high = int(filtered["AI Priority"].str.strip().str.lower().eq("high").sum()) if total else 0
resolved_mask = filtered["Status"].str.strip().str.lower().isin(RESOLVED_STATUSES)
resolved = int(resolved_mask.sum()) if total else 0
open_count = total - resolved
resolution_rate = round((resolved / total) * 100) if total else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total requests", f"{total:,}", help="Requests matching the current filters.")
k2.metric("High priority", f"{high:,}", help="Requests classified as High by the AI workflow.")
k3.metric("Open workload", f"{open_count:,}", help="Requests not marked Resolved, Closed or Completed.")
k4.metric("Resolution rate", f"{resolution_rate}%", help="Share of filtered requests marked resolved, closed or completed.")

# ---------- Dashboard / Requests / Analytics navigation ----------
page = st.session_state["ops_page"]
if page == "Dashboard":
    st.write("")
    if filtered.empty:
        st.info("No requests match the selected filters. Expand Filters and select more values, or submit a request through your existing form.")
    else:
        chart_left, chart_right = st.columns([1, 1], gap="large")
        with chart_left:
            st.subheader("Priority overview")
            st.markdown('<div class="section-note">Requests grouped by AI-assigned priority.</div>', unsafe_allow_html=True)
            priority_counts = (
                filtered["AI Priority"].replace("", "Unassigned")
                .value_counts().rename_axis("Priority").reset_index(name="Requests")
            )
            priority_colors = {
                "High": "#ef646f", "Medium": "#eab65d", "Low": "#55c7a5",
                "Unassigned": "#85859a",
            }
            fig = px.bar(
                priority_counts, x="Priority", y="Requests", color="Priority",
                color_discrete_map=priority_colors, text="Requests",
                category_orders={"Priority": ["High", "Medium", "Low", "Unassigned"]},
            )
            fig.update_traces(marker_line_width=0, textposition="outside", cliponaxis=False,
                              textfont=dict(color="#e8e8f4"))
            fig.update_layout(yaxis=dict(showgrid=True, gridcolor="#29293b", title=None,
                                         rangemode="tozero"),
                              xaxis=dict(showgrid=False, title=None), showlegend=False)
            st.plotly_chart(style_chart(fig), use_container_width=True)

        with chart_right:
            st.subheader("Workload by recommended team")
            st.markdown('<div class="section-note">Share of filtered requests by recommended department.</div>', unsafe_allow_html=True)
            department_counts = (
                filtered["Recommended Department"].replace("", "Unassigned")
                .value_counts().rename_axis("Team").reset_index(name="Requests")
            )
            fig = px.pie(
                department_counts, names="Team", values="Requests", hole=.68,
                color_discrete_sequence=["#8064f5", "#39b9c7", "#ad79f5", "#51c6a5",
                                         "#e9b65d", "#e87891", "#81819b"],
            )
            fig.update_traces(
                textposition="inside", textinfo="percent",
                textfont=dict(color="#ffffff", size=11),
                marker=dict(line=dict(color="#11111b", width=3)),
                hovertemplate="%{label}<br>%{value} requests (%{percent})<extra></extra>",
            )
            fig.update_layout(
                showlegend=True,
                legend=dict(orientation="h", y=-.15, x=0, font=dict(color="#b2b2c7", size=10)),
                annotations=[dict(
                    text=f"<b>{total}</b><br><span style='font-size:10px'>requests</span>",
                    x=.5, y=.5, showarrow=False, font=dict(size=19, color="#f4f5fb"),
                )],
            )
            st.plotly_chart(style_chart(fig), use_container_width=True)

    # Searchable request register remains on the dashboard for quick review.
    st.write("")
    st.subheader("Request register")
    st.markdown('<div class="section-note">Search request identifiers, people, summaries or descriptions.</div>', unsafe_allow_html=True)
    search = st.text_input(
        "Search requests", placeholder="Search requester, request ID, request type, summary or description…",
        key="dashboard_request_search", label_visibility="collapsed",
    )
    table = filtered.copy()
    if search.strip():
        search_columns = [
            "Request ID", "Requester Name", "Request Type", "Department",
            "AI Summary", "Request Description",
        ]
        searchable = table[search_columns].astype(str).agg(" ".join, axis=1)
        table = table[searchable.str.contains(search.strip(), case=False, na=False, regex=False)]

    display_columns = [
        "Request ID", "Requester Name", "Request Type", "Department", "AI Priority",
        "Recommended Department", "Status", "Submitted At",
    ]
    st.dataframe(
        table[display_columns], use_container_width=True, hide_index=True,
        column_config={
            "Request ID": st.column_config.TextColumn("Request ID", width="small"),
            "Requester Name": st.column_config.TextColumn("Requester", width="medium"),
            "Request Type": st.column_config.TextColumn("Request type", width="medium"),
            "Department": st.column_config.TextColumn("Department", width="medium"),
            "AI Priority": st.column_config.TextColumn("AI priority", width="small"),
            "Recommended Department": st.column_config.TextColumn("Recommended team", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Submitted At": st.column_config.TextColumn("Submitted at", width="medium"),
        },
    )
    st.caption(f"Showing {len(table)} of {total} requests after filters and search.")

    # Details selector uses the filtered data, independent of the search result.
    st.write("")
    st.subheader("Request intelligence")
    detail_frame = filtered.reset_index(drop=True)
    if detail_frame.empty:
        st.info("Request details will appear here when requests match the selected filters.")
    else:
        options = []
        for idx, row in detail_frame.iterrows():
            rid = row["Request ID"] or f"Row {idx + 1}"
            name = row["Requester Name"] or "Unknown requester"
            options.append(f"{rid}  ·  {name}  ·  {row['AI Priority']}")
        selected = st.selectbox("Choose a request to inspect", options, key="request_detail_select")
        req = detail_frame.iloc[options.index(selected)]
        detail_a, detail_b = st.columns([1.35, 1], gap="large")
        with detail_a:
            with st.container(border=True):
                st.markdown("#### Request description")
                st.write(req["Request Description"] or "No description provided.")
            with st.container(border=True):
                st.markdown("#### AI assessment")
                st.write(req["AI Summary"] or "No AI summary available.")
            with st.container(border=True):
                st.markdown("#### Recommended next action")
                st.write(req["Suggested Action"] or "No suggested action available.")
        with detail_b:
            with st.container(border=True):
                st.markdown("#### Request profile")
                st.write(f"**Requester:** {req['Requester Name'] or '—'}")
                st.write(f"**Submitted department:** {req['Department'] or '—'}")
                st.write(f"**Request type:** {req['Request Type'] or '—'}")
                st.write(f"**AI priority:** {req['AI Priority'] or '—'}")
                st.write(f"**Recommended team:** {req['Recommended Department'] or '—'}")
                st.write(f"**Current status:** {req['Status'] or '—'}")
                st.write(f"**Submitted:** {req['Submitted At'] or '—'}")

    high_rows = filtered[filtered["AI Priority"].str.strip().str.lower().eq("high")]
    if not high_rows.empty:
        st.write("")
        st.subheader("Needs attention")
        st.caption("High-priority requests visible under the active filters.")
        st.dataframe(
            high_rows[["Request ID", "Requester Name", "Request Type", "AI Summary",
                       "Recommended Department", "Status"]],
            use_container_width=True, hide_index=True,
        )

elif page == "Requests":
    st.subheader("Request register")
    st.caption("Browse and search all requests that match the current filters.")
    search = st.text_input(
        "Search requests", placeholder="Search ID, requester, type, department, summary or description…",
        key="requests_page_search",
    )
    table = filtered.copy()
    if search.strip():
        search_columns = [
            "Request ID", "Requester Name", "Request Type", "Department",
            "AI Summary", "Request Description",
        ]
        searchable = table[search_columns].astype(str).agg(" ".join, axis=1)
        table = table[searchable.str.contains(search.strip(), case=False, na=False, regex=False)]
    st.dataframe(
        table[["Request ID", "Requester Name", "Request Type", "Department", "AI Priority",
               "Recommended Department", "Status", "Submitted At"]],
        use_container_width=True, hide_index=True,
    )
    st.caption(f"{len(table)} matching request(s).")
    if table.empty:
        st.info("No requests match this search and the current filters.")
    else:
        detail_options = []
        detail_frame = table.reset_index(drop=True)
        for idx, row in detail_frame.iterrows():
            detail_options.append(
                f"{row['Request ID'] or f'Row {idx + 1}'} · "
                f"{row['Requester Name'] or 'Unknown requester'} · {row['AI Priority']}"
            )
        selected = st.selectbox("Inspect a request", detail_options, key="requests_page_detail")
        req = detail_frame.iloc[detail_options.index(selected)]
        left, right = st.columns(2, gap="large")
        with left:
            with st.container(border=True):
                st.markdown("#### Request description")
                st.write(req["Request Description"] or "No description provided.")
                st.markdown("#### AI summary")
                st.write(req["AI Summary"] or "No AI summary available.")
                st.markdown("#### Suggested action")
                st.write(req["Suggested Action"] or "No suggested action available.")
        with right:
            with st.container(border=True):
                st.markdown("#### Request profile")
                for label, column in [
                    ("Request ID", "Request ID"), ("Requester", "Requester Name"),
                    ("Submitted department", "Department"), ("Request type", "Request Type"),
                    ("AI priority", "AI Priority"), ("Recommended team", "Recommended Department"),
                    ("Status", "Status"), ("Submitted", "Submitted At"),
                ]:
                    st.write(f"**{label}:** {req[column] or '—'}")

elif page == "Analytics":
    st.subheader("Analytics")
    st.caption("Charts and workload summaries are calculated from the filtered request data.")
    if filtered.empty:
        st.info("There is no data to chart for the current filters.")
    else:
        chart_left, chart_right = st.columns(2, gap="large")
        with chart_left:
            st.markdown("#### Priority overview")
            priority_counts = (
                filtered["AI Priority"].replace("", "Unassigned")
                .value_counts().rename_axis("Priority").reset_index(name="Requests")
            )
            priority_colors = {"High": "#ef646f", "Medium": "#eab65d", "Low": "#55c7a5", "Unassigned": "#85859a"}
            fig = px.bar(priority_counts, x="Priority", y="Requests", color="Priority",
                         color_discrete_map=priority_colors, text="Requests")
            fig.update_traces(marker_line_width=0, textposition="outside", cliponaxis=False,
                              textfont=dict(color="#e8e8f4"))
            fig.update_layout(yaxis=dict(showgrid=True, gridcolor="#29293b", title=None, rangemode="tozero"),
                              xaxis=dict(showgrid=False, title=None), showlegend=False)
            st.plotly_chart(style_chart(fig), use_container_width=True)
        with chart_right:
            st.markdown("#### Workload by recommended team")
            department_counts = (
                filtered["Recommended Department"].replace("", "Unassigned")
                .value_counts().rename_axis("Team").reset_index(name="Requests")
            )
            fig = px.pie(department_counts, names="Team", values="Requests", hole=.68,
                         color_discrete_sequence=["#8064f5", "#39b9c7", "#ad79f5", "#51c6a5",
                                                  "#e9b65d", "#e87891", "#81819b"])
            fig.update_traces(textposition="inside", textinfo="percent",
                              textfont=dict(color="#ffffff", size=11),
                              marker=dict(line=dict(color="#11111b", width=3)))
            fig.update_layout(
                showlegend=True,
                legend=dict(orientation="h", y=-.15, x=0, font=dict(color="#b2b2c7", size=10)),
                annotations=[dict(text=f"<b>{total}</b><br><span style='font-size:10px'>requests</span>",
                                  x=.5, y=.5, showarrow=False, font=dict(size=19, color="#f4f5fb"))],
            )
            st.plotly_chart(style_chart(fig), use_container_width=True)

        st.write("")
        st.markdown("#### Workload by status")
        status_counts = filtered["Status"].replace("", "New").value_counts().rename_axis("Status").reset_index(name="Requests")
        fig = px.bar(status_counts, x="Status", y="Requests", text="Requests",
                     color_discrete_sequence=["#8064f5"])
        fig.update_traces(marker_line_width=0, textposition="outside", cliponaxis=False,
                          textfont=dict(color="#e8e8f4"))
        st.plotly_chart(style_chart(fig), use_container_width=True)

# ---------- Footer ----------
st.divider()
source_label = {
    "live": "n8n production webhook",
    "csv": "local CSV fallback",
    "error": "unavailable",
}.get(source, "unavailable")
last_refresh = st.session_state.get(
    "ops_last_refresh", datetime.now().strftime("%d %b %Y, %H:%M:%S")
)
st.markdown(
    f'<div class="small-muted">◈ OpsPilot · Data source: {source_label} · '
    f'Last refresh action: {last_refresh}</div>',
    unsafe_allow_html=True,
)
