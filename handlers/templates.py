# handlers/templates.py
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from database import Database
from globals import waiting_for_template, user_templates

logger = logging.getLogger(__name__)

class TemplatesHandler:
    @staticmethod
    async def add_template_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /addtemplate"""
        user_id = update.effective_user.id
        
        if user_id in waiting_for_template:
            await update.message.reply_text("❌ Вы уже добавляете шаблон! Закончите текущее добавление.")
            return
        
        waiting_for_template[user_id] = {"step": "name"}
        await update.message.reply_text(
            "📝 Введите название для нового шаблона (максимум 50 символов):"
        )

    @staticmethod
    async def handle_template_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик сообщений для шаблонов"""
        # ДОБАВЛЕНА ПРОВЕРКА ДЛЯ ИСПРАВЛЕНИЯ ПРЕДУПРЕЖДЕНИЯ
        if not update or not update.effective_user or not update.message:
            logger.warning("Нет update или effective_user в handle_template_message")
            return
            
        user_id = update.effective_user.id
        
        # Проверяем, есть ли сообщение и текст
        if not update.message or not update.message.text:
            return
            
        # Проверяем, находится ли пользователь в процессе добавления шаблона
        if user_id not in waiting_for_template:
            return
        
        step_data = waiting_for_template[user_id]
        message_text = update.message.text
        
        if step_data["step"] == "name":
            if len(message_text) > 30:  # Уменьшено до 30 для имени
                await update.message.reply_text("❌ Название слишком длинное (максимум 30 символов). Введите другое название:")
                return
                
            waiting_for_template[user_id] = {
                "step": "text", 
                "name": message_text
            }
            await update.message.reply_text(
                "📝 Теперь введите текст шаблона:\n"
                "⚠️ *Максимум 100 символов*\n"
                "⚠️ *Короткие шаблоны работают лучше!*"
            )
        
        elif step_data["step"] == "text":
            template_name = step_data["name"]
            template_text = message_text
            
            # ОГРАНИЧИВАЕМ ДЛИНУ ТЕКСТА ПРИ СОХРАНЕНИИ (100 символов)
            if len(template_text) > 100:
                await update.message.reply_text(
                    "❌ Текст шаблона слишком длинный! Максимум 100 символов.\n"
                    f"Сейчас: {len(template_text)} символов\n"
                    "Пожалуйста, введите более короткий текст:"
                )
                return
            
            # Сохраняем шаблон
            success, message = Database.add_user_template(user_id, template_name, template_text)
            del waiting_for_template[user_id]
            
            if success:
                # Сразу устанавливаем новый шаблон как активный
                user_templates[user_id] = {"name": template_name, "text": template_text}
                
                # Собираем статистику
                Database.update_user_stats(user_id, "template_created")
                
                # Успешное сообщение
                await update.message.reply_text(
                    f"✅ {message}\n\n"
                    f"📝 *Шаблон установлен как активный!*\n"
                    f"🔤 Длина текста: {len(template_text)}/100 символов",
                    parse_mode='Markdown'
                )
                
                # Простое сообщение с кнопкой без дополнительных отправок
                keyboard = [
                    [InlineKeyboardButton("📝 Перейти в настройку шаблонов", callback_data="templates_menu")],
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
            else:
                await update.message.reply_text(f"❌ {message}")

    @staticmethod
    async def select_template_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор шаблона при выборе режима (ИСПРАВЛЕН БАГ)"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        template_index_str = query.data.replace("select_template_", "")
        
        try:
            template_index = int(template_index_str)
        except ValueError:
            await query.answer("❌ Ошибка: неверный индекс шаблона", show_alert=True)
            return
        
        templates = Database.get_user_templates(user_id)
        
        if 0 <= template_index < len(templates):
            # Просто сохраняем шаблон без проверки длины
            user_templates[user_id] = templates[template_index]
            template_name = templates[template_index]["name"]
            await query.answer(f"✅ Выбран шаблон: {template_name}", show_alert=True)
            
            # Получаем выбранный режим
            from globals import user_modes
            from bot_config import SEARCH_MODES
            
            if user_id in user_modes:
                mode_key = user_modes[user_id]
                mode_name = SEARCH_MODES[mode_key]["name"]
                
                text = f"✅ *Выбран режим:* {mode_name}\n"
                text += f"📝 *Шаблон:* {template_name}\n\n"
                text += "Нажмите кнопку ниже чтобы начать поиск:"
                
                keyboard = [
                    [InlineKeyboardButton("🔍 Начать поиск NFT", callback_data="search")],
                    [InlineKeyboardButton("🎯 Сменить режим", callback_data="change_mode")],
                    [InlineKeyboardButton("📝 Сменить шаблон", callback_data="change_mode")],  # Возврат к выбору шаблона через смену режима
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
                ]
            else:
                text = f"📝 *Выбран шаблон:* {template_name}\n\n"
                text += "🎯 *Режим не выбран*\n\n"
                text += "Выберите режим поиска или начните поиск с текущим шаблоном:"
                
                keyboard = [
                    [InlineKeyboardButton("🎯 Выбрать режим", callback_data="change_mode")],
                    [InlineKeyboardButton("🔍 Начать поиск NFT", callback_data="search")],
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            
        else:
            await query.answer("❌ Шаблон не найден", show_alert=True)