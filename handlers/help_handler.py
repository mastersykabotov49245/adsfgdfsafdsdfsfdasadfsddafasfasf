# handlers/help_handler.py
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class HelpHandler:
    @staticmethod
    async def help_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню помощи/поддержки"""
        query = update.callback_query
        if query:
            await query.answer()
        
        text = "🛠 *Меню поддержки*\n\nВыберите нужный раздел:"
        
        keyboard = [
            [InlineKeyboardButton("📢 Владелец (реклама/сотрудничество)", url="https://t.me/qocus")],
            [InlineKeyboardButton("📖 Гайд по ворку", callback_data="work_manual")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    @staticmethod
    async def work_manual_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мануал по в0рку"""
        query = update.callback_query
        await query.answer()
        
        manual_text = "📖 *Гайд для новичков по скаму*\n\nПодробнее: t.me/c/3903354526/32"
   
        keyboard = [
            [InlineKeyboardButton("🔙 Назад в поддержку", callback_data="support_menu")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(manual_text, reply_markup=reply_markup, parse_mode='Markdown')
