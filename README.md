# AI Business Operations Copilot

An AI-powered business operations dashboard that helps teams manage incoming enquiries, prioritize requests, and organize work efficiently.

## Features

- Automated enquiry collection through an n8n form.
- AI-generated summaries and priority classification.
- Recommended departments and suggested actions.
- Automated customer confirmation emails through Gmail.
- Google Sheets integration for storing requests.
- Interactive Streamlit dashboard with charts and metrics.
- Live request data through an authenticated n8n webhook.
- Request filtering and analytics.

## Technology Stack

- Python
- Streamlit
- Pandas
- Plotly
- n8n
- OpenAI API
- Google Sheets
- Gmail

## How It Works

1. A customer submits an enquiry through the n8n form.
2. The AI workflow analyzes the enquiry.
3. The workflow generates a summary, priority, recommended department, and suggested action.
4. The request is stored in Google Sheets.
5. Gmail sends a confirmation email to the customer.
6. The Streamlit dashboard retrieves and displays request data through a separate n8n webhook.

## Run Locally

### 1. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 2. Configure secrets

Create `.streamlit/secrets.toml` and add your own n8n dashboard endpoint and authentication settings:

```toml
N8N_WEBHOOK_URL = "YOUR_N8N_DASHBOARD_WEBHOOK_URL"
N8N_HEADER_NAME = "X-Copilot-Key"
N8N_HEADER_VALUE = "YOUR_PRIVATE_HEADER_KEY"
```

Replace the placeholder values with your own credentials. Never publish real credentials to GitHub.

### 3. Run the dashboard

```powershell
streamlit run app_professional_compact.py
```

## Required Integrations

This project requires two n8n workflows:

1. **AI Business Operations Copilot** — receives enquiries, analyzes them with AI, stores results in Google Sheets, and sends customer confirmation emails through Gmail.
2. **Copilot Dashboard API** — provides authenticated access to request data for the Streamlit dashboard.

The n8n workflows and their Google Sheets, Gmail, and authentication credentials must be configured in your own n8n account.

## Security

- Keep `.streamlit/secrets.toml` private.
- Do not upload `.venv/`.
- Never commit API keys, passwords, OAuth credentials, or private authentication headers.
- Configure deployment secrets securely when hosting the dashboard.

## Project Purpose

This project demonstrates how AI, workflow automation, spreadsheets, email notifications, and interactive dashboards can be combined to improve business enquiry management.

## Future Enhancements

- Automatic alerts for high-priority enquiries.
- Improved refresh behavior and error monitoring.
- Request status tracking and additional analytics.

**Project Category:** AI Automation, Business Operations, and Data Analytics
