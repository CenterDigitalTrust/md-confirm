import os
import sys
from dotenv import load_dotenv

# Избегаем ошибки кодировки cp1251 в Windows консоли
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

from agent.workflow import analyze_provenance

def run_tests():
    print("--- Запуск тестирования Агента MD-Confirm ---")
    
    print("\nТЕСТ 1: Идеальный сценарий (Фото с настоящей подписью C2PA)")
    c2pa_data = {"status": "valid"}
    res1 = analyze_provenance(c2pa_data, is_original_claim=False)
    print(f"Решение агента: {res1.decision.upper()}")
    print(f"Логика агента: {res1.reasoning}")
    
    print("\nТЕСТ 2: Обычный мем или скриншот (Без подписи, без претензий на оригинал)")
    c2pa_data = {"status": "missing"}
    res2 = analyze_provenance(c2pa_data, is_original_claim=False)
    print(f"Решение агента: {res2.decision.upper()}")
    print(f"Логика агента: {res2.reasoning}")
    
    print("\nТЕСТ 3: ПОПЫТКА ОБМАНА (Подписи нет, но пользователь нажимает 'Я клянусь, что это оригинал')")
    c2pa_data = {"status": "missing"}
    res3 = analyze_provenance(c2pa_data, is_original_claim=True)
    print(f"Решение агента: {res3.decision.upper()}")
    print(f"Логика агента: {res3.reasoning}")

if __name__ == "__main__":
    run_tests()
