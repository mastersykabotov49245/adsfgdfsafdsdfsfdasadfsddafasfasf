import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler

from bot_config import ADMINS
from database import Database

logger = logging.getLogger(__name__)

class AdminHandler:
    @staticmethod
    async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.from_user.id not in ADMINS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        
        text = "👨‍💻 *Админ панель*\n\nВыберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("📊 Расширенная статистика", callback_data="admin_extended_stats")],
            [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast_info")],
            [InlineKeyboardButton("🧹 Очистить кэш", callback_data="admin_clear_cache")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.from_user.id not in ADMINS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        
        users = Database.load_users()
        total_users = len(users)
        
        from globals import user_modes, user_cooldowns, verified_nft_cache
        easy_count = len([uid for uid, mode in user_modes.items() if mode == "easy"])
        medium_count = len([uid for uid, mode in user_modes.items() if mode == "medium"])
        hard_count = len([uid for uid, mode in user_modes.items() if mode == "hard"])
        
        text = f"""📊 *Статистика бота*

👥 Всего пользователей: {total_users}
🎯 Активные режимы:
   🟢 Легкий: {easy_count}
   🟡 Средний: {medium_count}  
   🔴 Жирный: {hard_count}

💾 Кэш NFT: {len(verified_nft_cache)}
⏰ Кулдауны: {len(user_cooldowns)}"""

        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def admin_extended_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.from_user.id not in ADMINS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        
        admin_stats = Database.get_admin_stats()
        
        text = f"""📊 *Расширенная статистика*

👥 Всего пользователей: {admin_stats['total_users']}

📅 *За сегодня:*
   🔍 Поисков: {admin_stats['daily_searches']}
   👤 Уникальных пользователей: {admin_stats['daily_users']}

📅 *За неделю:*
   🔍 Поисков: {admin_stats['weekly_searches']}
   👤 Уникальных пользователей: {admin_stats['weekly_users']}

🎯 *Статистика по режимам поиска:*
   🟢 Легкий режим: {admin_stats['search_modes_stats']['easy']}
   🟡 Средний режим: {admin_stats['search_modes_stats']['medium']}
   🔴 Жирный режим: {admin_stats['search_modes_stats']['hard']}
   👩 Поиск девушек: {admin_stats['search_modes_stats']['girls']}"""

        keyboard = [
            [InlineKeyboardButton("📊 Простая статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def admin_clear_cache_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.from_user.id not in ADMINS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        
        from globals import verified_nft_cache, user_cooldowns
        cache_size = len(verified_nft_cache)
        cooldown_size = len(user_cooldowns)
        
        verified_nft_cache.clear()
        user_cooldowns.clear()
        
        text = f"🧹 *Кэш очищен!*\n\n✅ Кэш NFT: {cache_size} → 0\n✅ Кулдауны: {cooldown_size} → 0"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def admin_broadcast_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.from_user.id not in ADMINS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        
        text = """📢 *Рассылка сообщений*

Для рассылки используйте команды:

📝 *Текстовая рассылка:*
`/broadcast Ваш текст сообщения`

🖼️ *Рассылка с фото:*
Отправьте фото с подписью:
`/broadcast Ваш текст`

✅ *Поддерживаются:*
• Текст (с HTML-разметкой и ссылками)
• Фото с текстом
• Видео с текстом
• Документы с текстом

👥 Сообщение будет отправлено всем пользователям бота."""

        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if user_id not in ADMINS:
            await update.message.reply_text("❌ Доступ запрещен!")
            return
        
        users = Database.load_users()
        total_users = len(users)
        
        if total_users == 0:
            await update.message.reply_text("❌ Нет пользователей для рассылки")
            return
        
        if update.message.text and update.message.text.startswith('/broadcast'):
            message_text = update.message.text.replace('/broadcast', '').strip()
            
            if not message_text:
                await update.message.reply_text("❌ Введите текст для рассылки:\n`/broadcast Ваш текст`", parse_mode='Markdown')
                return
            
            status_msg = await update.message.reply_text(f"📢 Начинаю текстовую рассылку для {total_users} пользователей...")
            
            success_count = 0
            fail_count = 0
            
            for i, user_key in enumerate(users.keys()):
                try:
                    await context.bot.send_message(
                        chat_id=int(user_key),
                        text=message_text,
                        parse_mode='HTML',
                        disable_web_page_preview=False
                    )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Ошибка отправки пользователю {user_key}: {e}")
                    fail_count += 1
                
                if (i + 1) % 10 == 0:
                    try:
                        await status_msg.edit_text(f"📢 Рассылка...\n✅ Успешно: {success_count}\n❌ Ошибок: {fail_count}")
                    except:
                        pass
                
                await asyncio.sleep(0.1)
            
            await status_msg.edit_text(f"✅ Рассылка завершена!\n✅ Успешно: {success_count}\n❌ Ошибок: {fail_count}")
            
        else:
            await update.message.reply_text("❌ Используйте команду /broadcast с текстом")

    @staticmethod
    async def quick_broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if user_id not in ADMINS:
            await update.message.reply_text("❌ Доступ запрещен!")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: `/bc Ваш текст`", parse_mode='Markdown')
            return
        
        users = Database.load_users()
        total_users = len(users)
        
        if total_users == 0:
            await update.message.reply_text("❌ Нет пользователей для рассылки")
            return
        
        message_text = ' '.join(context.args)
        
        status_msg = await update.message.reply_text(f"📢 Начинаю быструю рассылку для {total_users} пользователей...")
        
        success_count = 0
        fail_count = 0
        
        for i, user_key in enumerate(users.keys()):
            try:
                await context.bot.send_message(
                    chat_id=int(user_key),
                    text=message_text,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Ошибка отправки пользователю {user_key}: {e}")
                fail_count += 1
            
            if (i + 1) % 10 == 0:
                try:
                    await status_msg.edit_text(f"📢 Рассылка...\n✅ Успешно: {success_count}\n❌ Ошибок: {fail_count}")
                except:
                    pass
            
            await asyncio.sleep(0.1)
        
        await status_msg.edit_text(f"✅ Рассылка завершена!\n✅ Успешно: {success_count}\n❌ Ошибок: {fail_count}")

    @staticmethod
    async def handle_media_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if user_id not in ADMINS:
            return
        
        if not update.message.caption or not update.message.caption.startswith('/broadcast'):
            return
        
        users = Database.load_users()
        total_users = len(users)
        
        if total_users == 0:
            await update.message.reply_text("❌ Нет пользователей для рассылки")
            return
        
        caption = update.message.caption.replace('/broadcast', '').strip()
        
        status_msg = await update.message.reply_text(f"📢 Начинаю медиа-рассылку для {total_users} пользователей...")
        
        success_count = 0
        fail_count = 0
        
        for i, user_key in enumerate(users.keys()):
            try:
                if update.message.photo:
                    photo = update.message.photo[-1]
                    await context.bot.send_photo(
                        chat_id=int(user_key),
                        photo=photo.file_id,
                        caption=caption,
                        parse_mode='HTML'
                    )
                elif update.message.video:
                    video = update.message.video
                    await context.bot.send_video(
                        chat_id=int(user_key),
                        video=video.file_id,
                        caption=caption,
                        parse_mode='HTML'
                    )
                elif update.message.document:
                    document = update.message.document
                    await context.bot.send_document(
                        chat_id=int(user_key),
                        document=document.file_id,
                        caption=caption,
                        parse_mode='HTML'
                    )
                success_count += 1
            except Exception as e:
                logger.error(f"Ошибка отправки пользователю {user_key}: {e}")
                fail_count += 1
            
            if (i + 1) % 5 == 0:
                try:
                    await status_msg.edit_text(f"📢 Рассылка медиа...\n✅ Успешно: {success_count}\n❌ Ошибок: {fail_count}")
                except:
                    pass
            
            await asyncio.sleep(0.15)
        
        await status_msg.edit_text(f"✅ Медиа-рассылка завершена!\n✅ Успешно: {success_count}\n❌ Ошибок: {fail_count}")