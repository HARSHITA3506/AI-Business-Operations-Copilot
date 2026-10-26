from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(
    page_title="OpsPilot | Business Operations",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Premium visual system ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --ink:#f4f5fb; --muted:#9ca3b8; --line:#272838; --paper:#0b0b10; --panel:#12121b; --purple:#8b5cf6; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background:var(--paper); color:var(--ink); }
.block-container { padding-top:1.2rem; padding-bottom:2rem; max-width:1680px; }
[data-testid="stHeader"] { background:rgba(11,11,16,.92); }
[data-testid="stSidebar"] { background:#0c0c12; border-right:1px solid #242431; }
[data-testid="stSidebar"] * { color:#e8e8f2 !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#9a9aae !important; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:.7rem; }
[data-testid="stSidebar"] [data-testid="stButton"] button { background:#171521; border:1px solid #302943; color:#eeeaff; border-radius:10px; }
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] { background:#8051f5; border-color:#8051f5; }
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] { background:#34235a; border:1px solid #6240a6; }
[data-testid="stSidebar"] hr { border-color:#282837; }
h1,h2,h3 { font-family:'Manrope',sans-serif !important; color:#f5f5fb !important; letter-spacing:-.035em; }
h1 { font-size:2rem !important; font-weight:800 !important; }
h2 { font-size:1.2rem !important; font-weight:750 !important; }
h3 { font-size:1rem !important; font-weight:700 !important; }
p, label, .stMarkdown, [data-testid="stCaptionContainer"] { color:#b0b0c2; }
[data-testid="stMetric"] { background:linear-gradient(145deg,#151520,#11111a); border:1px solid #282838; padding:20px 21px; border-radius:17px; box-shadow:0 8px 24px rgba(0,0,0,.12); }
[data-testid="stMetricLabel"] { color:#a7a7bb !important; font-size:.8rem !important; font-weight:600 !important; }
[data-testid="stMetricValue"] { color:#fff !important; font-family:'Manrope',sans-serif; font-weight:800 !important; font-size:1.9rem !important; }
[data-testid="stMetricDelta"] { font-size:.75rem !important; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius:16px; border-color:#282838 !important; background:#12121b; }
div[data-testid="stPlotlyChart"] { background:#12121b; border:1px solid #282838; padding:10px 10px 0; border-radius:17px; }
div[data-testid="stDataFrame"] { border:1px solid #282838; border-radius:14px; overflow:hidden; }
.stButton button { border-radius:10px; font-weight:650; }
.stTextInput input, .stSelectbox, .stMultiSelect { border-radius:10px; }
.ops-eyebrow { text-transform:uppercase; letter-spacing:.16em; color:#a78bfa; font-size:.68rem; font-weight:800; margin-bottom:.35rem; }
.ops-subtitle { color:#9b9bb0; margin-top:-.45rem; font-size:.92rem; }
.ops-banner { background:linear-gradient(115deg,#1b1730,#151523 65%,#11111b); border:1px solid #35294e; border-radius:16px; padding:19px 22px; color:#fff; margin:.8rem 0 1.15rem; }
.ops-banner-title { font-family:'Manrope',sans-serif; font-size:1.12rem; font-weight:800; color:#fff; }
.ops-banner-copy { color:#b9b5ce; font-size:.84rem; margin-top:5px; }
.ops-pill { display:inline-block; border-radius:999px; padding:7px 11px; font-size:.68rem; letter-spacing:.06em; font-weight:800; background:#142a27; color:#55d6b0; border:1px solid #214d43; }
.small-muted { color:#8d8da4; font-size:.78rem; }
.stAlert { border-radius:12px; }
[data-baseweb="select"] > div, [data-baseweb="input"] > div { background:#151520; border-color:#303044; }
</style>
""", unsafe_allow_html=True)

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

def normalize_rows(payload):
    if isinstance(payload, dict):
        for key in ("data", "rows", "items", "results"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
        else:
            payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("The webhook response must be a JSON array of rows.")
    records = [item for item in payload if isinstance(item, dict) and any(v not in (None, "") for v in item.values())]
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)
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
    if not df.empty and df.iloc[0]["Request ID"].lower() in ("request id", "request_id"):
        df = df.iloc[1:].copy()
    df["AI Priority"] = df["AI Priority"].replace("", "Unassigned")
    df["Status"] = df["Status"].replace("", "New")
    return df.reset_index(drop=True)

@st.cache_data(ttl=20, show_spinner=False)
def fetch_live_data(webhook_url, header_name, header_value):
    response = requests.get(webhook_url, headers={header_name: header_value}, timeout=20)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError("n8n returned a response that is not valid JSON.") from exc
    return normalize_rows(payload)

def load_data():
    try:
        webhook_url = st.secrets.get("N8N_WEBHOOK_URL", "").strip()
        header_name = st.secrets.get("N8N_HEADER_NAME", "X-Copilot-Key").strip()
        header_value = st.secrets.get("N8N_HEADER_VALUE", "").strip()
    except Exception:
        webhook_url, header_name, header_value = "", "X-Copilot-Key", ""
    if webhook_url and header_value:
        try:
            return fetch_live_data(webhook_url, header_name, header_value), "live", None
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            msg = ("n8n rejected dashboard credentials (401/403). Check Header Auth settings." if status in (401, 403)
                   else f"The n8n webhook returned HTTP {status}. Check the latest workflow execution.")
            return pd.DataFrame(columns=EXPECTED_COLUMNS), "error", msg
        except requests.exceptions.Timeout:
            return pd.DataFrame(columns=EXPECTED_COLUMNS), "error", "The n8n request timed out. Try refreshing."
        except requests.exceptions.RequestException:
            return pd.DataFrame(columns=EXPECTED_COLUMNS), "error", "Could not reach n8n. Check the published production URL."
        except Exception as exc:
            return pd.DataFrame(columns=EXPECTED_COLUMNS), "error", f"Could not read the n8n response: {exc}"
    csv_path = Path(__file__).parent / "requests.csv"
    if csv_path.exists():
        try:
            return normalize_rows(pd.read_csv(csv_path, dtype=str).fillna("").to_dict(orient="records")), "csv", \
                "Live settings not found. Showing requests.csv (static data)."
        except Exception as exc:
            return pd.DataFrame(columns=EXPECTED_COLUMNS), "error", f"Could not read requests.csv: {exc}"
    return pd.DataFrame(columns=EXPECTED_COLUMNS), "error", "No live settings found. Check .streamlit/secrets.toml."

def style_chart(fig, height=320):
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color="#a5a5ba", size=12),
        margin=dict(l=12, r=12, t=18, b=12), showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, linecolor="#303044", tickfont=dict(color="#9292a8")),
        yaxis=dict(showgrid=True, gridcolor="#252535", zeroline=False, title=None, tickfont=dict(color="#9292a8")),
    )
    return fig

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown('<div style="font-size:1.65rem;font-weight:800;color:white;letter-spacing:-.06em">◈ OpsPilot</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:.78rem;color:#9ca3af;margin-top:-5px">AI BUSINESS OPERATIONS</div>', unsafe_allow_html=True)
    st.divider()
    st.markdown("### Workspace")
    st.caption("Monitor requests, priorities and AI recommendations.")
    if st.button("↻  Refresh live data", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.markdown("### Filter requests")

df, source, load_error = load_data()
if "Submitted At" in df.columns:
    df["_submitted_datetime"] = pd.to_datetime(df["Submitted At"], errors="coerce", utc=True)
else:
    df["_submitted_datetime"] = pd.NaT

with st.sidebar:
    departments = sorted(x for x in df["Department"].unique().tolist() if x)
    priorities = sorted(x for x in df["AI Priority"].unique().tolist() if x)
    statuses = sorted(x for x in df["Status"].unique().tolist() if x)
    request_types = sorted(x for x in df["Request Type"].unique().tolist() if x)
    selected_departments = st.multiselect("Department", departments, default=departments)
    selected_priorities = st.multiselect("AI priority", priorities, default=priorities)
    selected_statuses = st.multiselect("Status", statuses, default=statuses)
    selected_types = st.multiselect("Request type", request_types, default=request_types)
    st.divider()
    st.markdown('<div class="small-muted">OpsPilot · Local workspace</div>', unsafe_allow_html=True)

filtered = df.copy()
for column, selection in [
    ("Department", selected_departments), ("AI Priority", selected_priorities),
    ("Status", selected_statuses), ("Request Type", selected_types)
]:
    filtered = filtered[filtered[column].isin(selection)] if selection else filtered.iloc[0:0]

# ---------- Header ----------
header_left, header_right = st.columns([3, 1])
with header_left:
    st.markdown('<div class="ops-eyebrow">OPERATIONS OVERVIEW</div>', unsafe_allow_html=True)
    st.title("Business command center")
    st.markdown('<div class="ops-subtitle">A live view of incoming requests, AI triage and operational workload.</div>', unsafe_allow_html=True)
with header_right:
    st.write("")
    st.write("")
    if source == "live":
        st.markdown('<span class="ops-pill">● LIVE · N8N CONNECTED</span>', unsafe_allow_html=True)
    elif source == "csv":
        st.markdown('<span class="ops-pill">● STATIC CSV DATA</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="ops-pill">● CONNECTION ISSUE</span>', unsafe_allow_html=True)

if source == "csv":
    st.warning(load_error)
elif source == "error":
    st.error(load_error)
else:
    st.markdown(
        '<div class="ops-banner"><div class="ops-banner-title">Operational intelligence at a glance.</div>'
        '<div class="ops-banner-copy">Monitor request volume, review AI triage, and direct attention to the work with the highest operational impact.</div></div>',
        unsafe_allow_html=True,
    )

total = len(filtered)
high = int((filtered["AI Priority"].str.lower() == "high").sum()) if total else 0
open_count = int((~filtered["Status"].str.lower().isin(["resolved", "closed", "completed"])).sum()) if total else 0
resolved = int(filtered["Status"].str.lower().isin(["resolved", "closed", "completed"]).sum()) if total else 0
resolution_rate = round(resolved / total * 100) if total else 0
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total requests", f"{total:,}", help="Requests matching the current filters")
k2.metric("High priority", f"{high:,}", help="Requests classified as high priority by AI")
k3.metric("Open workload", f"{open_count:,}", help="Requests not marked resolved, closed or completed")
k4.metric("Resolution rate", f"{resolution_rate}%", help="Share of filtered requests marked resolved or closed")

st.write("")
if filtered.empty:
    st.info("No requests match the selected filters. Adjust the sidebar filters or submit a request using your n8n form.")
else:
    chart_left, chart_right = st.columns([1, 1])
    with chart_left:
        st.subheader("Priority overview")
        priority_counts = filtered["AI Priority"].replace("", "Unassigned").value_counts().rename_axis("Priority").reset_index(name="Requests")
        priority_colors = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981", "Unassigned": "#94a3b8"}
        fig = px.bar(priority_counts, x="Priority", y="Requests", color="Priority",
                     color_discrete_map=priority_colors, text="Requests")
        fig.update_traces(marker_line_width=0, textposition="outside", cliponaxis=False)
        fig.update_layout(yaxis=dict(showgrid=True, gridcolor="#edf0f5", title=None),
                          xaxis=dict(showgrid=False, title=None), showlegend=False)
        st.plotly_chart(style_chart(fig), use_container_width=True)
    with chart_right:
        st.subheader("Workload by recommended team")
        department_counts = filtered["Recommended Department"].replace("", "Unassigned").value_counts().rename_axis("Team").reset_index(name="Requests")
        fig = px.pie(department_counts, names="Team", values="Requests", hole=.68,
                     color_discrete_sequence=["#4f46e5", "#06b6d4", "#8b5cf6", "#10b981", "#f59e0b", "#94a3b8"])
        fig.update_traces(textposition="inside", textinfo="percent", marker=dict(line=dict(color="#ffffff", width=3)))
        fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-.12, x=0),
                          annotations=[dict(text=f"<b>{total}</b><br><span style='font-size:11px'>requests</span>",
                                            x=.5, y=.5, showarrow=False, font=dict(size=20, color="#172033"))])
        st.plotly_chart(style_chart(fig), use_container_width=True)

    st.write("")
    st.subheader("Request register")
    search = st.text_input("⌕  Search requests", placeholder="Search requester, request ID, summary or description…")
    table = filtered.copy()
    if search.strip():
        searchable = table[["Request ID", "Requester Name", "Request Type", "Department", "AI Summary", "Request Description"]].astype(str).agg(" ".join, axis=1)
        table = table[searchable.str.contains(search.strip(), case=False, na=False)]
    display_columns = ["Request ID", "Requester Name", "Request Type", "Department", "AI Priority",
                       "Recommended Department", "Status", "Submitted At"]
    st.dataframe(
        table[display_columns], use_container_width=True, hide_index=True,
        column_config={
            "Request ID": st.column_config.TextColumn("Request ID", width="small"),
            "Requester Name": st.column_config.TextColumn("Requester", width="medium"),
            "Request Type": st.column_config.TextColumn("Request type", width="medium"),
            "AI Priority": st.column_config.TextColumn("AI priority", width="small"),
            "Recommended Department": st.column_config.TextColumn("Recommended team", width="medium"),
            "Submitted At": st.column_config.TextColumn("Submitted at", width="medium"),
        },
    )
    st.caption(f"Showing {len(table)} of {total} requests after filters and search.")

    st.write("")
    st.subheader("Request intelligence")
    options = []
    for idx, row in filtered.reset_index(drop=True).iterrows():
        rid = row["Request ID"] or f"Row {idx + 1}"
        name = row["Requester Name"] or "Unknown requester"
        options.append(f"{rid}  ·  {name}  ·  {row['AI Priority']}")
    selected = st.selectbox("Choose a request to inspect", options, label_visibility="collapsed")
    req = filtered.reset_index(drop=True).iloc[options.index(selected)]
    detail_a, detail_b = st.columns([1.35, 1])
    with detail_a:
        with st.container(border=True):
            st.markdown("#### Request summary")
            st.write(req["Request Description"] or "No description provided.")
            st.markdown("#### AI assessment")
            st.write(req["AI Summary"] or "No AI summary available.")
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

    high_rows = filtered[filtered["AI Priority"].str.lower() == "high"]
    if not high_rows.empty:
        st.write("")
        st.subheader("Needs attention")
        st.caption("High-priority requests currently visible under your selected filters.")
        st.dataframe(high_rows[["Request ID", "Requester Name", "Request Type", "AI Summary",
                                "Recommended Department", "Status"]],
                     use_container_width=True, hide_index=True)

st.divider()
st.markdown(
    f'<div class="small-muted">OpsPilot · Data source: {"n8n production webhook" if source == "live" else "local CSV fallback" if source == "csv" else "unavailable"}'
    f' · Last refreshed {datetime.now().strftime("%d %b %Y, %H:%M:%S")}</div>',
    unsafe_allow_html=True,
)
