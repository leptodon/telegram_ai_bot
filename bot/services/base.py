from abc import ABC
import logging
from typing import Optional


class BaseService(ABC):
    """Base service class"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)