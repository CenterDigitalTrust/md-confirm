import os
from google import genai
from pydantic import BaseModel, Field

# We will use the standard genai client
# During local dev, you can set GEMINI_API_KEY environment variable.
def get_client():
    return genai.Client()

class AgentDecision(BaseModel):
    decision: str = Field(description="One of: 'verified', 'unverified', 'flagged', 'tampered'")
    reasoning: str = Field(description="Step-by-step reasoning explaining the decision.")

def analyze_provenance(c2pa_data: dict, is_original_claim: bool) -> AgentDecision:
    """
    Анализирует метаданные и принимает решение о верификации.
    Few-shot логика:
    - Манифест валиден -> "verified"
    - Нет манифеста, и пользователь не утверждает, что это оригинал -> "unverified"
    - Нет манифеста, но пользователь утверждает "оригинал" -> "flagged"
    - Хеш не совпадает -> "tampered"
    """
    client = get_client()
    
    prompt = f"""
    You are the MD-Confirm Provenance Agent.
    Your job is to analyze C2PA metadata and user claims about an image.
    
    User claims it is original: {is_original_claim}
    C2PA metadata status: {c2pa_data.get('status')}
    
    Rules:
    1. If C2PA status is 'valid', decision is 'verified'.
    2. If C2PA status is 'missing' and user claim is False, decision is 'unverified'.
    3. If C2PA status is 'missing' and user claim is True, decision is 'flagged'.
    4. If C2PA status is 'invalid' or hash mismatch, decision is 'tampered'.
    
    Return a structured JSON with 'decision' and 'reasoning'.
    """
    
    # We use Gemini 3.5 Flash as required by the hackathon
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": AgentDecision,
        }
    )
    
    return response.parsed
