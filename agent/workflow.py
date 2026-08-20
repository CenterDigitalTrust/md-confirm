import os
from google import genai
from pydantic import BaseModel, Field

# We will use the standard genai client
# During local dev, you can set GEMINI_API_KEY environment variable.
def get_client():
    return genai.Client()

from pydantic import BaseModel
from typing import Literal

# Вердикт Provenance Verifier — только позитивное утверждение или "не подтверждено"
class VerdictSchema(BaseModel):
    decision: Literal["original_confirmed", "not_confirmed"]
    needs_review: bool          # True, если пользователь утверждал "оригинал", а подтвердить не вышло
    reason: str                 # для внутреннего лога/аудита, не показывается как публичный ярлык

# Решение Ledger Notary — когда флашить Merkle Tree
class FlushDecision(BaseModel):
    flush_now: bool
    trigger: Literal["count_threshold", "timeout", "high_priority", "not_yet"]
    reason: str

# We will use the standard genai client
def get_client():
    return genai.Client()

def analyze_provenance(file_hash: str, is_in_db: bool, user_claims_original: bool) -> VerdictSchema:
    """
    Анализирует криптографические данные и принимает решение по схеме VerdictSchema.
    Не утверждает, что контент — подделка или ИИ, только original_confirmed/not_confirmed.
    """
    client = get_client()
    
    prompt = f"""
    You are the MD-Confirm Provenance Agent (Verifier).
    Your job is to analyze cryptographic metadata and user claims about an image.
    
    User claims it is original: {user_claims_original}
    Cryptographic hash found in trusted on-device ledger (is_in_db): {is_in_db}
    
    Rules (Few-shot logic):
    1. If hash is found in trusted ledger (is_in_db=True) and matches known attested device -> decision: "original_confirmed", needs_review: False.
    2. If hash is missing, and user does not claim it is original (normal sharing) -> decision: "not_confirmed", needs_review: False.
    3. If hash is missing or mismatched, BUT user claims it is original -> decision: "not_confirmed", needs_review: True.
    
    CRITICAL: Never label content as "FAKE" or "AI-generated". You only verify if it is an exact cryptographic match to the original hardware capture.
    
    Return a structured JSON strictly matching the VerdictSchema.
    """
    
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": VerdictSchema,
        }
    )
    
    return response.parsed

async def handle_ledger_notary(pending_hashes_count: int, high_priority: bool) -> FlushDecision:
    """
    Sub-agent: Ledger Notary
    Решает, когда флашить Merkle Tree в блокчейн.
    """
    client = get_client()
    
    prompt = f"""
    You are the MD-Confirm Ledger Notary Agent.
    Your job is to manage the Merkle Tree of cryptographic image hashes and optimize blockchain transaction costs.
    
    Current state:
    - Hashes pending in Merkle Tree: {pending_hashes_count}
    - Contains high priority urgent media (e.g. Breaking News): {high_priority}
    
    Rules:
    1. If high_priority is True, you MUST flush immediately. (trigger: "high_priority", flush_now: True)
    2. If pending hashes >= 100, flush to save gas. (trigger: "count_threshold", flush_now: True)
    3. Otherwise, wait. (trigger: "not_yet", flush_now: False)
    
    Return a structured JSON strictly matching the FlushDecision schema.
    """
    
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": FlushDecision,
        }
    )
    return response.parsed
