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
    request_airdrop_if_needed()

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
    
    # === SOLANA INTEGRATION ===
    # Отправляем транзакцию-квитанцию в блокчейн
    tx_id = None
    if decision_result.decision.upper() in ["VERIFIED", "FLAGGED"]:
        try:
            tx_id = anchor_receipt(file_hash, decision_result.decision)
        except Exception as e:
            print(f"Ошибка отправки в Solana: {e}")
            tx_id = "error_solana_network"
    
    return JSONResponse({
        "status": "success",
        "file_hash": file_hash,
        "agent_decision": decision_result.decision,
        "agent_reasoning": decision_result.reasoning,
        "solana_tx_id": tx_id
    })
