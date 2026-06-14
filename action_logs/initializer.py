"""Инициализация системы логов"""
import logging
from core.database import db
from action_logs.views import ActionLogsPanelView
from action_logs.settings_view import ActionLogsSettingsView
from action_logs.manager import action_logs_manager

logger = logging.getLogger(__name__)


class ActionLogsInitializer:
    
    def __init__(self, bot):
        self.bot = bot
    
    async def initialize_all(self):
        logger.info("🔄 Инициализация системы логов...")
        print("📋 [ACTION_LOGS] Инициализация...")
        
        action_logs_manager.set_bot(self.bot)
        
        self.public_channel_id = db.get_setting('action_logs_channel')
        self.settings_channel_id = db.get_setting('action_logs_settings_channel')
        
        if self.public_channel_id:
            await self._init_public_channel()
        
        if self.settings_channel_id:
            await self._init_settings_channel()
        
        logger.info("✅ Инициализация системы логов завершена")
        print("📋 [ACTION_LOGS] Инициализация завершена")
    
    async def _init_public_channel(self):
        channel = self.bot.get_channel(int(self.public_channel_id))
        if not channel:
            logger.error(f"❌ Канал логов {self.public_channel_id} не найден")
            return
        
        found = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.components:
                await msg.edit(view=ActionLogsPanelView())
                found = True
                print(f"📋 [ACTION_LOGS] Обновлена панель в #{channel.name}")
                break
        
        if not found:
            embed = discord.Embed(
                title="📋 **ЛОГИ ДЕЙСТВИЙ**",
                description="Просмотр и поиск записей о действиях на сервере\n\n"
                            "**Доступные функции:**\n"
                            "└ 📋 Последние логи — последние 30 записей\n"
                            "└ 🔍 Поиск по пользователю — все действия конкретного пользователя\n"
                            "└ 🎯 Поиск по событию — все записи определённого типа\n"
                            "└ 📊 Статистика — общая информация по логам",
                color=0x7289da
            )
            await channel.send(embed=embed, view=ActionLogsPanelView())
            print(f"📋 [ACTION_LOGS] Создана панель в #{channel.name}")
    
    async def _init_settings_channel(self):
        channel = self.bot.get_channel(int(self.settings_channel_id))
        if not channel:
            logger.error(f"❌ Канал настроек {self.settings_channel_id} не найден")
            return
        
        found = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                await msg.edit(view=ActionLogsSettingsView())
                found = True
                print(f"📋 [ACTION_LOGS] Обновлена панель настроек в #{channel.name}")
                break
        
        if not found:
            embed = discord.Embed(
                title="⚙️ **НАСТРОЙКА ЛОГОВ ДЕЙСТВИЙ**",
                description="Настройка системы логирования",
                color=0x00ff00
            )
            await channel.send(embed=embed, view=ActionLogsSettingsView())
            print(f"📋 [ACTION_LOGS] Создана панель настроек в #{channel.name}")


initializer = None

async def setup(bot):
    global initializer
    initializer = ActionLogsInitializer(bot)
    await initializer.initialize_all()
    return initializer