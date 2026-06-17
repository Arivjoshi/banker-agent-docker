# Bank Customer Onboarding — Centralized Agent Marketplace

A Proof of Concept (POC) demonstrating a **centralized AI agent marketplace** for bank customer onboarding. Three specialized agents (KYC, Credit, Fraud) are exposed as REST API endpoints, containerized with Docker, and published on Docker Hub.

---

## Architecture

```
Centralized Agent Marketplace
        │
        ├── KYC-Validator Agent      → /kyc endpoint
        │     ├── document_verification MCP tool
        │     └── sanctions_screening MCP tool
        │
        ├── Credit-Checker Agent     → /credit endpoint
        │     ├── credit_bureau_lookup MCP tool
        │     └── credit_history_analysis MCP tool
        │
        └── Fraud-Detector Agent     → /fraud endpoint
              ├── device_risk_analysis MCP tool
              └── behavioral_analysis MCP tool
```

---

## Project Files

```
banker-agent-docker/
├── main.py              ← All agents + FastAPI endpoints
├── Dockerfile           ← Container build instructions
├── docker-compose.yml   ← One-command local run
├── requirements.txt     ← Python dependencies
└── README.md            ← This file
```

---

## Method 1 — Run with Uvicorn (No Docker needed)

### Step 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Start the server
```bash
uvicorn main:app --reload --port 8000
```

### Step 3 — Open in browser
```
http://localhost:8000/docs
```
FastAPI auto-generates an interactive UI — test all endpoints here without any curl commands.

---

## Method 2 — Run with Docker

### Step 1 — Make sure Docker Desktop is running
Download from: https://www.docker.com/products/docker-desktop

### Step 2 — Pull from Docker Hub
```bash
docker pull ariv19/bank-onboarding-agents:latest
```

### Step 3 — Run the container
```bash
docker run -p 8000:8000 --name bank-agents ariv19/bank-onboarding-agents:latest
```

### Step 4 — Open in browser
```
http://localhost:8000/docs
```

---

## API Endpoints

| Method | Endpoint   | Agent           | Description                    |
|--------|------------|-----------------|--------------------------------|
| GET    | /health    | —               | Health check                   |
| GET    | /agents    | —               | List all agents + MCP tools    |
| POST   | /kyc       | KYC-Validator   | Verify documents + sanctions   |
| POST   | /credit    | Credit-Checker  | Credit score + history         |
| POST   | /fraud     | Fraud-Detector  | Device + behavioral analysis   |
| POST   | /onboard   | All 3 together  | Full onboarding decision       |

---

## Request Body Examples

### POST /kyc
```json
{
  "customer_id": "CUST-001",
  "name": "John Doe",
  "documents": ["passport.pdf", "drivers_license.pdf"]
}
```

### POST /credit
```json
{
  "customer_id": "CUST-001",
  "name": "John Doe",
  "ssn": "123-45-6789"
}
```

### POST /fraud
```json
{
  "customer_id": "CUST-001",
  "ip_address": "192.168.1.100",
  "device_fingerprint": "abc123xyz789"
}
```

### POST /onboard (full onboarding — all 3 agents in parallel)
```json
{
  "customer_id": "CUST-001",
  "name": "John Doe",
  "ssn": "123-45-6789",
  "documents": ["passport.pdf", "drivers_license.pdf"],
  "ip_address": "192.168.1.100",
  "device_fingerprint": "abc123xyz789",
  "scenario": "approved"
}
```

---

## Scenario Testing

Pass a `scenario` field in the POST body to test different outcomes:

| Scenario         | What it simulates              | Decision       |
|-----------------|--------------------------------|----------------|
| `approved`      | All checks pass                | APPROVED       |
| `kyc_fail`      | Document not verified          | REJECTED       |
| `sanctions_fail`| Customer on OFAC list          | REJECTED       |
| `credit_fail`   | Credit score below 600         | REJECTED       |
| `fraud_fail`    | High fraud risk score          | REJECTED       |
| `manual_review` | Medium fraud risk              | MANUAL REVIEW  |
| `conditional`   | Borderline credit score        | CONDITIONAL    |

---

## Docker Hub

Public image: `ariv19/bank-onboarding-agents:latest`

```bash
docker pull ariv19/bank-onboarding-agents:latest
docker run -p 8000:8000 ariv19/bank-onboarding-agents:latest
```

---

## Going to Production

The only change needed to connect real third-party APIs is in `main.py` inside `MCPClient._simulate_response()`:

```python
# Replace the simulation with a real HTTP call:
import httpx
response = httpx.post(
    MCP_TOOLS[tool_name].mcp_server_url,
    json=tool_input,
    headers={"Authorization": f"Bearer {API_KEY}"}
)
return response.json()
```

Real MCP server mappings:
- `document_verification` → Onfido API
- `sanctions_screening` → OFAC/ComplyAdvantage
- `credit_bureau_lookup` → CIBIL / Experian
- `behavioral_analysis` → Seon / Sardine
