import asyncio
import os
import sys
from unittest.mock import patch, AsyncMock, MagicMock
import json

os.environ["DEVICE_ATTESTATION_KEY"] = "valid-hardware-key-123"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"

sys.modules['google'] = MagicMock()
sys.modules['google.cloud'] = MagicMock()
sys.modules['google.cloud.firestore'] = MagicMock()
sys.modules['google.cloud.pubsub_v1'] = MagicMock()
sys.modules['google.genai'] = MagicMock()

import api.main
from fastapi.testclient import TestClient

def test_e2e_verification_flow():
    print("======================================================")
    print("E2E TEST: Valid Photo Flow (Mocking GCP/Gemini network)")
    print("======================================================")
    
    with patch("api.main.check_hash_in_db_async", new_callable=AsyncMock) as mock_db, \
         patch("api.main.analyze_provenance", new_callable=AsyncMock) as mock_gemini_verifier, \
         patch("api.main.get_pending_merkle_count", new_callable=AsyncMock) as mock_count, \
         patch("api.main.handle_ledger_notary", new_callable=AsyncMock) as mock_ledger, \
         patch("api.main.anchor_receipt", new_callable=AsyncMock) as mock_anchor, \
         patch("api.main.request_airdrop_if_needed", new_callable=AsyncMock) as mock_airdrop:
         
        from api.main import app
        client = TestClient(app)
        
        mock_db.return_value = True # is_in_db = True
        
        from agent.workflow import VerdictSchema, FlushDecision
        mock_gemini_verifier.return_value = VerdictSchema(
            decision="original_confirmed",
            needs_review=False,
            reason="Cryptographic hash matches the on-device ledger perfectly."
        )
        
        mock_count.return_value = 105
        
        mock_ledger.return_value = FlushDecision(
            flush_now=True,
            trigger="count_threshold",
            reason="105 hashes pending, optimal gas conditions met."
        )
        
        mock_anchor.return_value = "solana_tx_dummy_777"
        
        # Patch db_client correctly for async
        api.main.db_client.collection.return_value.document.return_value.update = AsyncMock()
        
        print("Sending POST /verify with dummy image and high_priority=False...")
        response = client.post(
            "/verify",
            data={
                "is_original": "true",
                "high_priority": "false"
            },
            files={"file": ("test_photo.jpg", b"fake_image_data_123", "image/jpeg")}
        )
        
        print("\n--- TEST LOG ---")
        print(f"Status Code: {response.status_code}")
        print("is_in_db Mock Called:", mock_db.called)
        print("Gemini Verifier Called:", mock_gemini_verifier.called)
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
        
if __name__ == "__main__":
    test_e2e_verification_flow()
