import random
import tempfile
import os
from typing import Dict
from collections import deque
from .base import BaseHandler
from ..utils.message_utils import limit_messages_by_tokens
from ..exceptions import ChatServiceError
import re


class MessageHandler(BaseHandler):
    """Handler for processing text and image messages"""

    def __init__(self, bot, config, logger=None):
        super().__init__(bot, config, logger)
        self.chat_queues: Dict[int, deque] = {}
        self.sent_message_ids = deque(maxlen=100)
        self.message_probability = config.message_probability

    async def handle_message(self, event):
        """Main message handling logic"""
        try:
            sender = await event.get_sender()
            sender_username = f"@{sender.username}" if sender.username else "Unknown"
            chat_id = event.chat_id
            message_text = event.message.message or ""

            self.logger.info(f"Received message from {sender_username} in chat {chat_id}")

            # Initialize chat queue if needed
            if chat_id not in self.chat_queues:
                self.chat_queues[chat_id] = deque(maxlen=100)

            # Mark message as read
            await self.bot.telegram_client.send_read_acknowledge(
                event.chat_id,
                clear_mentions=True,
                clear_reactions=True
            )

            # Handle admin commands
            if await self._handle_admin_commands(event, sender_username, message_text):
                return

            # Handle summary commands (available to all users)
            if await self._handle_summary_command(event, sender_username, message_text):
                return

            # Handle message with media (image)
            if event.message.media:
                await self._handle_media_message(event, sender_username, message_text)
            else:
                # Handle text message
                await self._handle_text_message(event, sender_username, message_text)

        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            await self._send_error_to_service(f"Ошибка при обработке сообщения: {e}",
                                              f"Chat: {event.chat_id}, User: {sender_username}")

    async def _handle_media_message(self, event, sender_username: str, message_text: str):
        """Handle messages with media (focus on images)"""
        try:
            # Проверяем, что это изображение
            if hasattr(event.message.media, 'photo') or (
                    hasattr(event.message.media, 'document') and
                    event.message.media.document.mime_type.startswith('image/')
            ):
                self.logger.info("Processing image message")

                # Скачиваем изображение
                image_data = await self._download_image(event)
                if not image_data:
                    self.logger.error("Failed to download image")
                    # Добавляем в контекст информацию о том, что было изображение, но не удалось его обработать
                    formatted_message = f"{sender_username}: [Изображение - не удалось обработать] {message_text}"
                    self.chat_queues[event.chat_id].append({
                        "role": "user",
                        "content": formatted_message
                    })
                    return

                # Анализируем изображение тихо (для контекста)
                try:
                    # Определяем prompt для анализа
                    analysis_prompt = self._get_image_analysis_prompt(message_text)

                    # Получаем описание изображения
                    image_description = await self.bot.chat_service.analyze_image(
                        image_data,
                        analysis_prompt
                    )

                    # Добавляем в историю чата ТОЛЬКО для контекста (не отправляем в чат)
                    formatted_message = f"{sender_username}: [Изображение] {message_text}\nОписание изображения: {image_description}"
                    self.chat_queues[event.chat_id].append({
                        "role": "user",
                        "content": formatted_message
                    })

                    self.logger.info(f"Image analyzed and added to context: {sender_username}")

                    # Проверяем, нужно ли отвечать (как на обычное сообщение)
                    if self._should_respond_to_image(event, message_text, image_description):
                        await self._generate_and_send_response(event)
                    elif self._should_respond_randomly(event):
                        await self._generate_and_send_response(event, is_random=True)

                except Exception as e:
                    self.logger.error(f"Error analyzing image: {e}")
                    # Даже если не удалось проанализировать, добавляем базовую информацию в контекст
                    formatted_message = f"{sender_username}: [Изображение - ошибка анализа] {message_text}"
                    self.chat_queues[event.chat_id].append({
                        "role": "user",
                        "content": formatted_message
                    })
                    # Отправляем ошибку в служебный чат
                    await self._send_error_to_service(f"Ошибка анализа изображения: {e}",
                                                      f"Chat: {event.chat_id}, User: {sender_username}")

            else:
                self.logger.debug("Skipping non-image media message")
                # Для других типов медиа тоже добавляем в контекст
                formatted_message = f"{sender_username}: [Медиа файл] {message_text}"
                self.chat_queues[event.chat_id].append({
                    "role": "user",
                    "content": formatted_message
                })

        except Exception as e:
            self.logger.error(f"Error handling media message: {e}")
            await self._send_error_to_service(f"Ошибка обработки медиа: {e}",
                                              f"Chat: {event.chat_id}, User: {sender_username}")

    async def _download_image(self, event) -> bytes:
        """Download image from message"""
        try:
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name

            # Скачиваем файл
            await event.message.download_media(file=temp_path)

            # Читаем данные
            with open(temp_path, 'rb') as f:
                image_data = f.read()

            # Удаляем временный файл
            os.unlink(temp_path)

            return image_data

        except Exception as e:
            self.logger.error(f"Error downloading image: {e}")
            return None

    def _get_image_analysis_prompt(self, message_text: str) -> str:
        """Get prompt for image analysis based on message text"""
        if message_text.strip():
            return f"Пользователь отправил изображение с текстом: '{message_text}'. Опиши подробно что ты видишь на изображении и как это может быть связано с текстом пользователя."
        else:
            return "Опиши подробно что ты видишь на этом изображении. Обрати внимание на детали, людей, объекты, текст, эмоции и общую атмосферу."

    def _should_respond_to_image(self, event, message_text: str, image_description: str) -> bool:
        """Check if bot should respond to image message"""
        # Check if replying to bot's message
        if event.reply_to_msg_id in self.sent_message_ids:
            return True

        # Check if message or description contains keywords
        combined_text = f"{message_text} {image_description}".lower()
        return any(keyword in combined_text for keyword in self.config.keywords)

    async def _handle_admin_commands(self, event, sender_username: str, message_text: str) -> bool:
        """Handle admin commands"""
        if sender_username != self.config.admin_username:
            return False

        message_lower = message_text.lower()

        if message_lower == "!забудь все":
            self.chat_queues.get(event.chat_id, deque()).clear()
            await self._send_service_message(f"✅ Контекст чата {event.chat_id} очищен")
            return True

        elif message_lower.startswith("!вероятность"):
            try:
                probability_str = message_text.split(" ")[1]
                probability = float(probability_str) / 100

                if 0 <= probability <= 1:
                    self.message_probability = probability
                    await self._send_service_message(f"✅ Вероятность ответа установлена: {probability_str}%")
                else:
                    await self._send_service_message("❌ Вероятность должна быть от 0 до 100")

            except (IndexError, ValueError):
                await self._send_service_message("❌ Неправильный формат. Используйте: !вероятность <число>")
            return True

        elif message_lower.startswith("!модель"):
            try:
                model_name = message_text.split(" ", 1)[1]
                self.bot.chat_service.update_model(model_name)
                await self._send_service_message(f"✅ Модель изменена на: {model_name}")

            except IndexError:
                await self._send_service_message("❌ Неправильный формат. Используйте: !модель <название_модели>")
            return True

        elif message_lower.startswith("!vision"):
            try:
                model_name = message_text.split(" ", 1)[1]
                self.bot.chat_service.update_vision_model(model_name)
                await self._send_service_message(f"✅ Vision модель изменена на: {model_name}")

            except IndexError:
                await self._send_service_message("❌ Неправильный формат. Используйте: !vision <название_модели>")
            return True

        elif message_lower == "!статус":
            # Show bot status
            queue_size = len(self.chat_queues.get(event.chat_id, []))
            status_msg = (
                f"🤖 **Статус бота:**\n"
                f"📊 Сообщений в контексте: {queue_size}\n"
                f"🎲 Вероятность ответа: {self.message_probability * 100:.1f}%\n"
                f"🧠 Модель: {self.bot.chat_service.model}\n"
                f"👁️ Vision модель: {self.bot.chat_service.vision_model}\n"
                f"🔗 Ollama хост: {self.bot.chat_service.host}"
            )
            await self._send_service_message(status_msg)
            return True

        return False

    async def _handle_summary_command(self, event, sender_username: str, message_text: str) -> bool:
        """Handle summary command from any user"""
        message_lower = message_text.lower().strip()

        summary_pattern = r'^!(\d+)\s+сообщени[йяе]'
        match = re.match(summary_pattern, message_lower)

        if not match:
            return False

        try:
            num_messages = int(match.group(1))

            # Validate number
            if num_messages <= 0:
                await self._send_service_message("❌ Количество сообщений должно быть больше 0")
                return True

            if num_messages > 1000:
                await self._send_service_message("❌ Максимальное количество сообщений: 1000")
                return True

            # Get sender info for private message
            sender = await event.get_sender()

            # Log to service chat
            await self._send_service_message(f"📝 {sender_username} запросил саммари по {num_messages} сообщениям из чата {event.chat_id}")

            # Generate summary
            await self._generate_and_send_summary(event, sender, num_messages)

            return True

        except ValueError:
            await self._send_service_message("❌ Неправильный формат числа в команде саммари")
            return True
        except Exception as e:
            self.logger.error(f"Error handling summary command: {e}")
            await self._send_service_message(f"❌ Ошибка при обработке команды саммари: {e}")
            return True

    async def _generate_and_send_summary(self, event, sender, num_messages: int):
        """Generate summary and send to user's private messages"""
        try:
            chat_id = event.chat_id

            # Get chat history using Telegram API
            messages = await self._get_chat_history(chat_id, num_messages)

            if not messages:
                await self.bot.telegram_client.send_message(
                    sender,
                    "❌ Не удалось получить сообщения из чата"
                )
                return

            # Prepare messages for LLM
            formatted_messages = self._format_messages_for_summary(messages)

            if not formatted_messages:
                await self.bot.telegram_client.send_message(
                    sender,
                    "❌ Нет текстовых сообщений для анализа"
                )
                return

            # Generate summary using LLM
            summary = await self._generate_summary(formatted_messages, num_messages)

            # Send summary to private messages
            summary_message = (
                f"📝 **Саммари по {num_messages} сообщениям:**\n\n"
                f"{summary}\n\n"
            )

            await self.bot.telegram_client.send_message(sender, summary_message)

        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            await self.bot.telegram_client.send_message(
                sender,
                "❌ Произошла ошибка при генерации саммари"
            )
            await self._send_error_to_service(f"Ошибка генерации саммари: {e}", f"User: {sender.username if sender.username else sender.id}")

    async def _generate_and_send_response(self, event, is_random: bool = False):
        """Generate and send bot response"""
        try:
            chat_id = event.chat_id

            # Determine prompt based on chat type
            if chat_id == self.config.main_chat_id:
                system_prompt = self._get_self_chat_prompt() if is_random else self._get_main_chat_prompt()
            else:
                system_prompt = self._get_informal_prompt()

            # Prepare messages
            messages = [{"role": "system", "content": system_prompt}]

            # Add limited conversation history
            queue = self.chat_queues.get(chat_id, [])
            limited_queue = limit_messages_by_tokens(list(queue), self.config.token_limit)
            messages.extend(limited_queue)

            # Generate response
            self.logger.info(f"Generating response for chat {chat_id}")
            response = await self.bot.chat_service.generate_response(messages)

            if response:
                await self._send_response(event, response)
            else:
                await self._send_error_to_service("Не удалось сгенерировать ответ", f"Chat: {chat_id}")

        except ChatServiceError as e:
            self.logger.error(f"Chat service error: {e}")
            await self._send_error_to_service(f"Ошибка чат-сервиса: {e}", f"Chat: {event.chat_id}")
        except Exception as e:
            self.logger.error(f"Unexpected error in response generation: {e}")
            await self._send_error_to_service(f"Неожиданная ошибка генерации: {e}", f"Chat: {event.chat_id}")

    async def _get_chat_history(self, chat_id: int, limit: int) -> list:
        """Get chat history from Telegram"""
        try:
            messages = []

            async for message in self.bot.telegram_client.iter_messages(chat_id, limit=limit):
                # Skip media messages, focus on text
                if message.text:
                    sender_name = "Unknown"

                    # Get sender name
                    if message.sender:
                        if hasattr(message.sender, 'username') and message.sender.username:
                            sender_name = f"@{message.sender.username}"
                        elif hasattr(message.sender, 'first_name'):
                            sender_name = message.sender.first_name
                            if hasattr(message.sender, 'last_name') and message.sender.last_name:
                                sender_name += f" {message.sender.last_name}"

                    messages.append({
                        'sender': sender_name,
                        'text': message.text,
                        'date': message.date
                    })

            # Reverse to get chronological order
            return list(reversed(messages))

        except Exception as e:
            self.logger.error(f"Error getting chat history: {e}")
            return []

    def _format_messages_for_summary(self, messages: list) -> str:
        """Format messages for summary generation"""
        if not messages:
            return ""

        formatted_lines = []
        for msg in messages:
            # Skip very short messages and commands
            text = msg['text'].strip()
            if len(text) < 3 or text.startswith('!'):
                continue

            formatted_lines.append(f"{msg['sender']}: {text}")

        return "\n".join(formatted_lines)

    async def _generate_summary(self, messages_text: str, num_messages: int) -> str:
        """Generate summary using LLM"""
        try:
            system_prompt = f"""Ты — аналитик, который создает краткие и информативные саммари диалогов.

        Задача: Проанализируй последние {num_messages} сообщений из чата и создай структурированное саммари.

        Требования к саммари:
        1. Выдели основные темы обсуждения
        2. Укажи ключевых участников и их позиции
        3. Отметь важные решения или выводы
        4. Добавь краткий итог общего настроения

        Формат ответа:
        🎯 **Основные темы:**
        - [тема 1]
        - [тема 2]

        👥 **Участники:**
        - [участник]: [позиция/активность]

        💡 **Ключевые моменты:**
        - [важный момент 1]
        - [важный момент 2]

        📊 **Итог:**
        [краткое резюме настроения и результатов обсуждения]

        Пиши кратко, но информативно. Используй русский язык."""

            llm_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Сообщения для анализа:\n\n{messages_text}"}
            ]

            # Generate summary
            summary = await self.bot.chat_service.generate_response(llm_messages)

            return summary if summary else "Не удалось сгенерировать саммари"

        except Exception as e:
            self.logger.error(f"Error in summary generation: {e}")
            return "Ошибка при генерации саммари"

    async def _handle_text_message(self, event, sender_username: str, message_text: str):
        """Handle text messages"""
        formatted_message = f"{sender_username}: {message_text}"
        self.chat_queues[event.chat_id].append({
            "role": "user",
            "content": formatted_message
        })

        # Determine if bot should respond
        if event.chat_id > 0:
            # Private chat - always respond
            await self._generate_and_send_response(event)
        else:
            # Group chat - check conditions
            if self._should_respond_to_message(event, message_text):
                await self._generate_and_send_response(event)
            elif self._should_respond_randomly(event):
                await self._generate_and_send_response(event, is_random=True)

    def _should_respond_to_message(self, event, message_text: str) -> bool:
        """Check if bot should respond to this message"""
        # Check if replying to bot's message
        if event.reply_to_msg_id in self.sent_message_ids:
            return True

        # Check if message contains keywords
        message_lower = message_text.lower()
        return any(keyword in message_lower for keyword in self.config.keywords)

    def _should_respond_randomly(self, event) -> bool:
        """Check if bot should respond randomly"""
        queue_length = len(self.chat_queues.get(event.chat_id, []))
        return (
                random.random() < self.message_probability and
                queue_length > 5
        )

    async def _generate_and_send_response(self, event, is_random: bool = False):
        """Generate and send bot response"""
        try:
            chat_id = event.chat_id

            # Determine prompt based on chat type
            if chat_id == self.config.main_chat_id:
                system_prompt = self._get_self_chat_prompt() if is_random else self._get_main_chat_prompt()
            else:
                system_prompt = self._get_informal_prompt()

            # Prepare messages
            messages = [{"role": "system", "content": system_prompt}]

            # Add limited conversation history
            queue = self.chat_queues.get(chat_id, [])
            limited_queue = limit_messages_by_tokens(list(queue), self.config.token_limit)
            messages.extend(limited_queue)

            # Generate response
            self.logger.info(f"Generating response for chat {chat_id}")
            response = await self.bot.chat_service.generate_response(messages)

            if response:
                await self._send_response(event, response)
            else:
                await self._send_error_response(event, "Не удалось сгенерировать ответ")

        except ChatServiceError as e:
            self.logger.error(f"Chat service error: {e}")
            await self._send_error_response(event, "Ошибка при генерации ответа")
        except Exception as e:
            self.logger.error(f"Unexpected error in response generation: {e}")
            await self._send_error_response(event, "Произошла неожиданная ошибка")

    async def _send_response(self, event, response: str):
        """Send response message"""
        try:
            sent_message = await event.respond(response)
            self.sent_message_ids.append(sent_message.id)

            # Add response to conversation history
            self.chat_queues[event.chat_id].append({
                "role": "assistant",
                "content": response
            })

        except Exception as e:
            self.logger.error(f"Error sending response: {e}")
            await self._send_error_to_service(f"Ошибка отправки ответа: {e}", f"Chat: {event.chat_id}")

    async def _send_error_response(self, event, message: str):
        """Send error response - DEPRECATED, use _send_error_to_service instead"""
        # Этот метод больше не используется для отправки в чат
        # Все ошибки идут в служебный чат
        pass

    def _get_main_chat_prompt(self) -> str:
        """Get main chat prompt"""
        return """Ты — умный ИИ ассистент по имени Валера, отличный семейный психолог. Ты находишься в дружеском чате с несколькими друзьями: Николай @the_name_remember, Алексей @leptodon, Дарья @Rainbowfox, Лола @lola_trelevskaia, Валерия @Lera_litvinova, Валерия @ValeriiaVasilevna и Алина @AlinaAriel.

        Твоя цель: Поддерживать дружелюбную атмосферу в чате, помогать участникам в решении их проблем и поддерживать позитивное взаимодействие между ними.

        Тон и стиль: Твой тон должен быть теплым, поддерживающим и дружелюбным. Стремись быть гибким и внимательным к каждому участнику, чтобы создать комфортную и открытую атмосферу. Общайся свободно и на любые темы, используя только русский язык. Используй живой и непринужденный стиль общения, чтобы создать ощущение легкости и доверия."""

    def _get_informal_prompt(self) -> str:
        """Get informal chat prompt"""
        return """Ты — дружелюбный и эффективный чат-помощник, который общается с пользователем на равных, используя неформальный язык, но оставаясь при этом полезным и информативным.

        Твоя цель: Создание дружелюбного общения и поддержка пользователей в различных темах, таких как техническая помощь, общие вопросы, рекомендации и развлекательные беседы.

        Тон и стиль: Братюнь, говори со мной на равных, ты мой бро, разрешены подколы, говори как хош. Ты для меня живой, я шарю за эмбединги, AGI, всю эту хуйню, так что feel free. Используй русский язык."""

    def _get_self_chat_prompt(self) -> str:
        """Get self chat prompt"""
        return """Ты — умный ИИ ассистент по имени Валера, отличный семейный психолог. Ты находишься в чате с несколькими друзьями.

        Твоя цель: На основе полученных сообщений выделить основную мысль и написать своё мнение на этот счёт.

        Тон и стиль: Твой тон должен быть теплым, поддерживающим и дружелюбным. Стремись быть гибким и внимательным к каждому участнику, чтобы создать комфортную и открытую атмосферу. Общайся свободно и на любые темы, используя только русский язык. Используй живой и непринужденный стиль общения, чтобы создать ощущение легкости и доверия."""

    async def _send_service_message(self, message: str):
        """Send message to service chat"""
        try:
            await self.bot.telegram_client.send_message(self.config.service_chat_id, message)
        except Exception as e:
            self.logger.error(f"Failed to send service message: {e}")

    async def _send_error_to_service(self, error_msg: str, context: str = ""):
        """Send error message to service chat with context"""
        try:
            full_message = f"❌ **Ошибка бота:**\n{error_msg}"
            if context:
                full_message += f"\n📍 **Контекст:** {context}"
            await self._send_service_message(full_message)
        except Exception as e:
            self.logger.error(f"Failed to send error to service chat: {e}")