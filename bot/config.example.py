import os
from dataclasses import dataclass
from typing import List


@dataclass
class Config:
    """Configuration class for the bot"""
    # Telegram API
    api_id: int
    api_hash: str
    phone_number: str

    # Ollama
    ollama_host: str
    ollama_model: str
    ollama_vision_model: str

    # Bot settings
    token_limit: int
    message_probability: float
    max_retry_attempts: int
    retry_delay: int
    keywords: List[str]

    # Chat settings
    main_chat_id: int
    admin_username: str
    service_chat_id: int

    @classmethod
    def from_env(cls):
        """Create config from environment variables"""
        return cls(
            api_id=int(os.getenv('API_ID', '0')),
            api_hash=os.getenv('API_HASH', ''),
            phone_number=os.getenv('PHONE_NUMBER', ''),
            ollama_host=os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
            ollama_model=os.getenv('OLLAMA_MODEL', 'OxW/Vikhr-Nemo-12B-Instruct-R-21-09-24:q8_0'),
            ollama_vision_model=os.getenv('OLLAMA_VISION_MODEL', 'qwen2.5vl:7b'),
            token_limit=int(os.getenv('TOKEN_LIMIT', '4096')),
            message_probability=float(os.getenv('MESSAGE_PROBABILITY', '0.1')),
            max_retry_attempts=int(os.getenv('MAX_RETRY_ATTEMPTS', '30')),
            retry_delay=int(os.getenv('RETRY_DELAY', '1')),
            keywords=['валер', '@ai_valera'],
            main_chat_id=int(os.getenv('MAIN_CHAT_ID', '0')),
            admin_username=os.getenv('ADMIN_USERNAME', ''),
            service_chat_id=int(os.getenv('SERVICE_CHAT_ID', '0')),
        )
