import asyncio
import base64
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from ollama import Client
from .base import BaseService
from ..exceptions import ChatServiceError


class ChatService(BaseService):
    """Service for handling chat interactions with Ollama"""

    def __init__(self, host: str, model: str, vision_model: str, max_workers: int = 1, logger=None):
        super().__init__(logger)
        self.host = host
        self.model = model
        self.vision_model = vision_model
        self.client = None
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def initialize(self, max_attempts: int = 30, delay: int = 1):
        """Initialize connection to Ollama"""
        for attempt in range(max_attempts):
            try:
                client = Client(host=self.host)
                client.list()  # Test connection
                self.client = client
                self.logger.info("Successfully connected to Ollama")
                return

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1}/{max_attempts}: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(delay)
                else:
                    raise ChatServiceError(f"Failed to connect to Ollama after {max_attempts} attempts")

    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate response using Ollama"""
        if not self.client:
            raise ChatServiceError("Chat service not initialized")

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.client.chat(model=self.model, messages=messages)
            )

            content = response.get('message', {}).get('content', '')
            if not content:
                raise ChatServiceError("Empty response from Ollama")

            return content

        except Exception as e:
            self.logger.error(f"Failed to generate response: {e}")
            raise ChatServiceError(f"Failed to generate response: {e}")

    async def analyze_image(self, image_data: bytes, prompt: str = "Опиши что ты видишь на этой картинке") -> str:
        """Analyze image using vision model"""
        if not self.client:
            raise ChatServiceError("Chat service not initialized")

        try:
            # Конвертируем изображение в base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.client.chat(
                    model=self.vision_model,
                    messages=[{
                        'role': 'user',
                        'content': prompt,
                        'images': [image_base64]
                    }]
                )
            )

            content = response.get('message', {}).get('content', '')
            if not content:
                raise ChatServiceError("Empty response from vision model")

            return content

        except Exception as e:
            self.logger.error(f"Failed to analyze image: {e}")
            raise ChatServiceError(f"Failed to analyze image: {e}")

    def update_model(self, model: str):
        """Update the model being used"""
        self.model = model
        self.logger.info(f"Model updated to: {model}")

    def update_vision_model(self, model: str):
        """Update the vision model being used"""
        self.vision_model = model
        self.logger.info(f"Vision model updated to: {model}")

    def shutdown(self):
        """Shutdown the chat service"""
        if self.executor:
            self.executor.shutdown(wait=True)