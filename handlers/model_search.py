# handlers/model_search.py
import logging
import random
import asyncio
import aiohttp
import time
import math
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from bot_config import SEARCH_MODES, EXCLUDED_NFT, CONCURRENT_REQUESTS, HTTP_TIMEOUT, HEADERS, SEARCH_ANIMATION
from database import Database
from utils import Utils
from globals import user_cooldowns, verified_nft_cache, user_templates
from handlers.search import SearchHandler

logger = logging.getLogger(__name__)

class ModelSearchHandler:
    @staticmethod
    def get_user_results_interface(user_id):
        """Получает интерфейс результатов пользователя (совместимость)"""
        from database import Database
        user_settings = Database.get_user_settings(user_id)
        interface = user_settings.get("results_interface", "list")
        return interface
    
    @staticmethod
    async def show_single_model_result(update: Update, context: ContextTypes.DEFAULT_TYPE, index=0):
        """Показывает одиночный результат модели (покадровый режим) - ИСПРАВЛЕНО КАК В SEARCH.PY"""
        user_id = update.effective_user.id
        found_users = context.user_data.get("found_users", [])
        
        logger.info(f"👤 ОДИНОЧНЫЙ РЕЗУЛЬТАТ МОДЕЛЬ: Пользователь {user_id}, индекс {index}, всего {len(found_users)}")
        
        if not found_users:
            keyboard = [
                [InlineKeyboardButton("🔄 Искать снова", callback_data="start_model_search_from_single")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                try:
                    await update.callback_query.edit_message_text(
                        "❌ Нет результатов для отображения",
                        reply_markup=reply_markup
                    )
                except:
                    # Если не можем редактировать, отправляем новое
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
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
        
        # КНОПКИ ПАГИНАЦИИ КАК В SEARCH.PY
        pagination_buttons = []
        if index > 0:
            pagination_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"single_model_{index-1}"))
        
        pagination_buttons.append(InlineKeyboardButton(f"{index+1}/{len(found_users)}", callback_data="current_page_model"))
        
        if index < len(found_users) - 1:
            pagination_buttons.append(InlineKeyboardButton("➡️", callback_data=f"single_model_{index+1}"))
        
        if pagination_buttons:
            keyboard.append(pagination_buttons)
        
        # ОСНОВНЫЕ КНОПКИ
        keyboard.append([InlineKeyboardButton(f"{username}", url=f"https://t.me/{username[1:]}" if username.startswith('@') else f"https://t.me/{username}")])
        keyboard.append([InlineKeyboardButton("Написать", url=message_link)])
        keyboard.append([InlineKeyboardButton("🔄 Искать снова", callback_data="start_model_search_from_single")])
        keyboard.append([InlineKeyboardButton("📱 Главное меню", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            try:
                # ИСПОЛЬЗУЕМ ТОТ ЖЕ ПОДХОД, ЧТО И В SEARCH.PY
                from telegram import InputMediaPhoto
                
                # Создаем медиа для редактирования
                media = InputMediaPhoto(media=url)
                
                try:
                    # Пытаемся отредактировать медиа в существующем сообщении
                    await update.callback_query.edit_message_media(
                        media=media,
                        reply_markup=reply_markup
                    )
                    logger.info(f"✅ Успешно отредактировали медиа для модели {index+1}/{len(found_users)}")
                    
                except Exception as media_error:
                    logger.warning(f"⚠️ Не удалось отредактировать медиа: {media_error}")
                    # Если не получилось отредактировать медиа, пробуем отредактировать текст
                    try:
                        text = f"👤 {index+1}/{len(found_users)}: {username}"
                        await update.callback_query.edit_message_text(
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode='HTML',
                            disable_web_page_preview=False
                        )
                    except Exception as text_error:
                        logger.warning(f"⚠️ Не удалось отредактировать текст: {text_error}")
                        # Если и это не удалось, удаляем и отправляем новое фото
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
                logger.error(f"❌ Ошибка при смене NFT модели: {e}")
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
                    await update.callback_query.answer("Ошибка при загрузке NFT модели", show_alert=True)
        else:
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=url,
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Ошибка отправки фото модели: {e}")
                await update.message.reply_text(
                    text=f"👤 {index+1}/{len(found_users)}: {username}",
                    reply_markup=reply_markup,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
    
    @staticmethod
    async def handle_single_model_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик переключения страниц в покадровом режиме для моделей - ТОЧНО КАК В SEARCH.PY"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("single_model_"):
            try:
                index = int(data.replace("single_model_", ""))
                await ModelSearchHandler.show_single_model_result(update, context, index)
            except ValueError:
                await query.answer("❌ Ошибка переключения", show_alert=True)
        elif data == "current_page_model":
            await query.answer(f"Текущий пользователь", show_alert=False)
    
    @staticmethod
    async def show_search_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает выбор типа поиска"""
        query = update.callback_query
        if query:
            await query.answer()
        
        # Сбрасываем настройки при входе в меню
        if "selected_nft" in context.user_data:
            del context.user_data["selected_nft"]
        if "available_nft" in context.user_data:
            del context.user_data["available_nft"]
        
        text = "🔍 *Выберите тип поиска:*\n\n"
        text += "🎲 *Рандом поиск* - поиск по режимам (легкий, средний, жирный)\n"
        text += "🎯 *Поиск по модели* - точный поиск по конкретным NFT\n"
        text += "👩 *Поиск девушек* - поиск по женским именам\n"
        
        keyboard = [
            [InlineKeyboardButton("🎲 Рандом поиск", callback_data="random_search")],
            [InlineKeyboardButton("🎯 Поиск по модели", callback_data="model_search")],
            [InlineKeyboardButton("👩 Поиск девушек", callback_data="girls_search")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def show_model_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
        """Показывает выбор моделей NFT с пагинацией и поиском"""
        query = update.callback_query
        if query:
            await query.answer()
        
        # Проверяем откуда пришли
        from_results = context.user_data.get("from_results", False)
        
        # Получаем все NFT из всех режимов
        all_nft = []
        for mode_name, mode_data in SEARCH_MODES.items():
            for collection in mode_data["collections"]:
                if collection["name"] not in EXCLUDED_NFT:
                    all_nft.append({
                        "name": collection["name"],
                        "mode": mode_name,
                        "id_range": collection["id_range"],
                        "url_template": collection.get("url_template", "https://nft.ton.diamonds/api/v1/nft/{id}")
                    })
        
        # Сохраняем список NFT в контексте
        context.user_data["available_nft"] = all_nft
        if "selected_nft" not in context.user_data:
            context.user_data["selected_nft"] = []
        
        # Проверяем есть ли поисковый запрос
        search_query = context.user_data.get("model_search_query", "").lower()
        
        # Фильтруем NFT по поисковому запросу если он есть
        filtered_nft = all_nft
        if search_query:
            filtered_nft = [nft for nft in all_nft if search_query in nft["name"].lower()]
        
        # Настройки пагинации
        items_per_page = 15
        total_pages = (len(filtered_nft) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        current_nft = filtered_nft[start_idx:end_idx]
        
        selected_nft = context.user_data.get("selected_nft", [])
        selected_names = [nft["name"] for nft in selected_nft]
        
        # Текст сообщения
        text = f"🎯 *Поиск по модели*"
        
        if search_query:
            text += f"\n🔍 Поиск: '{search_query}'"
        
        text += f"\n\n✅ Выбрано: {len(selected_nft)} моделей"
        text += f"\n📋 Всего доступно: {len(filtered_nft)} моделей"
        
        if search_query and len(filtered_nft) == 0:
            text += f"\n❌ Ничего не найдено по запросу '{search_query}'"

        if len(selected_nft) == 0:
            text += f"\n⚠️ *Чтобы начать поиск, выберите модель*"
        
        text += f"\n\nСтр. {page+1}/{total_pages}:"
        
        # Создаем клавиатуру с моделями
        keyboard = []
        
        # Кнопка поиска модели
        keyboard.append([
            InlineKeyboardButton("🔍 Найти модель", callback_data="search_model_dialog")
        ])
        
        # Если есть поисковый запрос - кнопка сброса поиска
        if search_query:
            keyboard.append([
                InlineKeyboardButton("❌ Сбросить поиск", callback_data="reset_model_search")
            ])
        
        for nft in current_nft:
            is_selected = nft["name"] in selected_names
            icon = "✅" if is_selected else "⚪"
            btn_text = f"{icon} {nft['name']} ({nft['mode'][0].upper()})"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"toggle_nft_{nft['name']}")])
        
        # Кнопки пагинации
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"nft_page_{page-1}"))
        
        pagination_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="current_page_nft"))
        
        if page < total_pages - 1:
            pagination_buttons.append(InlineKeyboardButton("➡️", callback_data=f"nft_page_{page+1}"))
        
        if pagination_buttons:
            keyboard.append(pagination_buttons)
        
        # Кнопки управления
        control_buttons = []
        if selected_nft:
            control_buttons.append(InlineKeyboardButton("🔍 Начать поиск", callback_data="start_model_search"))
        
        control_buttons.append(InlineKeyboardButton("🔄 Сбросить выбор", callback_data="reset_nft_selection"))
        keyboard.append(control_buttons)
        
        # Кнопка назад в зависимости от контекста
        if from_results:
            keyboard.append([InlineKeyboardButton("🔙 Назад к результатам", callback_data="back_to_results_model")])
        else:
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="search_type_selection")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            try:
                # Проверяем, можно ли редактировать сообщение
                try:
                    # Пробуем отредактировать текст
                    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                except Exception as e:
                    if "not modified" in str(e):
                        pass  # Ничего не изменилось, это нормально
                    elif "There is no text in the message to edit" in str(e):
                        # Если сообщение - фото (без текста), удаляем его и отправляем новое
                        await query.message.delete()
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                    else:
                        # Другая ошибка - отправляем новое сообщение
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
            except Exception as e:
                # Если вообще не удалось, отправляем новое сообщение
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    @staticmethod
    async def search_model_dialog_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает диалог для поиска модели"""
        query = update.callback_query
        await query.answer()
        
        text = "🔍 *Поиск модели NFT*\n\n"
        text += "Введите название модели для поиска (например: 'SnoopDogg', 'UFCStrike'):"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="model_search")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Устанавливаем флаг ожидания ввода
        context.user_data["waiting_for_model_search"] = True

    @staticmethod
    async def handle_model_search_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает ввод поискового запроса для модели"""
        user_id = update.effective_user.id
        
        # Проверяем, ждем ли мы поисковый запрос
        if not context.user_data.get("waiting_for_model_search", False):
            return
        
        search_query = update.message.text.strip()
        
        if not search_query:
            await update.message.reply_text("❌ Введите название модели для поиска!")
            return
        
        # Сохраняем поисковый запрос
        context.user_data["model_search_query"] = search_query
        context.user_data["waiting_for_model_search"] = False
        
        # Показываем результаты поиска
        await ModelSearchHandler.show_model_selection(update, context, page=0)
        
        # Удаляем сообщение с запросом
        try:
            await update.message.delete()
        except:
            pass

    @staticmethod
    async def reset_model_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбрасывает поисковый запрос"""
        query = update.callback_query
        await query.answer()
        
        if "model_search_query" in context.user_data:
            del context.user_data["model_search_query"]
        
        if "waiting_for_model_search" in context.user_data:
            del context.user_data["waiting_for_model_search"]
        
        await query.answer("✅ Поиск сброшен", show_alert=True)
        await ModelSearchHandler.show_model_selection(update, context, page=0)

    @staticmethod
    async def handle_nft_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает выбор NFT"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "reset_nft_selection":
            # Сбрасываем выбор
            context.user_data["selected_nft"] = []
            await query.answer("✅ Выбор сброшен", show_alert=True)
            await ModelSearchHandler.show_model_selection(update, context, 0)
            return
        
        elif data == "start_model_search":
            # Начинаем поиск
            selected_nft = context.user_data.get("selected_nft", [])
            if not selected_nft:
                await query.answer("❌ Выберите хотя бы одну модель NFT", show_alert=True)
                return
            
            # Проверяем, что кнопка работает
            await query.answer("🔄 Запускаем поиск...")
            await ModelSearchHandler.start_model_search(update, context)
            return
        
        elif data.startswith("nft_page_"):
            # Переход по страницам
            page = int(data.replace("nft_page_", ""))
            await ModelSearchHandler.show_model_selection(update, context, page)
            return
        
        elif data == "current_page_nft":
            await query.answer(f"Страница {page+1}", show_alert=False)
            return
        
        elif data.startswith("toggle_nft_"):
            # Переключение выбора NFT
            nft_name = data.replace("toggle_nft_", "")
            all_nft = context.user_data.get("available_nft", [])
            selected_nft = context.user_data.get("selected_nft", [])
            
            # Находим NFT по имени
            nft_to_toggle = None
            for nft in all_nft:
                if nft["name"] == nft_name:
                    nft_to_toggle = nft
                    break
            
            if nft_to_toggle:
                # Проверяем, выбран ли уже этот NFT
                nft_in_selected = any(s["name"] == nft_name for s in selected_nft)
                if nft_in_selected:
                    selected_nft = [s for s in selected_nft if s["name"] != nft_name]
                    await query.answer(f"❌ {nft_name} удален из выбора", show_alert=True)
                else:
                    selected_nft.append(nft_to_toggle)
                    await query.answer(f"✅ {nft_name} добавлен в выбор", show_alert=True)
                
                context.user_data["selected_nft"] = selected_nft
            
            # Получаем текущую страницу для обновления
            current_page = 0
            if "available_nft" in context.user_data:
                all_nft = context.user_data["available_nft"]
                # Получаем поисковый запрос если есть
                search_query = context.user_data.get("model_search_query", "").lower()
                if search_query:
                    all_nft = [nft for nft in all_nft if search_query in nft["name"].lower()]
                
                for idx, nft in enumerate(all_nft):
                    if nft["name"] == nft_name:
                        current_page = idx // 15  # items_per_page = 15
                        break
            
            await ModelSearchHandler.show_model_selection(update, context, current_page)

    @staticmethod
    async def start_model_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запускает поиск по выбранным моделям"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if "found_users" in context.user_data:
            del context.user_data["found_users"]
        if "current_page" in context.user_data:
            del context.user_data["current_page"]
        
        selected_nft = context.user_data.get("selected_nft", [])
        
        if not selected_nft:
            await query.answer("❌ Не выбраны модели", show_alert=True)
            return
        
        template_text = "Здравствуйте, заинтересовался вашим NFT подарком, могу купить у вас его."
        template_name = "Стандартный"
        if user_id in user_templates:
            template_data = user_templates[user_id]
            template_text = template_data.get("text", "")
            template_name = template_data.get("name", "Стандартный")
        else:
            templates = Database.get_user_templates(user_id)
            if templates:
                template_text = templates[0].get("text", "")
                template_name = templates[0].get("name", "Стандартный")
        
        search_limit = SearchHandler.get_user_search_limit(user_id)
        
        nft_names = ", ".join([nft["name"] for nft in selected_nft[:3]])
        if len(selected_nft) > 3:
            nft_names += f" и еще {len(selected_nft) - 3}"
        
        # Сначала удаляем старое сообщение
        try:
            await query.message.delete()
        except:
            pass
        
        # Затем отправляем новое сообщение
        status_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"🎯 *Поиск по модели*\n"
                f"📋 Модели: {nft_names}\n"
                f"📝 Шаблон: {template_name}\n"
                f"🔢 Количество: {search_limit}\n\n"
                f"{SEARCH_ANIMATION[0]}\n✅ Найдено: 0/{search_limit}"
            ),
            parse_mode='Markdown'
        )
        
        start_time = time.time()
        found_nfts = []
        
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
                        text = f"🎯 *Поиск по модели*\n📋 Модели: {nft_names}\n📝 Шаблон: {template_name}\n🔢 Количество: {search_limit}\n\n{animation_frame}\n{progress}"
                        
                        try:
                            await status_message.edit_text(text, parse_mode='Markdown')
                        except:
                            pass
                        
                        frame += 1
                        await asyncio.sleep(0.5)
                
                animation_task = asyncio.create_task(run_animation())
                
                for wave in range(15):
                    if len(found_nfts) >= search_limit:
                        break
                    
                    tasks = []
                    for _ in range(min(80, (search_limit - len(found_nfts)) * 5)):
                        random_nft = random.choice(selected_nft)
                        
                        task = SearchHandler.fetch_random_nft_fast(session, random_nft)
                        tasks.append(task)
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, Exception):
                            continue
                            
                        if isinstance(result, tuple) and len(result) == 2:
                            url, username = result
                            if url and username:
                                if not any(nft[1] == username for nft in found_nfts):
                                    found_nfts.append((url, username))
                                    if len(found_nfts) >= search_limit:
                                        break
                    
                    await asyncio.sleep(0.1)
                
                if animation_task:
                    animation_task.cancel()
            
            search_time = int(time.time() - start_time)
            
            Database.update_user_stats(user_id, "search")
            Database.update_user_stats(user_id, "found", len(found_nfts))
            Database.update_user_stats(user_id, "active_day")
            
            search_mode = "model_search"
            Database.update_user_stats(user_id, "search", len(found_nfts), search_mode)
            
            Database.update_bot_stats("search_completed", user_id, search_mode)
            
            context.user_data["found_users"] = found_nfts
            context.user_data["current_page"] = 0
            context.user_data["search_limit"] = search_limit
            
            # Удаляем сообщение со статусом поиска
            try:
                await status_message.delete()
            except:
                pass
            
            # Показываем результаты
            await ModelSearchHandler.show_search_results_page(update, context, page=0)
            
        except Exception as e:
            logger.error(f"Ошибка поиска по модели: {e}", exc_info=True)
            
            # Удаляем сообщение со статусом поиска
            try:
                await status_message.delete()
            except:
                pass
            
            keyboard = [
                [InlineKeyboardButton("🔄 Искать снова", callback_data="model_search")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Ошибка при поиске NFT\n\nДетали: {str(e)[:100]}...\n\nПопробуйте еще раз!",
                reply_markup=reply_markup
            )

    @staticmethod
    async def show_search_results_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
        """Показывает страницу с результатами поиска по модели - ОБНОВЛЕНО ДЛЯ ПОДДЕРЖКИ ОБОИХ РЕЖИМОВ"""
        user_id = update.effective_user.id
        found_users = context.user_data.get("found_users", [])
        search_limit = context.user_data.get("search_limit", 15)
        
        logger.info(f"📄 ПОКАЗ РЕЗУЛЬТАТОВ ПОИСКА ПО МОДЕЛИ: Пользователь {user_id}, страница {page}")
        logger.info(f"📄 Найдено пользователей: {len(found_users)}")
        
        if not found_users:
            logger.warning(f"❌ Нет результатов для отображения у пользователя {user_id}")
            keyboard = [
                [InlineKeyboardButton("🔄 Искать снова", callback_data="model_search")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "❌ Нет результатов для отображения",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    "❌ Нет результатов для отображения",
                    reply_markup=reply_markup
                )
            return
        
        interface_type = ModelSearchHandler.get_user_results_interface(user_id)
        logger.info(f"📄 Тип интерфейса: {interface_type}")
        
        if interface_type == "single":
            logger.info(f"📄 Показываем одиночный интерфейс")
            await ModelSearchHandler.show_single_model_result(update, context, page)
            return
        
        # СПИСКОВЫЙ РЕЖИМ
        template_text = "Здравствуйте, заинтересовался вашим NFT подарком, могу купить у вас его."
        if user_id in user_templates:
            template_text = user_templates[user_id]["text"]
        else:
            templates = Database.get_user_templates(user_id)
            if templates:
                template_text = templates[0]["text"]
        
        # Получаем информацию о выбранных моделях
        selected_nft = context.user_data.get("selected_nft", [])
        nft_names = ", ".join([nft["name"] for nft in selected_nft[:3]])
        if len(selected_nft) > 3:
            nft_names += f" и еще {len(selected_nft) - 3}"
        
        template_name = "Стандартный"
        if user_id in user_templates:
            template_name = user_templates[user_id].get("name", "Стандартный")
        else:
            templates = Database.get_user_templates(user_id)
            if templates:
                template_name = templates[0].get("name", "Стандартный")
        
        items_per_page = 10
        total_pages = math.ceil(len(found_users) / items_per_page)
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        current_users = found_users[start_idx:end_idx]
        
        response_text = f"🎯 *Результаты поиска по модели*\n"
        response_text += f"📋 Модели: {nft_names}\n"
        response_text += f"📊 Найдено: {len(found_users)} пользователей\n"
        response_text += f"📝 Шаблон: {template_name}\n\n"
        
        for i, (url, username) in enumerate(current_users, start_idx + 1):
            message_link = Utils.create_message_link(username, template_text)
            response_text += f'{i:2d}. {username} | <a href="{message_link}">Написать</a>\n'
        
        response_text += f"\n📊 Страница {page + 1}/{total_pages}"
        
        keyboard = []
        
        # КНОПКИ ПАГИНАЦИИ
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"model_results_page_{page-1}"))
        
        pagination_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="current_page_results"))
        
        if page < total_pages - 1:
            pagination_buttons.append(InlineKeyboardButton("➡️ Вперед", callback_data=f"model_results_page_{page+1}"))
        
        if pagination_buttons:
            keyboard.append(pagination_buttons)
        
        # ОСНОВНЫЕ КНОПКИ
        keyboard.extend([
            [InlineKeyboardButton("🔄 Искать снова", callback_data="model_search")],
            [InlineKeyboardButton("📱 Главное меню", callback_data="back_to_menu")],
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем новое сообщение вместо редактирования
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=response_text,
                reply_markup=reply_markup,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            # Пытаемся удалить старое сообщение если есть
            if update.callback_query:
                try:
                    await update.callback_query.message.delete()
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"❌ Ошибка отправки результатов по модели: {e}")
            if update.callback_query:
                await update.callback_query.answer("❌ Ошибка при показе результатов", show_alert=True)

    @staticmethod
    async def handle_results_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик переключения страниц результатов (для поиска по модели)"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        logger.info(f"📄 ОБРАБОТКА СТРАНИЦЫ МОДЕЛЬ ПОИСКА: callback_data: {data}")
        
        if data.startswith("model_results_page_"):
            try:
                page = int(data.replace("model_results_page_", ""))
                logger.info(f"📄 Переключаемся на страницу: {page}")
                await ModelSearchHandler.show_search_results_page(update, context, page)
            except ValueError:
                logger.error(f"❌ Ошибка преобразования страницы: {data}")
                await query.answer("❌ Ошибка переключения страницы", show_alert=True)
        elif data == "current_page_results":
            await query.answer(f"Текущая страница", show_alert=False)