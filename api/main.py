from fastapi import FastAPI, UploadFile, File, Form, Request, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
import hashlib
import os
import json
import asyncio
import io

# === STRICT GOOGLE CLOUD INFRASTRUCTURE ===
from google.cloud import firestore
from google.cloud import pubsub_v1

db_client = firestore.AsyncClient()
publisher = pubsub_v1.PublisherClient()
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")

from agent.workflow import analyze_provenance, handle_ledger_notary
from api.watermark_engine import embed_watermark, extract_watermark_and_phash, extract_prnu_fingerprint
from blockchain.solana_service import anchor_receipt, request_airdrop_if_needed, verify_anchor_onchain

app = FastAPI(title="MD-Confirm Orchestrator")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.on_event("startup")
async def startup_event():
    try:
        await request_airdrop_if_needed()
    except Exception as e:
        print(f"Airdrop on startup failed (non-critical): {e}")

# === FIRESTORE DB ABSTRACTION (Receipts Schema) ===
async def save_hash_to_db(file_hash: str, watermark_id: str = None, phash: str = None, original_sha256: str = None):
    """Save a signed image receipt to Firestore with watermark metadata."""
    doc_data = {
        "image_hash": file_hash,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "status": "signed",
    }
    if watermark_id:
        doc_data["watermark_id"] = watermark_id
    if phash:
        doc_data["phash"] = phash
    if original_sha256:
        doc_data["original_sha256"] = original_sha256

    doc_ref = db_client.collection("receipts").document(file_hash)
    await doc_ref.set(doc_data)
    
    # Add to merkle pending queue
    pending_ref = db_client.collection("merkle_pending").document(file_hash)
    await pending_ref.set({"image_hash": file_hash, "timestamp": firestore.SERVER_TIMESTAMP})

async def check_hash_in_db_async(file_hash: str) -> bool:
    doc_ref = db_client.collection("receipts").document(file_hash)
    doc = await doc_ref.get()
    return doc.exists

async def get_receipt_from_db(file_hash: str) -> dict:
    """Get full receipt document from Firestore."""
    doc_ref = db_client.collection("receipts").document(file_hash)
    doc = await doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

async def find_receipt_by_watermark_id(watermark_id: str) -> dict:
    """Look up a receipt by its embedded watermark ID."""
    query = db_client.collection("receipts").where("watermark_id", "==", watermark_id)
    docs = query.stream()
    async for doc in docs:
        return doc.to_dict()
    return None

async def get_pending_merkle_count() -> int:
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
    """Agent 1: Capture Signature — embeds invisible watermark, computes hashes, saves to Firestore."""
    if x_device_attestation_key != "valid-hardware-key-123":
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Device Attestation Key")
        
    content = await file.read()
    
    try:
        # Embed invisible DWT-DCT-SVD watermark with Reed-Solomon error correction
        watermarked_bytes, watermark_id, phash_val, original_sha256 = embed_watermark(content)
        file_hash = original_sha256
    except Exception as e:
        # Fallback: if watermark embedding fails (e.g., tiny image), just hash
        file_hash = hashlib.sha256(content).hexdigest()
        watermarked_bytes = content
        watermark_id = None
        phash_val = None
        original_sha256 = file_hash
        print(f"Watermark embedding failed (fallback to raw hash): {e}")
    
    await save_hash_to_db(file_hash, watermark_id=watermark_id, phash=phash_val, original_sha256=original_sha256)
    
    # Return watermarked image as downloadable response
    return Response(
        content=watermarked_bytes,
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f'attachment; filename="watermarked_{file.filename}"',
            "X-MD-Confirm-Hash": file_hash,
            "X-MD-Confirm-Watermark-ID": watermark_id or "none",
            "X-MD-Confirm-Status": "signed",
        }
    )

@app.post("/verify")
async def verify_content(
    file: UploadFile = File(...), 
    is_original: bool = Form(...),
    high_priority: bool = Form(False)
):
    """Agent 2 + Agent 3: Verify provenance via Gemini reasoning + Solana anchoring."""
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    
    # --- Step 1: Check if this exact hash exists in DB ---
    is_in_db = await check_hash_in_db_async(file_hash)
    
    # --- Step 2: Try to extract watermark and find original receipt ---
    phash_distance = None
    prnu_confidence = None
    hashes_match = None
    existing_solana_tx_id = None
    original_receipt = None
    
    try:
        watermark_id, n_corrected, downloaded_phash, distance = extract_watermark_and_phash(content)
        
        if watermark_id:
            # Look up original receipt by watermark ID
            original_receipt = await find_receipt_by_watermark_id(watermark_id)
            if original_receipt:
                is_in_db = True
                stored_phash = original_receipt.get("phash")
                if stored_phash and distance is None:
                    # Recalculate distance against stored pHash
                    import imagehash
                    orig_hash = imagehash.hex_to_hash(stored_phash)
                    dl_hash = imagehash.hex_to_hash(downloaded_phash)
                    phash_distance = dl_hash - orig_hash
                else:
                    phash_distance = distance
                
                existing_solana_tx_id = original_receipt.get("solana_tx_id")
                
                # Verify on-chain hash matches if we have a tx_id
                if existing_solana_tx_id and existing_solana_tx_id not in ("error_solana_network", None):
                    try:
                        onchain_hash = await verify_anchor_onchain(existing_solana_tx_id)
                        stored_hash = original_receipt.get("image_hash")
                        hashes_match = (onchain_hash == stored_hash) if onchain_hash else None
                    except Exception:
                        hashes_match = None
        elif not is_in_db:
            # No watermark found and hash not in DB — check by hash directly
            original_receipt = await get_receipt_from_db(file_hash)
            if original_receipt:
                existing_solana_tx_id = original_receipt.get("solana_tx_id")
                phash_distance = 0  # exact hash match
    except Exception as e:
        print(f"Watermark extraction failed (non-critical): {e}")
    
    # PRNU simulation
    prnu_confidence = extract_prnu_fingerprint(content)
    
    # === AGENT 2: GEMINI VERIFIER ===
    try:
        verdict = await analyze_provenance(
            is_in_db=is_in_db,
            user_claims_original=is_original,
            phash_distance=phash_distance,
            prnu_confidence=prnu_confidence,
            hashes_match=hashes_match,
            file_hash=file_hash
        )
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Agent 2 (Gemini) failed: {str(e)}"}, status_code=500)
    
    # Override verdict if on-chain hash mismatch detected
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
                receipt_hash = original_receipt.get("image_hash", file_hash) if original_receipt else file_hash
                await db_client.collection("receipts").document(receipt_hash).update({
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
            print(f"Pub/Sub push error (non-critical): {e}")

    # UI-friendly decision label
    ui_decision = "VERIFIED" if verdict.decision == "original_confirmed" else "NOT_CONFIRMED"

    return JSONResponse({
        "status": "success",
        "file_hash": file_hash,
        "agent_decision": ui_decision,
        "agent_reasoning": verdict.reason,
        "needs_review": verdict.needs_review,
        "ledger_agent_log": ledger_agent_log,
        "solana_tx_id": tx_id
    })


@app.get("/receipt/{file_hash}")
async def get_receipt(file_hash: str):
    """Public lookup endpoint — anyone can check if an image was verified."""
    receipt = await get_receipt_from_db(file_hash)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found. This image hash has not been registered.")
    
    # Convert Firestore timestamp to string for JSON serialization
    timestamp = receipt.get("timestamp")
    if timestamp:
        timestamp = str(timestamp)
    
    return JSONResponse({
        "receipt_id": file_hash,
        "image_hash": receipt.get("image_hash"),
        "status": receipt.get("status", "unknown"),
        "decision": receipt.get("decision"),
        "watermark_id": receipt.get("watermark_id"),
        "solana_tx_id": receipt.get("solana_tx_id"),
        "registered_at": timestamp,
        "verified": receipt.get("decision") == "original_confirmed"
    })
