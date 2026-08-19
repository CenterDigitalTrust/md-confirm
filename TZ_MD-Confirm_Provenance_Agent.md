# ТЗ: MD-Confirm — Publish-Time Provenance Agent
### Заявка на All Things Agentic Hackathon (трек Taskmaster)

**Дедлайн:** 31 августа 2026, 17:00 PDT
**Автор концепции:** Юрий Иванов / Miracle Droplet MD™
**Статус документа:** рабочее ТЗ для сборки за ~12 дней

---

## 1. Резюме (elevator pitch)

Google Pixel уже подписывает каждое фото аппаратным C2PA-сертификатом в момент съёмки. Проблема в том, что **соцсети стирают эти метаданные при загрузке** — подтверждение подлинности умирает ровно в тот момент, когда контент становится публичным и начинает распространяться. Мы не конкурируем с C2PA/SynthID — мы строим агента, который **переживает публикацию**: в момент "поделиться" фиксирует хеш происхождения во внешнем неизменяемом реестре, привязывает его к конкретному посту на конкретной платформе, и позволяет любому проверить позже — уже после того, как исходные метаданные стёрты — было ли это фото верифицировано при съёмке.

**Одна фраза для судей:** "Google доказывает подлинность в момент съёмки. Мы доказываем, что это доказательство не потерялось, когда фото ушло в мир."

---

## 2. Проблема, которую решает агент

- C2PA/Content Credentials — сильный стандарт, но данные о происхождении живут **внутри файла**
- При загрузке в Instagram/TikTok/Facebook/X платформы транскодируют и стирают embedded-метаданные
- После этого у зрителя нет способа узнать, что фото было верифицировано при съёмке — только у автора, если он сам сохранил оригинал
- Это признанная, ещё не решённая индустрией проблема (см. отчёт Microsoft, февраль 2026: ни один метод в одиночку не решает задачу digital deception)
- Ручное решение (автор сохраняет пруфы, показывает по запросу) — это именно та "messy multi-step chore", которую должен автоматизировать агент

---

## 3. Трек хакатона и обоснование

**Taskmaster** — "Build a complete workflow, not just a chatbot... Build an agent that handles the details, sends the right info to the right places, and proves it can do the heavy lifting for you."

Наш workflow:
1. Пользователь снимает/выбирает фото → жмёт "Поделиться"
2. Агент **сам** извлекает C2PA-манифест, генерирует хеш-квитанцию, публикует её в реестр, дожидается подтверждения транзакции
3. Агент **сам** решает: контент верифицирован полностью / частично / не верифицирован — и соответственно либо продолжает публикацию с "receipt ID", либо предупреждает пользователя
4. После публикации — отдельный сервис агента отвечает на запросы верификации по URL поста, без участия пользователя

Ни один шаг не требует ручного вмешательства после нажатия "Поделиться" — это autonomous multi-step action, а не чат.

---

## 4. Что НЕ делаем в рамках хакатона (осознанно вне scope)

| Не делаем | Почему | Чем заменяем для демо |
|---|---|---|
| Реальный RAW/PRNU-захват сенсора | Требует глубокой интеграции с Camera2 API, недели работы | Симулируем: заранее подготовленный набор "verified" / "tampered" тестовых фото с синтетическими хешами |
| Продакшн Solana mainnet | Лишние расходы, риски инфраструктуры | Solana **devnet** — бесплатно, полностью рабочий блокчейн-уровень, честно показываем в демо |
| Реальную интеграцию с API Instagram/TikTok | Требует partner-доступа, недели апрувов | Свой mock "share endpoint", имитирующий поведение платформы (включая "стирание" метаданных) — показывает механику честно |
| Обучение ML-модели детекции дипфейков | Не нужно — детекция уже есть в C2PA/существующих SDK | Используем готовый python пакет для чтения C2PA-манифеста (c2pa-python) |

Отдельно проговорить в видео: это demo-архитектура, доказывающая механику агента, не production-продукт.

---

## 5. Пользовательский сценарий (end-to-end)

```
[Фото с C2PA-манифестом] 
        │
        ▼
[Пользователь: "Поделиться" → выбирает наш Share-обработчик]
        │
        ▼
┌─────────────────────────────────────────┐
│  ON-DEVICE (Android, лёгкий слой)        │
│  - извлекает C2PA-манифест из файла      │
│  - если манифеста нет → флаг "unverified"│
│  - отправляет ТОЛЬКО метаданные          │
│    (hash, timestamp, device attestation) │
│    в облако — САМО ФОТО не уходит        │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│  CLOUD AGENT (Gemini + Antigravity SDK)  │
│  1. Верифицирует C2PA-подпись            │
│  2. Решает: verified / partial / none    │
│  3. Регистрирует receipt в реестре       │
│     (Firestore + Solana devnet anchor)   │
│  4. Возвращает receipt_id + verdict      │
│  5. Если "none" при попытке выдать       │
│     фото за проверенное → эскалация:     │
│     предупреждение пользователю,         │
│     запись в audit-лог                   │
└─────────────────────────────────────────┘
        │
        ▼
[Публикация продолжается + receipt_id прикреплён
 как ссылка в описании/alt-тексте поста]
        │
        ▼
┌─────────────────────────────────────────┐
│  POST-PUBLICATION LOOKUP (тот же агент)  │
│  Любой человек переходит по receipt_id → │
│  агент отвечает: "Да, этот контент был   │
│  верифицирован при съёмке [timestamp],   │
│  устройство [attested], хеш совпадает"   │
└─────────────────────────────────────────┘
```

---

## 6. Архитектура системы

### 6.1 On-device слой (минимальный, для демо — эмулятор/тестовое Android-приложение)
- Простой Android-компонент (Kotlin), который:
  - читает C2PA-манифест из JPEG (библиотека c2pa-rs / c2pa-python на бэкенде проще — можно парсинг делать на облаке)
  - формирует payload: `{image_hash, c2pa_signature_valid: bool, capture_timestamp, device_attestation_id}`
  - отправляет payload в Cloud Agent через REST/gRPC
- **Важно**: сырое фото не покидает устройство в облако агента — только метаданные (сохраняем privacy-принцип из MD-Confirm/MD-Spectrum)

### 6.2 Cloud Agent (ядро хакатон-проекта) — на Google Antigravity SDK
- **Gemini** (через Antigravity SDK, с возможностью `vertex=True` для Gemini Enterprise Agent Platform) — слой рассуждения и принятия решения
- **Google Antigravity SDK** (`pip install google-antigravity`) — Python-фреймворк, управляющий agentic loop, state и tool execution; наш код описывает ЧТО делает агент, SDK берёт на себя КАК он это исполняет
- **Cloud Run** — хостинг агента (обязательное требование хакатона)
- **Firestore** — state/memory: receipts, история решений по устройствам/аккаунтам, audit-лог
- **Pub/Sub** (опционально, если успеваем) — асинхронная обработка регистрации в блокчейне, чтобы не блокировать UX

### 6.3 Blockchain anchor
- Solana devnet: транзакция с memo = `image_hash + timestamp + agent_decision`
- Даёт неизменяемую метку времени независимо от Google/платформы — это отличает решение от "просто Firestore"

### 6.4 Как это ложится на примитивы Antigravity SDK

Antigravity SDK даёт готовые строительные блоки — наш workflow (verify → decide → register → respond) собирается из них, а не пишется с нуля:

| Наш шаг | Примитив Antigravity SDK | Зачем именно он |
|---|---|---|
| Приём метаданных с устройства | `Agent(config)` + `agent.chat(...)` | Точка входа в agentic loop, конфигурируется через `LocalAgentConfig(vertex=True, project=..., location=...)` |
| Чтение/валидация C2PA-манифеста | **Custom Python Function tool** | Регистрируем `validate_c2pa(image_meta)` как обычный Python-callable — SDK сам подключает его в pipeline вызовов агента |
| Решение verified/unverified/flagged | **Structured Output (Pydantic model)** | Определяем `class VerdictSchema(BaseModel): decision: Literal["verified","unverified","flagged"]; reason: str` — агент обязан вернуть типизированный, валидированный ответ, а не свободный текст |
| Запись в Firestore + отправка в Solana | **Custom Python Function tools** | `register_receipt()` и `anchor_to_solana()` — два отдельных tool-вызова, видно по отдельности в трейсе выполнения |
| Ветка FLAGGED — предупредить пользователя | **Human-in-the-Loop hook** | SDK умеет приостановить выполнение и задать структурированный вопрос — идеально ложится на сценарий "агент сомневается, спрашивает подтверждение" |
| Разделение "проверка C2PA" и "решение по эскалации" | **Sub-agents** | Можно вынести валидацию в дочернего агента с независимым набором tools/контекстом, а решение эскалации — в родительского; это же прямое попадание в критерий "decouple systems" (30%) |
| Прозрачность для демо-видео | **Observability** (per-turn token usage, thinking traces) | Встроенный трейсинг рассуждений — показываем в видео живьём, как агент "думает" перед вердиктом |

Ключевая архитектурная деталь: **сам Antigravity-агент разворачивается как обычный процесс внутри Cloud Run-контейнера** (Python SDK + `GEMINI_API_KEY` или Vertex-конфиг в переменных окружения/Secret Manager) — то есть требование хакатона "Google Cloud infra" выполняется тем же контейнером, а не отдельным сервисом.

---

## 7. Технологический стек (маппинг на обязательные требования хакатона)

| Требование хакатона | Что используем |
|---|---|
| Gemini 3.5+ через API/Vertex AI | Gemini через Antigravity SDK; `LocalAgentConfig(vertex=True)` переключает на Gemini Enterprise Agent Platform (Vertex AI) |
| Google Agent Framework | **Google Antigravity SDK** (`google-antigravity`) — Agent, custom tools, structured output, sub-agents, human-in-the-loop |
| Google Cloud infra | Cloud Run (хостинг агента) + Firestore (state/memory) |
| (доп., не обязательно) | Pub/Sub для асинхронной публикации в блокчейн |

Дополнительно:
- **Solana devnet** (web3.js/solana-py) — внешний anchor
- **c2pa-python** — чтение/валидация C2PA-манифестов
- **FastAPI** — тонкая обёртка HTTP-эндпоинтов вокруг `Agent` из Antigravity SDK (сам SDK работает через `async with Agent(config) as agent`, FastAPI просто маршрутизирует HTTP → вызовы agent.chat())

---

## 8. Спецификация поведения агента

### 8.1 Состояния (states)
- `RECEIVED` — метаданные получены
- `C2PA_VALID` / `C2PA_MISSING` / `C2PA_INVALID` — результат проверки подписи
- `REGISTERED` — receipt зафиксирован в Firestore + отправлен в очередь на блокчейн-anchor
- `ANCHORED` — подтверждена транзакция в Solana devnet
- `FLAGGED` — попытка выдать неверифицированный контент за верифицированный (эскалация)

### 8.2 Правила принятия решений (few-shot, не ML-обучение)
Зашиваются в системный промпт агента как сценарии, например:

- Манифест валиден + подпись устройства совпадает с известным attested-устройством → `verified`, регистрируем без вопросов
- Манифеста нет вообще, но пользователь не заявляет "это подлинное фото" (обычный шэр) → `unverified`, просто помечаем, не блокируем
- Манифеста нет, но метаданные поста/подпись пользователя утверждают "оригинал/несмонтировано" → `FLAGGED`, агент **сам** решает придержать регистрацию и уведомить пользователя с объяснением почему
- Манифест есть, но hash не совпадает с фактическим файлом (подмена после подписи) → `FLAGGED`, `tampered`, лог инцидента

Это НЕ тренировка модели — это набор из 8–10 явных правил-примеров в системном промпте `Agent`, на которые Gemini опирается при рассуждении. Итоговый вердикт агент обязан вернуть через **Structured Output** — Pydantic-схему `VerdictSchema`, а не свободный текст, чтобы дальше по pipeline (регистрация, anchor) шли только валидные машиночитаемые данные.

### 8.3 State & memory
- Firestore коллекция `receipts`: image_hash, decision, timestamp, device_id (attested, не PII), solana_tx_id
- Firestore коллекция `device_history`: сколько раз устройство присылало valid/invalid — нужно для контекстных решений ("это устройство и раньше присылало флагованный контент")
- Внутри одного workflow (verify→register) Antigravity SDK держит **stateful multi-turn session** (`conversation.history`, `turn_count`) — это короткая рабочая память на время обработки одного фото; долгая память между сессиями — только через Firestore, session-стейт SDK не персистентен между вызовами `/verify`

### 8.4 Секьюрность/credentials
- Solana wallet private key — в Google Secret Manager, не в коде и не в переменных окружения репозитория
- Vertex AI/Cloud Run — Service Account с минимальными правами (принцип наименьших привилегий)
- On-device → Cloud: подписанные запросы (HMAC) с ключом, привязанным к attested-устройству

### 8.5 Обработка сбоев (failure handling)
- Gemini недоступен → агент переходит в детерминированный fallback-режим (просто регистрирует hash без reasoning-слоя через прямой Python-код, минуя `agent.chat()`, помечает `degraded_mode: true`)
- Solana devnet недоступен → receipt остаётся в статусе `REGISTERED` (Firestore), retry через Pub/Sub с экспоненциальным backoff, anchor подтягивается асинхронно
- Antigravity SDK даёт **lifecycle hooks** — вешаем hook на каждый tool-вызов (`register_receipt`, `anchor_to_solana`), чтобы ловить исключения централизованно, а не try/except в каждом месте
- Показать в демо намеренный сбой одного из сервисов и то, как агент деградирует gracefully — это прямое попадание в критерий "handle failures"

---

## 9. Пример данных (Firestore schema)

```json
// collection: receipts
{
  "receipt_id": "rcpt_8f3a...",
  "image_hash": "sha256:...",
  "c2pa_status": "valid",
  "device_attestation_id": "attest_xxxx",
  "decision": "verified",
  "capture_timestamp": "2026-08-20T10:15:00Z",
  "registered_at": "2026-08-20T10:15:03Z",
  "solana_tx_id": "5h3k...",
  "solana_status": "anchored"
}
```

### 9.1 Pydantic-схема вердикта агента (Structured Output)

```python
from pydantic import BaseModel
from typing import Literal

class VerdictSchema(BaseModel):
    decision: Literal["verified", "unverified", "flagged"]
    reason: str
    confidence_note: str  # короткое пояснение агента, почему именно так
```

### 9.2 Скелет самого агента (Antigravity SDK)

```python
import asyncio
from google.antigravity import Agent, LocalAgentConfig

async def handle_verify(image_meta: dict) -> VerdictSchema:
    config = LocalAgentConfig(
        vertex=True,              # переключаемся на Gemini Enterprise Agent Platform
        project="md-confirm-hackathon",
        location="us-central1",
    )
    async with Agent(config, tools=[validate_c2pa, register_receipt, anchor_to_solana]) as agent:
        response = await agent.chat(
            f"Проверь происхождение фото по метаданным: {image_meta}. "
            f"Верни решение по схеме VerdictSchema, опираясь на правила из системного промпта."
        )
        return await response.structured(VerdictSchema)
```

Это ядро, вокруг которого FastAPI просто маршрутизирует HTTP-запросы `/verify`, `/receipt/{id}` и т.д.

---

## 10. API-эндпоинты агента

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/verify` | Принимает метаданные с устройства, запускает Antigravity-агент (`handle_verify`) |
| GET | `/receipt/{receipt_id}` | Публичный lookup — "было ли это верифицировано" (прямой запрос в Firestore, без агента) |
| GET | `/device/{device_id}/history` | Внутренний — история решений по устройству (контекст для reasoning) |
| POST | `/webhook/solana-confirm` | Callback подтверждения транзакции |

---

## 11. Демо-сценарий (~4 минуты видео)

1. **0:00–0:30** — Проблема: показать реальный пример, как соцсеть стирает C2PA-метаданные (до/после скачивания с Instagram — метаданные исчезли)
2. **0:30–1:00** — "Вот наш агент" — коротко архитектура (диаграмма на экране)
3. **1:00–2:30** — Живое демо:
   - берём фото с валидным C2PA → жмём "поделиться через MD-Confirm Agent"
   - показываем реальный лог в Cloud Run/Vertex AI console — видно, как Gemini принимает решение
   - показываем запись в Firestore и подтверждённую транзакцию в Solana devnet explorer
   - открываем receipt-ссылку — "verified ✅ снято 20.08.2026, устройство подтверждено"
4. **2:30–3:15** — Сценарий FLAGGED: пытаемся протащить фото без манифеста с подписью "оригинал" → агент сам ловит и блокирует/предупреждает, объясняем почему это multi-step autonomous decision, а не if/else скрипт
5. **3:15–3:45** — Намеренно роняем Gemini API → показываем graceful degradation
6. **3:45–4:00** — Итог + ссылка на репозиторий

---

## 12. Чеклист сдачи (по требованиям Devpost)

- [ ] Категория: Taskmaster
- [ ] URL хостед-проекта (если успеваем задеплоить публично)
- [ ] Текстовое описание: features, technologies, data sources, findings/learnings
- [ ] Публичный/приватный репозиторий + README со Spin-up Instructions (доступ для testing@devpost.com и cloudhackathons@google.com, если приватный)
- [ ] Архитектурная диаграмма (визуальная версия схемы из раздела 5)
- [ ] Демо-видео ~4 мин (см. сценарий выше), с явным доказательством работы на Google Cloud (Cloud Run dashboard/Vertex AI logs)
- [ ] (бонус) Публикация о том, как строили проект + пост в соцсетях с #AllThingsAgenticHackathon

---

## 13. Детальный план сборки на Antigravity SDK (~12 дней)

### Фаза 0 — прямо сейчас, без Cloud-кредитов (первые 24–72 часа)

| День | Задача | Детали |
|---|---|---|
| 1, утро | Установка окружения | `pip install google-antigravity`, `pip install pydantic fastapi c2pa-python`, получить `GEMINI_API_KEY` через AI Studio (не требует биллинга) |
| 1, день | Hello-world агент | Скелет из раздела 9.2, но с `LocalAgentConfig()` без `vertex=True` — работает на голом `GEMINI_API_KEY`. Проверить, что `agent.chat()` отвечает |
| 1, вечер | Structured Output | Завести `VerdictSchema`, проверить `response.structured(VerdictSchema)` на 3-4 тестовых промптах вручную |
| 2, утро | Custom tools: `validate_c2pa` | Обвязка над `c2pa-python`: принимает путь к файлу/метаданные, возвращает `{signature_valid, capture_timestamp, device_attestation_id}`. Тестируем на реальных фото с Pixel 10 (или синтетических манифестах) |
| 2, день | Custom tools: `register_receipt` (заглушка) | Пока пишем в **Firestore emulator** (`firebase emulators:start`) вместо реального Firestore — схема из раздела 9 |
| 2, вечер | Правила решений (few-shot) | Написать 8-10 сценариев из раздела 8.2 прямо в системный промпт агента, прогнать вручную все ветки (verified/unverified/flagged) |
| 3, утро | Solana devnet | Кошелёк, тестовые SOL с faucet, функция `anchor_to_solana(memo)` — полностью рабочая, это не Google-инфраструктура и доступна уже сейчас |
| 3, день | Сборка workflow целиком | `/verify` эндпоинт на FastAPI, локально, дергает `handle_verify()`, пишет в emulator Firestore + Solana devnet — **весь агент работает end-to-end на ноутбуке** |
| 3, вечер | Human-in-the-loop hook | Реализовать паузу/вопрос для ветки FLAGGED — это то, что реально отличает "агента" от скрипта, стоит отладить пока есть время |

К концу 72 часов (до подтверждения кредитов) у вас должен быть **полностью рабочий агент локально** — не хватает только реального деплоя.

### Фаза 1 — после подтверждения Cloud-кредитов

| День | Задача |
|---|---|
| 4 | Создать GCP-проект, привязать billing (кредиты), включить Cloud Run + Firestore API + Secret Manager |
| 4 | Перевести `LocalAgentConfig()` → `LocalAgentConfig(vertex=True, project=..., location=...)`, проверить что агент отвечает через Vertex |
| 5 | Перенести Firestore emulator → реальный Firestore, перепроверить схему `receipts`/`device_history` |
| 5 | Secret Manager: Solana private key, любые API-ключи — убрать из кода/env файлов |
| 6 | Dockerfile для агента (Python + Antigravity SDK бинарники — проверить, что рантайм SDK корректно паковается в контейнер), деплой на Cloud Run |
| 6 | Sub-agents: вынести `validate_c2pa` в дочернего агента с независимым контекстом (раздел 6.4) — для критерия "decouple systems" |
| 7 | `/receipt/{id}` публичный lookup endpoint, `/device/{id}/history` |
| 7 | Pub/Sub (если успеваем) — асинхронный anchor в Solana, чтобы `/verify` не блокировался на подтверждении транзакции |
| 8 | Обработка сбоев: lifecycle hooks на каждый tool-вызов, degraded_mode при недоступности Gemini/Solana — намеренно протестировать оба сбоя |
| 9 | Мини-клиент для демо: простая веб-форма загрузки фото → вызывает `/verify` (полноценный Android не нужен, см. раздел 4) |
| 9 | Observability: включить per-turn token usage и thinking traces из Antigravity SDK — понадобится в видео |
| 10 | Прогнать 2-3 полных сценария (verified / flagged / degraded) от начала до конца, зафиксировать удачные дубли на видео как fallback |
| 11 | Съёмка демо-видео по сценарию из раздела 11, архитектурная диаграмма, README со Spin-up Instructions |
| 12 | Буфер: баги, финальная сборка сабмишена на Devpost, публикация (+бонус: пост в соцсетях с #AllThingsAgenticHackathon) |

**Важно:** Фаза 0 не тратится впустую в ожидании кредитов — весь агент, вся логика решений и оба внешних сервиса (Gemini через AI Studio, Solana devnet) можно закончить локально. Cloud-часть (Фаза 1) — это по сути "передеплой" уже готового и протестированного кода, а не написание его с нуля.

---

## 14. Соответствие критериям судейства

| Критерий | Вес | Как закрываем |
|---|---|---|
| Innovation & Operational Utility | 40% | Решаем реальную, признанную индустрией нерешённой проблему (стирание провенанса при публикации), агент принимает решения (verified/flagged/degraded) без хардкода if/else, автономно на каждом шаге |
| Architectural Discipline & Tech Stack | 30% | Чёткое разделение on-device/cloud, state в Firestore, секреты в Secret Manager, graceful degradation при сбое Gemini/Solana, асинхронность через Pub/Sub |
| Demo & Production Readiness | 30% | Живое демо с видимыми Cloud Run/Vertex AI логами, воспроизводимый README, честная архитектурная диаграмма |

---

## 15. Риски и как их обходим

| Риск | Митигация |
|---|---|
| Не успеваем реальную Android-интеграцию | Заменяем на веб-демо (upload формы), сама механика агента важнее клиента |
| Solana devnet нестабилен во время демо | Заранее делаем 2-3 успешных прогона, записываем как fallback-клип на случай сбоя во время живой съёмки |
| Жюри знает про C2PA/Pixel и посчитает вторичным | Чётко проговариваем в видео с первых 30 секунд: "мы не переизобретаем C2PA, мы решаем то, что C2PA признанно не решает" — со ссылкой на отчёт Microsoft |
| Слишком амбициозный scope за 12 дней | Раздел 4 ("что не делаем") — держать эту границу жёстко весь спринт |

---

## 16. Стратегическое видение (упомянуть в видео/описании, не строить)

Anchor-слой на хакатоне реализован на **Solana devnet** — открытый, бесплатный, доступен любому разработчику без онбординга.

Google параллельно строит собственный Layer-1 — **Google Cloud Universal Ledger (GCUL)**: permissioned блокчейн для платежей и токенизации активов, сейчас в закрытом тестнете (пилот с CME Group), с KYC-онбордингом для институтов, публичный коммерческий запуск ожидается в 2026 году. Доступа для сторонних разработчиков/хакатон-участников сейчас нет — поэтому не используем его в сборке.

Стоит явно проговорить в тексте заявки (не в коде): как только GCUL откроет доступ для верифицированных организаций, anchor-слой можно перенести туда — это даст более "нативную" для Google-экосистемы историю (единый провайдер: Vertex AI + Cloud Run + GCUL), не завязанную на внешний блокчейн. Это не меняет архитектуру демо, но показывает судьям стратегическое понимание экосистемы, в которой они сами строят продукт.
