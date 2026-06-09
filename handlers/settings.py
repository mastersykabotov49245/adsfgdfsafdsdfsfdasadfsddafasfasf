# handlers/settings.py
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from bot_config import DEFAULT_SEARCH_LIMIT, SEARCH_LIMIT_OPTIONS, MAX_SEARCH_LIMIT
from database import Database
from globals import user_search_limits

logger = logging.getLogger(__name__)

class SettingsHandler:
    @staticmethod
    async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            user_id = query.from_user.id
        else:
            user_id = update.effective_user.id
        
        user_settings = Database.get_user_settings(user_id)
        search_limit = user_settings.get("search_limit", DEFAULT_SEARCH_LIMIT)
        results_interface = user_settings.get("results_interface", "list")
        interface_name = "Список" if results_interface == "list" else "Покадровый"
        
        text = f"⚙️ <b>Настройки</b>\n\nВыберите категорию настроек:"
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"Количество результатов ({search_limit})",
                    callback_data="change_search_limit",
                    icon_custom_emoji_id="5870982283724328568",  # Настройки
                    style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Интерфейс результатов ({interface_name})",
                    callback_data="change_results_interface",
                    style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Настройка шаблонов",
                    callback_data="templates_menu",
                    style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Выбрать режим",
                    callback_data="change_mode",
                    style="success"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Управление NFT",
                    callback_data="block_management",
                    style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Главное меню",
                    callback_data="back_to_menu",
                    icon_custom_emoji_id="5352759161945867747",
                    style="primary"
                )
            ],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')