from abc import ABC
import logging
from typing import Optional


class BaseHandler(ABC):
    """Base handler class"""

    def __init__(self, bot, config, logger: Optional[logging.Logger] = None):
        self.bot = bot
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)