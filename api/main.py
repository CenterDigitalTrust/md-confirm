from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
import os
import hashlib
import json
from dotenv import load_dotenv

load_dotenv()
from agent.workflow import analyze_provenance
from blockchain.solana_service import anchor_receipt, request_airdrop_if_needed

app = FastAPI(title="MD-Confirm", description="Publish-Time Provenance Agent")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")
DB_FILE = os.path.join(BASE_DIR, "db.json")

@app.on_event("startup")
async def startup_event():
    # При запуске сервера проверяем баланс и просим тестовые SOL
    await request_airdrop_if_needed()

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: 
            return json.load(f)
    return {"signed_hashes": []}

def save_db(data):
    with open(DB_FILE, "w") as f: 
        json.dump(data, f)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    html_path = os.path.join(FRONTEND_DIR, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.post("/sign")
async def sign_content(file: UploadFile = File(...)):
    """
    Эмулирует камеру: вычисляет точный SHA-256 хеш файла 
    и сохраняет его в доверенную базу данных.
    """
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    
    db = load_db()
    if file_hash not in db["signed_hashes"]:
        db["signed_hashes"].append(file_hash)
        save_db(db)
        
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
    
    db = load_db()
    
    if file_hash in db["signed_hashes"]:
        c2pa_data = {"status": "valid"}
    else:
        c2pa_data = {"status": "missing"}
    
    try:
        decision_result = analyze_provenance(c2pa_data, is_original)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    
    # === AGENT 3: LEDGER NOTARY REASONING (SIMULATED) ===
    # Агент 3 принимает решение: копить хеш в Дерево Меркла или отправлять срочно.
    ledger_agent_log = ""
    tx_id = None
    
    if decision_result.decision.upper() == "VERIFIED":
        # Эмуляция принятия решения Агентом 3
        ledger_agent_log = "Ledger Agent 3 Reasoning: High-priority immediate publication detected. Action: Bypassing Merkle queue. Flushing directly to Solana (GCUL emulation)."
        try:
            tx_id = await anchor_receipt(file_hash, decision_result.decision)
        except Exception as e:
            print(f"Ошибка отправки в Solana: {e}")
            tx_id = "error_solana_network"
    elif decision_result.decision.upper() == "FLAGGED":
        ledger_agent_log = "Ledger Agent 3 Reasoning: Content flagged as altered. Action: No blockchain anchor required. Storing incident in local cache."

    return JSONResponse({
        "status": "success",
        "file_hash": file_hash,
        "agent_decision": decision_result.decision,
        "agent_reasoning": decision_result.reasoning,
        "ledger_agent_log": ledger_agent_log,
        "solana_tx_id": tx_id
    })
