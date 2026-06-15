"""Инициализация каналов системы статистики"""
import discord
import logging
from core.database import db
from stats.views import StatsPanelView, BackupPanelView
from stats.settings import StatsSettingsView

logger = logging.getLogger(__name__)


class StatsInitializer:
    
    def __init__(self, bot):
        self.bot = bot
    
    async def initialize_all(self):
        logger.info("🔄 Инициализация системы статистики...")
        print("📊 [STATS] Инициализация системы статистики...")
        
        self.stats_channel_id = db.get_setting('stats_channel')
        self.settings_channel_id = db.get_setting('stats_settings_channel')
        
        if self.stats_channel_id and self.stats_channel_id != 'null':
            await self._init_stats_channel()
        
        if self.settings_channel_id and self.settings_channel_id != 'null':
            await self._init_settings_channel()
        
        logger.info("✅ Инициализация системы статистики завершена")
        print("📊 [STATS] Инициализация завершена")
    
    async def _init_stats_channel(self):
        try:
            channel = self.bot.get_channel(int(self.stats_channel_id))
            if not channel:
                logger.error(f"❌ Канал статистики {self.stats_channel_id} не найден")
                return
        except (ValueError, TypeError):
            logger.error(f"❌ Неверный ID канала статистики: {self.stats_channel_id}")
            return
        
        # Удаляем старые сообщения
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                await msg.delete()
        
        # Отправляем новые панели
        embed = discord.Embed(
            title="📊 ПАНЕЛЬ СТАТИСТИКИ",
            description="Управление статистикой сервера",
            color=0x7289da
        )
        await channel.send(embed=embed, view=StatsPanelView())
        
        embed2 = discord.Embed(
            title="💾 ПАНЕЛЬ БЕКАПА",
            description="Управление бекапами сервера (только для супер-админа)",
            color=0xffa500
        )
        await channel.send(embed=embed2, view=BackupPanelView())
        
        print(f"📊 [STATS] Созданы панели в #{channel.name}")
    
    async def _init_settings_channel(self):
        try:
            channel = self.bot.get_channel(int(self.settings_channel_id))
            if not channel:
                logger.error(f"❌ Канал настроек {self.settings_channel_id} не найден")
                return
        except (ValueError, TypeError):
            logger.error(f"❌ Неверный ID канала настроек: {self.settings_channel_id}")
            return
        
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                await msg.delete()
        
        embed = discord.Embed(
            title="⚙️ **НАСТРОЙКА СТАТИСТИКИ**",
            description="Настройка системы статистики и бекапов",
            color=0x00ff00
        )
        await channel.send(embed=embed, view=StatsSettingsView())
        print(f"📊 [STATS] Создана панель настроек в #{channel.name}")


initializer = None

async def setup(bot):
    global initializer
    initializer = StatsInitializer(bot)
    await initializer.initialize_all()
    return initializer