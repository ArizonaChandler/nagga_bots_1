"""Инициализация каналов системы MCL"""
import discord
import logging
from datetime import datetime
import pytz
from core.database import db
from mcl_registration.embeds import create_registration_embed
from mcl_registration.views import ModerationView, PublicView
from mcl_registration.settings import MCLSettingsView
from mcl_registration.manager import mcl_manager

logger = logging.getLogger(__name__)
MSK_TZ = pytz.timezone('Europe/Moscow')


class MCLInitializer:
    """Инициализатор каналов системы MCL"""

    def __init__(self, bot):
        self.bot = bot

    async def initialize_all(self):
        """Инициализировать все каналы системы MCL"""
        logger.info("🔄 Инициализация системы MCL...")
        print("🎯 [MCL] Инициализация системы MCL/ВЗМ...")

        # Загружаем настройки из БД
        self.main_channel_id = db.get_setting('mcl_reg_main_channel')
        self.reserve_channel_id = db.get_setting('mcl_reg_reserve_channel')
        self.settings_channel_id = db.get_setting('mcl_settings_channel')

        # 1. Канал настроек (панель управления)
        await self._init_settings_channel()

        # 2. Каналы регистрации (если настроены)
        if self.main_channel_id and self.reserve_channel_id:
            await self._init_registration_channels()

        logger.info("✅ Инициализация системы MCL завершена")
        print("🎯 [MCL] Инициализация системы MCL/ВЗМ завершена")

    async def _init_settings_channel(self):
        """Канал настроек (панель управления системой)"""
        if not self.settings_channel_id:
            logger.warning("⚠️ Канал настроек MCL не настроен")
            print("⚠️ [MCL] Канал настроек MCL не настроен")
            return

        channel = self.bot.get_channel(int(self.settings_channel_id))
        if not channel:
            logger.error(f"❌ Канал настроек MCL {self.settings_channel_id} не найден")
            return

        # Удаляем старые сообщения бота
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                await msg.delete()

        # Создаём новое сообщение с панелью управления
        embed = discord.Embed(
            title="⚙️ **УПРАВЛЕНИЕ СИСТЕМОЙ MCL**",
            description="Настройка системы MCL/ВЗМ",
            color=0x00ff00
        )
        await channel.send(embed=embed, view=MCLSettingsView())
        print(f"🎯 [MCL] Создана панель управления в #{channel.name}")

    async def _init_registration_channels(self):
        """Инициализация каналов регистрации"""
        main_channel = self.bot.get_channel(int(self.main_channel_id))
        reserve_channel = self.bot.get_channel(int(self.reserve_channel_id))

        if not main_channel or not reserve_channel:
            logger.error("❌ Каналы MCL не найдены")
            return

        # Очищаем старые сообщения бота
        for channel in [main_channel, reserve_channel]:
            async for msg in channel.history(limit=50):
                if msg.author == self.bot.user:
                    await msg.delete()

        # Получаем активную сессию и списки
        session = db.mcl_get_active_session()
        main_list = db.mcl_get_registrations('main')
        reserve_list = db.mcl_get_registrations('reserve')

        session_info = None
        if session:
            session_info = {
                'event_name': session.get('event_name'),
                'event_time': session.get('event_time'),
                'additional_info': session.get('additional_info'),
                'started_by_name': f"<@{session['started_by']}>"
            }

        embed = create_registration_embed(main_list, reserve_list, session_info)

        # Отправляем сообщения с кнопками
        main_msg = await main_channel.send(embed=embed, view=ModerationView())
        reserve_msg = await reserve_channel.send(embed=embed, view=PublicView())

        # Сохраняем ID сообщений в сессии
        if session:
            db.mcl_update_session_messages(session['id'], str(main_msg.id), str(reserve_msg.id))

        print(f"🎯 [MCL] Кнопки созданы в #{main_channel.name} и #{reserve_channel.name}")


initializer = None

async def setup(bot):
    """Функция для вызова из bot.py"""
    global initializer
    initializer = MCLInitializer(bot)
    await initializer.initialize_all()
    return initializer