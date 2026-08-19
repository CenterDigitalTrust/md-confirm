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

## ⚙️ Architecture & Tech Stack
* **Agent Reasoning:** Google Gemini 3.5 Flash (`google-genai` SDK)
* **Backend:** FastAPI (Python)
* **Blockchain Anchor:** Solana Devnet (`solders`, `solana-py`)
* **Frontend:** Vanilla JS / HTML5

## 🏃‍♂️ How to Run Locally
1. `python -m venv venv`
2. `.\venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. Add `GEMINI_API_KEY="your_key"` to a `.env` file.
5. `python -m uvicorn api.main:app --host 0.0.0.0 --port 8000`

## 🔮 Strategic Vision & Offline-First Architecture
While this demo uses Solana and real-time processing, the production architecture is designed for edge-cases and global scale:
* **Offline-First Camera Agent:** If the user has no internet (e.g., taking photos in nature), the Edge Agent continues generating cryptographic hashes locally.
* **Merkle Tree Batching:** When the internet connection is restored, the smartphone doesn't spam the network. It compiles all offline hashes into a single Merkle Tree and sends only the **Merkle Root** to the Cloud Agent.
* **Google Cloud Universal Ledger (GCUL):** The Cloud Agent anchors this single root to GCUL, securely validating thousands of offline photos with zero gas fees for the user. 
We are building the fault-tolerant infrastructure of truth for the AI era.
