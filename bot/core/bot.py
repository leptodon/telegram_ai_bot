import logging
from telethon import TelegramClient, events
from ..config import Config
from ..services.chat_service import ChatService
from ..handlers.message_handler import MessageHandler
from ..exceptions import BotException


class TelegramBot:
    """Simple text-only Telegram bot"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = self._setup_logging()

        # Initialize services
        self.chat_service = None

        # Initialize Telegram client
        self.telegram_client = None

        # Initialize handlers
        self.message_handler = None

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Reduce telethon logging
        logging.getLogger('telethon').setLevel(logging.WARNING)

        return logging.getLogger(__name__)

    async def initialize(self):
        """Initialize all bot components"""
        try:
            self.logger.info("Initializing bot components...")

            # Initialize services
            await self._initialize_services()

            # Initialize Telegram client
            await self._initialize_telegram_client()

            # Initialize handlers
            self._initialize_handlers()

            self.logger.info("Bot initialization completed successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize bot: {e}")
            raise BotException(f"Bot initialization failed: {e}")

    async def _initialize_services(self):
        """Initialize chat service"""
        self.chat_service = ChatService(
            self.config.ollama_host,
            self.config.ollama_model,
            self.config.ollama_vision_model,
            logger=self.logger
        )
        await self.chat_service.initialize(
            self.config.max_retry_attempts,
            self.config.retry_delay
        )

    async def _initialize_telegram_client(self):
        """Initialize Telegram client"""
        self.telegram_client = TelegramClient(
            self.config.phone_number,
            self.config.api_id,
            self.config.api_hash,
            device_model="Python Text Bot",
            system_version="1.0",
            app_version="1.0.0",
            lang_code='en',
            system_lang_code='ru',
        )

        await self.telegram_client.start()
        self.logger.info("Successfully connected to Telegram")

    def _initialize_handlers(self):
        """Initialize event handlers"""
        self.message_handler = MessageHandler(self, self.config, self.logger)

        # Register event handlers
        self.telegram_client.add_event_handler(
            self.message_handler.handle_message,
            events.NewMessage()
        )

    async def start(self):
        """Start the bot"""
        try:
            await self.initialize()
            self.logger.info("🤖 Bot started successfully - text-only mode")

            # Keep the bot running
            await self.telegram_client.run_until_disconnected()

        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Bot crashed: {e}")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Shutdown the bot gracefully"""
        self.logger.info("Shutting down bot...")

        try:
            if self.chat_service:
                self.chat_service.shutdown()

            if self.telegram_client:
                await self.telegram_client.disconnect()

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

        self.logger.info("Bot shutdown completed")