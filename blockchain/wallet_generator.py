import os
import json
from solders.keypair import Keypair

def generate_wallet():
    # В новых версиях solana-py используется solders для ключей
    kp = Keypair()
    pubkey = str(kp.pubkey())
    secret_key = list(bytes(kp))
    
    wallet_data = {
        "public_key": pubkey,
        "secret_key": secret_key
    }
    
    wallet_path = os.path.join(os.path.dirname(__file__), "devnet_wallet.json")
    with open(wallet_path, "w") as f:
        json.dump(wallet_data, f, indent=4)
        
    print(f"[OK] Новыи кошелек Solana devnet создан!")
    print(f"Публичный ключ (Адрес): {pubkey}")
    print(f"Ключи сохранены в: {wallet_path}")

if __name__ == "__main__":
    generate_wallet()
