# handlers/start.py
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from bot_config import ADMINS
from database import Database
from utils import Utils

logger = logging.getLogger(__name__)

class StartHandler:
    @staticmethod
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        Database.add_user(user.id, user.username, user.first_name, user.last_name)
        
        if not await Utils.check_subscription(user.id, context):
            await Utils.require_subscription(update, context)
            return
        
        await StartHandler.show_main_menu(update, context)

    @staticmethod
    async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Поиск NFT",
                    callback_data="search_type_selection",
                    icon_custom_emoji_id="5309965701241379366",
                    style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Мой профиль",
                    callback_data="profile_menu",
                    icon_custom_emoji_id="5451709985765468632",
                    style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Настройки",
                    callback_data="settings_menu",
                    icon_custom_emoji_id="5870982283724328568",
                    style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Поддержка",
                    callback_data="support_menu",
                    icon_custom_emoji_id="5832352677849205948",
                    style="primary"
                )
            ],
        ]
        
        if user.id in ADMINS:
            keyboard.append([
                InlineKeyboardButton(
                    text="Админ панель",
                    callback_data="admin_panel",
                    icon_custom_emoji_id="5397866377367268054",
                    style="primary"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        username = f"@{user.username}" if user.username else user.first_name
        welcome_text = f"👋 Привет, {username}! Это парсер для поиска лохматых."

        try:
            if update.callback_query:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=welcome_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                try:
                    await update.callback_query.message.delete()
                except:
                    pass
            else:
                await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Ошибка отправки главного меню: {e}")