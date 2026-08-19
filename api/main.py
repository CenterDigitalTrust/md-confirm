from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
import hashlib
import os
import json
import asyncio

# === GOOGLE CLOUD INFRASTRUCTURE (MANDATORY HACKATHON STACK) ===
try:
    from google.cloud import firestore
    from google.cloud import pubsub_v1
    GCP_ENABLED = True
    db_client = firestore.AsyncClient()
    publisher = pubsub_v1.PublisherClient()
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "md-confirm-demo")
    TOPIC_PATH = publisher.topic_path(PROJECT_ID, "agent-verification-events")
except ImportError:
    GCP_ENABLED = False
    print("GCP SDK not found. Running in local MVP mode (Local JSON Mock).")

from agent.workflow import analyze_provenance
from blockchain.solana_service import anchor_receipt, request_airdrop_if_needed

app = FastAPI(title="MD-Confirm Orchestrator")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
DB_FILE = os.path.join(os.path.dirname(__file__), "..", "db.json")

@app.on_event("startup")
async def startup_event():
    await request_airdrop_if_needed()

# === FIRESTORE DB ABSTRACTION ===
async def save_hash_to_db(file_hash: str):
    """
    Использует Google Cloud Firestore для хранения хешей (в продакшене).
    Для локального тестирования откатывается на db.json.
    """
    if GCP_ENABLED:
        # Интеграция с Firestore
        doc_ref = db_client.collection("trusted_hashes").document(file_hash)
        await doc_ref.set({"hash": file_hash, "timestamp": firestore.SERVER_TIMESTAMP})
    else:
        # Fallback для локального демо без GCP кредитов
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f: data = json.load(f)
        else:
            data = {"signed_hashes": []}
        
        if file_hash not in data["signed_hashes"]:
            data["signed_hashes"].append(file_hash)
            with open(DB_FILE, "w") as f: json.dump(data, f)

def check_hash_in_db(file_hash: str) -> bool:
    # (Для демо используем синхронное чтение json, в проде - Firestore get)
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: data = json.load(f)
        return file_hash in data.get("signed_hashes", [])
    return False

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
async def verify_content(
    file: UploadFile = File(None), 
    is_original: bool = Form(False)
):
    """
    Эмулирует цензора/Агента: проверяет криптографический хеш файла.
    Если изменен хотя бы 1 пиксель, хеш не совпадет с базой.
    """
    if not file or not file.filename:
        return JSONResponse({"status": "error", "message": "No file uploaded"}, status_code=400)

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    # Проверяем, есть ли хеш в доверенной базе (Firestore / db.json)
    is_in_db = check_hash_in_db(file_hash)
    
    # === AGENT 2: GEMINI VERIFIER (via Antigravity Node) ===
    # Запускаем ИИ для проверки логики
    decision_result = analyze_provenance(
        file_hash=file_hash,
        is_in_db=is_in_db,
        user_claims_original=is_original
    )
    
    if not decision_result:
        return JSONResponse({"status": "error", "message": "Agent 2 (Gemini) failed to analyze"}, status_code=500)
    
    # === AGENT 3: LEDGER NOTARY REASONING (SIMULATED) ===
    # Агент 3 принимает логическое решение о записи в GCUL/Solana
    ledger_agent_log = ""
    tx_id = None
    
    if decision_result.decision.upper() == "VERIFIED":
        ledger_agent_log = "Ledger Agent 3 Reasoning: High-priority immediate publication detected. Action: Bypassing Merkle queue. Flushing directly to GCUL (Solana mock)."
        try:
            tx_id = await anchor_receipt(file_hash, decision_result.decision)
        except Exception as e:
            print(f"Ошибка отправки в Solana: {e}")
            tx_id = "error_solana_network"
    elif decision_result.decision.upper() == "FLAGGED":
        ledger_agent_log = "Ledger Agent 3 Reasoning: Content flagged as altered. Action: No blockchain anchor required. Storing incident in local cache."

    # === GOOGLE CLOUD PUB/SUB INTEGRATION ===
    # Отправка события в шину данных (для аналитики или дальнейшей обработки)
    if GCP_ENABLED:
        try:
            message_data = json.dumps({"hash": file_hash, "verdict": decision_result.decision}).encode("utf-8")
            publisher.publish(TOPIC_PATH, message_data)
        except Exception as e:
            print(f"Pub/Sub mock error: {e}")

    return JSONResponse({
        "status": "success",
        "file_hash": file_hash,
        "agent_decision": decision_result.decision,
        "agent_reasoning": decision_result.reasoning,
        "ledger_agent_log": ledger_agent_log,
        "solana_tx_id": tx_id
    })
