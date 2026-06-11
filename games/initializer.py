"""Инициализация каналов системы игр"""
import discord
import logging
from games.battleship.embeds import get_rules_embed, get_top_embed
from games.battleship.views import GameLobbyView
from games.settings import GamesSettingsView
from core.database import db

logger = logging.getLogger(__name__)


class GamesInitializer:
    """Инициализатор каналов системы игр"""

    def __init__(self, bot):
        self.bot = bot

    async def initialize_all(self):
        """Инициализировать все каналы системы игр"""
        logger.info("🔄 Инициализация системы игр...")
        print("🎮 [Games] Инициализация системы игр...")

        # Загружаем настройки ИЗ БД напрямую
        self.rules_channel_id = db.get_setting('games_rules_channel')
        self.lobby_channel_id = db.get_setting('games_lobby_channel')
        self.log_channel_id = db.get_setting('games_log_channel')
        self.settings_channel_id = db.get_setting('games_settings_channel')
        self.category_id = db.get_setting('games_category_id')

        # 1. Канал с правилами
        await self._init_rules_channel()

        # 2. Канал лобби
        await self._init_lobby_channel()

        # 3. Канал логов
        await self._init_log_channel()

        # 4. Канал настроек
        await self._init_settings_channel()

        logger.info("✅ Инициализация системы игр завершена")
        print("🎮 [Games] Инициализация системы игр завершена")

    async def _init_rules_channel(self):
        """Канал с правилами игры"""
        # Получаем ID из БД напрямую, а не из self
        rules_channel_id = db.get_setting('games_rules_channel')
        
        if not rules_channel_id:
            logger.warning("⚠️ Канал правил игр не настроен")
            print("⚠️ [Games] Канал правил игр не настроен")
            return

        channel = self.bot.get_channel(int(rules_channel_id))
        if not channel:
            logger.error(f"❌ Канал правил игр {rules_channel_id} не найден")
            print(f"❌ [Games] Канал правил игр {rules_channel_id} не найден")
            return

        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "МОРСКОЙ БОЙ" in msg.embeds[0].title:
                    await msg.edit(embed=get_rules_embed())
                    logger.info(f"✅ Обновлён embed правил в #{channel.name}")
                    return

        await channel.send(embed=get_rules_embed())
        logger.info(f"✅ Создан embed правил в #{channel.name}")

    async def _init_lobby_channel(self):
        lobby_channel_id = db.get_setting('games_lobby_channel')
        
        if not lobby_channel_id:
            logger.warning("⚠️ Канал лобби игр не настроен")
            return

        channel = self.bot.get_channel(int(lobby_channel_id))
        if not channel:
            logger.error(f"❌ Канал лобби игр {lobby_channel_id} не найден")
            return

        from games.battleship.views import GameLobbyView
        
        # Удаляем старые сообщения
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                await msg.delete()
        
        # Создаём новое сообщение с view
        view = GameLobbyView(self.bot, lobby_channel_id)
        embed = get_lobby_embed([], [])  # или view.update_embed() создаст embed
        await channel.send(embed=embed, view=view)
        logger.info(f"✅ Создана панель лобби в #{channel.name}")

    async def _init_log_channel(self):
        """Канал логов игр"""
        if not self.log_channel_id:
            logger.warning("⚠️ Канал логов игр не настроен")
            return

        channel = self.bot.get_channel(int(self.log_channel_id))
        if not channel:
            logger.error(f"❌ Канал логов игр {self.log_channel_id} не найден")
            return

        logger.info(f"✅ Канал логов игр: #{channel.name}")

    async def _init_settings_channel(self):
        """Канал настроек игр"""
        if not self.settings_channel_id:
            logger.warning("⚠️ Канал настроек игр не настроен")
            return

        channel = self.bot.get_channel(int(self.settings_channel_id))
        if not channel:
            logger.error(f"❌ Канал настроек игр {self.settings_channel_id} не найден")
            return

        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "НАСТРОЙКИ ИГР" in msg.embeds[0].title:
                    await msg.edit(view=GamesSettingsView())
                    logger.info(f"✅ Обновлена панель настроек игр в #{channel.name}")
                    return

        embed = discord.Embed(
            title="⚙️ **НАСТРОЙКИ ИГР**",
            description="Настройка системы игр Discord",
            color=0x00ff00
        )
        await channel.send(embed=embed, view=GamesSettingsView())
        logger.info(f"✅ Создана панель настроек игр в #{channel.name}")

    async def stop(self):
        """Остановить систему игр"""
        print("🎮 [GAMES] Остановка системы игр...")
        
        # Очищаем лобби
        if self.lobby_channel_id:
            channel = self.bot.get_channel(int(self.lobby_channel_id))
            if channel:
                async for msg in channel.history(limit=50):
                    if msg.author == self.bot.user and msg.embeds:
                        await msg.edit(
                            embed=discord.Embed(
                                title="🎮 **ИГРЫ DISCORD**",
                                description="⛔ **Система отключена администратором**\nОбратитесь к администрации для включения.",
                                color=0x808080
                            ),
                            view=None
                        )
                        break


# Глобальный экземпляр
initializer = None

async def setup(bot):
    global initializer
    from games.manager import setup as setup_manager
    initializer = GamesInitializer(bot)
    await initializer.initialize_all()
    await setup_manager(bot)
    return initializer