FROM python:3.9-slim

RUN apt-get update && apt-get install -y gcc build-essential

WORKDIR /app

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY . .

# Запускаем бота
CMD ["python", "bot.py"]
