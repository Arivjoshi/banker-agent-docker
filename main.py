"""
Bank Customer Onboarding — Agent Marketplace API
=================================================
Three agents exposed as REST endpoints so anyone who pulls
the Docker image can call them over HTTP.

Endpoints:
  POST /kyc      → KYCValidatorAgent
  POST /credit   → CreditCheckerAgent
  POST /fraud    → FraudDetectorAgent
  POST /onboard  → All three in parallel (full onboarding)
  GET  /health   → Health check
  GET  /agents   → Lists all agents + their MCP tools
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# ============================================================================
# SCENARIO SWITCH  ← only line you change to switch between outcomes
# ============================================================================
# Options:
#   "approved"      → KYC pass, credit 750, fraud low    → APPROVED
#   "kyc_fail"      → document not verified               → REJECTED
#   "sanctions_fail"→ customer on sanctions list          → REJECTED
#   "credit_fail"   → credit score 520                    → REJECTED
#   "fraud_fail"    → high fraud risk score               → REJECTED
#   "manual_review" → medium fraud risk                   → MANUAL REVIEW
#   "conditional"   → credit score 630 (borderline)       → CONDITIONAL

SCENARIO = "approved"  # ← change this one word, save, server auto-restarts

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# ============================================================================
# REQUEST MODELS  (what the caller must send)
# ============================================================================

class KYCRequest(BaseModel):
    customer_id: str
    name: str
    documents: List[str]          # e.g. ["passport.pdf", "drivers_license.pdf"]

class CreditRequest(BaseModel):
    customer_id: str
    name: str
    ssn: str                      # SSN (US) or PAN (India)

class FraudRequest(BaseModel):
    customer_id: str
    ip_address: str
    device_fingerprint: str

class OnboardRequest(BaseModel):
    """Full onboarding — combines all three agents"""
    customer_id: str
    name: str
    ssn: str
    documents: List[str]
    ip_address: str
    device_fingerprint: str
    scenario: Optional[str] = None  # override SCENARIO from POST body if provided


# ============================================================================
# MCP TOOL DEFINITIONS
# ============================================================================

@dataclass
class MCPTool:
    name: str
    description: str
    mcp_server_url: str


MCP_TOOLS = {
    # KYC Agent tools
    "document_verification": MCPTool(
        name="document_verification",
        description="Verify identity documents using OCR and blockchain",
        mcp_server_url="http://mcp-kyc.bank.local/verify-document"
    ),
    "sanctions_screening": MCPTool(
        name="sanctions_screening",
        description="Check customer against OFAC, UN, EU sanctions lists",
        mcp_server_url="http://mcp-kyc.bank.local/check-sanctions"
    ),
    # Credit Agent tools
    "credit_bureau_lookup": MCPTool(
        name="credit_bureau_lookup",
        description="Query Equifax, Experian, TransUnion for credit score",
        mcp_server_url="http://mcp-credit.bank.local/query-bureau"
    ),
    "credit_history_analysis": MCPTool(
        name="credit_history_analysis",
        description="Analyze credit history trends and predict risk",
        mcp_server_url="http://mcp-credit.bank.local/analyze-history"
    ),
    # Fraud Agent tools
    "device_risk_analysis": MCPTool(
        name="device_risk_analysis",
        description="Analyze device fingerprint for fraud patterns",
        mcp_server_url="http://mcp-fraud.bank.local/analyze-device"
    ),
    "behavioral_analysis": MCPTool(
        name="behavioral_analysis",
        description="ML-based behavioral pattern analysis",
        mcp_server_url="http://mcp-fraud.bank.local/analyze-behavior"
    ),
}


# ============================================================================
# MCP CLIENT  (simulated — swap _simulate_response for real httpx calls)
# ============================================================================

class MCPClient:

    @staticmethod
    async def call(tool_name: str, tool_input: Dict, scenario: str = None) -> Dict:
        if tool_name not in MCP_TOOLS:
            raise ValueError(f"Unknown MCP tool: {tool_name}")
        await asyncio.sleep(0.2)
        return MCPClient._simulate_response(tool_name, tool_input, scenario)

    @staticmethod
    def _simulate_response(tool_name: str, tool_input: Dict, scenario: str = None) -> Dict:
        """
        Returns different data depending on SCENARIO.
        PRODUCTION SWAP: replace this entire method body with:
            import httpx
            r = httpx.post(MCP_TOOLS[tool_name].mcp_server_url, json=tool_input)
            return r.json()
        """
        s = scenario or SCENARIO   # use passed scenario, fall back to global
        ts = datetime.now().isoformat()

        # ── KYC Tool 1: Document verification ────────────────────────────────
        if tool_name == "document_verification":
            if s == "kyc_fail":
                return {
                    "verified": False,             # ← document check fails
                    "document_type": tool_input.get("document_type", "passport"),
                    "confidence_score": 0.21,      # ← very low confidence
                    "expiration_date": "2019-01-01",
                    "issuing_country": "UNKNOWN",
                    "timestamp": ts
                }
            return {
                "verified": True,
                "document_type": tool_input.get("document_type", "passport"),
                "confidence_score": 0.98,
                "expiration_date": "2028-05-15",
                "issuing_country": "US",
                "timestamp": ts
            }

        # ── KYC Tool 2: Sanctions screening ──────────────────────────────────
        elif tool_name == "sanctions_screening":
            if s == "sanctions_fail":
                return {
                    "on_sanctions_list": True,     # ← customer is on OFAC list
                    "risk_level": "critical",
                    "matched_list": "OFAC",
                    "checked_lists": ["OFAC", "UN", "EU"],
                    "timestamp": ts
                }
            return {
                "on_sanctions_list": False,
                "risk_level": "low",
                "checked_lists": ["OFAC", "UN", "EU"],
                "timestamp": ts
            }

        # ── Credit Tool 1: Bureau lookup ──────────────────────────────────────
        elif tool_name == "credit_bureau_lookup":
            if s == "credit_fail":
                return {
                    "credit_score": 520,           # ← below 600 = rejected
                    "inquiries_6m": 14,
                    "accounts_in_good_standing": 0,
                    "delinquencies": 6,
                    "timestamp": ts
                }
            if s == "conditional":
                return {
                    "credit_score": 630,           # ← 600-649 = conditional
                    "inquiries_6m": 5,
                    "accounts_in_good_standing": 2,
                    "delinquencies": 1,
                    "timestamp": ts
                }
            return {
                "credit_score": 750,               # ← approved range
                "inquiries_6m": 2,
                "accounts_in_good_standing": 5,
                "delinquencies": 0,
                "timestamp": ts
            }

        # ── Credit Tool 2: History analysis ──────────────────────────────────
        elif tool_name == "credit_history_analysis":
            if s == "credit_fail":
                return {
                    "credit_trends": "declining",
                    "payment_history": "poor",
                    "risk_score": 9,
                    "recommended_credit_limit": 0,
                    "timestamp": ts
                }
            if s == "conditional":
                return {
                    "credit_trends": "stable",
                    "payment_history": "fair",
                    "risk_score": 6,
                    "recommended_credit_limit": 10000,
                    "timestamp": ts
                }
            return {
                "credit_trends": "improving",
                "payment_history": "excellent",
                "risk_score": 2,
                "recommended_credit_limit": 50000,
                "timestamp": ts
            }

        # ── Fraud Tool 1: Device risk ─────────────────────────────────────────
        elif tool_name == "device_risk_analysis":
            if s == "fraud_fail":
                return {
                    "is_vpn": True,                # ← VPN detected
                    "risk_score": 0.92,            # ← above 0.8 = high fraud
                    "device_age_days": 1,
                    "timestamp": ts
                }
            if s == "manual_review":
                return {
                    "is_vpn": False,
                    "risk_score": 0.65,            # ← 0.5-0.8 = medium = manual review
                    "device_age_days": 30,
                    "timestamp": ts
                }
            return {
                "is_vpn": False,
                "risk_score": 0.1,                 # ← below 0.5 = low = approved
                "device_age_days": 180,
                "timestamp": ts
            }

        # ── Fraud Tool 2: Behavioral analysis ────────────────────────────────
        elif tool_name == "behavioral_analysis":
            if s == "fraud_fail":
                return {
                    "anomaly_score": 0.91,
                    "behavior_profile": "suspicious",
                    "ml_risk_score": 0.89,         # ← above 0.8 = high fraud
                    "timestamp": ts
                }
            if s == "manual_review":
                return {
                    "anomaly_score": 0.61,
                    "behavior_profile": "unusual",
                    "ml_risk_score": 0.58,         # ← 0.5-0.8 = medium
                    "timestamp": ts
                }
            return {
                "anomaly_score": 0.15,
                "behavior_profile": "normal",
                "ml_risk_score": 0.08,
                "timestamp": ts
            }


# ============================================================================
# AGENTS
# ============================================================================

class KYCValidatorAgent:
    name = "KYC-Validator"
    tools = ["document_verification", "sanctions_screening"]
    mcp = MCPClient()

    async def validate(self, data: Dict, scenario: str = None) -> Dict:
        doc_results = []
        for doc in data.get("documents", []):
            result = await self.mcp.call("document_verification", {
                "document_type": "passport",
                "document_path": doc,
                "customer_id": data["customer_id"]
            }, scenario)
            doc_results.append(result)

        sanctions = await self.mcp.call("sanctions_screening", {
            "customer_name": data["name"],
            "customer_id": data["customer_id"]
        }, scenario)

        all_verified = all(r.get("verified", False) for r in doc_results)
        sanctions_clear = not sanctions.get("on_sanctions_list", False)
        passed = all_verified and sanctions_clear

        if not all_verified:
            message = "FAILED - Document could not be verified. It may be expired, fake, or unreadable."
        elif not sanctions_clear:
            message = "FAILED - Customer name matched on the OFAC/UN/EU sanctions list. Onboarding blocked."
        else:
            message = "PASSED - All identity documents verified and customer cleared all sanctions checks."

        return {
            "agent": self.name,
            "status": "verified" if passed else "rejected",
            "message": message,
            "documents_verified": all_verified,
            "sanctions_clear": sanctions_clear,
            "sanctions_detail": sanctions,
            "document_results": doc_results,
            "risk_score": 1 if passed else 10,
            "timestamp": datetime.now().isoformat()
        }


class CreditCheckerAgent:
    name = "Credit-Checker"
    tools = ["credit_bureau_lookup", "credit_history_analysis"]
    mcp = MCPClient()

    async def check_credit(self, data: Dict, scenario: str = None) -> Dict:
        bureau = await self.mcp.call("credit_bureau_lookup", {
            "ssn": data["ssn"],
            "name": data["name"],
            "bureau": "all"
        }, scenario)
        history = await self.mcp.call("credit_history_analysis", {
            "ssn": data["ssn"],
            "analysis_type": "detailed"
        }, scenario)

        score = bureau.get("credit_score", 600)
        delinquencies = bureau.get("delinquencies", 0)

        if score < 600:
            message = f"FAILED - Credit score is {score}, which is below the minimum threshold of 600. Customer has {delinquencies} delinquent account(s). Application rejected."
        elif score < 650:
            message = f"CONDITIONAL - Credit score is {score}, which is in the borderline range (600-649). Approval possible with additional conditions or a lower credit limit."
        else:
            message = f"PASSED - Credit score is {score}, which meets the required threshold. Payment history is {history.get('payment_history', 'unknown')} with {delinquencies} delinquencies."

        return {
            "agent": self.name,
            "message": message,
            "credit_score": score,
            "payment_history": history.get("payment_history", "unknown"),
            "delinquencies": delinquencies,
            "recommended_limit": history.get("recommended_credit_limit", 10000),
            "risk_score": history.get("risk_score", 5),
            "bureau_data": bureau,
            "history_data": history,
            "timestamp": datetime.now().isoformat()
        }


class FraudDetectorAgent:
    name = "Fraud-Detector"
    tools = ["device_risk_analysis", "behavioral_analysis"]
    mcp = MCPClient()

    async def detect_fraud(self, data: Dict, scenario: str = None) -> Dict:
        device = await self.mcp.call("device_risk_analysis", {
            "device_fingerprint": data["device_fingerprint"],
            "ip_address": data["ip_address"]
        }, scenario)
        behavior = await self.mcp.call("behavioral_analysis", {
            "customer_id": data["customer_id"],
            "ip_address": data["ip_address"],
            "device_fingerprint": data["device_fingerprint"]
        }, scenario)

        max_risk = max(
            device.get("risk_score", 0),
            behavior.get("ml_risk_score", 0)
        )
        fraud_risk = "low" if max_risk < 0.5 else "medium" if max_risk < 0.8 else "high"
        is_vpn = device.get("is_vpn", False)
        behavior_profile = behavior.get("behavior_profile", "normal")

        if fraud_risk == "high":
            vpn_note = " VPN usage detected." if is_vpn else ""
            message = f"FAILED - High fraud risk detected (score: {round(max_risk, 2)}).{vpn_note} Behavioral profile flagged as '{behavior_profile}'. Onboarding blocked."
        elif fraud_risk == "medium":
            message = f"REVIEW NEEDED - Medium fraud risk detected (score: {round(max_risk, 2)}). Behavioral profile is '{behavior_profile}'. Needs manual review before approval."
        else:
            message = f"PASSED - Fraud risk is low (score: {round(max_risk, 2)}). Device and behavioral checks normal. No suspicious activity detected."

        return {
            "agent": self.name,
            "message": message,
            "fraud_risk": fraud_risk,
            "anomaly_score": round(max_risk, 3),
            "device_analysis": device,
            "behavioral_analysis": behavior,
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Bank Onboarding Agent Marketplace",
    description=(
        "Three specialized agents exposed as REST APIs. "
        "Pull from Docker Hub and call /kyc, /credit, /fraud, or /onboard."
    ),
    version="1.0.0"
)

kyc_agent    = KYCValidatorAgent()
credit_agent = CreditCheckerAgent()
fraud_agent  = FraudDetectorAgent()


@app.get("/health")
def health():
    """Health check — confirms the container is running"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/agents")
def list_agents():
    """Lists all available agents and their MCP tools"""
    return {
        "agents": [
            {
                "name": kyc_agent.name,
                "endpoint": "/kyc",
                "mcp_tools": kyc_agent.tools,
                "description": "Verifies identity documents and screens against sanctions lists"
            },
            {
                "name": credit_agent.name,
                "endpoint": "/credit",
                "mcp_tools": credit_agent.tools,
                "description": "Queries credit bureaus and analyzes credit history"
            },
            {
                "name": fraud_agent.name,
                "endpoint": "/fraud",
                "mcp_tools": fraud_agent.tools,
                "description": "Analyzes device risk and behavioral patterns for fraud"
            }
        ],
        "total_mcp_tools": len(MCP_TOOLS)
    }


@app.post("/kyc")
async def run_kyc(req: KYCRequest):
    """
    KYC Validator Agent
    Calls: document_verification + sanctions_screening MCP tools
    """
    try:
        result = await kyc_agent.validate(req.model_dump())
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/credit")
async def run_credit(req: CreditRequest):
    """
    Credit Checker Agent
    Calls: credit_bureau_lookup + credit_history_analysis MCP tools
    """
    try:
        result = await credit_agent.check_credit(req.model_dump())
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/fraud")
async def run_fraud(req: FraudRequest):
    """
    Fraud Detector Agent
    Calls: device_risk_analysis + behavioral_analysis MCP tools
    """
    try:
        result = await fraud_agent.detect_fraud(req.model_dump())
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/onboard")
async def run_full_onboarding(req: OnboardRequest):
    """
    Full onboarding — runs all 3 agents IN PARALLEL.
    This is the main endpoint for complete customer onboarding.
    """
    try:
        data = req.model_dump()
        scenario = req.scenario  # from POST body, or None → falls back to global SCENARIO

        # Run all 3 agents simultaneously
        kyc_result, credit_result, fraud_result = await asyncio.gather(
            kyc_agent.validate(data, scenario),
            credit_agent.check_credit(data, scenario),
            fraud_agent.detect_fraud(data, scenario)
        )

        # Final decision logic
        decision = _make_decision(kyc_result, credit_result, fraud_result)

        return JSONResponse(content={
            "customer_id": req.customer_id,
            "decision": decision,
            "kyc": kyc_result,
            "credit": credit_result,
            "fraud": fraud_result,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _make_decision(kyc: Dict, credit: Dict, fraud: Dict) -> Dict:
    status = "approved"
    risk_level = "low"
    summary = ""

    if kyc.get("status") != "verified":
        return {
            "status": "rejected",
            "risk_level": "critical",
            "summary": "Application REJECTED — KYC check failed. " + kyc.get("message", ""),
            "kyc_status": kyc.get("status"),
            "credit_score": credit.get("credit_score"),
            "fraud_risk": fraud.get("fraud_risk"),
            "recommended_limit": None
        }

    if credit.get("credit_score", 1000) < 600:
        status = "rejected"
        risk_level = "critical"
    elif credit.get("credit_score", 1000) < 650:
        status = "conditional"
        risk_level = "medium"

    fraud_risk = fraud.get("fraud_risk", "low")
    if fraud_risk == "high":
        status = "rejected"
        risk_level = "critical"
    elif fraud_risk == "medium":
        status = "manual_review"
        risk_level = "medium"

    # Build plain English summary for the final decision
    if status == "approved":
        summary = (
            f"Application APPROVED — KYC verified, credit score {credit.get('credit_score')} "
            f"is above threshold, and fraud risk is low. "
            f"Recommended credit limit: {credit.get('recommended_limit', 0):,}."
        )
    elif status == "conditional":
        summary = (
            f"Application CONDITIONAL — KYC verified and fraud risk is low, but credit score "
            f"{credit.get('credit_score')} is in the borderline range (600-649). "
            f"Approval possible with a reduced credit limit."
        )
    elif status == "manual_review":
        summary = (
            f"Application needs MANUAL REVIEW — KYC verified and credit score is acceptable, "
            f"but fraud risk is medium (score: {fraud.get('anomaly_score', 'N/A')}). "
            f"A human agent must review before proceeding."
        )
    elif status == "rejected":
        if fraud_risk == "high":
            summary = (
                f"Application REJECTED — High fraud risk detected (score: {fraud.get('anomaly_score', 'N/A')}). "
                f"Fraud agent flagged suspicious device or behavioral patterns."
            )
        else:
            summary = (
                f"Application REJECTED — Credit score {credit.get('credit_score')} is below "
                f"the minimum threshold of 600. Customer has too many delinquencies."
            )

    return {
        "status": status,
        "risk_level": risk_level,
        "summary": summary,
        "kyc_status": kyc.get("status"),
        "credit_score": credit.get("credit_score"),
        "fraud_risk": fraud_risk,
        "recommended_limit": credit.get("recommended_limit") if status == "approved" else None
    }