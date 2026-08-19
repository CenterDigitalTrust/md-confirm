# MD-Confirm: Publish-Time Provenance Agent 🛡️

**A next-generation AI agent that survives content publication to combat deepfakes and protect society from disinformation.**
*Built for the Google All Things Agentic Hackathon (Taskmaster Track).*

## 🌍 The Scale & Societal Impact
In the tidal wave of AI generation, MD-Confirm is not just a tool—it is the ultimate shield against deepfakes and mass disinformation. The scale of this solution applies directly to high-stakes global sectors:
* **Law Enforcement & Courts:** Ensuring the absolute truthfulness and chain of custody for digital evidence. A cryptographically anchored photo cannot be disputed.
* **Journalism & Mass Media:** Allowing news organizations to cryptographically prove the authenticity of their field reporting, ensuring public trust in correctly presented information.
* **Public Protection:** Immediately protecting ordinary users from falling victim to AI-generated scams, fake news, and manipulated media.

## 🚀 The Problem
Modern cameras (like Google Pixel) embed cryptographic C2PA signatures (and physical sensor PRNU noise) to prove an image is real. **However, social media platforms strip this metadata upon upload.** Once published, the proof of authenticity is dead.

## 💡 The Solution
MD-Confirm is an autonomous multi-step agent that sits between the camera and the network. 
When a user clicks "Share", the agent:
1. Verifies the hardware signature (sensor noise).
2. Uses **Gemini 3.5 Flash** to reason about the image's authenticity.
3. **Anchors the receipt to a blockchain (Solana)**, creating an indestructible proof of originality.

## ⚙️ Architecture & Tech Stack (GCP Native)
* **Agent 1 (Edge Orchestrator):** Hardware-level PRNU extraction & SHA-256 signing.
* **Agent 2 (Verifier):** Gemini 3.5 Flash for contextual reasoning and logic verification.
* **Agent 3 (Ledger Notary):** Autonomous reasoning agent managing Merkle trees.
* **Orchestration Framework:** Antigravity (AGY) Agentic Framework pattern.
* **Google Cloud Infrastructure (Mandatory Stack):** 
  * `Cloud Firestore` (Immutable hash storage & Merkle tree queuing)
  * `Cloud Pub/Sub` (Asynchronous event streaming from edge devices)
  * `Cloud Run` (Serverless backend hosting)
* **Backend:** FastAPI (Python)
* **Blockchain Anchor:** Solana Devnet (transitioning to GCUL)
* **Frontend:** Vanilla JS / HTML5

## 🏃‍♂️ How to Run Locally
1. `python -m venv venv`
2. `.\venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. Add `GEMINI_API_KEY="your_key"` to a `.env` file.
5. `python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`

## 🔮 Strategic Vision & Google Crypto Integration
While this MVP uses Solana for demonstration, the production architecture is natively designed for the Google Ecosystem:
* **Google Pixel Hardware Crypto:** Future iterations will utilize the native Titan M2 chip in Google Pixel phones to securely sign the hashes at the hardware level, making spoofing physically impossible.
* **Google Cloud Universal Ledger (GCUL):** Instead of public blockchains, Agent 3 will anchor Merkle Roots directly into Google's enterprise ledger (GCUL). This guarantees 100% data sovereignty, zero gas fees for the end-user, and instant global verification across all platforms (Android, Chrome, Google Search).
* **Agent 3 (Ledger Notary) Logic:** This is not a simple API call. Agent 3 is a reasoning agent that evaluates network traffic and urgency, deciding autonomously whether to queue hashes in a local Merkle Tree (offline/low-priority mode) or flush them immediately to GCUL (high-priority mode). 

We are building the fault-tolerant infrastructure of truth for the AI era.
