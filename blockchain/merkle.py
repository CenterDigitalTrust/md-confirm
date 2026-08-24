import hashlib

def merkle_root(hashes: list[str]) -> str:
    layer = [bytes.fromhex(h) if len(h) == 64 else hashlib.sha256(h.encode()).digest() for h in sorted(hashes)]
    if not layer:
        return hashlib.sha256(b"").hexdigest()
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [hashlib.sha256(layer[i] + layer[i+1]).digest() for i in range(0, len(layer), 2)]
    return layer[0].hex()
