import os
from google import genai
from pydantic import BaseModel
from typing import Literal

def get_client():
    if os.getenv("GEMINI_API_KEY"):
        return genai.Client()
    return genai.Client(vertexai=True, project=os.getenv("GOOGLE_CLOUD_PROJECT") or "gen-lang-client-0166064225", location="us-central1")

class VerdictSchema(BaseModel):
    decision: Literal["original_confirmed", "not_confirmed"]
    needs_review: bool
    reason: str

class FlushDecision(BaseModel):
    flush_now: bool
    trigger: Literal["count_threshold", "timeout", "high_priority", "not_yet"]
    reason: str

def deterministic_verdict(is_in_db: bool, user_claims_original: bool, phash_distance: int, hashes_match: bool, c2pa_status: str) -> VerdictSchema | None:
    if is_in_db and hashes_match and phash_distance is not None and phash_distance > 10:
        return VerdictSchema(decision="not_confirmed", needs_review=True, reason="Receipt ID exists but does not match this image (possible ID reuse)")
    if hashes_match is False:
        return VerdictSchema(decision="not_confirmed", needs_review=True, reason="On-chain/registry hash mismatch")
    if is_in_db and hashes_match and phash_distance is not None and phash_distance < 10:
        return VerdictSchema(decision="original_confirmed", needs_review=False, reason="Registry hit + phash within threshold")
    if c2pa_status == "missing" and user_claims_original:
        return VerdictSchema(decision="not_confirmed", needs_review=True, reason="No C2PA manifest; user claimed original")
        return VerdictSchema(decision="original_confirmed", needs_review=False, reason="Registry hit + phash within threshold")
    if not is_in_db and user_claims_original:
        return VerdictSchema(decision="not_confirmed", needs_review=True, reason="No registry record; user claimed original")
    if not is_in_db:
        return VerdictSchema(decision="not_confirmed", needs_review=False, reason="No registry record; no original claim")
    return None

async def analyze_provenance(
    is_in_db: bool, 
    user_claims_original: bool,
    phash_distance: int = None,
    hashes_match: bool = None,
    prnu_confidence: float = None,
    c2pa_status: str = "missing"
) -> VerdictSchema:
    verdict = deterministic_verdict(is_in_db, user_claims_original, phash_distance, hashes_match, c2pa_status)
    if verdict is None:
        verdict = VerdictSchema(decision="not_confirmed", needs_review=True, reason="Ambiguous state")
        
    client = get_client()
    prompt = f"""
    You are the MD-Confirm Provenance Explainer.
    The cryptographic engine has already made a deterministic decision: {verdict.decision}.
    
    Data context:
    - User claimed original: {user_claims_original}
    - Found in DB: {is_in_db}
    - On-chain match: {hashes_match}
    - pHash distance: {phash_distance}
    
    Write a 1-sentence technical explanation (reason) for this outcome. 
    CRITICAL RULES: Do NOT use the words "fake", "AI", "deepfake", or "tampered". 
    If original_confirmed, explain that it matches the hardware ledger. 
    If not_confirmed, explain that the origin cannot be verified.
    """
    
    import asyncio
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt
            )
            verdict.reason = response.text.strip()
            break
        except Exception as e:
            error_str = str(e)
            print(f"Gemini API attempt {attempt+1} failed: {error_str}")
            if "503" in error_str or "UNAVAILABLE" in error_str:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
            # If we exhausted retries or it's a different error, raise it
            raise e
    return verdict

async def handle_ledger_notary(pending_hashes_count: int, high_priority: bool) -> FlushDecision:
    client = get_client()
    
    prompt = f"""
    You are the MD-Confirm Ledger Notary Agent.
    Your job is to manage the Merkle Tree of cryptographic image hashes.
    
    Current state:
    - Hashes pending in Merkle Tree: {pending_hashes_count}
    - Contains high priority urgent media: {high_priority}
    
    Rules:
    1. If high_priority is True, flush immediately. (trigger: "high_priority", flush_now: True)
    2. If pending hashes >= 100, flush based on policy. (trigger: "count_threshold", flush_now: True)
    3. Otherwise, wait. (trigger: "not_yet", flush_now: False)
    
    Focus on policy decisions, not economics.
    
    Return a structured JSON strictly matching the FlushDecision schema.
    """
    
    import asyncio
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": FlushDecision,
                }
            )
            return response.parsed
        except Exception as e:
            error_str = str(e)
            print(f"Gemini API Notary attempt {attempt+1} failed: {error_str}")
            if "503" in error_str or "UNAVAILABLE" in error_str:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            raise e
