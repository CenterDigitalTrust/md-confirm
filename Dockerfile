FROM python:3.10-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .

# Cloud Run ожидает, что приложение будет слушать порт, переданный в переменной окружения PORT.
# По умолчанию Cloud Run использует порт 8080.
ENV PORT=8080

# Запуск FastAPI через Uvicorn
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
