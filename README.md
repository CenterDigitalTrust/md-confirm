# MD-Confirm — A Demo Architecture for Provenance 🛡️📸

Built for the **All things agentic hackathon** (Gemini + Google Cloud).

**MD-Confirm** is an autonomous fleet of AI agents designed to establish cryptographically verifiable provenance for digital media. 

Instead of trying to "catch up" with Generative AI to detect fakes, **MD-Confirm proposes proactive cryptographic verification of digital content provenance at the exact moment of creation.**

### 🎯 Core Positioning
MD-Confirm does **not** claim:
❌ *"We know this image is truth."*

MD-Confirm claims:
✅ *"We can verify that this image has a confirmed origin and that its provenance chain has not been broken."*

## 🏆 Track: The Taskmaster
MD-Confirm acts as an autonomous workflow agent. It takes the messy, multi-step chore of visual forensics and handles it end-to-end: automatically signing images at capture, managing zero-trust state via Google Firestore, and triggering a reasoning agent to analyze and anchor proofs on a public blockchain.

## 🏗️ Architecture

```text
[ Camera/Client ] 
       │ (1. Uploads Image)
       ▼
┌────────────────────────────────────────────────────────┐
│ MD-Confirm Agentic Gateway (FastAPI)                   │
├─────────────────────────┬──────────────────────────────┤
│ 📸 Agent 1: Edge        │ ⚖️ Agent 3: Notary           │
│ Simulates hardware      │ Manages evidence publication │
│ attestation & capture   │ policy (anchoring to chain)  │
└──────┬──────────────────┴───────────────┬──────────────┘
       │                                  │
       ▼ (2. Stores State)                ▼ (3. Anchors Hash)
[ ☁️ Google Cloud Firestore]      [ 🔗 Solana Blockchain ]
       │                                  │
       │ (4. Fetches State)               │ (5. Verifies Hash)
       ▼                                  ▼
┌────────────────────────────────────────────────────────┐
│ 🧠 Agent 2: Gemini Verifier                            │
│ Deterministic crypto check first, then LLM generates   │
│ a human-readable explanation of the final verdict.     │
└─────────────────────────┬──────────────────────────────┘
                          │ (6. Autonomous Verdict)
                          ▼
             [ 🟢 VERIFIED / 🔴 NOT_CONFIRMED ]
```

* **Agent 1 (Edge):** Simulates hardware-level device attestation and *provenance-at-capture*. The PoC uses cryptographic device identification, SHA-256, and invisible watermarking, while hardware-level PRNU is simulated in software.
* **Agent 2 (Verifier):** Performs deterministic verification of cryptographic and provenance signals first. Gemini then generates a human-readable explanation of the resulting verdict. **The LLM is NOT the source of truth and does not make the cryptographic decision.**
* **Agent 3 (Blockchain Notary):** Manages the evidence publication policy. It can anchor a single receipt or a batch/Merkle root to Solana. A flush is triggered dynamically by a threshold, a timeout, or a high-priority event.

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

## ⚠️ Hackathon Disclaimers
- **Demo Architecture:** This is a proof-of-concept for the hackathon, not a production-ready security system.
- **Simulated Hardware:** Hardware-level attestation is simulated in this PoC. Production deployment would move this component into a trusted capture environment / secure hardware layer.
- **Blockchain:** We use the Solana Devnet proxy, not a production ledger.
- **Positive Badge Only:** Following provenance best practices, the system only awards an ORIGINAL CONFIRMED badge. It does not label images as "fakes" or "deepfakes", but rather defaults to NOT_CONFIRMED / NEEDS_REVIEW.
