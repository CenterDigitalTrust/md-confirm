"""
embed.py — MD-Confirm capture-time embedding.

Pipeline:
  1. Generate a short watermark ID (8 bytes / 64 bits) — NOT a full blockchain
     address (too long to embed robustly). This ID is just a pointer.
  2. Reed-Solomon encode it -> 16-byte codeword (8 data + 8 parity bytes),
     giving error correction margin for social-media recompression damage.
  3. Embed the 128-bit codeword into the image across the whole frame using
     invisible-watermark's DWT-DCT-SVD method (frequency domain -> survives
     JPEG recompression, unlike single-pixel/LSB approaches).
  4. Compute a perceptual hash (phash) + exact sha256 of the ORIGINAL file.
  5. Notarize {watermark_id, phash, sha256} on the ledger (local now,
     Solana devnet later via ledger.notarize_on_solana_devnet).

Usage:
    python embed.py path/to/photo.jpg
Outputs:
    path/to/photo_watermarked.jpg   <- publish THIS one to social media
    prints the watermark_id and ledger record
"""

import sys
import os
import hashlib
import secrets

import cv2
import imagehash
from PIL import Image
from reedsolo import RSCodec
from imwatermark import WatermarkEncoder

import ledger

DATA_BYTES = 8       # 64-bit ID
PARITY_BYTES = 8      # RS parity -> corrects up to PARITY_BYTES//2 byte errors
CODEWORD_BITS = (DATA_BYTES + PARITY_BYTES) * 8  # 128 bits total payload


def generate_id() -> bytes:
    return secrets.token_bytes(DATA_BYTES)


def bytes_to_bits(data: bytes) -> list:
    bits = []
    for byte in data:
        bits.extend([(byte >> i) & 1 for i in range(7, -1, -1)])
    return bits


def main():
    if len(sys.argv) != 2:
        print("Usage: python embed.py path/to/photo.jpg")
        sys.exit(1)

    src_path = sys.argv[1]
    if not os.path.exists(src_path):
        print(f"File not found: {src_path}")
        sys.exit(1)

    # 1. Generate ID
    raw_id = generate_id()
    watermark_id_hex = raw_id.hex()

    # 2. Reed-Solomon encode -> 16-byte codeword
    rsc = RSCodec(PARITY_BYTES)
    codeword = rsc.encode(raw_id)  # bytes, length DATA_BYTES + PARITY_BYTES
    bits = bytes_to_bits(bytes(codeword))
    assert len(bits) == CODEWORD_BITS, f"expected {CODEWORD_BITS} bits, got {len(bits)}"

    # 3. Embed watermark across the whole pixel area (frequency domain)
    img = cv2.imread(src_path)
    if img is None:
        print("cv2 could not read the image — check format/path.")
        sys.exit(1)

    encoder = WatermarkEncoder()
    encoder.set_watermark('bits', bits)
    watermarked = encoder.encode(img, 'dwtDctSvd')

    base, ext = os.path.splitext(src_path)
    out_path = f"{base}_watermarked.jpg"
    cv2.imwrite(out_path, watermarked, [cv2.IMWRITE_JPEG_QUALITY, 95])

    # 4. Hashes of the ORIGINAL (pre-watermark) file — this is your ground truth
    with open(src_path, "rb") as f:
        original_bytes = f.read()
    file_sha256 = hashlib.sha256(original_bytes).hexdigest()
    phash = str(imagehash.phash(Image.open(src_path)))

    # 5. Notarize
    record = ledger.notarize(
        watermark_id=watermark_id_hex,
        phash=phash,
        file_sha256=file_sha256,
    )

    print("=" * 60)
    print("EMBEDDED + NOTARIZED")
    print("=" * 60)
    print(f"watermark_id : {watermark_id_hex}")
    print(f"phash        : {phash}")
    print(f"sha256       : {file_sha256}")
    print(f"ledger record: {record['record_hash']}")
    print(f"watermarked file -> {out_path}")
    print()
    print("Publish THIS file to social media, then download it back and run:")
    print(f"    python verify.py <downloaded_file>")


if __name__ == "__main__":
    main()
