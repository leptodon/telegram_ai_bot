import tiktoken
from typing import List, Dict


def count_tokens(messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo") -> int:
    """Count tokens in messages"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        total_tokens = 0

        for message in messages:
            content = message.get('content', '')
            tokens = encoding.encode(content)
            total_tokens += len(tokens)

        return total_tokens

    except Exception:
        # Fallback: rough estimation
        total_chars = sum(len(msg.get('content', '')) for msg in messages)
        return total_chars // 4  # Rough approximation


def limit_messages_by_tokens(messages: List[Dict[str, str]], token_limit: int, model: str = "gpt-3.5-turbo") -> List[
    Dict[str, str]]:
    """Limit messages to fit within token limit"""
    if not messages:
        return []

    try:
        encoding = tiktoken.encoding_for_model(model)
        limited_messages = []
        total_tokens = 0

        # Process messages from newest to oldest
        for message in reversed(messages):
            content = message.get('content', '')
            tokens = encoding.encode(content)

            if total_tokens + len(tokens) > token_limit:
                break

            limited_messages.insert(0, message)
            total_tokens += len(tokens)

        return limited_messages

    except Exception:
        # Fallback: limit by character count
        char_limit = token_limit * 4  # Rough approximation
        limited_messages = []
        total_chars = 0

        for message in reversed(messages):
            content = message.get('content', '')
            if total_chars + len(content) > char_limit:
                break

            limited_messages.insert(0, message)
            total_chars += len(content)

        return limited_messages