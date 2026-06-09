# main.py
import logging
import asyncio
from telegram import Update, ChatMember
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from bot_config import BOT_TOKEN, ADMINS
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
from handlers.menu_commands import MenuCommands
from utils import Utils

import globals

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NFTBot:
    def __init__(self):
        self.application = ApplicationBuilder().token(BOT_TOKEN).build()
        self.setup_handlers()
        self.setup_error_handler()

    def setup_error_handler(self):
        async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.error(f"Exception while handling an update: {context.error}", exc_info=True)
            
            try:
                if update and update.effective_user:
                    await context.bot.send_message(
                        chat_id=update.effective_user.id,
                        text="❌ Произошла ошибка. Пожалуйста, попробуйте еще раз или обратитесь к администратору."
                    )
            except:
                pass
        
        self.application.add_error_handler(error_handler)

    def setup_handlers(self):
        # Основные команды
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
        
        # Админ команды
        self.application.add_handler(CommandHandler("broadcast", AdminHandler.broadcast_command))
        self.application.add_handler(CommandHandler("bc", AdminHandler.quick_broadcast_command))
        
        # Медиа рассылка
        self.application.add_handler(MessageHandler(
            filters.CAPTION & (filters.PHOTO | filters.VIDEO | filters.Document.ALL) & filters.User(ADMINS), 
            AdminHandler.handle_media_broadcast
        ))
        
        # Обработчик текстовых сообщений
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_text_message
        ))
        
        # Обработчик callback запросов
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        if not update or not update.effective_user or not update.message:
            return
        
        user_id = update.effective_user.id
        
        # ПРОВЕРКА ПОДПИСКИ
        if not await Utils.check_subscription(user_id, context):
            await Utils.require_subscription(update, context)
            return
        
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
        """Обработка callback запросов"""
        if not update or not update.callback_query:
            return
        
        query = update.callback_query
        user_id = query.from_user.id
        
        # ПРОВЕРКА ПОДПИСКИ (кроме кнопки check_subscription)
        if query.data != "check_subscription":
            if not await Utils.check_subscription(user_id, context):
                context.user_data["pending_action"] = query.data
                await Utils.require_subscription(update, context)
                return
        
        await query.answer()
        data = query.data
        
        if not data:
            return
        
        try:
            logger.info(f"🔄 CALLBACK: Пользователь {query.from_user.id}, callback_data: {data}")
            
            # Кнопка проверки подписки
            if data == "check_subscription":
                if await Utils.check_subscription(user_id, context):
                    await query.answer("✅ Подписка подтверждена!", show_alert=True)
                    pending = context.user_data.pop("pending_action", None)
                    if pending:
                        query.data = pending
                        await self.handle_callback(update, context)
                    else:
                        await StartHandler.show_main_menu(update, context)
                else:
                    await query.answer("❌ Вы не подписаны на канал!", show_alert=True)
                    await Utils.require_subscription(update, context)
                return
            
            # Профиль
            elif data == "profile_menu":
                await ProfileHandler.profile_callback(update, context)
            elif data == "detailed_stats":
                await ProfileHandler.detailed_stats_callback(update, context)
            elif data == "weekly_stats":
                await ProfileHandler.weekly_stats_callback(update, context)
            elif data == "quick_settings":
                await ProfileHandler.quick_settings_callback(update, context)
            
            # Шаблоны
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
            
            # Админ панель
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
            
            # Настройки
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
            
            # Режимы поиска
            elif data.startswith("mode_"):
                await SearchHandler.mode_callback(update, context)
            
            # Поиск
            elif data == "search":
                from globals import user_modes
                
                logger.info(f"🔍 КНОПКА ПОИСКА: Пользователь {user_id} нажал 'search'")
                
                if user_id not in user_modes:
                    logger.warning(f"❌ У пользователя {user_id} не выбран режим!")
                    await query.answer("❌ Сначала выберите режим!", show_alert=True)
                    await SearchHandler.show_mode_selection(update, context)
                    return
                
                if "found_users" in context.user_data:
                    del context.user_data["found_users"]
                if "current_page" in context.user_data:
                    del context.user_data["current_page"]
                
                logger.info(f"🔍 Вызываем random_nft_search для пользователя {user_id}")
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
            
            # Управление NFT
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
            
            # Поиск по модели
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
            
            # Страницы результатов
            elif data.startswith("model_results_page_"):
                await ModelSearchHandler.handle_results_page(update, context)
            
            elif data.startswith("random_results_page_"):
                await SearchHandler.handle_results_page(update, context)
            
            elif data.startswith("girls_results_page_"):
                await GirlsSearchHandler.handle_girls_results_page(update, context)
            
            # Одиночные режимы
            elif data.startswith("single_result_"):
                await SearchHandler.handle_single_result_page(update, context)
            elif data.startswith("single_model_"):
                await ModelSearchHandler.handle_single_model_page(update, context)
            elif data.startswith("single_girl_"):
                await GirlsSearchHandler.handle_single_girl_page(update, context)
            
            # Поиск девушек
            elif data == "girls_search":
                if "found_girls" in context.user_data:
                    del context.user_data["found_girls"]
                if "current_page" in context.user_data:
                    del context.user_data["current_page"]
                
                await GirlsSearchHandler.start_girls_search(update, context)
            
            # Назад к результатам
            elif data == "back_to_results_search":
                await SearchHandler.show_search_results_page(update, context, page=0)
            elif data == "back_to_results_model":
                await ModelSearchHandler.show_search_results_page(update, context, page=0)
            elif data == "back_to_results_girls":
                await GirlsSearchHandler.show_girls_results_page(update, context, page=0)
            
            # Текущая страница
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
            
            # Поддержка
            elif data == "support_menu":
                await HelpHandler.help_menu_callback(update, context)
            elif data == "work_manual":
                await HelpHandler.work_manual_callback(update, context)

            # Главное меню
            elif data == "back_to_menu":
                try:
                    await query.message.delete()
                except:
                    pass
                await StartHandler.show_main_menu(update, context)
            
            else:
                logger.warning(f"❌ Неизвестная callback команда: {data}")
                await query.answer("❌ Неизвестная команда")
                
        except Exception as e:
            logger.error(f"❌ Ошибка в обработчике callback: {e}", exc_info=True)
            try:
                await query.answer("❌ Произошла ошибка")
            except:
                pass

    async def post_init(self):
        """Устанавливает кнопку Menu после запуска бота"""
        await MenuCommands.set_commands(self.application)

    def run(self):
        """Запуск бота"""
        logger.info("🤖 NFT Gift Bot запущен!")
        print("🤖 NFT Gift Bot запущен!")
        
        # Устанавливаем кнопку Menu (аналог post_init)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.post_init())
        
        self.application.run_polling()

if __name__ == "__main__":
    bot = NFTBot()
    bot.run()
