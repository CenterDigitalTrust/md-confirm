# MD-Confirm — The Infrastructure of Truth 🛡️📸

Built for the **All things agentic hackathon** (Gemini + Google Cloud).

**MD-Confirm** is an autonomous fleet of AI agents designed to establish an unbreakable chain of custody for digital media. By combining invisible cryptographic watermarking, Gemini 3.5 Flash vision-reasoning, and immutable Solana blockchain anchoring, our agentic fleet autonomously verifies the authenticity of any image.

## 🏆 Track: The Taskmaster
MD-Confirm acts as an autonomous workflow agent. Instead of a simple chatbot, it takes the messy, multi-step chore of visual forensics and handles it end-to-end: automatically signing images at capture, managing zero-trust state via Google Firestore, and triggering a reasoning agent to analyze and anchor proofs on a public blockchain.

## 🏗️ Architecture

```text
[ Camera/Client ] 
       │ (1. Uploads Image)
       ▼
┌────────────────────────────────────────────────────────┐
│ MD-Confirm Agentic Gateway (FastAPI)                   │
├─────────────────────────┬──────────────────────────────┤
│ 🕵️ Agent 1:            │ 📝 Agent 3:                  │
│ Capture Signature Sim   │ Ledger Notary                │
│ (Hardware attestation)  │ (Anchors state to chain)     │
└──────┬──────────────────┴───────────────┬──────────────┘
       │                                  │
       ▼ (2. Stores State)                ▼ (3. Anchors Hash)
[ ☁️ Google Cloud Firestore]      [ 🔗 Solana Blockchain ]
       │                                  │
       │ (4. Fetches State)               │ (5. Verifies Hash)
       ▼                                  ▼
┌────────────────────────────────────────────────────────┐
│ 🧠 Agent 2: Gemini Verifier (Gemini 3.5 Flash)         │
│ Evaluates image integrity, handles provenance checks,  │
│ and cross-references Firestore vs Solana data.         │
└─────────────────────────┬──────────────────────────────┘
                          │ (6. Autonomous Verdict)
                          ▼
             [ 🟢 VERIFIED / 🔴 TAMPERED ]
```

## 🛠️ Tech Stack
* **AI Model:** Gemini 3.5 Flash (via Google GenAI SDK)
* **Google Cloud:** Firestore (Agent Memory Bank)
* **Blockchain:** Solana Devnet (solana-py, solders)
* **Backend:** FastAPI (Python 3.10+)
* **Computer Vision:** opencv-python, imagehash, invisible-watermark

## 🚀 Spin-up Instructions

### 1. Prerequisites
* Python 3.10+
* Google Cloud Project with **Firestore** enabled.
* Gemini API Key.

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/md-confirm.git
cd md-confirm

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
1. Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key
X_DEVICE_ATTESTATION_KEY=your_secret_key_here
```
2. Place your Google Cloud Service Account JSON key in the `env/` folder and name it `firestore-key.json`.
3. (Optional) Generate a Solana Devnet wallet in `blockchain/devnet_wallet.json` and fund it with Devnet SOL for on-chain anchoring.

### 4. Run the Agentic Fleet
```bash
python -m uvicorn api.main:app --reload --port 8000
```
Open your browser and navigate to `http://localhost:8000`. 
1. Upload an image to "Snap & Sign".
2. Download the watermarked result.
3. Upload it to the "Verify" tab to see the agents in action!
