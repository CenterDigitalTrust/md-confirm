from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
import hashlib
import os
import json
import asyncio

# === STRICT GOOGLE CLOUD INFRASTRUCTURE ===
# По правилам хакатона мы ОБЯЗАНЫ использовать реальную инфраструктуру GCP.
# Никаких фейковых db.json. Приложение должно падать, если GCP не настроен.
from google.cloud import firestore
from google.cloud import pubsub_v1

db_client = firestore.AsyncClient()
publisher = pubsub_v1.PublisherClient()
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") # Cloud Run подставляет это автоматически

from agent.workflow import analyze_provenance
from blockchain.solana_service import anchor_receipt, request_airdrop_if_needed

app = FastAPI(title="MD-Confirm Orchestrator")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.on_event("startup")
async def startup_event():
    await request_airdrop_if_needed()

# === FIRESTORE DB ABSTRACTION ===
async def save_hash_to_db(file_hash: str):
    """Строго сохраняем хеш в Google Cloud Firestore"""
    doc_ref = db_client.collection("trusted_hashes").document(file_hash)
    await doc_ref.set({"hash": file_hash, "timestamp": firestore.SERVER_TIMESTAMP})

async def check_hash_in_db_async(file_hash: str) -> bool:
    """Асинхронная проверка наличия хеша в Firestore"""
    doc_ref = db_client.collection("trusted_hashes").document(file_hash)
    doc = await doc_ref.get()
    return doc.exists

# === ANTIGRAVITY ORCHESTRATION PIPELINE ===
# Этот модуль выступает в роли Chief Orchestrator, управляя потоками между Агентами и GCP.

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    html_path = os.path.join(FRONTEND_DIR, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.post("/sign")
async def sign_content(file: UploadFile = File(...)):
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    await save_hash_to_db(file_hash)
    return JSONResponse({"status": "signed", "hash": file_hash})

@app.post("/verify")
async def verify_content(file: UploadFile = File(...), is_original: bool = Form(...)):
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    
    # Проверяем, есть ли хеш в доверенной базе (Строго Firestore)
    is_in_db = await check_hash_in_db_async(file_hash)
    
    # === AGENT 2: GEMINI VERIFIER ===
    try:
        verdict = analyze_provenance(
            file_hash=file_hash,
            is_in_db=is_in_db,
            user_claims_original=is_original
        )
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Agent 2 (Gemini) failed: {str(e)}"}, status_code=500)
    
    # === AGENT 3: LEDGER NOTARY REASONING ===
    # Agent 3 explicitly reasons about when to write to Solana
    ledger_agent_log = ""
    tx_id = None
    
    if verdict.decision == "original_confirmed":
        # Simulating Merkle Tree pending hashes logic for Agent 3
        pending_hashes_count = 101 # Simulated state (normally read from DB)
        high_priority = True # Simulated news event
        
        from agent.workflow import handle_ledger_notary
        try:
            flush_decision = await handle_ledger_notary(pending_hashes_count, high_priority)
            ledger_agent_log = f"Ledger Notary Decision: {flush_decision.trigger}. Reason: {flush_decision.reason}"
            
            if flush_decision.flush_now:
                # DENY BY DEFAULT policy overridden by explicitly verified status
                tx_id = await anchor_receipt(file_hash, verdict.decision)
        except Exception as e:
            ledger_agent_log = f"Ledger Notary Error: {str(e)}"
            tx_id = "error_solana_network"
            
    elif verdict.decision == "not_confirmed":
        if verdict.needs_review:
            ledger_agent_log = "Ledger Agent 3: Content not confirmed but claimed original -> NEEDS_REVIEW. No blockchain write."
        else:
            ledger_agent_log = "Ledger Agent 3: Normal unverified sharing. No blockchain write."

    # === GOOGLE CLOUD PUB/SUB INTEGRATION ===
    if PROJECT_ID:
        TOPIC_PATH = publisher.topic_path(PROJECT_ID, "agent-verification-events")
        try:
            message_data = json.dumps({"hash": file_hash, "verdict": verdict.decision}).encode("utf-8")
            publisher.publish(TOPIC_PATH, message_data)
        except Exception as e:
            print(f"Pub/Sub push error: {e}")

    # Return structure for UI
    # The frontend expects "agent_decision" = "VERIFIED" or "FLAGGED" for its logic
    ui_decision = "VERIFIED" if verdict.decision == "original_confirmed" else "FLAGGED"

    return JSONResponse({
        "status": "success",
        "file_hash": file_hash,
        "agent_decision": ui_decision, # Mapped for frontend compatibility
        "agent_reasoning": verdict.reason,
        "ledger_agent_log": ledger_agent_log,
        "solana_tx_id": tx_id
    })
