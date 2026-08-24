import cv2
import numpy as np
import imagehash
from PIL import Image
import hashlib
import secrets
import io
from reedsolo import RSCodec, ReedSolomonError
from imwatermark import WatermarkEncoder, WatermarkDecoder

DATA_BYTES = 8
PARITY_BYTES = 8
CODEWORD_BITS = (DATA_BYTES + PARITY_BYTES) * 8

def bytes_to_bits(data: bytes) -> list:
    bits = []
    for byte in data:
        bits.extend([(byte >> i) & 1 for i in range(7, -1, -1)])
    return bits

def bits_to_bytes(bits: list) -> bytes:
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for b in bits[i:i + 8]:
            byte = (byte << 1) | int(b)
        out.append(byte)
    return bytes(out)

def embed_watermark(image_bytes: bytes):
    """
    Returns (watermarked_image_bytes, watermark_id_hex, original_phash, original_sha256)
    """
    raw_id = secrets.token_bytes(DATA_BYTES)
    watermark_id_hex = raw_id.hex()

    rsc = RSCodec(PARITY_BYTES)
    codeword = rsc.encode(raw_id)
    bits = bytes_to_bits(bytes(codeword))

    # Read image from bytes
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")

    # Embed
    encoder = WatermarkEncoder()
    encoder.set_watermark('bits', bits)
    watermarked_img = encoder.encode(img, 'dwtDctSvd')

    # Encode back to bytes (JPEG)
    success, encoded_img = cv2.imencode('.jpg', watermarked_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not success:
        raise ValueError("Could not encode watermarked image")

    # Calculate hashes on ORIGINAL bytes
    original_sha256 = hashlib.sha256(image_bytes).hexdigest()
    
    # Calculate phash on ORIGINAL bytes
    pil_img = Image.open(io.BytesIO(image_bytes))
    phash_val = str(imagehash.phash(pil_img))

    return encoded_img.tobytes(), watermark_id_hex, phash_val, original_sha256

def extract_watermark_and_phash(image_bytes: bytes, original_phash_str: str = None):
    """
    Returns (watermark_id_hex, n_corrected_bytes, downloaded_phash, phash_distance)
    If watermark cannot be decoded, returns (None, 0, downloaded_phash, distance_or_none)
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Calc downloaded phash
    pil_img = Image.open(io.BytesIO(image_bytes))
    downloaded_phash = imagehash.phash(pil_img)
    
    distance = None
    if original_phash_str:
        orig_hash = imagehash.hex_to_hash(original_phash_str)
        distance = downloaded_phash - orig_hash

    if img is None:
        return None, 0, str(downloaded_phash), distance

    decoder = WatermarkDecoder('bits', CODEWORD_BITS)
    try:
        recovered_bits = decoder.decode(img, 'dwtDctSvd')
        codeword = bits_to_bytes(recovered_bits)
    except Exception as e:
        return None, 0, str(downloaded_phash), distance

    rsc = RSCodec(PARITY_BYTES)
    try:
        decoded_msg, decoded_full, errata_pos = rsc.decode(codeword)
        watermark_id_hex = bytes(decoded_msg).hex()
        n_corrected = len(errata_pos)
        return watermark_id_hex, n_corrected, str(downloaded_phash), distance
    except ReedSolomonError:
        return None, 0, str(downloaded_phash), distance

def extract_prnu_fingerprint(image_bytes: bytes) -> float | None:
    """Demo stub. Real PRNU needs Camera2/raw - out of hackathon scope."""
    return None  # never invent confidence.
