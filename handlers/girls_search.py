# handlers/girls_search.py
import logging
import random
import asyncio
import aiohttp
import time
import math
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from bot_config import CONCURRENT_REQUESTS, HTTP_TIMEOUT, HEADERS, SEARCH_ANIMATION, SEARCH_MODES
from database import Database
from utils import Utils
from globals import user_cooldowns, verified_nft_cache, user_templates, user_modes
from handlers.search import SearchHandler

logger = logging.getLogger(__name__)

class GirlsSearchHandler:
    # Список женских имен и их вариантов (русская транскрипция)
    FEMALE_NAMES = [
        # Анна и варианты
        'anna', 'ann', 'ana', 'anya', 'аня', 'анна', 'анушка', 'аннушка', 'анютка', 'анюта',
        'annushka', 'anyuta', 'anyutka', 'анн', 'анночка', 'аннчк', 'аннушк', 'анют',
        
        # Мария и варианты
        'maria', 'mary', 'masha', 'mariya', 'mari', 'маша', 'мария', 'маруся', 'марусенька',
        'машенька', 'машуня', 'машута', 'машутка', 'marya', 'mariia', 'мари', 'мариша',
        'марин', 'марина', 'marina', 'мариночка', 'маринк', 'мариш', 'мариш',
        
        # Екатерина и варианты
        'ekaterina', 'katerina', 'katya', 'katia', 'katy', 'kate', 'катя', 'екатерина',
        'катерина', 'катюша', 'катенька', 'катюшка', 'катюшенька', 'katusha', 'katenka',
        'katyusha', 'катяня', 'катюня', 'катюн', 'катю', 'katyunya', 'katyunya',
        
        # Елена и варианты
        'elena', 'helen', 'lena', 'elina', 'елена', 'лена', 'ленка', 'лёня', 'лёна',
        'еленька', 'еленка', 'елочка', 'елен', 'elinochka', 'lenochka', 'lenusya',
        'ленуся', 'ленусь', 'ленусенька', 'lenusia', 'lenusya',
        
        # Ольга и варианты
        'olga', 'olya', 'ольга', 'оля', 'олька', 'олечка', 'ольчик', 'ольг',
        'olichka', 'olya', 'olyushka', 'олюша', 'олюшка', 'олюшенька',
        
        # Наталья и варианты
        'natalia', 'natalya', 'natali', 'natalie', 'nata', 'natasha', 'настя', 'настасья',
        'наталья', 'наташа', 'натуся', 'наточка', 'натуля', 'ната', 'нату', 'натуш',
        'натуша', 'natusha', 'natusya', 'natochka',
        
        # Ирина и варианты
        'irina', 'ira', 'ирина', 'ира', 'ирочка', 'ируся', 'иришка', 'ириша', 'ирин',
        'irusha', 'irochka', 'irusya', 'irishka', 'irina',
        
        # Светлана и варианты
        'svetlana', 'sveta', 'света', 'светлана', 'светуля', 'светуня', 'светусь',
        'светка', 'светочка', 'svetochka', 'svetulya', 'svetunya', 'svetka',
        
        # Дарья и варианты
        'daria', 'darya', 'dasha', 'даша', 'дарья', 'дашуля', 'дашенька', 'дашуня',
        'dashulya', 'dashenka', 'dashunya', 'дар', 'дарь', 'дарюш', 'дарюша',
        
        # Юлия и варианты
        'yulia', 'julia', 'yulya', 'юля', 'юлия', 'юленька', 'юлечка', 'юлюся',
        'yulenka', 'yulechka', 'yulyusya', 'юльч', 'юль', 'юли', 'jul', 'julie',
        
        # Александра и варианты
        'alexandra', 'alex', 'sasha', 'sashka', 'саша', 'александра', 'сашенька',
        'сашуля', 'сашуня', 'sashenka', 'sashulya', 'sashunya', 'алекс', 'алекса',
        'александр', 'алексан',
        
        # Виктория и варианты
        'victoria', 'vika', 'viktorija', 'вика', 'виктория', 'викуся', 'викуля',
        'викочка', 'vikusya', 'vikulya', 'vikochka', 'вик', 'виктор', 'викторя',
        
        # Полина и варианты
        'polina', 'polya', 'полина', 'поля', 'полечка', 'полиночка', 'полинка',
        'polechka', 'polinochka', 'polinka', 'пол', 'полин', 'поли',
        
        # Алина и варианты
        'alina', 'alinka', 'алина', 'алиночка', 'алинка', 'алинуся', 'алинусь',
        'alinushka', 'alinusya', 'алин', 'али',
        
        # Кристина и варианты
        'christina', 'kristina', 'kristi', 'kristy', 'кристина', 'кристинка',
        'кристюша', 'кристюшка', 'kristinka', 'kristusha', 'kristyusha', 'крис',
        'крист', 'кристи',
        
        # Татьяна и варианты
        'tatyana', 'tanya', 'таня', 'татьяна', 'танечка', 'танюша', 'танюшка',
        'tanechka', 'tanyusha', 'tanyushka', 'тат', 'тать', 'татьян',
        
        # Валерия и варианты
        'valeria', 'valeriya', 'valya', 'lera', 'валерия', 'валя', 'лера', 'валенька',
        'валюша', 'валюшка', 'valenka', 'valyusha', 'valyushka', 'вал', 'валер',
        
        # Анастасия и варианты
        'anastasia', 'anastasiya', 'nastya', 'nastyusha', 'настя', 'анастасия',
        'настенька', 'настюша', 'настюшка', 'nastenka', 'nastyusha', 'nastyushka',
        'анаст', 'анастас', 'наст',
        
        # Марина и варианты
        'marina', 'mari', 'марина', 'маринка', 'мариночка', 'маринуся', 'маринусь',
        'marinka', 'marinochka', 'marinusya', 'марин', 'мариш',
        
        # Елизавета и варианты
        'elizaveta', 'eliza', 'liza', 'лиза', 'елизавета', 'лизочка', 'лизуся',
        'лизусь', 'lizochka', 'lizusya', 'lizus', 'елиз', 'елизавет',
        
        # Яна и варианты
        'yana', 'янка', 'яна', 'яночка', 'януся', 'янусь', 'yanochka', 'yanusya',
        'yanus', 'ян', 'янч',
        
        # Алиса и варианты
        'alice', 'alisa', 'алиса', 'алиска', 'алисочка', 'алисуся', 'aliska',
        'alisochka', 'alisusya', 'ал', 'алис',
        
        # Варвара и варианты
        'varvara', 'varia', 'варвара', 'варя', 'варенька', 'варечка', 'варюша',
        'varenka', 'varechka', 'varyusha', 'вар', 'варв',
        
        # София и варианты
        'sofia', 'sophia', 'sofya', 'sonya', 'софия', 'софья', 'соня', 'софочка',
        'софонька', 'софушка', 'sofochka', 'sofonka', 'sofushka', 'соф', 'софь',
        
        # Ульяна и варианты
        'ulyana', 'uliana', 'ulya', 'ульяна', 'уля', 'улечка', 'ульянка', 'ульяночка',
        'ulechka', 'ulyanka', 'ulyanochka', 'уль', 'ульян',
        
        # Ксения и варианты
        'ksenia', 'kseniya', 'ksu', 'ksusha', 'ксения', 'ксюша', 'ксюшенька', 'ксю',
        'ксюня', 'ksusha', 'ksushenka', 'ksunya', 'кс', 'ксен',
        
        # Милана и варианты
        'milana', 'mila', 'милана', 'мила', 'милочка', 'милуся', 'милусь', 'milochka',
        'milusya', 'milus', 'мил', 'милан',
        
        # Вероника и варианты
        'veronika', 'vera', 'вероника', 'вера', 'верочка', 'веруся', 'верусь',
        'verochka', 'verusya', 'verus', 'вер', 'верон',
        
        # Диана и варианты
        'diana', 'dian', 'диана', 'дианка', 'дианочка', 'диануся', 'dianka',
        'dianochka', 'dianusya', 'ди', 'диан',
        
        # Маргарита и варианты
        'margarita', 'rita', 'маргарита', 'рита', 'риточка', 'ритуся', 'ритусь',
        'ritochka', 'ritusya', 'ritus', 'марг', 'маргарит',
        
        # Эмилия и варианты
        'emilia', 'emily', 'emiliya', 'эмилия', 'эмили', 'эмиль', 'эмма', 'emma',
        'эмми', 'emmi', 'эм', 'эми',
        
        # Ариана и варианты
        'ariana', 'ari', 'ариана', 'ари', 'ариша', 'аришка', 'ариночка', 'arisha',
        'arishka', 'arinochka', 'ар', 'ариан',
        
        # Ева и варианты
        'eva', 'eve', 'ева', 'евка', 'евушка', 'евуся', 'евусь', 'evka', 'evushka',
        'evusya', 'evus', 'ев', 'евч',
        
        # Злата и варианты
        'zlata', 'zlatochka', 'злата', 'златочка', 'златуся', 'златусь', 'zlatusya',
        'zlatus', 'злат', 'зла',
        
        # Мирослава и варианты
        'miroslava', 'mira', 'slava', 'мирослава', 'мира', 'слава', 'мирочка',
        'мируся', 'мирусь', 'mirochka', 'mirusya', 'mirus', 'мир', 'мирос',
        
        # Олеся и варианты
        'olesya', 'olesia', 'олеся', 'олеська', 'олесенька', 'олесюша', 'oleska',
        'olesenka', 'olesyusha', 'олес', 'оле',
        
        # Рената и варианты
        'renata', 'rena', 'рената', 'рена', 'реночка', 'ренуся', 'ренусь', 'renochka',
        'renusya', 'renus', 'рен', 'ренат',
        
        # Снежана и варианты
        'snejana', 'snezhana', 'snezha', 'снежана', 'снежа', 'снежок', 'снежинка',
        'snezhok', 'snezhinka', 'снеж', 'снежан',
        
        # Элина и варианты
        'elina', 'elinka', 'элина', 'элинка', 'элиночка', 'элинуся', 'elinushka',
        'elinusya', 'элин', 'эли',
        
        # Ярослава и варианты
        'yaroslava', 'yara', 'ярослава', 'яра', 'ярочка', 'яруся', 'ярусь', 'yarochka',
        'yarusya', 'yarus', 'яр', 'ярос',
        
        # Другие женские имена
        'angelina', 'angel', 'ангелина', 'ангел', 'ангелин', 'ангелинка',
        'angelinka', 'angelinochka',
        
        'karina', 'karin', 'карина', 'карин', 'кариночка', 'каринуся', 'karinochka',
        'karinusya',
        
        'lilia', 'lily', 'liliya', 'лилия', 'лиля', 'лилечка', 'лилюся', 'lilechka',
        'liliusya',
        
        'nina', 'нини', 'нина', 'ниночка', 'нинуся', 'нинусь', 'ninichka', 'ninusya',
        'ninus',
        
        'toma', 'tom', 'тома', 'том', 'томочка', 'томуся', 'tomochka', 'tomusya',
        
        'fiona', 'фиона', 'фион', 'фионочка', 'фионуся', 'fionochka', 'fionusya',
        
        'elvira', 'el', 'эльвира', 'эль', 'эльвирочка', 'эльвируся', 'elvirochka',
        'elvirusya',
        
        'isabella', 'bella', 'изabella', 'изаб', 'изабэлла', 'изабэл', 'bella',
        'belle', 'изабэ',
        
        'jasmine', 'jasmin', 'жасмин', 'жасми', 'жасминочка', 'жасминуся', 'jasminochka',
        'jasminusya',
        
        'lucia', 'lucy', 'люсия', 'люси', 'люсь', 'люсечка', 'люсюся', 'lyusechka',
        'lyusyusya',
        
        'melanie', 'melanya', 'мелания', 'мелан', 'меланочка', 'мелануся', 'melanochka',
        'melanusya',
        
        'nadia', 'nadiya', 'надия', 'надя', 'надежда', 'наденька', 'наде', 'nadenka',
        
        'roxana', 'rox', 'роксана', 'рокс', 'роксаночка', 'роксануся', 'roxanochka',
        'roxanusya',
        
        'sabrina', 'sabrin', 'сабрина', 'сабрин', 'сабриночка', 'сабринуся', 'sabrinochka',
        'sabrinusya',
        
        'tamara', 'tam', 'тамара', 'там', 'тамарочка', 'тамаруся', 'tamarchik',
        'tamarusya',
        
        'valentina', 'val', 'валентина', 'валь', 'валентиночка', 'валентинуся', 'valentinochka',
        'valentinusya',
        
        'zoya', 'zoy', 'зоя', 'зой', 'зоенька', 'зоюся', 'зоюсь', 'zoenka', 'zoyusya',
        'zoyus',
        
        # Общие женские окончания и сокращения
        'ka', 'енька', 'ечка', 'юша', 'юшка', 'уля', 'усь', 'уся', 'очка', 'онька',
        'ичка', 'иша', 'ишка', 'ишу', 'иш', 'ищ', 'ич', 'ик', 'ик', 'иц', 'иця',
        'ица', 'ице', 'ици', 'ицик', 'ичик', 'ичи', 'ича', 'ич', 'ишь', 'ишк',
        'ишка', 'ишки', 'ишкин', 'ишк', 'ишк', 'ишк', 'ишк', 'ишк',
    ]
    
    @staticmethod
    def is_girl_username(username: str) -> bool:
        """Проверяет, содержит ли юзернейм женское имя"""
        if not username or username == "@Telegram":
            return False
        
        # Приводим к нижнему регистру и убираем @
        username_lower = username.lower().replace('@', '')
        
        # Проверяем наличие женских имен
        for name in GirlsSearchHandler.FEMALE_NAMES:
            if name in username_lower:
                return True
        
        # Дополнительные проверки для русских имен
        # Проверяем наличие характерных окончаний для женских имен
        russian_female_endings = ['на', 'та', 'ля', 'ня', 'ся', 'ша', 'ла', 'ра', 'га', 'да']
        for ending in russian_female_endings:
            if username_lower.endswith(ending) and len(username_lower) > 3:
                return True
        
        # Проверяем наличие мягкого знака (часто в женских именах)
        if 'ь' in username_lower:
            return True
            
        return False
    
    @staticmethod
    def get_user_results_interface(user_id):
        """Получает интерфейс результатов пользователя (совместимость)"""
        from database import Database
        user_settings = Database.get_user_settings(user_id)
        interface = user_settings.get("results_interface", "list")
        return interface
    
    @staticmethod
    async def show_single_girl_result(update: Update, context: ContextTypes.DEFAULT_TYPE, index=0):
        """Показывает одиночный результат девушки (покадровый режим) - ИСПРАВЛЕНО КАК В SEARCH.PY"""
        user_id = update.effective_user.id
        found_girls = context.user_data.get("found_girls", [])
        
        logger.info(f"👤 ОДИНОЧНЫЙ РЕЗУЛЬТАТ ДЕВУШКИ: Пользователь {user_id}, индекс {index}, всего {len(found_girls)}")
        
        if not found_girls:
            keyboard = [
                [InlineKeyboardButton("🔄 Искать снова", callback_data="girls_search")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                try:
                    await update.callback_query.edit_message_text(
                        text="❌ Нет результатов для отображения",
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Ошибка редактирования: {e}")
                    # Если не удалось отредактировать, отправляем новое
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="❌ Нет результатов для отображения",
                        reply_markup=reply_markup
                    )
            return
        
        if index >= len(found_girls):
            index = len(found_girls) - 1
        if index < 0:
            index = 0
        
        url, username = found_girls[index]
        
        template_text = "Здравствуйте, заинтересовался вашим NFT подарком, могу купить у вас его."
        if user_id in user_templates:
            template_text = user_templates[user_id]["text"]
        else:
            templates = Database.get_user_templates(user_id)
            if templates:
                template_text = templates[0]["text"]
        
        message_link = Utils.create_message_link(username, template_text)
        
        # СОЗДАЕМ КЛАВИАТУРУ КАК В SEARCH.PY
        keyboard = []
        
        # Кнопки пагинации
        pagination_buttons = []
        if index > 0:
            pagination_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"single_girl_{index-1}"))
        
        pagination_buttons.append(InlineKeyboardButton(f"{index+1}/{len(found_girls)}", callback_data="current_page_girl"))
        
        if index < len(found_girls) - 1:
            pagination_buttons.append(InlineKeyboardButton("➡️", callback_data=f"single_girl_{index+1}"))
        
        if pagination_buttons:
            keyboard.append(pagination_buttons)
        
        # Основные кнопки как в search.py
        keyboard.append([
            InlineKeyboardButton(
                f"{username}", 
                url=f"https://t.me/{username[1:]}" if username.startswith('@') else f"https://t.me/{username}"
            )
        ])
        keyboard.append([InlineKeyboardButton("Написать", url=message_link)])
        keyboard.append([InlineKeyboardButton("🔄 Искать снова", callback_data="girls_search")])
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
                    logger.info(f"✅ Успешно отредактировали медиа для девушки {index+1}/{len(found_girls)}")
                    
                except Exception as media_error:
                    logger.warning(f"⚠️ Не удалось отредактировать медиа: {media_error}")
                    # Если не получилось отредактировать медиа, пробуем отредактировать текст
                    try:
                        text = f"👩 Девушка {index+1}/{len(found_girls)}\n👤 {username}"
                        await update.callback_query.edit_message_text(
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
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
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                        
            except Exception as e:
                logger.error(f"❌ Ошибка при смене NFT девушки: {e}")
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
                    await update.callback_query.answer("Ошибка при загрузке NFT девушки", show_alert=True)
        else:
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=url,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Ошибка отправки фото девушки: {e}")
                await update.message.reply_text(
                    text=f"👩 Девушка {index+1}/{len(found_girls)}\n👤 {username}\n\nНажмите кнопку 'Написать' для отправки сообщения",
                    reply_markup=reply_markup,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
    
    @staticmethod
    async def handle_single_girl_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик переключения страниц в покадровом режиме для девушек"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("single_girl_"):
            try:
                index = int(data.replace("single_girl_", ""))
                await GirlsSearchHandler.show_single_girl_result(update, context, index)
            except ValueError:
                await query.answer("❌ Ошибка переключения", show_alert=True)
        elif data == "current_page_girl":
            await query.answer(f"Текущий пользователь", show_alert=False)
    
    @staticmethod
    async def start_girls_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запускает поиск девушек"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # ОЧИСТКА ДАННЫХ ПРЕДЫДУЩЕГО ПОИСКА
        if "found_girls" in context.user_data:
            del context.user_data["found_girls"]
        if "current_page" in context.user_data:
            del context.user_data["current_page"]
        
        # Сохраняем режим
        user_modes[user_id] = "girls"
        
        # Получаем выбранный шаблон
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
        
        # Получаем лимит поиска
        search_limit = SearchHandler.get_user_search_limit(user_id)
        
        # Отправляем начальное сообщение С ПРИМЕЧАНИЕМ О ВОЗМОЖНЫХ ОШИБКАХ
        try:
            # Пытаемся отредактировать существующее сообщение
            status_message = await query.edit_message_text(
                text=f"👩 *Поиск девушек*\n"
                f"📝 Шаблон: {template_name}\n"
                f"🔢 Количество: {search_limit}\n"
                f"⚠️ *Примечание:* Поиск может ошибаться и выдавать не девушку\n\n"
                f"{SEARCH_ANIMATION[0]}\n✅ Найдено: 0/{search_limit}",
                parse_mode='Markdown'
            )
        except Exception as e:
            # Если не удалось отредактировать (например, предыдущее сообщение было фото),
            # отправляем новое сообщение
            logger.warning(f"Не удалось отредактировать сообщение, отправляем новое: {e}")
            try:
                # Пытаемся удалить предыдущее сообщение если оно фото
                await query.message.delete()
            except:
                pass
                
            status_message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"👩 *Поиск девушек*\n"
                    f"📝 Шаблон: {template_name}\n"
                    f"🔢 Количество: {search_limit}\n"
                    f"⚠️ *Примечание:* Поиск может ошибаться и выдавать не девушку\n\n"
                    f"{SEARCH_ANIMATION[0]}\n✅ Найдено: 0/{search_limit}",
                parse_mode='Markdown'
            )
        
        start_time = time.time()
        found_girls = []
        
        try:
            connector = aiohttp.TCPConnector(limit=CONCURRENT_REQUESTS, ssl=False)
            
            async with aiohttp.ClientSession(
                headers=HEADERS,
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
            ) as session:
                
                # Анимация поиска
                async def run_animation():
                    frame = 0
                    while len(found_girls) < search_limit:
                        animation_frame = SEARCH_ANIMATION[frame % len(SEARCH_ANIMATION)]
                        progress = f"✅ Найдено девушек: {len(found_girls)}/{search_limit}"
                        text = f"👩 *Поиск девушек*\n📝 Шаблон: {template_name}\n🔢 Количество: {search_limit}\n⚠️ *Примечание:* Поиск может ошибаться\n\n{animation_frame}\n{progress}"
                        
                        try:
                            await status_message.edit_text(text=text, parse_mode='Markdown')
                        except Exception as e:
                            logger.warning(f"Ошибка обновления анимации: {e}")
                        
                        frame += 1
                        await asyncio.sleep(0.5)
                
                animation_task = asyncio.create_task(run_animation())
                
                # Получаем коллекции из всех режимов для большего охвата
                all_collections = []
                for mode_name, mode_data in SEARCH_MODES.items():
                    all_collections.extend(mode_data["collections"])
                
                # Убираем дубликаты
                unique_collections = []
                seen_names = set()
                for collection in all_collections:
                    if collection["name"] not in seen_names:
                        unique_collections.append(collection)
                        seen_names.add(collection["name"])
                
                # Основной поиск
                for wave in range(25):  # Увеличиваем количество волн для поиска девушек
                    if len(found_girls) >= search_limit:
                        break
                    
                    # Создаем задачи для поиска
                    tasks = []
                    for _ in range(min(100, (search_limit - len(found_girls)) * 10)):
                        random_collection = random.choice(unique_collections)
                        
                        task = GirlsSearchHandler.fetch_random_nft(session, random_collection)
                        tasks.append(task)
                    
                    # Ждем завершения всех задач
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Обрабатываем результаты
                    for result in results:
                        if isinstance(result, Exception):
                            continue
                            
                        if isinstance(result, tuple) and len(result) == 2:
                            url, username = result
                            if url and username:
                                # Проверяем, является ли девушкой
                                if GirlsSearchHandler.is_girl_username(username):
                                    # Проверяем дубликаты
                                    if not any(girl[1] == username for girl in found_girls):
                                        found_girls.append((url, username))
                                        if len(found_girls) >= search_limit:
                                            break
                    
                    # Небольшая пауза между волнами
                    await asyncio.sleep(0.05)
                
                # Останавливаем анимацию
                if animation_task:
                    try:
                        animation_task.cancel()
                        await animation_task
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.error(f"Ошибка при отмене анимации: {e}")
            
            search_time = int(time.time() - start_time)
            
            # УДАЛЯЕМ СООБЩЕНИЕ О СТАТУСЕ ПОИСКА ПЕРЕД ПОКАЗОМ РЕЗУЛЬТАТОВ
            try:
                await status_message.delete()
            except Exception as delete_error:
                logger.warning(f"Не удалось удалить сообщение о статусе поиска: {delete_error}")
            
            if len(found_girls) == 0:
                keyboard = [
                    [InlineKeyboardButton("🔄 Искать снова", callback_data="girls_search")],
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"❌ Поиск не дал результатов\n"
                        f"⏱ Время поиска: {search_time} сек\n"
                        f"⚠️ *Примечание:* Поиск может ошибаться\n\n"
                        f"Попробуйте увеличить лимит поиска или изменить настройки.",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения о пустом результате: {e}")
                return
            
            Database.update_user_stats(user_id, "search")
            Database.update_user_stats(user_id, "found", len(found_girls))
            Database.update_user_stats(user_id, "active_day")
            Database.update_user_stats(user_id, "search", len(found_girls), "girls_search")

            # Обновляем статистику бота
            Database.update_bot_stats("search_completed", user_id, "girls")
            
            # Сохраняем найденных девушек для пагинации
            context.user_data["found_girls"] = found_girls
            context.user_data["current_page"] = 0
            context.user_data["search_limit"] = search_limit
            
            # ВАЖНО: Проверяем тип интерфейса пользователя
            interface_type = GirlsSearchHandler.get_user_results_interface(user_id)
            logger.info(f"🔍 Показ результатов для пользователя {user_id}, интерфейс: {interface_type}")
            
            if interface_type == "single":
                # Покадровый режим
                await GirlsSearchHandler.show_single_girl_result(update, context, index=0)  # <-- index вместо page
            else:
                # Списковый режим
                await GirlsSearchHandler.show_girls_results_page(update, context, page=0)
            
        except Exception as e:
            logger.error(f"Ошибка поиска девушек: {e}", exc_info=True)
            
            # УДАЛЯЕМ СООБЩЕНИЕ О СТАТУСЕ ПОИСКА ПРИ ОШИБКЕ
            try:
                await status_message.delete()
            except Exception as delete_error:
                logger.warning(f"Не удалось удалить сообщение о статусе при ошибке: {delete_error}")
            
            keyboard = [
                [InlineKeyboardButton("🔄 Искать снова", callback_data="girls_search")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ Ошибка при поиске девушек\n\n"
                    f"Детали: {str(e)[:100]}...\n\n"
                    f"Попробуйте еще раз!",
                    reply_markup=reply_markup
                )
            except Exception as e2:
                logger.error(f"Ошибка отправки сообщения об ошибке: {e2}")
    
    @staticmethod
    async def fetch_random_nft(session: aiohttp.ClientSession, collection: dict):
        """Поиск случайного NFT"""
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
    async def show_girls_results_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
        """Показывает страницу с результатами поиска девушек"""
        user_id = update.effective_user.id
        found_girls = context.user_data.get("found_girls", [])
        search_limit = context.user_data.get("search_limit", 15)
        
        logger.info(f"📄 ПОКАЗ РЕЗУЛЬТАТОВ ДЕВУШКИ: Пользователь {user_id}, страница {page}")
        logger.info(f"📄 Найдено девушек: {len(found_girls)}")
        
        if not found_girls:
            keyboard = [
                [InlineKeyboardButton("🔄 Искать снова", callback_data="girls_search")],  
                [InlineKeyboardButton("📱 Главное меню", callback_data="back_to_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text="❌ Не найдено девушек по заданным критериям\n⚠️ *Примечание:* Поиск может ошибаться",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    text="❌ Не найдено девушек по заданным критериям\n⚠️ *Примечание:* Поиск может ошибаться",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            return
        
        # ПРОВЕРЯЕМ ИНТЕРФЕЙС ПОЛЬЗОВАТЕЛЯ
        interface_type = GirlsSearchHandler.get_user_results_interface(user_id)
        logger.info(f"📄 Тип интерфейса: {interface_type}")
        
        if interface_type == "single":
            logger.info(f"📄 Показываем одиночный интерфейс")
            await GirlsSearchHandler.show_single_girl_result(update, context, index=page)  # <-- index вместо page
            return
        
        # СПИСКОВЫЙ РЕЖИМ
        template_text = "Здравствуйте, заинтересовался вашим NFT подарком, могу купить у вас его."
        template_name = "Стандартный"
        if user_id in user_templates:
            template_data = user_templates[user_id]
            template_text = template_data.get("text", "")
            template_name = template_data.get("name", "Стандартный")
        else:
            templates = Database.get_user_templates(user_id)
            if templates:
                template_text = templates[0]["text"]
                template_name = templates[0]["name"]
        
        items_per_page = 10
        total_pages = math.ceil(len(found_girls) / items_per_page)
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        current_girls = found_girls[start_idx:end_idx]
        
        # Формируем текст результата С ПРИМЕЧАНИЕМ
        response_text = f"👩 *Результаты поиска девушек*\n"
        response_text += f"📊 Найдено: {len(found_girls)} девушек\n"
        response_text += f"📝 Шаблон: {template_name}\n"
        response_text += f"⚠️ *Примечание:* Поиск может ошибаться\n\n"
        
        # Отображаем девушек на текущей странице
        for i, (url, username) in enumerate(current_girls, start_idx + 1):
            message_link = Utils.create_message_link(username, template_text)
            response_text += f'{i:2d}. {username} | <a href="{message_link}">Написать</a>\n'
        
        response_text += f"\n📊 Страница {page + 1}/{total_pages}"
        
        # Создаем клавиатуру с пагинацией
        keyboard = []
        
        # Кнопки пагинации
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"girls_results_page_{page-1}"))
        
        pagination_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="current_page_results_girls"))
        
        if page < total_pages - 1:
            pagination_buttons.append(InlineKeyboardButton("➡️ Вперед", callback_data=f"girls_results_page_{page+1}"))
        
        if pagination_buttons:
            keyboard.append(pagination_buttons)
        
        # Основные кнопки
        keyboard.extend([
            [InlineKeyboardButton("🔄 Искать снова", callback_data="girls_search")],
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
            logger.error(f"❌ Ошибка отправки результатов девушек: {e}")
            if update.callback_query:
                await update.callback_query.answer("❌ Ошибка при показе результатов", show_alert=True)
    
    @staticmethod
    async def handle_girls_results_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик переключения страниц результатов для девушек"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("girls_results_page_"):
            try:
                page = int(data.replace("girls_results_page_", ""))
                await GirlsSearchHandler.show_girls_results_page(update, context, page)
            except ValueError:
                await query.answer("❌ Ошибка переключения страницы", show_alert=True)
        elif data == "current_page":
            await query.answer(f"Текущая страница", show_alert=False)