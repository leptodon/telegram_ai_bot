# Telegram Bot with Ollama Integration

Умный Telegram-бот с интеграцией Ollama для обработки текстовых сообщений и анализа изображений. Бот может работать в групповых чатах и личных сообщениях, поддерживает различные модели ИИ и имеет гибкую систему настроек.

## ✨ Особенности

- **Текстовые сообщения**: Интеллектуальные ответы на основе контекста беседы
- **Анализ изображений**: Описание и анализ загруженных изображений
- **Адаптивные промпты**: Разные стили общения для разных типов чатов
- **Система команд**: Административные команды для управления ботом
- **Генерация саммари**: Создание кратких резюме по истории чата
- **Контекстная память**: Сохранение истории беседы с ограничением по токенам
- **Настраиваемая вероятность**: Случайные ответы в групповых чатах

## 🚀 Быстрый старт

### Требования

- Python 3.9+
- Docker (опционально)
- Ollama server с установленными моделями
- Telegram API credentials

### Установка

1. **Клонируйте репозиторий:**
```bash
git clone <repository-url>
cd telegram-ollama-bot
```

2. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

3. **Настройте переменные окружения:**
```bash
cp .env.example .env
# Отредактируйте .env файл с вашими настройками
```

4. **Запустите бота:**
```bash
python bot/main.py
```

### Docker

```bash
docker build -t telegram-bot .
docker run --env-file .env telegram-bot
```

## ⚙️ Настройка

### Переменные окружения

```env
# Telegram API
API_ID=your_api_id
API_HASH=your_api_hash
PHONE_NUMBER=your_phone_number

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=your_text_model
OLLAMA_VISION_MODEL=your_vision_model

# Bot Settings
TOKEN_LIMIT=4096
MESSAGE_PROBABILITY=0.1
MAX_RETRY_ATTEMPTS=30
RETRY_DELAY=1

# Chat Settings
MAIN_CHAT_ID=your_main_chat_id
ADMIN_USERNAME=@your_username
SERVICE_CHAT_ID=your_service_chat_id
```

### Рекомендуемые модели

**Текстовые модели:**
- `OxW/Vikhr-Nemo-12B-Instruct-R-21-09-24:q8_0`
- `llama3.1:8b`
- `qwen2.5:7b`

**Vision модели:**
- `qwen2.5vl:7b`
- `llava:7b`
- `moondream:latest`

## 🤖 Функционал

### Основные возможности

#### Обработка текста
- Ответы на прямые обращения и ключевые слова
- Контекстные диалоги с сохранением истории
- Различные стили общения в зависимости от типа чата

#### Анализ изображений
- Автоматическое описание загруженных изображений
- Анализ связи между изображением и текстом сообщения
- Добавление описания в контекст беседы

#### Система команд
Доступные команды для администратора:

- `!забудь все` - Очистить контекст чата
- `!вероятность <число>` - Установить вероятность случайных ответов (0-100%)
- `!модель <название>` - Изменить текстовую модель
- `!vision <название>` - Изменить vision модель
- `!статус` - Показать статус бота

#### Генерация саммари
Команда для всех пользователей:
- `!<число> сообщений` - Создать саммари по указанному количеству сообщений

### Логика ответов

**В групповых чатах бот отвечает когда:**
- Сообщение содержит ключевые слова (`валер`, `@ai_valera`)
- Ответ на сообщение бота
- Случайно (с настраиваемой вероятностью)

**В личных сообщениях:**
- Бот отвечает на все сообщения

## 📁 Структура проекта

```
bot/
├── __init__.py
├── main.py                 # Точка входа
├── config.py              # Конфигурация
├── exceptions.py          # Исключения
├── core/
│   └── bot.py            # Основной класс бота
├── handlers/
│   ├── base.py           # Базовый класс обработчиков
│   └── message_handler.py # Обработчик сообщений
├── services/
│   ├── __init__.py
│   ├── base.py           # Базовый класс сервисов
│   └── chat_service.py   # Сервис работы с Ollama
└── utils/
    └── message_utils.py  # Утилиты для работы с сообщениями
```

## 🔧 Разработка

### Добавление новых функций

1. **Новый сервис:**
```python
from bot.services.base import BaseService

class YourService(BaseService):
    def __init__(self, logger=None):
        super().__init__(logger)
        # Ваша логика
```

2. **Новый обработчик:**
```python
from bot.handlers.base import BaseHandler

class YourHandler(BaseHandler):
    async def handle_event(self, event):
        # Ваша логика
```

### Настройка промптов

Промпты настраиваются в `message_handler.py`:
- `_get_main_chat_prompt()` - для основного чата
- `_get_informal_prompt()` - для других чатов
- `_get_self_chat_prompt()` - для случайных ответов

## 🐛 Отладка

### Логирование

Бот использует стандартное Python logging:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Служебные сообщения

Все ошибки и важные события отправляются в служебный чат, указанный в `SERVICE_CHAT_ID`.

### Типичные проблемы

1. **Ollama недоступен:**
   - Проверьте, что Ollama запущен и доступен по указанному адресу
   - Убедитесь, что нужные модели установлены

2. **Ошибки Telegram API:**
   - Проверьте правильность API_ID, API_HASH и номера телефона
   - Убедитесь, что у бота есть права на чтение сообщений

3. **Проблемы с изображениями:**
   - Проверьте, что vision модель поддерживает загруженный формат
   - Убедитесь, что достаточно памяти для обработки изображений

## 📝 Лицензия

MIT License

## 🤝 Вклад в проект

1. Fork проекта
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request