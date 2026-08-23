"""
verify.py — MD-Confirm verification of a downloaded (re-compressed) image.

Usage:
    python verify.py path/to/downloaded_from_instagram.jpg

Pipeline:
  1. Decode the 128-bit watermark payload from the image (survives resize/
     JPEG recompression because it lives in the DWT-DCT-SVD domain, not in
     raw pixel values).
  2. Reed-Solomon DECODE -> corrects up to PARITY_BYTES//2 corrupted bytes.
     This is the safety margin against whatever the social platform did.
  3. Recovered watermark_id -> look up the ledger record.
  4. Compute phash of the DOWNLOADED file and compare (Hamming distance)
     against the phash notarized at capture time -> catches "same watermark,
     but content substantially altered/edited" attacks.
  5. Verdict.
"""

import sys
import os

import cv2
import imagehash
from PIL import Image
from reedsolo import RSCodec, ReedSolomonError
from imwatermark import WatermarkDecoder

import ledger

DATA_BYTES = 8
PARITY_BYTES = 8
CODEWORD_BITS = (DATA_BYTES + PARITY_BYTES) * 8

PHASH_MAX_DISTANCE = 8  # tune this after real-world social platform tests


def bits_to_bytes(bits: list) -> bytes:
    assert len(bits) % 8 == 0
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for b in bits[i:i + 8]:
            byte = (byte << 1) | int(b)
        out.append(byte)
    return bytes(out)


def main():
    if len(sys.argv) != 2:
        print("Usage: python verify.py path/to/downloaded.jpg")
        sys.exit(1)

    path = sys.argv[1]
    img = cv2.imread(path)
    if img is None:
        print("cv2 could not read the image.")
        sys.exit(1)

    # 1. Decode raw bits
    decoder = WatermarkDecoder('bits', CODEWORD_BITS)
    recovered_bits = decoder.decode(img, 'dwtDctSvd')
    codeword = bits_to_bytes(recovered_bits)

    # 2. ECC correction
    rsc = RSCodec(PARITY_BYTES)
    try:
        decoded_msg, decoded_full, errata_pos = rsc.decode(codeword)
        watermark_id_hex = bytes(decoded_msg).hex()
        n_corrected = len(errata_pos)
    except ReedSolomonError:
        print("=" * 60)
        print("FAILED: watermark unreadable — too much damage to recover,")
        print("even with error correction. Falls back to PRNU check.")
        print("=" * 60)
        sys.exit(2)

    print(f"Recovered watermark_id: {watermark_id_hex}  ({n_corrected} bytes ECC-corrected)")

    # 3. Ledger lookup
    record = ledger.lookup(watermark_id_hex)
    if record is None:
        print("FAILED: no ledger record for this ID. Not notarized / possibly forged.")
        sys.exit(3)

    # 4. Perceptual hash comparison
    downloaded_phash = imagehash.phash(Image.open(path))
    original_phash = imagehash.hex_to_hash(record["phash"])
    distance = downloaded_phash - original_phash

    print(f"Original phash : {record['phash']}")
    print(f"Downloaded phash: {downloaded_phash}")
    print(f"Hamming distance: {distance}  (threshold: {PHASH_MAX_DISTANCE})")

    print("=" * 60)
    if distance <= PHASH_MAX_DISTANCE:
        print("VERIFIED: content matches notarized original.")
        print(f"Notarized at: {record['timestamp']}")
        print(f"Ledger record hash: {record['record_hash']}")
    else:
        print("WARNING: watermark/ID checks out, but visual content has")
        print("drifted beyond threshold — possible edit/manipulation after capture.")
    print("=" * 60)


if __name__ == "__main__":
    main()
