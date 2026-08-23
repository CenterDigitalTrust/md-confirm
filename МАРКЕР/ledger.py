"""
ledger.py — Ledger Notary stub for MD-Confirm.

Two modes:
  1. LOCAL  — append-only JSON file, hash-chained (sha256(prev_hash + record)),
              so any tampering with a past record breaks every hash after it.
              Good enough to prove the concept TODAY without needing SOL/RPC setup.
  2. SOLANA — anchors just the record's sha256 hash on-chain via the Memo program
              on devnet. Real blockchain notarization. Requires a funded devnet
              wallet. Stubbed here — fill in when you're ready to wire it in.

Record schema (one JSON object per line, JSONL):
{
  "watermark_id": "a1b2c3d4e5f6a1b2",   # hex, the short ID embedded in pixels
  "phash": "8f373114...",                # perceptual hash of ORIGINAL image
  "sha256": "...",                       # exact byte hash of ORIGINAL file
  "prnu_ref": "...",                     # optional, path/hash to PRNU fingerprint record
  "timestamp": "2026-08-23T12:00:00Z",
  "prev_hash": "...",                    # hash of previous record (chain link)
  "record_hash": "..."                   # sha256 of this record (excluding this field)
}
"""

import json
import hashlib
import os
from datetime import datetime, timezone

LEDGER_PATH = os.path.join(os.path.dirname(__file__), "ledger.jsonl")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _last_record_hash() -> str:
    if not os.path.exists(LEDGER_PATH):
        return "0" * 64  # genesis
    last = None
    with open(LEDGER_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                last = line
    if last is None:
        return "0" * 64
    return json.loads(last)["record_hash"]


def notarize(watermark_id: str, phash: str, file_sha256: str, prnu_ref: str = "") -> dict:
    """Append a new notarization record to the local hash-chained ledger."""
    prev_hash = _last_record_hash()
    record = {
        "watermark_id": watermark_id,
        "phash": phash,
        "sha256": file_sha256,
        "prnu_ref": prnu_ref,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prev_hash": prev_hash,
    }
    record_bytes = json.dumps(record, sort_keys=True).encode("utf-8")
    record["record_hash"] = _sha256_hex(record_bytes)

    with open(LEDGER_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

    return record


def lookup(watermark_id: str) -> dict | None:
    """Find the most recent record for a given watermark_id."""
    if not os.path.exists(LEDGER_PATH):
        return None
    found = None
    with open(LEDGER_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("watermark_id") == watermark_id:
                found = rec
    return found


def verify_chain_integrity() -> bool:
    """Walk the whole ledger and confirm no record has been tampered with."""
    if not os.path.exists(LEDGER_PATH):
        return True
    prev_hash = "0" * 64
    with open(LEDGER_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            claimed_hash = rec["record_hash"]
            check = dict(rec)
            del check["record_hash"]
            recomputed = _sha256_hex(json.dumps(check, sort_keys=True).encode("utf-8"))
            if recomputed != claimed_hash:
                return False
            if rec["prev_hash"] != prev_hash:
                return False
            prev_hash = claimed_hash
    return True


# --- Solana devnet anchoring stub (wire in when ready) -------------------
def notarize_on_solana_devnet(record_hash_hex: str, keypair_path: str, rpc_url: str = "https://api.devnet.solana.com") -> str:
    """
    Anchors record_hash_hex on-chain via the SPL Memo program.
    Requires: pip install solders solana
    Requires: a funded devnet keypair (solana-keygen new, then `solana airdrop 1 --url devnet`)

    Returns the transaction signature (your on-chain proof).
    This is intentionally left as a stub — plug in when you move past local testing.
    """
    raise NotImplementedError(
        "Wire this in once local pipeline is verified. "
        "See: https://spl.solana.com/memo for the Memo program approach."
    )
