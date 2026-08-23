import asyncio
import os
import sys
from dotenv import load_dotenv

# Avoid cp1251 encoding errors on Windows console
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

from agent.workflow import analyze_provenance

async def run_tests():
    print("--- Запуск тестирования Агента MD-Confirm ---")
    
    print("\nТЕСТ 1: Идеальный сценарий (Фото найдено в БД, хеши совпадают)")
    res1 = await analyze_provenance(
        is_in_db=True, user_claims_original=True,
        phash_distance=0, prnu_confidence=0.98, hashes_match=True,
        file_hash="test_hash_ideal"
    )
    print(f"Решение агента: {res1.decision.upper()}")
    print(f"Логика агента: {res1.reason}")
    
    print("\nТЕСТ 2: Обычный мем (Не в БД, без претензий на оригинал)")
    res2 = await analyze_provenance(
        is_in_db=False, user_claims_original=False,
        phash_distance=None, prnu_confidence=None, hashes_match=None,
        file_hash="test_hash_meme"
    )
    print(f"Решение агента: {res2.decision.upper()}")
    print(f"Логика агента: {res2.reason}")
    
    print("\nТЕСТ 3: ПОПЫТКА ОБМАНА (Не в БД, но утверждает что оригинал)")
    res3 = await analyze_provenance(
        is_in_db=False, user_claims_original=True,
        phash_distance=None, prnu_confidence=None, hashes_match=None,
        file_hash="test_hash_deception"
    )
    print(f"Решение агента: {res3.decision.upper()}")
    print(f"Логика агента: {res3.reason}")

if __name__ == "__main__":
    asyncio.run(run_tests())
