from fastapi import FastAPI, UploadFile, File, Form, Request, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import hashlib
import os
import json
import asyncio

# === STRICT GOOGLE CLOUD INFRASTRUCTURE ===
from google.cloud import firestore
from google.cloud import pubsub_v1

db_client = firestore.AsyncClient()
publisher = pubsub_v1.PublisherClient()
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")

from agent.workflow import analyze_provenance, handle_ledger_notary
from api.watermark_engine import extract_prnu_fingerprint
from blockchain.solana_service import anchor_receipt, request_airdrop_if_needed, verify_anchor_onchain

app = FastAPI(title="MD-Confirm Orchestrator")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.on_event("startup")
async def startup_event():
    await request_airdrop_if_needed()

# === FIRESTORE DB ABSTRACTION (Receipts Schema) ===
async def save_hash_to_db(file_hash: str):
    doc_ref = db_client.collection("receipts").document(file_hash)
    await doc_ref.set({"image_hash": file_hash, "timestamp": firestore.SERVER_TIMESTAMP, "status": "signed"})
    
    # Add to merkle pending queue
    pending_ref = db_client.collection("merkle_pending").document(file_hash)
    await pending_ref.set({"image_hash": file_hash, "timestamp": firestore.SERVER_TIMESTAMP})

async def check_hash_in_db_async(file_hash: str) -> bool:
    doc_ref = db_client.collection("receipts").document(file_hash)
    doc = await doc_ref.get()
    return doc.exists

async def get_pending_merkle_count() -> int:
    # Get current count of pending hashes for Agent 3
    docs = db_client.collection("merkle_pending").stream()
    count = 0
    async for _ in docs:
        count += 1
    return count

# === ANTIGRAVITY ORCHESTRATION PIPELINE ===
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    html_path = os.path.join(FRONTEND_DIR, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.post("/sign")
async def sign_content(
    file: UploadFile = File(...),
    x_device_attestation_key: str = Header(None)
):
    if x_device_attestation_key != "valid-hardware-key-123":
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Device Attestation Key")
        
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    await save_hash_to_db(file_hash)
    return JSONResponse({"status": "signed", "hash": file_hash})

@app.post("/verify")
async def verify_content(
    file: UploadFile = File(...), 
    is_original: bool = Form(...),
    high_priority: bool = Form(False)
):
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    
    is_in_db = await check_hash_in_db_async(file_hash)
    
    # === AGENT 2: GEMINI VERIFIER ===
    try:
        verdict = await analyze_provenance(file_hash=file_hash, is_in_db=is_in_db, user_claims_original=is_original)
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Agent 2 (Gemini) failed: {str(e)}"}, status_code=500)
    
    if hashes_match is False:
        verdict.decision = "not_confirmed"
        verdict.reason = "CRITICAL: On-chain hash does NOT match Database record! Possible database tamper."
        verdict.needs_review = True

    # === AGENT 3: LEDGER NOTARY REASONING ===
    ledger_agent_log = ""
    tx_id = existing_solana_tx_id
    
    if verdict.decision == "original_confirmed" and not existing_solana_tx_id:
        pending_hashes_count = await get_pending_merkle_count()
        
        try:
            flush_decision = await handle_ledger_notary(pending_hashes_count, high_priority)
            ledger_agent_log = f"Ledger Notary Decision: {flush_decision.trigger}. Reason: {flush_decision.reason}"
            
            if flush_decision.flush_now:
                tx_id = await anchor_receipt(file_hash, verdict.decision)
                # Update DB with transaction
                await db_client.collection("receipts").document(file_hash).update({
                    "solana_tx_id": tx_id,
                    "decision": verdict.decision
                })
        except Exception as e:
            ledger_agent_log = f"Ledger Notary Error: {str(e)}"
            tx_id = "error_solana_network"
            
    elif verdict.decision == "not_confirmed":
        if verdict.needs_review:
            ledger_agent_log = "Ledger Agent 3: Content not confirmed but claimed original -> NEEDS_REVIEW."
        else:
            ledger_agent_log = "Ledger Agent 3: Normal unverified sharing."

    # === GOOGLE CLOUD PUB/SUB INTEGRATION ===
    if PROJECT_ID:
        TOPIC_PATH = publisher.topic_path(PROJECT_ID, "agent-verification-events")
        try:
            message_data = json.dumps({"hash": file_hash, "verdict": verdict.decision}).encode("utf-8")
            future = publisher.publish(TOPIC_PATH, message_data)
            future.result(timeout=5)
        except Exception as e:
            print(f"Pub/Sub push error: {e}")

    # Neutral UI decision
    ui_decision = "VERIFIED" if verdict.decision == "original_confirmed" else "NOT_CONFIRMED"

    return JSONResponse({
        "status": "success",
        "file_hash": file_hash,
        "agent_decision": ui_decision,
        "agent_reasoning": verdict.reason,
        "ledger_agent_log": ledger_agent_log,
        "solana_tx_id": tx_id
    })
