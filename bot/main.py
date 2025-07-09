import asyncio
import sys
from bot.config import Config
from bot.core.bot import TelegramBot
from bot.exceptions import BotException


async def main():
    """Main entry point"""
    try:
        # Load configuration
        config = Config.from_env()

        # Create and start bot
        bot = TelegramBot(config)
        await bot.start()

    except BotException as e:
        print(f"Bot error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
