import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from database import Database
from globals import waiting_for_template, user_templates

logger = logging.getLogger(__name__)

class TemplatesManager:
    @staticmethod
    async def templates_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        templates = Database.get_user_templates(user_id)
        
        active_template = user_templates.get(user_id, {"name": "Стандартный", "text": "Здравствуйте, заинтересовался вашим NFT подарком, могу купить у вас его."})
        
        text = "📝 *Настройка шаблонов*\n\n"
        text += f"✅ Активный шаблон: *{active_template['name']}*\n\n"
        
        if templates:
            text += "📋 Ваши шаблоны:\n"
            for i, template in enumerate(templates, 1):
                is_active = "*" if template['name'] == active_template['name'] else ""
                text += f"{i}. {is_active}{template['name']}{is_active}\n"
        else:
            text += "❌ У вас пока нет шаблонов\n\n"
            text += "Добавьте шаблон чтобы использовать его в поиске."
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить шаблон", callback_data="add_template_dialog")],
        ]
        
        if templates:
            keyboard.append([InlineKeyboardButton("🎯 Выбрать активный шаблон", callback_data="select_active_template")])
            keyboard.append([InlineKeyboardButton("🗑 Удалить шаблон", callback_data="delete_template_menu")])
            keyboard.append([InlineKeyboardButton("👁 Просмотреть шаблоны", callback_data="view_all_templates")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад в настройки", callback_data="settings_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def add_template_dialog_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if user_id in waiting_for_template:
            await query.answer("❌ Вы уже добавляете шаблон!", show_alert=True)
            return
        
        waiting_for_template[user_id] = {"step": "name"}
        await query.edit_message_text(
            "📝 *Добавление нового шаблона*\n\n"
            "Введите название для нового шаблона (максимум 30 символов):"
        )

    @staticmethod
    async def select_active_template_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        templates = Database.get_user_templates(user_id)
        
        if not templates:
            await query.answer("❌ У вас нет шаблонов", show_alert=True)
            return
        
        text = "🎯 *Выберите активный шаблон:*\n\n"
        
        keyboard = []
        for i, template in enumerate(templates):
            button_text = template['name'][:50]
            keyboard.append([
                InlineKeyboardButton(
                    f"{i+1}. {button_text}", 
                    callback_data=f"set_active_template_{i}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="templates_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def set_active_template_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        template_index_str = query.data.replace("set_active_template_", "")
        
        try:
            template_index = int(template_index_str)
        except ValueError:
            await query.answer("❌ Ошибка: неверный индекс шаблона", show_alert=True)
            return
        
        templates = Database.get_user_templates(user_id)
        
        if 0 <= template_index < len(templates):
            user_templates[user_id] = templates[template_index]
            template_name = templates[template_index]["name"]
            
            await query.answer(f"✅ Установлен активный шаблон: {template_name}", show_alert=True)
            
            await TemplatesManager.templates_menu_callback(update, context)
            
        else:
            await query.answer("❌ Шаблон не найден", show_alert=True)

    @staticmethod
    async def delete_template_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        templates = Database.get_user_templates(user_id)
        
        if not templates:
            await query.answer("❌ У вас нет шаблонов", show_alert=True)
            return
        
        text = "🗑 *Выберите шаблон для удаления:*\n\n"
        for i, template in enumerate(templates, 1):
            text += f"{i}. {template['name']}\n"
        
        keyboard = []
        for i, template in enumerate(templates):
            button_text = template['name'][:30]
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ Удалить '{button_text}'", 
                    callback_data=f"delete_template_{i}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="templates_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def delete_template_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        template_index_str = query.data.replace("delete_template_", "")
        
        try:
            template_index = int(template_index_str)
        except ValueError:
            await query.answer("❌ Ошибка: неверный индекс шаблона", show_alert=True)
            return
        
        templates = Database.get_user_templates(user_id)
        
        if 0 <= template_index < len(templates):
            template_name = templates[template_index]["name"]
            success, message = Database.delete_user_template(user_id, template_index)
            
            if success:
                if user_id in user_templates and user_templates[user_id].get("name") == template_name:
                    del user_templates[user_id]
                    await query.answer(f"✅ Шаблон '{template_name}' удален (был активным)", show_alert=True)
                else:
                    await query.answer(f"✅ Шаблон '{template_name}' удален", show_alert=True)
                
                await TemplatesManager.templates_menu_callback(update, context)
            else:
                await query.answer(f"❌ Ошибка: {message}", show_alert=True)
        else:
            await query.answer("❌ Шаблон не найден", show_alert=True)

    @staticmethod
    async def view_all_templates_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        templates = Database.get_user_templates(user_id)
        
        if not templates:
            await query.answer("❌ У вас нет шаблонов", show_alert=True)
            return
        
        text = "📝 *Все ваши шаблоны:*\n\n"
        
        for i, template in enumerate(templates, 1):
            template_text = template['text']
            
            if len(template_text) > 1000:
                display_text = template_text[:1000] + "...\n[Текст обрезан, оригинал сохранен]"
            else:
                display_text = template_text
            
            text += f"*{i}. {template['name']}*\n"
            text += f"`{display_text}`\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🎯 Выбрать активный шаблон", callback_data="select_active_template")],
            [InlineKeyboardButton("🔙 Назад", callback_data="templates_menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')