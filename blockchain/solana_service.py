import os
import json
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solders.instruction import Instruction
from solders.message import Message
from solders.transaction import VersionedTransaction
from solders.signature import Signature

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

from solders.signature import Signature
async def verify_anchor_onchain(tx_id: str) -> str:
    from solana.rpc.async_api import AsyncClient
    async with AsyncClient("https://api.devnet.solana.com") as client:
        try:
            sig = Signature.from_string(tx_id)
            tx_response = await client.get_transaction(sig, encoding="jsonParsed", max_supported_transaction_version=0)
            if not tx_response or not tx_response.value:
                return None
            message = tx_response.value.transaction.transaction.message
            for ix in message.instructions:
                if str(ix.program_id) == str(MEMO_PROGRAM_ID):
                    memo_str = ""
                    if hasattr(ix, 'parsed') and ix.parsed:
                        memo_str = ix.parsed
                    elif hasattr(ix, 'data'):
                        try:
                            memo_str = str(ix.parsed) if hasattr(ix, 'parsed') else str(ix.data)
                        except:
                            pass
                    if not memo_str and type(ix).__name__ == "UiPartiallyDecodedInstruction":
                        import base58
                        try:
                            memo_str = base58.b58decode(ix.data).decode('utf-8')
                        except:
                            memo_str = str(ix.data)
                    if not memo_str and hasattr(ix, 'parsed'):
                         memo_str = str(ix.parsed)
                    if isinstance(memo_str, str):
                        if "Hash: " in memo_str:
                            parts = memo_str.split("Hash: ")
                            if len(parts) > 1:
                                return parts[1].split(" |")[0].strip()
            return None
        except Exception as e:
            return None


async def anchor_merkle_root(root_hash: str, batch_size: int) -> str:
    from datetime import datetime
    async with AsyncClient("https://api.devnet.solana.com") as client:
        wallet = load_wallet()
        ts = datetime.utcnow().isoformat()
        memo_message = f"MD-Confirm | Root: {root_hash} | BatchSize: {batch_size} | TS: {ts}"
        
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
