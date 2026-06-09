# handlers/nft_management.py
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from bot_config import SEARCH_MODES, EXCLUDED_NFT
from database import Database
from utils import Utils

logger = logging.getLogger(__name__)

class NFTManagementHandler:
    @staticmethod
    def get_all_nft_list():
        """Получает полный список всех NFT с нумерацией"""
        all_nft = []
        nft_number = 1
        
        for mode_name, mode_data in SEARCH_MODES.items():
            for collection in mode_data["collections"]:
                if collection["name"] not in EXCLUDED_NFT:
                    all_nft.append({
                        "number": nft_number,
                        "name": collection["name"],
                        "mode": mode_name,
                        "id_range": collection["id_range"]
                    })
                    nft_number += 1
        
        return all_nft

    @staticmethod
    def get_nft_by_number(nft_number):
        """Получает NFT по номеру"""
        all_nft = NFTManagementHandler.get_all_nft_list()
        for nft in all_nft:
            if nft["number"] == nft_number:
                return nft
        return None

    @staticmethod
    def get_nft_by_name_and_mode(nft_name, mode_name):
        """Получает NFT по имени и режиму"""
        if mode_name not in SEARCH_MODES:
            return None
            
        nft_number = 1
        for check_mode_name, mode_data in SEARCH_MODES.items():
            for collection in mode_data["collections"]:
                if collection["name"] not in EXCLUDED_NFT:
                    if collection["name"] == nft_name and check_mode_name == mode_name:
                        return {
                            "number": nft_number,
                            "name": collection["name"],
                            "mode": mode_name,
                            "id_range": collection["id_range"]
                        }
                    nft_number += 1
        return None

    @staticmethod
    async def nft_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает список всех NFT"""
        user_id = update.effective_user.id
        blocked_nft = Database.get_blocked_nft(user_id)
        
        # Проверяем откуда пришли
        from_results = context.user_data.get("from_results", False)
        
        all_nft = NFTManagementHandler.get_all_nft_list()
        
        # Разбиваем список на части чтобы избежать Message_too_long
        text_parts = []
        current_text = "📋 *Список всех NFT:*\n\n"
        
        # Создаем inline кнопки для блокировки
        keyboard = []
        row = []
        
        for nft in all_nft:
            nft_line = f"{'🔴' if nft['number'] in blocked_nft else '🟢'} {nft['number']}. {nft['name']}\n"
            nft_line += f"   🎯 {nft['mode']} | ID: {nft['id_range'][0]}-{nft['id_range'][1]}\n\n"
            
            # Если текущая часть становится слишком длинной, начинаем новую
            if len(current_text + nft_line) > 3500:
                text_parts.append(current_text)
                current_text = ""
            
            current_text += nft_line
            
            # Добавляем кнопку для блокировки/разблокировки
            btn_text = f"{'✅' if nft['number'] in blocked_nft else '❌'} {nft['name']}"
            row.append(InlineKeyboardButton(btn_text, callback_data=f"toggle_nft_{nft['number']}"))
            
            if len(row) == 2:  # 2 кнопки в ряд
                keyboard.append(row)
                row = []
        
        # Добавляем последний ряд если он не полный
        if row:
            keyboard.append(row)
        
        # Добавляем последнюю часть
        if current_text:
            current_text += f"🔢 Всего NFT: {len(all_nft)}\n"
            current_text += f"🔒 Заблокировано: {len(blocked_nft)}\n\n"
            current_text += "🔒 Заблокировать: /block <номер>\n"
            current_text += "🔓 Разблокировать: /unblock <номер>\n"
            current_text += "📋 Мои блокировки: /myblock"
            text_parts.append(current_text)
        
        # Добавляем кнопки навигации
        if from_results:
            keyboard.append([InlineKeyboardButton("📋 Мои блокировки", callback_data="myblock_list")])
            keyboard.append([InlineKeyboardButton("🔙 Назад к результатам", callback_data="back_to_results_search")])
        else:
            keyboard.append([InlineKeyboardButton("📋 Мои блокировки", callback_data="myblock_list")])
            keyboard.append([InlineKeyboardButton("🔙 Назад к настройкам", callback_data="settings_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.answer()
            # Отправляем первую часть
            await update.callback_query.edit_message_text(
                text_parts[0], 
                reply_markup=reply_markup, 
                parse_mode='Markdown'
            )
            # Отправляем остальные части как новые сообщения
            for part in text_parts[1:]:
                await Utils.safe_send_message(
                    context, user_id, part, parse_mode='Markdown'
                )
        else:
            # Отправляем все части
            for i, part in enumerate(text_parts):
                if i == 0:
                    await update.message.reply_text(part, reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    await update.message.reply_text(part, parse_mode='Markdown')

    @staticmethod
    async def toggle_nft_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик переключения блокировки NFT"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        nft_id_str = query.data.replace("toggle_nft_", "")
        
        try:
            nft_id = int(nft_id_str)
        except ValueError:
            await query.answer("❌ Ошибка: неверный номер NFT", show_alert=True)
            return
        
        nft_info = NFTManagementHandler.get_nft_by_number(nft_id)
        if not nft_info:
            await query.answer("❌ NFT не найден", show_alert=True)
            return
        
        blocked_nft = Database.get_blocked_nft(user_id)
        
        if nft_id in blocked_nft:
            # Разблокировать
            if Database.remove_blocked_nft(user_id, nft_id):
                await query.answer(f"✅ NFT '{nft_info['name']}' разблокирован", show_alert=True)
        else:
            # Заблокировать
            if Database.add_blocked_nft(user_id, nft_id):
                Database.update_user_stats(user_id, "nft_blocked")
                await query.answer(f"✅ NFT '{nft_info['name']}' заблокирован", show_alert=True)
        
        # Обновляем сообщение
        await NFTManagementHandler.nft_command(update, context)

    @staticmethod
    async def block_management_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню управления блокировками"""
        query = update.callback_query
        await query.answer()
        
        # Проверяем откуда пришли
        from_results = context.user_data.get("from_results", False)
        
        text = "🔧 *Управление блокировками NFT*\n\nВыберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("🚫 Заблокировать NFT", callback_data="block_nft_menu")],
            [InlineKeyboardButton("✅ Разблокировать NFT", callback_data="unblock_nft_menu")],
            [InlineKeyboardButton("📋 Список заблокированных", callback_data="myblock_list")],
            [InlineKeyboardButton("📋 Весь список NFT", callback_data="nft_list")],
        ]
        
        # Кнопка назад в зависимости от контекста
        if from_results:
            keyboard.append([InlineKeyboardButton("🔙 Назад к результатам", callback_data="back_to_results_search")])
        else:
            keyboard.append([InlineKeyboardButton("🔙 Назад к настройкам", callback_data="settings_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Блокировка NFT"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(
                "❌ Использование: /block <номер_nft>\n"
                "📋 Посмотреть все NFT: /nft"
            )
            return
        
        try:
            nft_number = int(context.args[0])
            nft_info = NFTManagementHandler.get_nft_by_number(nft_number)
            
            if not nft_info:
                await update.message.reply_text("❌ NFT с таким номером не найден")
                return
            
            if Database.add_blocked_nft(user_id, nft_number):
                # СОБИРАЕМ СТАТИСТИКУ
                Database.update_user_stats(user_id, "nft_blocked")
                
                await update.message.reply_text(
                    f"✅ NFT '{nft_info['name']}' заблокирован\n"
                    f"🔢 Номер: {nft_number}\n"
                    f"🎯 Режим: {nft_info['mode']}\n\n"
                    f"📋 Заблокированные NFT: /myblock"
                )
            else:
                await update.message.reply_text("❌ Этот NFT уже заблокирован")
                
        except ValueError:
            await update.message.reply_text("❌ Номер NFT должен быть числом")

    @staticmethod
    async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Разблокировка NFT"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(
                "❌ Использование: /unblock <номер_nft>\n"
                "📋 Посмотреть заблокированные: /myblock"
            )
            return
        
        try:
            nft_number = int(context.args[0])
            nft_info = NFTManagementHandler.get_nft_by_number(nft_number)
            
            if not nft_info:
                await update.message.reply_text("❌ NFT с таким номером не найден")
                return
            
            if Database.remove_blocked_nft(user_id, nft_number):
                await update.message.reply_text(
                    f"✅ NFT '{nft_info['name']}' разблокирован\n"
                    f"🔢 Номер: {nft_number}\n"
                    f"🎯 Режим: {nft_info['mode']}\n\n"
                    f"📋 Заблокированные NFT: /myblock"
                )
            else:
                await update.message.reply_text("❌ Этот NFT не был заблокирован")
                
        except ValueError:
            await update.message.reply_text("❌ Номер NFT должен быть числом")

    @staticmethod
    async def myblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает заблокированные NFT"""
        user_id = update.effective_user.id
        blocked_nft = Database.get_blocked_nft(user_id)
        
        # Проверяем откуда пришли
        from_results = context.user_data.get("from_results", False)
        
        if not blocked_nft:
            # Создаем клавиатуру в зависимости от контекста
            if from_results:
                keyboard = [
                    [InlineKeyboardButton("📋 Список всех NFT", callback_data="nft_list")],
                    [InlineKeyboardButton("🔧 Управление блокировками", callback_data="block_management")],
                    [InlineKeyboardButton("🔙 Назад к результатам", callback_data="back_to_results_search")],
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton("📋 Список всех NFT", callback_data="nft_list")],
                    [InlineKeyboardButton("🔧 Управление блокировками", callback_data="block_management")],
                    [InlineKeyboardButton("🔙 Назад к настройкам", callback_data="settings_menu")],
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "📋 У вас нет заблокированных NFT\n"
                    "🔒 Заблокировать NFT: /block <номер>\n"
                    "📖 Список всех NFT: /nft",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    "📋 У вас нет заблокированных NFT\n"
                    "🔒 Заблокировать NFT: /block <номер>\n"
                    "📖 Список всех NFT: /nft"
                )
            return
        
        text = "📋 Ваши заблокированные NFT:\n\n"
        
        for nft_number in blocked_nft:
            nft_info = NFTManagementHandler.get_nft_by_number(nft_number)
            if nft_info:
                text += f"🔒 {nft_number}. {nft_info['name']} ({nft_info['mode']})\n"
        
        text += f"\n🔢 Всего заблокировано: {len(blocked_nft)}\n"
        text += "🔓 Разблокировать: /unblock <номер>"
        
        # Создаем клавиатуру в зависимости от контекста
        if from_results:
            keyboard = [
                [InlineKeyboardButton("📋 Список всех NFT", callback_data="nft_list")],
                [InlineKeyboardButton("🔧 Управление блокировками", callback_data="block_management")],
                [InlineKeyboardButton("🔙 Назад к результатам", callback_data="back_to_results_search")],
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("📋 Список всех NFT", callback_data="nft_list")],
                [InlineKeyboardButton("🔧 Управление блокировками", callback_data="block_management")],
                [InlineKeyboardButton("🔙 Назад к настройкам", callback_data="settings_menu")],
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text)

    @staticmethod
    async def block_nft_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Callback для блокировки NFT"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        nft_id = int(query.data.replace("block_", ""))
        
        if Database.add_blocked_nft(user_id, nft_id):
            # СОБИРАЕМ СТАТИСТИКУ
            Database.update_user_stats(user_id, "nft_blocked")
            await query.answer(f"✅ NFT #{nft_id} заблокирован", show_alert=True)
        else:
            await query.answer(f"❌ NFT #{nft_id} уже заблокирован", show_alert=True)