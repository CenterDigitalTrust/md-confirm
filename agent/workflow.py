import os
from google import genai
from pydantic import BaseModel, Field
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

async def analyze_provenance(
    is_in_db: bool, 
    user_claims_original: bool,
    phash_distance: int = None,
    prnu_confidence: float = None,
    hashes_match: bool = None,
    file_hash: str = None
) -> VerdictSchema:
    client = get_client()
    
    prompt = f"""
    You are the MD-Confirm Provenance Agent (Verifier).
    Your job is to analyze cryptographic metadata and visual integrity of an image.
    
    Data:
    - User claims it is original: {user_claims_original}
    - Cryptographic ID found in Database: {is_in_db}
    - On-chain Solana hash matches Database: {hashes_match}
    - pHash distance from original: {phash_distance}
    - PRNU (Silicon Fingerprint) Match Confidence: {prnu_confidence} (0 is identical, < 5 is compression, > 10 is deepfake/crop).
    
    Rules (Few-shot logic):
    1. If on-chain hash mismatch (hashes_match=False), decision MUST be "not_confirmed", needs_review: True.
    2. If pHash distance is clearly > 10, image is visibly altered. decision MUST be "not_confirmed".
    3. If is_in_db=True, hashes_match=True, and pHash distance is small (<10), decision: "original_confirmed", needs_review: False.
    4. If is_in_db=False, and user does not claim it is original -> decision: "not_confirmed", needs_review: False.
    
    CRITICAL: Base your reasoning strictly on the cryptographic and pHash data provided.
    
    Return a structured JSON strictly matching the VerdictSchema.
    """
    
    response = await client.aio.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": VerdictSchema,
        }
    )
    
    return response.parsed

async def handle_ledger_notary(pending_hashes_count: int, high_priority: bool) -> FlushDecision:
    client = get_client()
    
    prompt = f"""
    You are the MD-Confirm Ledger Notary Agent.
    Your job is to manage the Merkle Tree of cryptographic image hashes and optimize blockchain transaction costs.
    
    Current state:
    - Hashes pending in Merkle Tree: {pending_hashes_count}
    - Contains high priority urgent media: {high_priority}
    
    Rules:
    1. If high_priority is True, flush immediately. (trigger: "high_priority", flush_now: True)
    2. If pending hashes >= 100, flush to save gas. (trigger: "count_threshold", flush_now: True)
    3. Otherwise, wait. (trigger: "not_yet", flush_now: False)
    
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
