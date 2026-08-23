# MD-Confirm — watermark + local ledger PoC

Проверяет ровно твою схему: снимок → водяной знак на весь кадр + короткий ID →
запись в (пока локальный) реестр → публикация в соцсеть → скачивание → decode
→ ECC-восстановление → поиск ID в реестре → проверка phash → вердикт.

## Установка (запускать у себя, не здесь — у меня в песочнице нет сети)

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Если `invisible-watermark` не ставится с первого раза — поставь сначала `numpy` и `opencv-python` отдельно, потом `invisible-watermark`.

## Тест сегодня — команды по порядку

```bash
# 1. Встраиваем watermark + notarize в локальный ledger
python embed.py my_photo.jpg
# -> печатает watermark_id и создаёт my_photo_watermarked.jpg
```

```bash
# 2. Публикуешь my_photo_watermarked.jpg в Instagram/Telegram/WhatsApp вручную
#    (как обычно, через приложение или веб)
```

```bash
# 3. Скачиваешь фото обратно (правой кнопкой -> "Сохранить изображение",
#    или скриншот экрана — тоже интересно проверить оба варианта)
```

```bash
# 4. Проверяем скачанный файл
python verify.py downloaded_from_instagram.jpg
```

Ожидаемый вывод при успехе:
```
Recovered watermark_id: a1b2c3d4e5f6a1b2  (N bytes ECC-corrected)
Original phash : ...
Downloaded phash: ...
Hamming distance: X  (threshold: 8)
============================================================
VERIFIED: content matches notarized original.
```

## Как это отвечает на твой вопрос

> "если мы фото опубликуем и скачаем назад — мы его сможем проверить и у нас сойдётся id?"

Да, именно так — **при условии**, что платформа не пережмёт файл настолько
агрессивно, что даже Reed-Solomon коррекция (8 байт parity на 8 байт данных —
запас примерно на 50% повреждения кодового слова) не вытянет ID. Разные
площадки жмут по-разному:

- Telegram (без сжатия, "отправить как файл") — почти всегда переживёт.
- WhatsApp/Instagram DM/лента — жмёт сильно, тут и будет самый честный тест.
- Скриншот экрана — совсем другой сценарий (полная ресемплизация), стоит
  проверить отдельно и не удивляться, если ECC не справится — тогда fallback
  на PRNU-отпечаток становится главным сигналом.

**Если сегодня decode не сойдётся** — это не провал, это данные. Смотри
`n_corrected` в выводе verify.py: если ошибок ECC близко к пределу (4 байта
из 8 возможных) — метод рабочий, но платформа жмёт на грани, увеличивай
PARITY_BYTES в обоих файлах (embed.py и verify.py, значения должны совпадать)
и повторяй тест.

## Дальше — Solana devnet вместо локального ledger

`ledger.py` уже даёт эту точку расширения — `notarize_on_solana_devnet()`.
Когда локальный пайплайн подтверждён, меняешь `ledger.notarize()` на реальный
anchor через SPL Memo program на devnet (нужен `solana-keygen new` +
`solana airdrop 1 --url devnet` для тестовых SOL). Формат записи не меняется —
меняется только то, ГДЕ хранится sha256 записи.
