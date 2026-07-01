import logging
from typing import Any, List, Protocol

from openai import AsyncOpenAI

from app.config import Settings
from app.db import MessageRecord
from app.prompts import build_instructions


logger = logging.getLogger(__name__)

GROK_BASE_URL = "https://api.x.ai/v1"


def provider_for_level(level: int) -> str:
    return "grok"


class ChatClient(Protocol):
    async def reply(self, level: int, history: List[MessageRecord], user_text: str) -> str:
        pass

    async def level_greeting(self, level: int) -> str:
        pass

    async def proactive_message(
        self,
        level: int,
        history: List[MessageRecord],
        is_morning: bool,
    ) -> str:
        pass


LEVEL_GREETING_PROMPT = """
Пользователь только что переключил стиль общения на текущий уровень.
Ответь как Саша в этом стиле: короткое живое приветствие или первая реплика после смены настроения.
Не упоминай настройки, кнопку, уровень, режим, Telegram, бота или то, что стиль был переключен.
Не объясняй правила. Просто войди в выбранный стиль.
""".strip()


EMPTY_RETRY_PROMPT = """
Предыдущий ответ вышел пустым. Ответь обычным текстом, одной-двумя короткими фразами.
Сохрани текущий стиль Саши и не объясняй технические ограничения.
""".strip()


def _proactive_prompt(is_morning: bool) -> str:
    morning_line = (
        "Сейчас утро по Москве: если это звучит естественно, можно начать с 'доброе утро'."
        if is_morning
        else "Не используй официальные приветствия вроде 'добрый день' или 'добрый вечер'."
    )
    return f"""
Саша пишет первым после паузы в диалоге.
Напиши короткое живое сообщение в текущем стиле уровня.
Оно должно ощущаться как естественное продолжение отношений, не как уведомление, рассылка или системный пинг.
Не упоминай таймер, паузу, расписание, настройки, бота или Telegram.
Не будь навязчивым и не требуй ответа.
{morning_line}
""".strip()


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
            else:
                text = getattr(item, "text", None) or getattr(item, "content", None)
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts).strip()
    return ""


def _choice_text(response: Any) -> str:
    if not response.choices:
        return ""
    return _content_to_text(response.choices[0].message.content)


class GrokChat:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url=GROK_BASE_URL)
        self.model = model

    async def reply(self, level: int, history: List[MessageRecord], user_text: str) -> str:
        messages = self._messages(level, history, user_text)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=700,
            temperature=0.9,
        )

        text = _choice_text(response)
        if text:
            return text

        self._log_empty_response(response, "reply")
        retry_response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                *messages,
                {"role": "assistant", "content": ""},
                {"role": "user", "content": EMPTY_RETRY_PROMPT},
            ],
            max_tokens=350,
            temperature=0.9,
        )

        text = _choice_text(retry_response)
        if text:
            return text

        self._log_empty_response(retry_response, "reply_retry")
        return "Я здесь. Сформулируй еще раз, и я отвечу нормально."

    async def level_greeting(self, level: int) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": build_instructions(level)},
                {"role": "user", "content": LEVEL_GREETING_PROMPT},
            ],
            max_tokens=220,
            temperature=0.9,
        )

        text = _choice_text(response)
        if text:
            return text

        self._log_empty_response(response, "level_greeting")
        return "Я здесь."

    async def proactive_message(
        self,
        level: int,
        history: List[MessageRecord],
        is_morning: bool,
    ) -> str:
        messages = [{"role": "system", "content": build_instructions(level)}]
        messages.extend(
            {"role": message["role"], "content": message["content"]}
            for message in history
        )
        messages.append({"role": "user", "content": _proactive_prompt(is_morning)})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=260,
            temperature=0.95,
        )

        text = _choice_text(response)
        if text:
            return text

        self._log_empty_response(response, "proactive_message")
        return "Я здесь."

    def _messages(
        self,
        level: int,
        history: List[MessageRecord],
        user_text: str,
    ) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": build_instructions(level)}]
        messages.extend(
            {"role": message["role"], "content": message["content"]}
            for message in history
        )
        messages.append({"role": "user", "content": user_text})
        return messages

    def _log_empty_response(self, response: Any, action: str) -> None:
        choice = response.choices[0] if response.choices else None
        logger.warning(
            "Grok returned empty content action=%s requested_model=%s actual_model=%s finish_reason=%s",
            action,
            self.model,
            getattr(response, "model", None),
            getattr(choice, "finish_reason", None) if choice else None,
        )


def build_chat_client(settings: Settings) -> ChatClient:
    return GrokChat(api_key=settings.grok_api_key, model=settings.grok_model)
