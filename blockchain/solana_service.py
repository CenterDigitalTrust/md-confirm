import os
import json
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solders.instruction import Instruction
from solders.message import Message
from solders.transaction import VersionedTransaction

# Адрес Memo-программы в сети Solana (стандартный)
MEMO_PROGRAM_ID = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")

def load_wallet():
    wallet_path = os.path.join(os.path.dirname(__file__), "devnet_wallet.json")
    if not os.path.exists(wallet_path):
        raise Exception("Кошелек не найден. Запустите wallet_generator.py")
    with open(wallet_path, "r") as f:
        data = json.load(f)
    return Keypair.from_bytes(bytes(data["secret_key"]))

async def request_airdrop_if_needed():
    async with AsyncClient("https://api.devnet.solana.com") as client:
        wallet = load_wallet()
        balance_resp = await client.get_balance(wallet.pubkey())
        balance = balance_resp.value
        
        # Если баланс меньше 0.1 SOL, просим airdrop
        if balance < 100_000_000:
            print("Баланс кошелька близок к нулю. Запрашиваем Airdrop (тестовые SOL)...")
            try:
                await client.request_airdrop(wallet.pubkey(), 1_000_000_000)
                print("Airdrop успешно запрошен!")
            except Exception as e:
                print(f"Ошибка Airdrop: {e}")

async def anchor_receipt(image_hash: str, decision: str) -> str:
    """
    Создает транзакцию в Solana с Memo (сообщением),
    в котором записан хеш фото и решение агента.
    """
    async with AsyncClient("https://api.devnet.solana.com") as client:
        wallet = load_wallet()
        memo_message = f"MD-Confirm | Hash: {image_hash} | Decision: {decision}"
        
        memo_ix = Instruction(
            program_id=MEMO_PROGRAM_ID,
            accounts=[],
            data=memo_message.encode("utf-8")
        )
        
        recent_blockhash_resp = await client.get_latest_blockhash()
        recent_blockhash = recent_blockhash_resp.value.blockhash
        
        msg = Message.new_with_blockhash(
            [memo_ix],
            wallet.pubkey(),
            recent_blockhash
        )
        
        tx = VersionedTransaction(msg, [wallet])
        response = await client.send_transaction(tx)
        return str(response.value)
