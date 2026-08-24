import os
from google import genai
from pydantic import BaseModel
from typing import Literal

def get_client():
    return genai.Client()

class VerdictSchema(BaseModel):
    decision: Literal["original_confirmed", "not_confirmed"]
    needs_review: bool
    reason: str

class FlushDecision(BaseModel):
    flush_now: bool
    trigger: Literal["count_threshold", "timeout", "high_priority", "not_yet"]
    reason: str

def deterministic_verdict(is_in_db: bool, user_claims_original: bool, phash_distance: int, hashes_match: bool) -> VerdictSchema | None:
    if hashes_match is False:
        return VerdictSchema(decision="not_confirmed", needs_review=True, reason="On-chain/registry hash mismatch")
    if is_in_db and hashes_match and phash_distance is not None and phash_distance < 10:
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
    prnu_confidence: float = None
) -> VerdictSchema:
    verdict = deterministic_verdict(is_in_db, user_claims_original, phash_distance, hashes_match)
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
    
    response = await client.aio.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt
    )
    
    verdict.reason = response.text.strip()
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
    
    response = await client.aio.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": FlushDecision,
        }
    )
    return response.parsed
