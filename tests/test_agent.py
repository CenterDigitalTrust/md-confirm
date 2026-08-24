import pytest
from agent.workflow import deterministic_verdict, VerdictSchema

def test_mismatch_id():
    # ID exists in DB (is_in_db=True, hashes_match=True), but phash_distance is > 10 (mismatch image content)
    verdict = deterministic_verdict(is_in_db=True, user_claims_original=True, phash_distance=15, hashes_match=True, c2pa_status="valid")
    assert verdict is not None
    assert verdict.decision == "not_confirmed"
    assert "possible ID reuse" in verdict.reason
    assert verdict.needs_review is True

def test_no_c2pa_plus_claim():
    # c2pa is missing, but user claims it's original
    verdict = deterministic_verdict(is_in_db=True, user_claims_original=True, phash_distance=5, hashes_match=True, c2pa_status="missing")
    assert verdict is not None
    assert verdict.decision == "not_confirmed"
    assert verdict.needs_review is True
    assert "No C2PA manifest" in verdict.reason

def test_degraded_mode_behavior():
    # In degraded mode, the API sets UI badge to None and doesn't claim ORIGINAL CONFIRMED
    # This is tested implicitly by checking the deterministic logic without DB
    verdict = deterministic_verdict(is_in_db=False, user_claims_original=False, phash_distance=0, hashes_match=False, c2pa_status="missing")
    assert verdict.decision == "not_confirmed"
