FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        gcc \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Создание директорий для данных и логов
RUN mkdir -p /app/logs

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY bot/ ./bot/
COPY bot/79992553618.session ./79992553618.session

# Создание пользователя для безопасности
RUN groupadd -r botuser && useradd -r -g botuser botuser
RUN chown -R botuser:botuser /app

# Переключение на пользователя
USER botuser

# Запуск бота
CMD ["python", "-m", "bot.main"]