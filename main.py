import logging
import subprocess
import sys
import os
import tempfile
import time
import json
from typing import Dict
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Импорты для основного бота (твои оригинальные)
from bot_config import BOT_TOKEN, ADMINS, REQUIRED_CHANNEL_LINK, REQUIRED_CHANNEL_ID

# Импорт всех твоих хендлеров для основного бота
from handlers.start import StartHandler
from handlers.search import SearchHandler
from handlers.nft_management import NFTManagementHandler
from handlers.templates import TemplatesHandler
from handlers.admin import AdminHandler
from handlers.model_search import ModelSearchHandler
from handlers.settings import SettingsHandler
from handlers.profile import ProfileHandler
from handlers.templates_manager import TemplatesManager
from handlers.girls_search import GirlsSearchHandler
from handlers.help_handler import HelpHandler
import globals

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

active_mirrors: Dict[str, dict] = {}

# ==================== СОЗДАНИЕ СКРИПТА ДЛЯ ЗЕРКАЛА (ПОЛНАЯ КОПИЯ) ====================
def create_mirror_script(token: str) -> str:
    """Создаёт временный Python скрипт, который является полной копией твоего бота с переданным токеном"""
    # Собираем содержимое скрипта. Включаем все необходимые импорты и логику.
    script_code = '''#!/usr/bin/env python3
import logging
import sys
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Добавляем текущую директорию в путь, чтобы импортировать твои модули
sys.path.insert(0, os.getcwd())

# Импортируем всё из твоих файлов
from bot_config import ADMINS, REQUIRED_CHANNEL_LINK, REQUIRED_CHANNEL_ID
from handlers.start import StartHandler
from handlers.search import SearchHandler
from handlers.nft_management import NFTManagementHandler
from handlers.templates import TemplatesHandler
from handlers.admin import AdminHandler
from handlers.model_search import ModelSearchHandler
from handlers.settings import SettingsHandler
from handlers.profile import ProfileHandler
from handlers.templates_manager import TemplatesManager
from handlers.girls_search import GirlsSearchHandler
from handlers.help_handler import HelpHandler
import globals

# Токен для этого зеркала
BOT_TOKEN = "''' + token + '''"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MirrorBot:
    def __init__(self):
        self.application = ApplicationBuilder().token(BOT_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        # Все команды
        self.application.add_handler(CommandHandler("start", StartHandler.start_command))
        self.application.add_handler(CommandHandler("profile", ProfileHandler.profile_command))
        self.application.add_handler(CommandHandler("mode", SearchHandler.show_mode_selection))
        self.application.add_handler(CommandHandler("random", SearchHandler.random_search_handler))
        self.application.add_handler(CommandHandler("nft", NFTManagementHandler.nft_command))
        self.application.add_handler(CommandHandler("block", NFTManagementHandler.block_command))
        self.application.add_handler(CommandHandler("unblock", NFTManagementHandler.unblock_command))
        self.application.add_handler(CommandHandler("myblock", NFTManagementHandler.myblock_command))
        self.application.add_handler(CommandHandler("addtemplate", TemplatesHandler.add_template_command))
        self.application.add_handler(CommandHandler("settings", SettingsHandler.settings_menu))
        self.application.add_handler(CommandHandler("broadcast", AdminHandler.broadcast_command))
        self.application.add_handler(CommandHandler("bc", AdminHandler.quick_broadcast_command))
        self.application.add_handler(MessageHandler(
            filters.CAPTION & (filters.PHOTO | filters.VIDEO | filters.Document.ALL) & filters.User(ADMINS),
            AdminHandler.handle_media_broadcast
        ))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update or not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        if not update.message or not update.message.text:
            return
        message_text = update.message.text.strip()
        if user_id in globals.waiting_for_template:
            from handlers.templates import TemplatesHandler
            await TemplatesHandler.handle_template_message(update, context)
            return
        if context.user_data.get("waiting_for_model_search", False):
            if message_text.startswith('/'):
                return
            if not message_text:
                await update.message.reply_text("❌ Введите название модели для поиска!")
                return
            await ModelSearchHandler.handle_model_search_message(update, context)
            return

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update or not update.callback_query:
            return
        query = update.callback_query
        await query.answer()
        data = query.data
        if not data:
            return
        try:
            logger.info(f"CALLBACK зеркала: {query.from_user.id} -> {data}")
            # ========== ТВОЙ ПОЛНЫЙ ОБРАБОТЧИК (ВСЕ ВЕТКИ) ==========
            if data == "check_subscription":
                from utils import Utils
                user_id = query.from_user.id
                if await Utils.check_subscription(user_id, context):
                    await query.answer("✅ Проверка пройдена! Добро пожаловать!", show_alert=True)
                    await StartHandler.start_command(update, context)
                else:
                    await query.answer("❌ Вы не подписаны на канал!", show_alert=True)
                    await Utils.require_subscription(update, context)
                return
            elif data == "profile_menu":
                await ProfileHandler.profile_callback(update, context)
            elif data == "detailed_stats":
                await ProfileHandler.detailed_stats_callback(update, context)
            elif data == "weekly_stats":
                await ProfileHandler.weekly_stats_callback(update, context)
            elif data == "quick_settings":
                await ProfileHandler.quick_settings_callback(update, context)
            elif data == "templates_menu":
                await TemplatesManager.templates_menu_callback(update, context)
            elif data == "delete_template_menu":
                await TemplatesManager.delete_template_menu_callback(update, context)
            elif data.startswith("delete_template_"):
                await TemplatesManager.delete_template_callback(update, context)
            elif data.startswith("set_active_template_"):
                await TemplatesManager.set_active_template_callback(update, context)
            elif data.startswith("select_template_"):
                await TemplatesHandler.select_template_callback(update, context)
            elif data == "select_active_template":
                await TemplatesManager.select_active_template_callback(update, context)
            elif data == "view_all_templates":
                await TemplatesManager.view_all_templates_callback(update, context)
            elif data == "add_template_dialog":
                await TemplatesManager.add_template_dialog_callback(update, context)
            elif data == "admin_panel":
                await AdminHandler.admin_panel_callback(update, context)
            elif data == "admin_stats":
                await AdminHandler.admin_stats_callback(update, context)
            elif data == "admin_extended_stats":
                await AdminHandler.admin_extended_stats_callback(update, context)
            elif data == "admin_clear_cache":
                await AdminHandler.admin_clear_cache_callback(update, context)
            elif data == "admin_broadcast_info":
                await AdminHandler.admin_broadcast_info_callback(update, context)
            elif data == "settings_menu":
                await SettingsHandler.settings_menu(update, context)
            elif data == "change_search_limit":
                context.user_data["from_results"] = False
                await SettingsHandler.change_search_limit(update, context)
            elif data.startswith("set_limit_"):
                await SettingsHandler.handle_limit_selection(update, context)
            elif data == "change_results_interface":
                await SettingsHandler.change_results_interface(update, context)
            elif data == "set_interface_list":
                await SettingsHandler.handle_interface_selection(update, context)
            elif data == "set_interface_single":
                await SettingsHandler.handle_interface_selection(update, context)
            elif data == "settings_back":
                await SettingsHandler.settings_menu(update, context)
            elif data == "back_to_settings":
                await SettingsHandler.settings_menu(update, context)
            elif data.startswith("mode_"):
                await SearchHandler.mode_callback(update, context)
            elif data == "search":
                user_id = query.from_user.id
                from globals import user_modes
                if user_id not in user_modes:
                    await query.answer("❌ Сначала выберите режим!", show_alert=True)
                    await SearchHandler.show_mode_selection(update, context)
                    return
                if "found_users" in context.user_data:
                    del context.user_data["found_users"]
                if "current_page" in context.user_data:
                    del context.user_data["current_page"]
                await SearchHandler.random_nft_search(update, context)
            elif data == "random_search":
                await SearchHandler.show_mode_selection(update, context)
            elif data == "change_mode":
                context.user_data["from_results"] = False
                await SearchHandler.show_mode_selection(update, context)
            elif data == "change_mode_from_results":
                context.user_data["from_results"] = True
                await SearchHandler.show_mode_selection(update, context)
            elif data == "search_with_default":
                await SearchHandler.search_with_default_callback(update, context)
            elif data == "nft_list":
                await NFTManagementHandler.nft_command(update, context)
            elif data == "block_management":
                context.user_data["from_results"] = False
                await NFTManagementHandler.block_management_callback(update, context)
            elif data == "block_management_from_results":
                context.user_data["from_results"] = True
                await NFTManagementHandler.block_management_callback(update, context)
            elif data == "myblock_list":
                await NFTManagementHandler.myblock_command(update, context)
            elif data == "block_nft_menu":
                await NFTManagementHandler.nft_command(update, context)
            elif data == "unblock_nft_menu":
                await NFTManagementHandler.myblock_command(update, context)
            elif data.startswith("toggle_nft_"):
                if "available_nft" in context.user_data:
                    await ModelSearchHandler.handle_nft_selection(update, context)
                else:
                    await NFTManagementHandler.toggle_nft_callback(update, context)
            elif data == "search_type_selection":
                await ModelSearchHandler.show_search_type_selection(update, context)
            elif data == "model_search":
                context.user_data["from_results"] = False
                await ModelSearchHandler.show_model_selection(update, context)
            elif data == "model_search_from_results":
                context.user_data["from_results"] = True
                await ModelSearchHandler.show_model_selection(update, context)
            elif data == "start_model_search_from_single":
                selected_nft = context.user_data.get("selected_nft", [])
                if not selected_nft:
                    await query.answer("❌ Сначала выберите модели NFT", show_alert=True)
                    try:
                        await query.message.delete()
                    except:
                        pass
                    context.user_data["from_results"] = False
                    await ModelSearchHandler.show_model_selection(update, context)
                    return
                try:
                    await query.message.delete()
                except:
                    pass
                await ModelSearchHandler.start_model_search(update, context)
                return
            elif data == "search_model_dialog":
                await ModelSearchHandler.search_model_dialog_callback(update, context)
            elif data == "reset_model_search":
                await ModelSearchHandler.reset_model_search_callback(update, context)
            elif data.startswith("nft_page_"):
                await ModelSearchHandler.handle_nft_selection(update, context)
            elif data == "reset_nft_selection":
                await ModelSearchHandler.handle_nft_selection(update, context)
            elif data == "start_model_search":
                await ModelSearchHandler.start_model_search(update, context)
            elif data.startswith("model_results_page_"):
                await ModelSearchHandler.handle_results_page(update, context)
            elif data.startswith("random_results_page_"):
                await SearchHandler.handle_results_page(update, context)
            elif data.startswith("girls_results_page_"):
                await GirlsSearchHandler.handle_girls_results_page(update, context)
            elif data.startswith("single_result_"):
                await SearchHandler.handle_single_result_page(update, context)
            elif data.startswith("single_model_"):
                await ModelSearchHandler.handle_single_model_page(update, context)
            elif data.startswith("single_girl_"):
                await GirlsSearchHandler.handle_single_girl_page(update, context)
            elif data == "girls_search":
                if "found_girls" in context.user_data:
                    del context.user_data["found_girls"]
                if "current_page" in context.user_data:
                    del context.user_data["current_page"]
                await GirlsSearchHandler.start_girls_search(update, context)
            elif data == "back_to_results_search":
                await SearchHandler.show_search_results_page(update, context, page=0)
            elif data == "back_to_results_model":
                await ModelSearchHandler.show_search_results_page(update, context, page=0)
            elif data == "back_to_results_girls":
                await GirlsSearchHandler.show_girls_results_page(update, context, page=0)
            elif data == "current_page":
                await query.answer("Текущая страница", show_alert=False)
            elif data == "current_page_model":
                await query.answer("Текущий пользователь", show_alert=False)
            elif data == "current_page_girl":
                await query.answer("Текущий пользователь", show_alert=False)
            elif data == "current_page_results":
                await query.answer("Текущая страница", show_alert=False)
            elif data == "current_page_results_girls":
                await query.answer("Текущая страница", show_alert=False)
            elif data == "current_page_nft":
                await query.answer("Текущая страница", show_alert=False)
            elif data == "support_menu":
                await HelpHandler.help_menu_callback(update, context)
            elif data == "work_manual":
                await HelpHandler.work_manual_callback(update, context)
            elif data == "back_to_menu":
                try:
                    await query.message.delete()
                except:
                    pass
                await StartHandler.show_main_menu(update, context)
            else:
                await query.answer("❌ Неизвестная команда")
        except Exception as e:
            logger.error(f"Callback error: {e}")

    def run(self):
        self.application.run_polling()

if __name__ == "__main__":
    bot = MirrorBot()
    bot.run()
'''
    fd, path = tempfile.mkstemp(suffix='.py', prefix='mirror_')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(script_code)
    return path

async def start_mirror(token: str, owner_id: int) -> str:
    if token in active_mirrors:
        return "❌ Зеркало уже запущено"
    try:
        test_app = ApplicationBuilder().token(token).build()
        me = await test_app.bot.get_me()
        await test_app.shutdown()
    except Exception as e:
        return f"❌ Неверный токен: {str(e)[:50]}"
    script_path = create_mirror_script(token)
    proc = subprocess.Popen([sys.executable, script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    active_mirrors[token] = {
        "process": proc,
        "owner": owner_id,
        "username": me.username,
        "script_path": script_path
    }
    time.sleep(2)
    return f"✅ Зеркало @{me.username} запущено!\n\n⚠️ ОБЯЗАТЕЛЬНО НАПИШИТЕ АДМИНИСТРАТОРУ @tonswisa и добавьте этого бота в администраторы канала для проверки подписки!"

def stop_user_mirrors(owner_id: int) -> int:
    count = 0
    for token, data in list(active_mirrors.items()):
        if data["owner"] == owner_id:
            data["process"].terminate()
            try:
                os.unlink(data["script_path"])
            except:
                pass
            del active_mirrors[token]
            count += 1
    return count

# ==================== ОСНОВНОЙ БОТ ====================
class NFTBot:
    def __init__(self):
        self.application = ApplicationBuilder().token(BOT_TOKEN).build()
        self.setup_handlers()
        self.setup_error_handler()

    def setup_error_handler(self):
        async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.error(f"Exception: {context.error}", exc_info=True)
        self.application.add_error_handler(error_handler)

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", StartHandler.start_command))
        self.application.add_handler(CommandHandler("profile", ProfileHandler.profile_command))
        self.application.add_handler(CommandHandler("mode", SearchHandler.show_mode_selection))
        self.application.add_handler(CommandHandler("random", SearchHandler.random_search_handler))
        self.application.add_handler(CommandHandler("nft", NFTManagementHandler.nft_command))
        self.application.add_handler(CommandHandler("block", NFTManagementHandler.block_command))
        self.application.add_handler(CommandHandler("unblock", NFTManagementHandler.unblock_command))
        self.application.add_handler(CommandHandler("myblock", NFTManagementHandler.myblock_command))
        self.application.add_handler(CommandHandler("addtemplate", TemplatesHandler.add_template_command))
        self.application.add_handler(CommandHandler("settings", SettingsHandler.settings_menu))
        self.application.add_handler(CommandHandler("broadcast", AdminHandler.broadcast_command))
        self.application.add_handler(CommandHandler("bc", AdminHandler.quick_broadcast_command))
        self.application.add_handler(MessageHandler(
            filters.CAPTION & (filters.PHOTO | filters.VIDEO | filters.Document.ALL) & filters.User(ADMINS),
            AdminHandler.handle_media_broadcast
        ))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data.get("waiting_for_mirror_token"):
            token = update.message.text.strip()
            user_id = update.effective_user.id
            result = await start_mirror(token, user_id)
            await update.message.reply_text(result, parse_mode='HTML')
            context.user_data["waiting_for_mirror_token"] = False
            return

        if not update or not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        if not update.message or not update.message.text:
            return
        message_text = update.message.text.strip()
        if user_id in globals.waiting_for_template:
            from handlers.templates import TemplatesHandler
            await TemplatesHandler.handle_template_message(update, context)
            return
        if context.user_data.get("waiting_for_model_search", False):
            if message_text.startswith('/'):
                return
            if not message_text:
                await update.message.reply_text("❌ Введите название модели для поиска!")
                return
            await ModelSearchHandler.handle_model_search_message(update, context)
            return

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Полный обработчик для основного бота (такой же как и в зеркале)
        if not update or not update.callback_query:
            return
        query = update.callback_query
        await query.answer()
        data = query.data
        if not data:
            return
        try:
            logger.info(f"CALLBACK осн: {query.from_user.id} -> {data}")
            # Вставь сюда свой полный обработчик (он идентичен тому, что внутри зеркала)
            # Для краткости я скопирую его из зеркала, но ты можешь использовать свой.
            if data == "check_subscription":
                from utils import Utils
                user_id = query.from_user.id
                if await Utils.check_subscription(user_id, context):
                    await query.answer("✅ Проверка пройдена!", show_alert=True)
                    await StartHandler.start_command(update, context)
                else:
                    await query.answer("❌ Вы не подписаны!", show_alert=True)
                    await Utils.require_subscription(update, context)
                return
            elif data == "profile_menu":
                await ProfileHandler.profile_callback(update, context)
            elif data == "detailed_stats":
                await ProfileHandler.detailed_stats_callback(update, context)
            elif data == "weekly_stats":
                await ProfileHandler.weekly_stats_callback(update, context)
            elif data == "quick_settings":
                await ProfileHandler.quick_settings_callback(update, context)
            elif data == "templates_menu":
                await TemplatesManager.templates_menu_callback(update, context)
            elif data == "delete_template_menu":
                await TemplatesManager.delete_template_menu_callback(update, context)
            elif data.startswith("delete_template_"):
                await TemplatesManager.delete_template_callback(update, context)
            elif data.startswith("set_active_template_"):
                await TemplatesManager.set_active_template_callback(update, context)
            elif data.startswith("select_template_"):
                await TemplatesHandler.select_template_callback(update, context)
            elif data == "select_active_template":
                await TemplatesManager.select_active_template_callback(update, context)
            elif data == "view_all_templates":
                await TemplatesManager.view_all_templates_callback(update, context)
            elif data == "add_template_dialog":
                await TemplatesManager.add_template_dialog_callback(update, context)
            elif data == "admin_panel":
                await AdminHandler.admin_panel_callback(update, context)
            elif data == "admin_stats":
                await AdminHandler.admin_stats_callback(update, context)
            elif data == "admin_extended_stats":
                await AdminHandler.admin_extended_stats_callback(update, context)
            elif data == "admin_clear_cache":
                await AdminHandler.admin_clear_cache_callback(update, context)
            elif data == "admin_broadcast_info":
                await AdminHandler.admin_broadcast_info_callback(update, context)
            elif data == "settings_menu":
                await SettingsHandler.settings_menu(update, context)
            elif data == "change_search_limit":
                context.user_data["from_results"] = False
                await SettingsHandler.change_search_limit(update, context)
            elif data.startswith("set_limit_"):
                await SettingsHandler.handle_limit_selection(update, context)
            elif data == "change_results_interface":
                await SettingsHandler.change_results_interface(update, context)
            elif data == "set_interface_list":
                await SettingsHandler.handle_interface_selection(update, context)
            elif data == "set_interface_single":
                await SettingsHandler.handle_interface_selection(update, context)
            elif data == "settings_back":
                await SettingsHandler.settings_menu(update, context)
            elif data == "back_to_settings":
                await SettingsHandler.settings_menu(update, context)
            elif data.startswith("mode_"):
                await SearchHandler.mode_callback(update, context)
            elif data == "search":
                user_id = query.from_user.id
                from globals import user_modes
                if user_id not in user_modes:
                    await query.answer("❌ Сначала выберите режим!", show_alert=True)
                    await SearchHandler.show_mode_selection(update, context)
                    return
                if "found_users" in context.user_data:
                    del context.user_data["found_users"]
                if "current_page" in context.user_data:
                    del context.user_data["current_page"]
                await SearchHandler.random_nft_search(update, context)
            elif data == "random_search":
                await SearchHandler.show_mode_selection(update, context)
            elif data == "change_mode":
                context.user_data["from_results"] = False
                await SearchHandler.show_mode_selection(update, context)
            elif data == "change_mode_from_results":
                context.user_data["from_results"] = True
                await SearchHandler.show_mode_selection(update, context)
            elif data == "search_with_default":
                await SearchHandler.search_with_default_callback(update, context)
            elif data == "nft_list":
                await NFTManagementHandler.nft_command(update, context)
            elif data == "block_management":
                context.user_data["from_results"] = False
                await NFTManagementHandler.block_management_callback(update, context)
            elif data == "block_management_from_results":
                context.user_data["from_results"] = True
                await NFTManagementHandler.block_management_callback(update, context)
            elif data == "myblock_list":
                await NFTManagementHandler.myblock_command(update, context)
            elif data == "block_nft_menu":
                await NFTManagementHandler.nft_command(update, context)
            elif data == "unblock_nft_menu":
                await NFTManagementHandler.myblock_command(update, context)
            elif data.startswith("toggle_nft_"):
                if "available_nft" in context.user_data:
                    await ModelSearchHandler.handle_nft_selection(update, context)
                else:
                    await NFTManagementHandler.toggle_nft_callback(update, context)
            elif data == "search_type_selection":
                await ModelSearchHandler.show_search_type_selection(update, context)
            elif data == "model_search":
                context.user_data["from_results"] = False
                await ModelSearchHandler.show_model_selection(update, context)
            elif data == "model_search_from_results":
                context.user_data["from_results"] = True
                await ModelSearchHandler.show_model_selection(update, context)
            elif data == "start_model_search_from_single":
                selected_nft = context.user_data.get("selected_nft", [])
                if not selected_nft:
                    await query.answer("❌ Сначала выберите модели NFT", show_alert=True)
                    try:
                        await query.message.delete()
                    except:
                        pass
                    context.user_data["from_results"] = False
                    await ModelSearchHandler.show_model_selection(update, context)
                    return
                try:
                    await query.message.delete()
                except:
                    pass
                await ModelSearchHandler.start_model_search(update, context)
                return
            elif data == "search_model_dialog":
                await ModelSearchHandler.search_model_dialog_callback(update, context)
            elif data == "reset_model_search":
                await ModelSearchHandler.reset_model_search_callback(update, context)
            elif data.startswith("nft_page_"):
                await ModelSearchHandler.handle_nft_selection(update, context)
            elif data == "reset_nft_selection":
                await ModelSearchHandler.handle_nft_selection(update, context)
            elif data == "start_model_search":
                await ModelSearchHandler.start_model_search(update, context)
            elif data.startswith("model_results_page_"):
                await ModelSearchHandler.handle_results_page(update, context)
            elif data.startswith("random_results_page_"):
                await SearchHandler.handle_results_page(update, context)
            elif data.startswith("girls_results_page_"):
                await GirlsSearchHandler.handle_girls_results_page(update, context)
            elif data.startswith("single_result_"):
                await SearchHandler.handle_single_result_page(update, context)
            elif data.startswith("single_model_"):
                await ModelSearchHandler.handle_single_model_page(update, context)
            elif data.startswith("single_girl_"):
                await GirlsSearchHandler.handle_single_girl_page(update, context)
            elif data == "girls_search":
                if "found_girls" in context.user_data:
                    del context.user_data["found_girls"]
                if "current_page" in context.user_data:
                    del context.user_data["current_page"]
                await GirlsSearchHandler.start_girls_search(update, context)
            elif data == "back_to_results_search":
                await SearchHandler.show_search_results_page(update, context, page=0)
            elif data == "back_to_results_model":
                await ModelSearchHandler.show_search_results_page(update, context, page=0)
            elif data == "back_to_results_girls":
                await GirlsSearchHandler.show_girls_results_page(update, context, page=0)
            elif data == "current_page":
                await query.answer("Текущая страница", show_alert=False)
            elif data == "current_page_model":
                await query.answer("Текущий пользователь", show_alert=False)
            elif data == "current_page_girl":
                await query.answer("Текущий пользователь", show_alert=False)
            elif data == "current_page_results":
                await query.answer("Текущая страница", show_alert=False)
            elif data == "current_page_results_girls":
                await query.answer("Текущая страница", show_alert=False)
            elif data == "current_page_nft":
                await query.answer("Текущая страница", show_alert=False)
            elif data == "support_menu":
                await HelpHandler.help_menu_callback(update, context)
            elif data == "work_manual":
                await HelpHandler.work_manual_callback(update, context)
            elif data == "back_to_menu":
                try:
                    await query.message.delete()
                except:
                    pass
                await StartHandler.show_main_menu(update, context)
            else:
                await query.answer("❌ Неизвестная команда")
        except Exception as e:
            logger.error(f"Callback error: {e}")

    def run(self):
        logger.info("Основной бот запущен")
        self.application.run_polling()

# ==================== КОМАНДЫ ДЛЯ ЗЕРКАЛ ====================
async def mirror_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["waiting_for_mirror_token"] = True
    await update.message.reply_text(
        "🔧 Отправь токен своего бота.\n/cancel - отмена.\n\nПосле создания зеркала напиши @tonswisa и добавь бота в администраторы канала."
    )

async def cancel_mirror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_for_mirror_token"):
        context.user_data["waiting_for_mirror_token"] = False
        await update.message.reply_text("Отменено.")

async def stop_mirror_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = stop_user_mirrors(update.effective_user.id)
    await update.message.reply_text(f"Остановлено зеркал: {count}")

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    bot = NFTBot()
    bot.application.add_handler(CommandHandler("mirror", mirror_command))
    bot.application.add_handler(CommandHandler("mirrors", mirror_command))
    bot.application.add_handler(CommandHandler("cancel", cancel_mirror))
    bot.application.add_handler(CommandHandler("stop_mirror", stop_mirror_cmd))
    bot.run()