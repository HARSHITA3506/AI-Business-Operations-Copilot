import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# ------------------------------------------------------------
# AI Business Operations Copilot — Streamlit Dashboard
# Live data source: n8n production webhook -> Google Sheets
# ------------------------------------------------------------

st.set_page_config(
    page_title="AI Business Operations Copilot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 AI Business Operations Copilot")
st.caption("AI-assisted request triage, prioritization, and business operations monitoring.")

EXPECTED_COLUMNS = [
    "Request ID",
    "Request Description",
    "Requester Name",
    "Department",
    "Request Type",
    "Customer Email",
    "AI Summary",
    "AI Priority",
    "Recommended Department",
    "Suggested Action",
    "Status",
    "Submitted At",
]

# Accept minor differences in column naming returned by Google Sheets.
COLUMN_ALIASES = {
    "Request ID": ["Request ID", "request_id", "requestId"],
    "Request Description": ["Request Description", "Request description", "request_description"],
    "Requester Name": ["Requester Name", "Requester Name.", "requester_name"],
    "Department": ["Department", "department"],
    "Request Type": ["Request Type", "request_type"],
    "Customer Email": ["Customer Email", "customer_email"],
    "AI Summary": ["AI Summary", "AI summary", "summary"],
    "AI Priority": ["AI Priority", "AI Priority ", "priority", "Priority"],
    "Recommended Department": [
        "Recommended Department",
        "Recommended Departm",
        "recommended_department",
    ],
    "Suggested Action": ["Suggested Action", "suggested_action"],
    "Status": ["Status", "status"],
    "Submitted At": ["Submitted At", "Submitted at", "submittedAt", "submitted_at"],
}


def normalize_rows(payload):
    """Convert n8n JSON response into a clean DataFrame."""
    if isinstance(payload, dict):
        # Some webhook configurations wrap rows in a key.
        for key in ("data", "rows", "items", "results"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
        else:
            payload = [payload]

    if not isinstance(payload, list):
        raise ValueError("The webhook response must be a JSON array of rows.")

    records = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        # Ignore entirely empty rows.
        if any(value not in (None, "") for value in item.values()):
            records.append(item)

    df = pd.DataFrame(records)

    if df.empty:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    # Rename aliases to the dashboard's expected column names.
    rename_map = {}
    for expected, aliases in COLUMN_ALIASES.items():
        if expected in df.columns:
            continue
        for alias in aliases:
            if alias in df.columns:
                rename_map[alias] = expected
                break
    df = df.rename(columns=rename_map)

    # Add missing columns so the dashboard still renders if the sheet has blanks.
    for column in EXPECTED_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    # Keep only the dashboard columns, in a consistent order.
    df = df[EXPECTED_COLUMNS].copy()

    for column in EXPECTED_COLUMNS:
        df[column] = df[column].fillna("").astype(str).str.strip()

    # Ignore the Google Sheets header row if n8n returns it as a data row.
    if not df.empty:
        first_row = df.iloc[0].astype(str).str.strip().str.lower()
        if first_row.get("Request ID", "") in ("request id", "request_id"):
            df = df.iloc[1:].copy()

    # A numeric ID is not required, but make empty IDs visibly distinguishable.
    df["AI Priority"] = df["AI Priority"].replace("", "Unassigned")
    df["Status"] = df["Status"].replace("", "New")
    return df.reset_index(drop=True)


@st.cache_data(ttl=20, show_spinner=False)
def fetch_live_data(webhook_url, header_name, header_value):
    """Fetch current rows through the authenticated n8n production webhook."""
    response = requests.get(
        webhook_url,
        headers={header_name: header_value},
        timeout=20,
    )
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError("n8n returned a response that is not valid JSON.") from exc

    return normalize_rows(payload)


def load_data():
    """Load from n8n. CSV is used only when explicitly selected as a fallback."""
    try:
        webhook_url = st.secrets.get("N8N_WEBHOOK_URL", "").strip()
        header_name = st.secrets.get("N8N_HEADER_NAME", "X-Copilot-Key").strip()
        header_value = st.secrets.get("N8N_HEADER_VALUE", "").strip()
    except Exception:
        webhook_url, header_name, header_value = "", "X-Copilot-Key", ""

    if webhook_url and header_value:
        try:
            df = fetch_live_data(webhook_url, header_name, header_value)
            return df, "live", None
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            if status == 401 or status == 403:
                message = (
                    "n8n rejected the dashboard credentials (401/403). Check that "
                    "N8N_HEADER_NAME and N8N_HEADER_VALUE match the Webhook's Header Auth credential."
                )
            else:
                message = f"The n8n webhook returned HTTP {status}. Check the workflow's latest execution in n8n."
            return pd.DataFrame(columns=EXPECTED_COLUMNS), "error", message
        except requests.exceptions.Timeout:
            return pd.DataFrame(columns=EXPECTED_COLUMNS), "error", "The n8n request timed out. Try refreshing in a moment."
        except requests.exceptions.RequestException:
            return pd.DataFrame(columns=EXPECTED_COLUMNS), "error", "Could not reach the n8n webhook. Check that the workflow is published and the Production URL is correct."
        except Exception as exc:
            return pd.DataFrame(columns=EXPECTED_COLUMNS), "error", f"Could not read the n8n response: {exc}"

    # Safe fallback for local setup only; the CSV is not live.
    csv_path = Path(__file__).parent / "requests.csv"
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path, dtype=str).fillna("")
            df = normalize_rows(df.to_dict(orient="records"))
            return df, "csv", "Live n8n settings were not found. Showing requests.csv (static data)."
        except Exception as exc:
            return pd.DataFrame(columns=EXPECTED_COLUMNS), "error", f"Could not read requests.csv: {exc}"

    return (
        pd.DataFrame(columns=EXPECTED_COLUMNS),
        "error",
        "No live webhook settings were found and requests.csv is missing. Check .streamlit/secrets.toml.",
    )


# Sidebar controls
with st.sidebar:
    st.header("Dashboard Controls")
    st.caption("Live data refreshes every 20 seconds when the page reruns.")
    if st.button("🔄 Refresh data now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.subheader("Filters")

df, source, load_error = load_data()

if source == "live":
    st.success("Connected to the n8n production webhook.")
elif source == "csv":
    st.warning(load_error)
else:
    st.error(load_error or "Unable to load data.")

# Add normalized date field for sorting and time-related display.
if "Submitted At" in df.columns:
    df["_submitted_datetime"] = pd.to_datetime(df["Submitted At"], errors="coerce", utc=True)
else:
    df["_submitted_datetime"] = pd.NaT

with st.sidebar:
    departments = sorted([x for x in df["Department"].dropna().unique().tolist() if x])
    priorities = sorted([x for x in df["AI Priority"].dropna().unique().tolist() if x])
    statuses = sorted([x for x in df["Status"].dropna().unique().tolist() if x])
    request_types = sorted([x for x in df["Request Type"].dropna().unique().tolist() if x])

    selected_departments = st.multiselect("Department", departments, default=departments)
    selected_priorities = st.multiselect("AI Priority", priorities, default=priorities)
    selected_statuses = st.multiselect("Status", statuses, default=statuses)
    selected_types = st.multiselect("Request Type", request_types, default=request_types)

filtered = df.copy()
if selected_departments:
    filtered = filtered[filtered["Department"].isin(selected_departments)]
else:
    filtered = filtered.iloc[0:0]
if selected_priorities:
    filtered = filtered[filtered["AI Priority"].isin(selected_priorities)]
else:
    filtered = filtered.iloc[0:0]
if selected_statuses:
    filtered = filtered[filtered["Status"].isin(selected_statuses)]
else:
    filtered = filtered.iloc[0:0]
if selected_types:
    filtered = filtered[filtered["Request Type"].isin(selected_types)]
else:
    filtered = filtered.iloc[0:0]

# KPI cards
total_requests = len(filtered)
high_priority = int((filtered["AI Priority"].str.lower() == "high").sum()) if total_requests else 0
open_requests = int((~filtered["Status"].str.lower().isin(["resolved", "closed", "completed"])).sum()) if total_requests else 0
departments_count = int(filtered["Recommended Department"].replace("", pd.NA).nunique()) if total_requests else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Requests", f"{total_requests:,}")
k2.metric("High Priority", f"{high_priority:,}")
k3.metric("Open Requests", f"{open_requests:,}")
k4.metric("Recommended Departments", f"{departments_count:,}")

st.divider()

if filtered.empty:
    st.info("No requests match the selected filters. Submit a request through your n8n form or adjust the filters.")
else:
    left, right = st.columns(2)

    with left:
        st.subheader("Requests by AI Priority")
        priority_counts = (
            filtered["AI Priority"].replace("", "Unassigned").value_counts().rename_axis("Priority").reset_index(name="Requests")
        )
        fig_priority = px.bar(
            priority_counts,
            x="Priority",
            y="Requests",
            color="Priority",
            text="Requests",
            title=None,
        )
        fig_priority.update_layout(
            showlegend=False,
            xaxis_title="AI Priority",
            yaxis_title="Number of requests",
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig_priority, use_container_width=True)

    with right:
        st.subheader("Requests by Department")
        department_counts = (
            filtered["Recommended Department"]
            .replace("", "Unassigned")
            .value_counts()
            .rename_axis("Recommended Department")
            .reset_index(name="Requests")
        )
        fig_department = px.pie(
            department_counts,
            names="Recommended Department",
            values="Requests",
            hole=0.45,
        )
        fig_department.update_layout(margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_department, use_container_width=True)

    st.subheader("Request Register")
    display_columns = [
        "Request ID",
        "Requester Name",
        "Request Type",
        "Department",
        "AI Priority",
        "Recommended Department",
        "Status",
        "Submitted At",
    ]
    st.dataframe(
        filtered[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Request ID": st.column_config.TextColumn("Request ID"),
            "AI Priority": st.column_config.TextColumn("AI Priority"),
            "Submitted At": st.column_config.TextColumn("Submitted At"),
        },
    )

    st.subheader("Request Details")
    options = []
    for idx, row in filtered.reset_index(drop=True).iterrows():
        label_id = row["Request ID"] or f"Row {idx + 1}"
        label_name = row["Requester Name"] or "Unknown requester"
        label_priority = row["AI Priority"] or "Unassigned"
        options.append(f"{label_id} — {label_name} — {label_priority}")

    selected_label = st.selectbox("Select a request to inspect", options)
    selected_index = options.index(selected_label)
    request = filtered.reset_index(drop=True).iloc[selected_index]

    detail_left, detail_right = st.columns(2)
    with detail_left:
        st.markdown("**Request description**")
        st.write(request["Request Description"] or "No description provided.")
        st.markdown("**AI summary**")
        st.write(request["AI Summary"] or "No AI summary available.")
        st.markdown("**Suggested action**")
        st.write(request["Suggested Action"] or "No suggested action available.")
    with detail_right:
        st.markdown("**Request information**")
        st.write(f"**Requester:** {request['Requester Name'] or '—'}")
        st.write(f"**Department:** {request['Department'] or '—'}")
        st.write(f"**Request type:** {request['Request Type'] or '—'}")
        st.write(f"**AI priority:** {request['AI Priority'] or '—'}")
        st.write(f"**Recommended department:** {request['Recommended Department'] or '—'}")
        st.write(f"**Status:** {request['Status'] or '—'}")
        st.write(f"**Submitted at:** {request['Submitted At'] or '—'}")

    high_rows = filtered[filtered["AI Priority"].str.lower() == "high"]
    if not high_rows.empty:
        st.divider()
        st.subheader("🚨 High-Priority Requests")
        st.dataframe(
            high_rows[
                [
                    "Request ID",
                    "Requester Name",
                    "Request Type",
                    "AI Summary",
                    "Recommended Department",
                    "Status",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

st.caption(
    f"Data source: {'n8n live webhook' if source == 'live' else 'local CSV fallback' if source == 'csv' else 'unavailable'}"
    + f" · Last page render: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
