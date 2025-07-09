class BotException(Exception):
    """Base exception for bot errors"""
    pass

class ChatServiceError(BotException):
    """Exception for chat service errors"""
    pass