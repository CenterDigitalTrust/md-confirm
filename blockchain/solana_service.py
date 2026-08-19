import os
import json
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solders.instruction import Instruction
from solders.message import Message
from solders.transaction import VersionedTransaction

# Адрес Memo-программы в сети Solana (стандартный)
MEMO_PROGRAM_ID = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")

def get_client():
    return Client("https://api.devnet.solana.com")

def load_wallet():
    wallet_path = os.path.join(os.path.dirname(__file__), "devnet_wallet.json")
    if not os.path.exists(wallet_path):
        raise Exception("Кошелек не найден. Запустите wallet_generator.py")
    with open(wallet_path, "r") as f:
        data = json.load(f)
    # Восстанавливаем Keypair из массива секретного ключа
    return Keypair.from_bytes(bytes(data["secret_key"]))

def request_airdrop_if_needed():
    client = get_client()
    wallet = load_wallet()
    balance_resp = client.get_balance(wallet.pubkey())
    balance = balance_resp.value
    
    # Если баланс меньше 0.1 SOL, просим airdrop (1 SOL = 1_000_000_000 lamports)
    if balance < 100_000_000:
        print("Баланс кошелька близок к нулю. Запрашиваем Airdrop (тестовые SOL)...")
        try:
            client.request_airdrop(wallet.pubkey(), 1_000_000_000)
            print("Airdrop успешно запрошен!")
        except Exception as e:
            print(f"Ошибка Airdrop (возможно лимит запросов): {e}")

def anchor_receipt(image_hash: str, decision: str) -> str:
    """
    Создает транзакцию в Solana с Memo (сообщением),
    в котором записан хеш фото и решение агента.
    Возвращает ID транзакции (signature).
    """
    client = get_client()
    wallet = load_wallet()
    
    # Формируем текст, который навсегда останется в блокчейне
    memo_message = f"MD-Confirm | Hash: {image_hash} | Decision: {decision}"
    
    # Создаем инструкцию для Memo Program
    memo_ix = Instruction(
        program_id=MEMO_PROGRAM_ID,
        accounts=[],
        data=memo_message.encode("utf-8")
    )
    
    # Получаем последний blockhash
    recent_blockhash = client.get_latest_blockhash().value.blockhash
    
    # Собираем сообщение транзакции
    msg = Message.new_with_blockhash(
        [memo_ix],
        wallet.pubkey(),
        recent_blockhash
    )
    
    # Подписываем
    tx = VersionedTransaction(msg, [wallet])
    
    # Отправляем в сеть
    response = client.send_transaction(tx)
    return str(response.value)
