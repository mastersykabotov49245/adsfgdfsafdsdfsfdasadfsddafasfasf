# handlers/search.py
import random
import time
import asyncio
import aiohttp
import logging
import math
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from bot_config import SEARCH_MODES, SEARCH_ANIMATION, CONCURRENT_REQUESTS, HTTP_TIMEOUT, HEADERS, EXCLUDED_NFT
from database import Database
from utils import Utils
from globals import user_modes, user_cooldowns, verified_nft_cache, user_templates, user_search_limits

logger = logging.getLogger(__name__)

class SearchHandler:
    @staticmethod
    def get_user_results_interface(user_id):
        user_settings = Database.get_user_settings(user_id)
        interface = user_settings.get("results_interface", "list")
        logger.info(f"📊 Интерфейс пользователя {user_id}: {interface}")
        return interface

    @staticmethod
    async def show_single_result(update: Update, context: ContextTypes.DEFAULT_TYPE, index=0):
        user_id = update.effective_user.id
        found_users = context.user_data.get("found_users", [])
        
        logger.info(f"👤 ОДИНОЧНЫЙ РЕЗУЛЬТАТ: Пользователь {user_id}, индекс {index}, всего {len(found_users)}")
        
        if not found_users:
            keyboard = [
                [InlineKeyboardButton("🔄 Искать снова", callback_data="search")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text="❌ Нет результатов для отображения",
                    reply_markup=reply_markup
                )
            return
        
        if index >= len(found_users):
            index = len(found_users) - 1
        if index < 0:
            index = 0
        
        url, username = found_users[index]
        
        template_text = "Здравствуйте, заинтересовался вашим NFT подарком, могу купить у вас его."
        if user_id in user_templates:
            template_text = user_templates[user_id]["text"]
        else:
            templates = Database.get_user_templates(user_id)
            if templates:
                template_text = templates[0]["text"]
        
        message_link = Utils.create_message_link(username, template_text)
        
        keyboard = []
        
        pagination_buttons = []
        if index > 0:
            pagination_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"single_result_{index-1}"))
        
        pagination_buttons.append(InlineKeyboardButton(f"{index+1}/{len(found_users)}", callback_data="current_page"))
        
        if index < len(found_users) - 1:
            pagination_buttons.append(InlineKeyboardButton("➡️", callback_data=f"single_result_{index+1}"))
        
        if pagination_buttons:
            keyboard.append(pagination_buttons)
        
        keyboard.append([InlineKeyboardButton(f"{username}", url=f"https://t.me/{username[1:]}" if username.startswith('@') else f"https://t.me/{username}")])
        keyboard.append([InlineKeyboardButton("Написать", url=message_link)])
        keyboard.append([InlineKeyboardButton("🔄 Искать снова", callback_data="search")])
        keyboard.append([InlineKeyboardButton("📱 Главное меню", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            try:
                # Редактируем медиа сообщение
                from telegram import InputMediaPhoto
                
                # Создаем новое медиа с тем же message_id
                media = InputMediaPhoto(media=url)
                
                try:
                    # Пытаемся отредактировать медиа
                    await update.callback_query.edit_message_media(
                        media=media,
                        reply_markup=reply_markup
                    )
                    logger.info(f"✅ Успешно отредактировали медиа для индекса {index}")
                except Exception as media_error:
                    logger.warning(f"⚠️ Не удалось отредактировать медиа: {media_error}")
                    # Если не получилось отредактировать медиа, удаляем и отправляем новое
                    try:
                        await update.callback_query.message.delete()
                    except:
                        pass
                    
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=url,
                        reply_markup=reply_markup
                    )
                    
            except Exception as e:
                logger.error(f"❌ Ошибка при смене NFT: {e}")
                # Резервный вариант
                try:
                    await update.callback_query.message.delete()
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=url,
                        reply_markup=reply_markup
                    )
                except Exception as backup_error:
                    logger.error(f"❌ Резервный вариант тоже не сработал: {backup_error}")
                    await update.callback_query.answer("Ошибка при загрузке NFT", show_alert=True)
        else:
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=url,
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Ошибка отправки фото: {e}")
                await update.message.reply_text(
                    text=f"🎯 NFT #{index+1}\n👤 {username}",
                    reply_markup=reply_markup
                )

    @staticmethod
    async def handle_single_result_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("single_result_"):
            try:
                index = int(data.replace("single_result_", ""))
                await SearchHandler.show_single_result(update, context, index)
            except ValueError:
                await query.answer("❌ Ошибка переключения", show_alert=True)
        elif data == "current_page":
            await query.answer(f"Текущий пользователь", show_alert=False)

    @staticmethod
    async def show_mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if query:
            await query.answer()
        
        from_results = context.user_data.get("from_results", False)
        
        is_from_random_search = False
        if query:
            message_text = query.message.text
            is_from_random_search = message_text and "Выберите режим поиска" in message_text
        
        text = "🎯 *Выберите режим поиска:*\n\n"
        
        for mode_key, mode_data in SEARCH_MODES.items():
            text += f"{mode_data['name']}\n"
            text += f"{mode_data['description']}\n\n"
        
        keyboard = []
        for mode_key in SEARCH_MODES.keys():
            mode_name = SEARCH_MODES[mode_key]["name"]
            keyboard.append([InlineKeyboardButton(mode_name, callback_data=f"mode_{mode_key}")])
        
        if from_results:
            keyboard.append([InlineKeyboardButton("🔙 Назад к результатам", callback_data="back_to_results_search")])
        elif is_from_random_search:
            keyboard.append([InlineKeyboardButton("🔙 Назад к выбору типа", callback_data="search_type_selection")])
            keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")])
        else:
            keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def random_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        from globals import user_modes
        
        if user_id not in user_modes:
            await update.message.reply_text(
                "❌ *Сначала выберите режим поиска!*\nИспользуйте команду /mode",
                parse_mode='Markdown'
            )
            return
        
        await SearchHandler.random_nft_search(update, context)

    @staticmethod
    async def mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        mode_key = query.data.replace("mode_", "")
        
        if mode_key not in SEARCH_MODES:
            await query.answer("❌ Неизвестный режим")
            return
        
        user_modes[user_id] = mode_key
        mode_name = SEARCH_MODES[mode_key]["name"]
        
        logger.info(f"🎯 Пользователь {user_id} выбрал режим: {mode_key} ({mode_name})")
        
        from_results = context.user_data.get("from_results", False)
        
        message_text = query.message.text
        is_from_search_type = message_text and "Выберите тип поиска" in message_text
        is_from_random_search = message_text and "Выберите режим поиска" in message_text
        
        templates = Database.get_user_templates(user_id)
        
        if templates:
            text = f"✅ *Выбран режим:* {mode_name}\n\n"
            text += "📝 *Теперь выберите шаблон сообщения:*\n\n"
            
            keyboard = []
            for i, template in enumerate(templates):
                keyboard.append([
                    InlineKeyboardButton(
                        f"{i+1}. {template['name']}", 
                        callback_data=f"select_template_{i}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("🔍 Начать поиск со стандартным", callback_data="search_with_default")])
            
            if from_results:
                keyboard.append([InlineKeyboardButton("🔙 Назад к режимам", callback_data="change_mode_from_results")])
                keyboard.append([InlineKeyboardButton("🔙 Назад к результатам", callback_data="back_to_results_search")])
            elif is_from_search_type:
                keyboard.append([InlineKeyboardButton("🔙 Назад к режимам", callback_data="random_search")])
                keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")])
            elif is_from_random_search:
                keyboard.append([InlineKeyboardButton("🔙 Назад к режимам", callback_data="change_mode")])
                keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")])
            else:
                keyboard.append([InlineKeyboardButton("🔙 Назад к режимам", callback_data="change_mode")])
                keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            user_templates[user_id] = {"name": "Стандартный", "text": "Здравствуйте, заинтересовался вашим NFT подарком, могу купить у вас его."}
            
            text = f"✅ *Выбран режим:* {mode_name}\n"
            text += f"📝 *Шаблон:* Стандартный\n\n"
            text += "Нажмите кнопку ниже чтобы начать поиск:"
            
            keyboard = [
                [InlineKeyboardButton("🔍 Начать поиск NFT", callback_data="search")],
            ]
            
            if from_results:
                keyboard.append([InlineKeyboardButton("🔙 Назад к режимам", callback_data="change_mode_from_results")])
                keyboard.append([InlineKeyboardButton("🔙 Назад к результатам", callback_data="back_to_results_search")])
            elif is_from_search_type:
                keyboard.append([InlineKeyboardButton("🔙 Назад к режимам", callback_data="random_search")])
                keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")])
            elif is_from_random_search:
                keyboard.append([InlineKeyboardButton("🔙 Назад к режимам", callback_data="change_mode")])
                keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")])
            else:
                keyboard.append([InlineKeyboardButton("🔙 Назад к режимам", callback_data="change_mode")])
                keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def search_with_default_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        user_templates[user_id] = {"name": "Стандартный", "text": "Здравствуйте, заинтересовался вашим NFT подарком, могу купить у вас его."}
        
        await SearchHandler.random_nft_search(update, context)

    @staticmethod
    def is_cooldown(user_id: int):
        """Проверяет кулдаун для поиска (60 секунд)"""
        now = time.time()
        if user_id in user_cooldowns:
            last_time = user_cooldowns[user_id]
            if now - last_time < 60:
                remaining = 60 - int(now - last_time)
                logger.info(f"⏰ Кулдаун для пользователя {user_id}: осталось {remaining} сек")
                return True, remaining
        user_cooldowns[user_id] = now
        logger.info(f"⏰ Нет кулдауна для пользователя {user_id}, устанавливаем время {now}")
        return False, 0

    @staticmethod
    def get_filtered_collections(user_id, mode_name=None):
        from handlers.nft_management import NFTManagementHandler
        blocked_nft = Database.get_blocked_nft(user_id)
        filtered_collections = []
        
        if mode_name and mode_name in SEARCH_MODES:
            modes_to_check = {mode_name: SEARCH_MODES[mode_name]}
        else:
            modes_to_check = SEARCH_MODES
        
        for current_mode_name, mode_data in modes_to_check.items():
            for collection in mode_data["collections"]:
                if collection["name"] not in EXCLUDED_NFT:
                    nft_info = NFTManagementHandler.get_nft_by_name_and_mode(collection["name"], current_mode_name)
                    if nft_info and nft_info["number"] not in blocked_nft:
                        filtered_collections.append(collection)
        
        logger.info(f"📚 Фильтрация коллекций: найдено {len(filtered_collections)} доступных коллекций")
        return filtered_collections

    @staticmethod
    async def fetch_random_nft_fast(session: aiohttp.ClientSession, collection: dict):
        collection_name = collection["name"]
        min_id, max_id = collection["id_range"]
        
        if min_id == max_id:
            random_id = random.randint(max(1, min_id - 1000), min_id + 1000)
        else:
            random_id = random.randint(min_id, max_id)
        
        url = f"https://t.me/nft/{collection_name}-{random_id}"
        
        if url in verified_nft_cache:
            return verified_nft_cache[url]
        
        try:
            html = await Utils.fetch_html_fast(session, url)
            if not html:
                verified_nft_cache[url] = None
                return None
            
            if "not be found" in html or "tgme_page_error_title" in html:
                verified_nft_cache[url] = None
                return None
            
            username = Utils.extract_real_username(html)
            
            if not username or username == "@Telegram" or username.lower() == "@m":
                verified_nft_cache[url] = None
                return None
                
            result = (url, username)
            verified_nft_cache[url] = result
            return result
            
        except Exception as e:
            logger.warning(f"Ошибка при поиске NFT {url}: {e}")
        
        verified_nft_cache[url] = None
        return None

    @staticmethod
    def get_user_search_limit(user_id):
        from globals import user_search_limits
        
        if user_id in user_search_limits:
            limit = user_search_limits[user_id]
            logger.info(f"🔢 Лимит поиска пользователя {user_id} из кэша: {limit}")
            return limit
        
        user_settings = Database.get_user_settings(user_id)
        limit = user_settings.get("search_limit", 15)
        
        user_search_limits[user_id] = limit
        logger.info(f"🔢 Лимит поиска пользователя {user_id} из БД: {limit}")
        return limit

    @staticmethod
    async def random_nft_search(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
        user_id = update.effective_user.id
        
        logger.info(f"🎯 НАЧАЛО ПОИСКА: Пользователь {user_id}, страница {page}")
        logger.info(f"🎯 Текущий режим пользователя: {user_modes.get(user_id, 'НЕТ')}")
        logger.info(f"🎯 context.user_data: {context.user_data}")
        
        # Проверяем, есть ли выбранный режим
        if user_id not in user_modes:
            logger.warning(f"❌ У пользователя {user_id} нет режима в user_modes!")
            # Если режим не выбран, показываем выбор режима
            if update.callback_query:
                await update.callback_query.answer("❌ Сначала выберите режим!", show_alert=True)
                await SearchHandler.show_mode_selection(update, context)
            else:
                await update.message.reply_text(
                    "❌ *Сначала выберите режим поиска!*",
                    parse_mode='Markdown'
                )
                await SearchHandler.show_mode_selection(update, context)
            return
        
        selected_mode = user_modes[user_id]
        mode_info = SEARCH_MODES[selected_mode]
        
        logger.info(f"🎯 Выбран режим: {selected_mode} ({mode_info['name']})")
        
        # Получаем выбранный шаблон
        template_text = "Здравствуйте, заинтересовался вашим NFT подарком, могу купить у вас его."
        template_name = "Стандартный"
        
        if user_id in user_templates:
            template_data = user_templates[user_id]
            template_text = template_data.get("text", "")
            template_name = template_data.get("name", "Стандартный")
            logger.info(f"📝 Используется пользовательский шаблон: {template_name}")
        else:
            templates = Database.get_user_templates(user_id)
            if templates:
                template_text = templates[0].get("text", "")
                template_name = templates[0].get("name", "Стандартный")
                user_templates[user_id] = {"name": template_name, "text": template_text}
                logger.info(f"📝 Используется шаблон из БД: {template_name}")
            else:
                logger.info(f"📝 Используется стандартный шаблон")
        
        search_limit = SearchHandler.get_user_search_limit(user_id)
        logger.info(f"🔢 Лимит поиска: {search_limit}")
        
        # УДАЛЯЕМ предыдущее сообщение с результатами, если это callback_query
        if update.callback_query:
            try:
                # Отвечаем на callback_query, чтобы убрать "часики"
                await update.callback_query.answer()
                
                # Получаем сообщение с результатами поиска
                results_message = update.callback_query.message
                
                # Если это поиск снова, удаляем старое сообщение с результатами
                if update.callback_query.data == "search":
                    try:
                        await results_message.delete()
                        logger.info(f"🗑️ Удалили старое сообщение с результатами для пользователя {user_id}")
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось удалить старое сообщение: {e}")
                    
                    # Сохраняем chat_id для отправки нового сообщения
                    chat_id = results_message.chat_id
                    
                    # Отправляем новое сообщение с поиском
                    status_message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"🎯 Режим: {mode_info['name']}\n"
                            f"📝 Шаблон: {template_name}\n"
                            f"🔢 Количество: {search_limit}\n\n"
                            f"{SEARCH_ANIMATION[0]}\n✅ Найдено: 0/{search_limit}",
                        parse_mode='Markdown'
                    )
                else:
                    # Если не "искать снова", то просто редактируем существующее сообщение
                    try:
                        await update.callback_query.edit_message_text(
                            text=f"🎯 Режим: {mode_info['name']}\n"
                                f"📝 Шаблон: {template_name}\n"
                                f"🔢 Количество: {search_limit}\n\n"
                                f"{SEARCH_ANIMATION[0]}\n✅ Найдено: 0/{search_limit}",
                            parse_mode='Markdown'
                        )
                        status_message = update.callback_query.message
                    except Exception as e:
                        logger.error(f"❌ Ошибка редактирования сообщения: {e}")
                        # Если не удалось отредактировать, отправляем новое сообщение
                        status_message = await update.callback_query.message.reply_text(
                            text=f"🎯 Режим: {mode_info['name']}\n"
                                f"📝 Шаблон: {template_name}\n"
                                f"🔢 Количество: {search_limit}\n\n"
                                f"{SEARCH_ANIMATION[0]}\n✅ Найдено: 0/{search_limit}",
                            parse_mode='Markdown'
                        )
            except Exception as e:
                logger.error(f"❌ Ошибка обработки callback_query: {e}")
                # Если произошла ошибка, просто отправляем новое сообщение
                if update.callback_query:
                    status_message = await update.callback_query.message.reply_text(
                        text=f"🎯 Режим: {mode_info['name']}\n"
                            f"📝 Шаблон: {template_name}\n"
                            f"🔢 Количество: {search_limit}\n\n"
                            f"{SEARCH_ANIMATION[0]}\n✅ Найдено: 0/{search_limit}",
                        parse_mode='Markdown'
                    )
        else:
            # Если это не callback_query (команда), просто отправляем новое сообщение
            logger.info(f"✏️ Отправляем новое сообщение")
            status_message = await update.message.reply_text(
                text=f"🎯 Режим: {mode_info['name']}\n"
                    f"📝 Шаблон: {template_name}\n"
                    f"🔢 Количество: {search_limit}\n\n"
                    f"{SEARCH_ANIMATION[0]}\n✅ Найдено: 0/{search_limit}",
                parse_mode='Markdown'
            )
        
        start_time = time.time()
        found_nfts = []
        
        logger.info(f"🚀 Начинаем поиск NFT...")
        
        try:
            connector = aiohttp.TCPConnector(limit=CONCURRENT_REQUESTS, ssl=False)
            
            async with aiohttp.ClientSession(
                headers=HEADERS,
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
            ) as session:
                
                async def run_animation():
                    frame = 0
                    while len(found_nfts) < search_limit:
                        animation_frame = SEARCH_ANIMATION[frame % len(SEARCH_ANIMATION)]
                        progress = f"✅ Найдено: {len(found_nfts)}/{search_limit}"
                        text = f"🎯 Режим: {mode_info['name']}\n📝 Шаблон: {template_name}\n🔢 Количество: {search_limit}\n\n{animation_frame}\n{progress}"
                        
                        try:
                            await status_message.edit_text(text=text, parse_mode='Markdown')
                        except Exception as e:
                            logger.warning(f"Ошибка обновления анимации: {e}")
                        
                        frame += 1
                        await asyncio.sleep(0.5)
                
                animation_task = asyncio.create_task(run_animation())
                
                collections = SearchHandler.get_filtered_collections(user_id, selected_mode)
                logger.info(f"📚 Коллекций для поиска: {len(collections)}")
                
                if not collections:
                    logger.warning(f"❌ Нет доступных коллекций для поиска!")
                    if animation_task:
                        try:
                            animation_task.cancel()
                            await animation_task
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            logger.error(f"Ошибка при отмене анимации: {e}")
                    
                    # Удаляем сообщение с поиском перед показом ошибки
                    try:
                        await status_message.delete()
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось удалить сообщение с поиском: {e}")
                    
                    # Отправляем сообщение об ошибке
                    keyboard = [
                        [InlineKeyboardButton("🔄 Искать снова", callback_data="search")],
                        [InlineKeyboardButton("📱 Главное меню", callback_data="back_to_menu")],
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="❌ Все NFT в этом режиме заблокированы!\nИспользуйте /myblock для просмотра и /unblock для разблокировки.",
                        reply_markup=reply_markup
                    )
                    return
                
                for wave in range(15):
                    if len(found_nfts) >= search_limit:
                        logger.info(f"✅ Достигнут лимит поиска: {len(found_nfts)}/{search_limit}")
                        break
                        
                    tasks = []
                    for _ in range(min(80, (search_limit - len(found_nfts)) * 5)):
                        random_collection = random.choice(collections)
                        task = SearchHandler.fetch_random_nft_fast(session, random_collection)
                        tasks.append(task)
                    
                    logger.info(f"🌊 Волна {wave+1}: создано {len(tasks)} задач")
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, tuple) and len(result) == 2:
                            url, username = result
                            if url and username:
                                if not any(nft[1] == username for nft in found_nfts):
                                    found_nfts.append((url, username))
                                    logger.debug(f"✅ Найден NFT: {username}")
                                    if len(found_nfts) >= search_limit:
                                        break
                    
                    await asyncio.sleep(0.1)

            if animation_task:
                logger.info(f"⏹ Останавливаем анимацию")
                try:
                    animation_task.cancel()
                    await animation_task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Ошибка при отмене анимации: {e}")
            
            search_time = int(time.time() - start_time)
            logger.info(f"⏱ Поиск завершен за {search_time} сек, найдено {len(found_nfts)} NFT")
            
            Database.update_user_stats(user_id, "search")
            Database.update_user_stats(user_id, "found", len(found_nfts))
            Database.update_user_stats(user_id, "active_day")
            Database.update_user_stats(user_id, "search", len(found_nfts), selected_mode)

            Database.update_bot_stats("search_completed", user_id, selected_mode)
            
            context.user_data["found_users"] = found_nfts
            context.user_data["current_page"] = page
            context.user_data["search_limit"] = search_limit
            
            logger.info(f"📊 Сохраняем результаты в context.user_data: найдено {len(found_nfts)}")
            
            # УДАЛЯЕМ сообщение с анимацией поиска после завершения
            try:
                if 'status_message' in locals() and status_message:
                    await status_message.delete()
                    logger.info(f"🗑️ Удалили сообщение с анимацией поиска для пользователя {user_id}")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось удалить сообщение с анимацией: {e}")
            
            await SearchHandler.show_search_results_page(update, context, page=page)
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}", exc_info=True)
            
            # УДАЛЯЕМ сообщение с анимацией поиска при ошибке
            try:
                if 'status_message' in locals() and status_message:
                    await status_message.delete()
            except Exception as delete_error:
                logger.warning(f"⚠️ Не удалось удалить сообщение с анимацией при ошибке: {delete_error}")
            
            keyboard = [
                [InlineKeyboardButton("🔄 Искать снова", callback_data="search")],
                [InlineKeyboardButton("📱 Главное меню", callback_data="back_to_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Ошибка при поиске NFT\nПопробуйте еще раз!",
                reply_markup=reply_markup
            )

    @staticmethod
    async def show_search_results_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
        user_id = update.effective_user.id
        found_users = context.user_data.get("found_users", [])
        search_limit = context.user_data.get("search_limit", 15)
        
        logger.info(f"📄 ПОКАЗ РЕЗУЛЬТАТОВ: Пользователь {user_id}, страница {page}")
        logger.info(f"📄 Найдено пользователей: {len(found_users)}")
        logger.info(f"📄 Лимит поиска: {search_limit}")
        logger.info(f"📄 context.user_data keys: {list(context.user_data.keys())}")
        
        if not found_users:
            logger.warning(f"❌ Нет результатов для отображения у пользователя {user_id}")
            keyboard = [
                [InlineKeyboardButton("🔄 Искать снова", callback_data="search")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text="❌ Нет результатов для отображения",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    text="❌ Нет результатов для отображения",
                    reply_markup=reply_markup
                )
            return
        
        interface_type = SearchHandler.get_user_results_interface(user_id)
        logger.info(f"📄 Тип интерфейса: {interface_type}")
        
        if interface_type == "single":
            logger.info(f"📄 Показываем одиночный интерфейс, индекс: {page}")
            await SearchHandler.show_single_result(update, context, page)
            return
        
        # ДОБАВЛЕНО: Код для отображения спискового режима
        template_text = "Здравствуйте, заинтересовался вашим NFT подарком, могу купить у вас его."
        if user_id in user_templates:
            template_text = user_templates[user_id]["text"]
        else:
            templates = Database.get_user_templates(user_id)
            if templates:
                template_text = templates[0]["text"]
        
        # Получаем текущий режим
        from globals import user_modes
        from bot_config import SEARCH_MODES
        mode_name = "Неизвестно"
        if user_id in user_modes:
            mode_key = user_modes[user_id]
            mode_name = SEARCH_MODES[mode_key]["name"]
        
        items_per_page = 10
        total_pages = math.ceil(len(found_users) / items_per_page)
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        current_users = found_users[start_idx:end_idx]
        
        response_text = f"🎯 *Результаты поиска*\n"
        response_text += f"📊 Найдено: {len(found_users)} пользователей\n"
        response_text += f"🎯 Режим: {mode_name}\n\n"
        
        for i, (url, username) in enumerate(current_users, start_idx + 1):
            message_link = Utils.create_message_link(username, template_text)
            response_text += f'{i:2d}. {username} | <a href="{message_link}">Написать</a>\n'
        
        response_text += f"\n📊 Страница {page + 1}/{total_pages}"
        
        keyboard = []
        
        # Кнопки пагинации
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"random_results_page_{page-1}"))
        
        pagination_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="current_page"))
        
        if page < total_pages - 1:
            pagination_buttons.append(InlineKeyboardButton("➡️ Вперед", callback_data=f"random_results_page_{page+1}"))
        
        if pagination_buttons:
            keyboard.append(pagination_buttons)
        
        # Основные кнопки
        keyboard.extend([
            [InlineKeyboardButton("🔄 Искать снова", callback_data="search")],
            [InlineKeyboardButton("📱 Главное меню", callback_data="back_to_menu")],
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # ВАЖНОЕ ИСПРАВЛЕНИЕ: Не пытаемся редактировать сообщение, а отправляем новое
        try:
            # Всегда отправляем новое сообщение с результатами
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=response_text,
                reply_markup=reply_markup,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            # Пытаемся удалить старое сообщение с поиском (если оно еще есть)
            if update.callback_query:
                try:
                    await update.callback_query.message.delete()
                except:
                    pass  # Если не удалось удалить, это нормально
                    
        except Exception as e:
            logger.error(f"❌ Ошибка отправки результатов: {e}")
            await update.callback_query.answer("❌ Ошибка при показе результатов", show_alert=True)

    @staticmethod
    async def handle_results_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        logger.info(f"📄 ОБРАБОТКА СТРАНИЦЫ: callback_data: {data}")
        
        if data.startswith("random_results_page_"):
            try:
                page = int(data.replace("random_results_page_", ""))
                logger.info(f"📄 Переключаемся на страницу: {page}")
                await SearchHandler.show_search_results_page(update, context, page)
            except ValueError:
                logger.error(f"❌ Ошибка преобразования страницы: {data}")
                await query.answer("❌ Ошибка переключения страницы", show_alert=True)
        elif data == "current_page":
            await query.answer(f"Текущая страница", show_alert=False)

    @staticmethod
    async def show_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await SearchHandler.show_search_results_page(update, context, page=0)