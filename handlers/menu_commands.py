# handlers/menu_commands.py
import logging
from telegram import BotCommand
from bot_config import ADMINS

logger = logging.getLogger(__name__)

class MenuCommands:
    
    @staticmethod
    async def set_commands(application):
        """Устанавливает кнопку Menu только с командой /start"""
        
        # Только одна команда
        commands = [
            BotCommand("start", "🚀 Перезапустить бота"),
        ]
        
        try:
            await application.bot.set_my_commands(commands)
            logger.info("✅ Установлена команда /start в меню")
        except Exception as e:
            logger.error(f"❌ Ошибка установки команды: {e}")
