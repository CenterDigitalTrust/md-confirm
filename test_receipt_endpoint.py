import asyncio
import os
import hashlib
from fastapi.testclient import TestClient

# We will run this against the actual running app or TestClient
# Better to use TestClient to avoid needing uvicorn running
from api.main import app

client = TestClient(app)

def run_tests():
    print("=== STARTING RECEIPT TESTS ===")
    
    # 1. Sign
    print("\n--- 1. SIGNING A MOCK FILE ---")
    mock_content = b"this is a mock image for receipt testing 2026-08-23"
    file_hash = hashlib.sha256(mock_content).hexdigest()
    print(f"Computed hash: {file_hash}")
    
    auth_header = os.getenv("DEVICE_ATTESTATION_KEY", "valid-hardware-key-123")
    
    res_sign = client.post(
        "/sign",
        files={"file": ("test.jpg", mock_content, "image/jpeg")},
        headers={"X-Device-Attestation-Key": auth_header}
    )
    print(f"/sign response: {res_sign.status_code}")
    print(res_sign.json())
    
    # 2. Verify (forcing high_priority to ensure anchor happens)
    print("\n--- 2. VERIFYING CONTENT ---")
    res_verify = client.post(
        "/verify",
        files={"file": ("test.jpg", mock_content, "image/jpeg")},
        data={"is_original": "true", "high_priority": "true"}
    )
    print(f"/verify response: {res_verify.status_code}")
    print(res_verify.json())
    
    # 3. Test Positive Receipt
    print(f"\n--- 3. TESTING RECEIPT (SUCCESS SCENARIO) FOR {file_hash} ---")
    res_receipt = client.get(f"/receipt/{file_hash}")
    print(f"/receipt response: {res_receipt.status_code}")
    print(res_receipt.json())
    
    # 4. Test Negative Receipt
    fake_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    print(f"\n--- 4. TESTING RECEIPT (404 SCENARIO) FOR {fake_hash} ---")
    res_fail = client.get(f"/receipt/{fake_hash}")
    print(f"/receipt response: {res_fail.status_code}")
    print(res_fail.json())

if __name__ == "__main__":
    run_tests()
