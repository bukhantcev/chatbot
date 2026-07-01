# Telegram Grok Bot

Персональный Telegram-бот под одного или нескольких разрешенных пользователей: короткий контекст, Grok/xAI API, SQLite, две кнопки в меню.

## Возможности

- доступ только для ID из `TELEGRAM_USER_IDS`;
- опциональное зеркало переписки на `MIRROR_TELEGRAM_ID`;
- ненавязчивые сообщения первым после 6-12 часов тишины, без отправки ночью по Москве;
- меню снизу: `Уровень` и `Сбросить контекст`;
- inline-клавиатура уровней:
  - `1. Пиздолиз`
  - `2. Мягкий`
  - `3. Нормальный`
  - `4. Жесткий`
  - `5. Саша`
- контекст последних `CONTEXT_PAIRS` пар сообщений;
- настройки через `.env`.

## Провайдер ИИ

Все уровни идут через Grok/xAI.

```dotenv
GROK_API_KEY=xai-...
GROK_MODEL=grok-4.3
```

## Зеркало переписки

Чтобы получать копии сообщений на второй свой Telegram ID:

```dotenv
MIRROR_TELEGRAM_ID=987654321
```

Если оставить пустым, дублирование отключено.

## Локальный запуск

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Docker

```bash
cp .env.example .env
docker compose up --build -d
```

Когда образ будет опубликован в Docker Hub:

```bash
BOT_IMAGE=your-dockerhub-user/chatbot:latest docker compose up -d
```
