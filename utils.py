import re
import aiohttp
import logging
import urllib.parse
from telegram import Update, ChatMember, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

from bot_config import HEADERS, HTTP_TIMEOUT, BANNED_USERNAMES, REQUIRED_CHANNEL_ID, REQUIRED_CHANNEL_LINK

logger = logging.getLogger(__name__)

class Utils:
    @staticmethod
    async def check_subscription(user_id, context):
        """Проверяет, подписан ли пользователь на канал"""
        try:
            member = await context.bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
            return member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
        except Exception as e:
            logger.error(f"Ошибка проверки подписки для {user_id}: {e}")
            return False

    @staticmethod
    async def require_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет сообщение с требованием подписаться"""
        text = "📢 *Для использования бота подпишитесь на наш новостной канал!*\n\n"
        text += "Подписывайтесь, чтобы быть в курсе обновлений и новых функций парсера.\n\n"
        text += "После подписки нажмите кнопку '✅ Я подписался' для продолжения."
        
        keyboard = [
            [InlineKeyboardButton("📢 Подписаться на канал", url=REQUIRED_CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            if update.callback_query:
                # Пытаемся отредактировать сообщение
                try:
                    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                except:
                    # Если не получилось, отправляем новое
                    await update.callback_query.message.delete()
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о подписке: {e}")

    @staticmethod
    async def safe_send_message(context, chat_id, text, reply_markup=None, parse_mode=None):
        try:
            return await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.warning(f"Ошибка отправки сообщения: {e}")
            return None

    @staticmethod
    async def safe_send_photo(context, chat_id, photo, caption=None, reply_markup=None, parse_mode=None):
        try:
            if caption and len(caption) > 1024:
                caption = caption[:1021] + "..."
            
            return await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.warning(f"Ошибка отправки фото: {e}")
            if caption:
                return await Utils.safe_send_message(context, chat_id, caption, reply_markup, parse_mode)
            return None

    @staticmethod
    async def safe_edit_message(message, text, reply_markup=None, parse_mode=None):
        try:
            await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return True
        except BadRequest as e:
            if "Message is not modified" not in str(e) and "Message to edit not found" not in str(e):
                logger.warning(f"Ошибка редактирования: {e}")
            return False
        except Exception as e:
            logger.warning(f"Ошибка редактирования: {e}")
            return False

    @staticmethod
    def extract_real_username(html: str) -> str:
        try:
            username_match = re.search(r't\.me/([a-zA-Z0-9_]{5,32})(?![a-zA-Z0-9_])', html)
            if username_match:
                username = username_match.group(1)
                banned_list = ['telegram', 'telegramgifts', 'giftspreview', 'preview', 'm'] + BANNED_USERNAMES
                if username.lower() not in [u.lower().replace('@', '') for u in banned_list]:
                    return f"@{username}"
            
            table_match = re.search(r'<table[^>]*class=[\'"]tgme_gift_table[\'"][^>]*>(.*?)</table>', html, re.DOTALL)
            if table_match:
                table_content = table_match.group(1)
                owner_match = re.search(r'@([a-zA-Z0-9_]{5,32})', table_content)
                if owner_match:
                    username = owner_match.group(1)
                    banned_list = ['telegram', 'telegramgifts'] + BANNED_USERNAMES
                    if username.lower() not in [u.lower() for u in banned_list]:
                        return f"@{username}"
            
            return ""
        except Exception as e:
            logger.error(f"Ошибка извлечения username: {e}")
            return ""

    @staticmethod
    def create_message_link(username: str, template_text: str) -> str:
        encoded_text = urllib.parse.quote(template_text)
        
        if username.startswith('@'):
            username = username[1:]
        
        return f"https://t.me/{username}?text={encoded_text}"

    @staticmethod
    async def fetch_html_fast(session: aiohttp.ClientSession, url: str):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as response:
                if response.status == 200:
                    return await response.text()
        except Exception as e:
            logger.warning(f"Ошибка запроса {url}: {e}")
        return None
