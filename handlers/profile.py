# handlers/profile.py
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from database import Database
from bot_config import SEARCH_MODES
from globals import user_modes, user_templates

logger = logging.getLogger(__name__)

class ProfileHandler:
    @staticmethod
    async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает профиль пользователя"""
        query = update.callback_query
        if query:
            await query.answer()
        
        user = update.effective_user
        user_id = user.id
        
        # Получаем основную информацию
        users_data = Database.load_users()
        user_data = users_data.get(str(user_id), {})
        
        # Получаем статистику
        stats = Database.get_user_stats(user_id)
        
        # Получаем текущий режим
        current_mode = "Не выбран"
        if user_id in user_modes:
            mode_key = user_modes[user_id]
            if mode_key in SEARCH_MODES:
                current_mode = SEARCH_MODES[mode_key]["name"]
        
        # Получаем текущий шаблон
        current_template = "Стандартный"
        if user_id in user_templates:
            current_template = user_templates[user_id]["name"]
        
        # Получаем настройки
        settings = Database.get_user_settings(user_id)
        search_limit = settings.get("search_limit", 15)
        
        # Получаем заблокированные NFT
        blocked_nft = Database.get_blocked_nft(user_id)
        
        # Получаем шаблоны
        templates = Database.get_user_templates(user_id)
        
        # Формируем текст профиля
        username = f"@{user.username}" if user.username else user.first_name
        join_date = user_data.get("join_date", "Неизвестно")
        
        text = f"👤 *ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ*\n\n"
        text += f"🆔 ID: `{user_id}`\n"
        text += f"👤 Имя: {username}\n"
        text += f"📅 Дата регистрации: {join_date}\n"
        text += f"📊 Активных дней: {stats.get('active_days', 1)}\n\n"
        
        text += f"📈 *СТАТИСТИКА*\n"
        text += f"🔍 Всего поисков: {stats.get('searches_count', 0)}\n"
        text += f"👥 Найдено пользователей: {stats.get('total_found', 0)}\n"
        text += f"📝 Создано шаблонов: {len(templates)}\n"
        text += f"🚫 Заблокировано NFT: {len(blocked_nft)}\n\n"
        
        text += f"⚙️ *ТЕКУЩИЕ НАСТРОЙКИ*\n"
        text += f"🎯 Режим: {current_mode}\n"
        text += f"📝 Активный шаблон: {current_template}\n"
        text += f"🔢 Лимит поиска: {search_limit}\n"
        
        if stats.get("last_search"):
            text += f"\n⏰ Последний поиск: {stats['last_search']}"
        
        # Клавиатура
        keyboard = [
            [InlineKeyboardButton("📊 Детальная статистика", callback_data="detailed_stats")],
            [InlineKeyboardButton("📅 Статистика за неделю", callback_data="weekly_stats")],
            [InlineKeyboardButton("⚙️ Быстрые настройки", callback_data="quick_settings")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def detailed_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подробная статистика"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        stats = Database.get_user_stats(user_id)
        
        # Получаем историю поиска
        history = stats.get("search_history", [])
        
        # Вычисляем средние значения
        searches_count = stats.get("searches_count", 0)
        total_found = stats.get("total_found", 0)
        
        avg_per_search = total_found / max(searches_count, 1)
        
        # Находим лучший день
        day_stats = {}
        for entry in history:
            date = entry["date"]
            if date not in day_stats:
                day_stats[date] = {"searches": 0, "found": 0}
            day_stats[date]["searches"] += 1
            day_stats[date]["found"] += entry.get("found_count", 0)
        
        best_day = None
        best_found = 0
        for date, data in day_stats.items():
            if data["found"] > best_found:
                best_found = data["found"]
                best_day = date
        
        text = "📊 *ДЕТАЛЬНАЯ СТАТИСТИКА*\n\n"
        
        text += f"📈 *Основные метрики:*\n"
        text += f"🔍 Всего поисков: {searches_count}\n"
        text += f"👥 Всего найдено: {total_found}\n"
        text += f"📊 Средний результат: {avg_per_search:.1f} пользователей за поиск\n\n"
        
        text += f"🏆 *Рекорды:*\n"
        if best_day:
            text += f"📅 Лучший день: {best_day}\n"
            text += f"👥 Найдено в лучший день: {best_found}\n"
        else:
            text += "📅 Данных о рекордах пока нет\n"
        
        if history:
            text += f"\n📋 *Последние 10 поисков:*\n"
            for i, entry in enumerate(history[-10:][::-1], 1):
                mode_name = entry.get('mode', 'unknown')
                if mode_name in ['easy', 'medium', 'hard']:
                    mode_display = {
                        'easy': '🟢 Легкий',
                        'medium': '🟡 Средний',
                        'hard': '🔴 Жирный'
                    }.get(mode_name, mode_name)
                else:
                    mode_display = mode_name
                text += f"{i}. {entry['date']} - {entry.get('found_count', 0)} пользователей ({mode_display})\n"
        else:
            text += "\n📋 История поисков пока пуста\n"
        
        keyboard = [
            [InlineKeyboardButton("📅 Статистика за неделю", callback_data="weekly_stats")],
            [InlineKeyboardButton("👤 Назад в профиль", callback_data="profile_menu")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def weekly_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика за неделю"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        daily_stats = Database.get_daily_stats(user_id, days=7)
        
        text = "📅 *СТАТИСТИКА ЗА НЕДЕЛЮ*\n\n"
        
        # Сортируем даты в обратном порядке (сначала последние)
        dates = sorted(daily_stats.keys(), reverse=True)
        
        total_searches = 0
        total_found = 0
        
        for date in dates:
            day_data = daily_stats[date]
            searches = day_data["searches"]
            found = day_data["found"]
            
            total_searches += searches
            total_found += found
            
            # Форматируем дату для отображения
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d.%m')
            
            # Эмодзи для активности
            if searches > 0:
                emoji = "🔥" if searches >= 5 else "✅"
                text += f"{emoji} {formatted_date}: {searches} поисков, {found} найдено\n"
            else:
                text += f"⚪ {formatted_date}: нет активности\n"
        
        text += f"\n📈 *Итого за неделю:*\n"
        text += f"🔍 Поисков: {total_searches}\n"
        text += f"👥 Найдено: {total_found}\n"
        
        if total_searches > 0:
            avg_per_day = total_found / total_searches
            text += f"📊 Среднее: {avg_per_day:.1f} на поиск"
        
        keyboard = [
            [InlineKeyboardButton("📊 Детальная статистика", callback_data="detailed_stats")],
            [InlineKeyboardButton("👤 Назад в профиль", callback_data="profile_menu")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def quick_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Быстрые настройки из профиля"""
        query = update.callback_query
        await query.answer()
        
        from handlers.settings import SettingsHandler
        await SettingsHandler.settings_menu(update, context)

    @staticmethod
    async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /profile"""
        await ProfileHandler.profile_callback(update, context)