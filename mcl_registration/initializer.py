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

        # Преобразуем 'null' в None
        if self.main_channel_id == 'null' or self.main_channel_id is None:
            self.main_channel_id = None
        if self.reserve_channel_id == 'null' or self.reserve_channel_id is None:
            self.reserve_channel_id = None
        if self.settings_channel_id == 'null' or self.settings_channel_id is None:
            self.settings_channel_id = None

        # 1. Канал настроек (панель управления)
        await self._init_settings_channel()

        # 2. Каналы регистрации (только если оба настроены)
        if self.main_channel_id and self.reserve_channel_id:
            await self._init_registration_channels()
        else:
            print("🎯 [MCL] Каналы регистрации не настроены, пропускаем")

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

        # Ищем существующую панель управления
        found = False
        async for msg in channel.history(limit=100):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "УПРАВЛЕНИЕ СИСТЕМОЙ MCL" in msg.embeds[0].title:
                    await msg.edit(view=MCLSettingsView())
                    found = True
                    print(f"🎯 [MCL] Найдена существующая панель, обновлена")
                    break

        if not found:
            embed = discord.Embed(
                title="⚙️ **УПРАВЛЕНИЕ СИСТЕМОЙ MCL**",
                description="Настройка системы MCL/ВЗМ",
                color=0x00ff00
            )
            await channel.send(embed=embed, view=MCLSettingsView())
            print(f"🎯 [MCL] Создана новая панель управления в #{channel.name}")

    async def _init_registration_channels(self):
        try:
            main_channel = self.bot.get_channel(int(self.main_channel_id))
            reserve_channel = self.bot.get_channel(int(self.reserve_channel_id))
        except (ValueError, TypeError) as e:
            print(f"🎯 [MCL] Ошибка конвертации ID канала: {e}")
            return

        if not main_channel or not reserve_channel:
            logger.error("❌ Каналы MCL не найдены")
            return

        # Получаем АКТИВНУЮ сессию
        session = db.mcl_get_active_session()
        active = session is not None
        
        if session:
            mcl_manager.active_session = session['id']
            mcl_manager.session_info = {
                'event_name': session.get('event_name'),
                'event_time': session.get('event_time'),
                'additional_info': session.get('additional_info'),
                'started_by_name': f"<@{session['started_by']}>"
            }
            mcl_manager.main_message_id = session.get('main_message_id')
            mcl_manager.reserve_message_id = session.get('reserve_message_id')
            print(f"🎯 [MCL] Восстановлена активная сессия #{session['id']}")
        else:
            mcl_manager.active_session = None
            mcl_manager.session_info = None
            mcl_manager.main_message_id = None
            mcl_manager.reserve_message_id = None

        from mcl_registration.embeds import create_registration_embed
        from mcl_registration.views import ModerationView, PublicView

        main_list = db.mcl_get_registrations('main')
        reserve_list = db.mcl_get_registrations('reserve')
        
        if active and mcl_manager.session_info:
            embed = create_registration_embed(main_list, reserve_list, mcl_manager.session_info)
        else:
            embed = create_registration_embed(main_list, reserve_list, None)

        # 🔥 Восстанавливаем view с правильным состоянием кнопок
        mod_view = ModerationView()
        mod_view.update_buttons(active)  # active = True → кнопки управления АКТИВНЫ!
        
        pub_view = PublicView()
        pub_view.set_registration_active(active)  # active = True → кнопки присоединения АКТИВНЫ!

        # Ищем существующие сообщения
        main_msg = None
        reserve_msg = None

        async for msg in main_channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                main_msg = msg
                break

        async for msg in reserve_channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                reserve_msg = msg
                break

        if main_msg and reserve_msg:
            await main_msg.edit(embed=embed, view=mod_view)
            await reserve_msg.edit(embed=embed, view=pub_view)
            print(f"🎯 [MCL] Восстановлены сообщения с активными кнопками (active={active})")
            
            mcl_manager.main_message_id = str(main_msg.id)
            mcl_manager.reserve_message_id = str(reserve_msg.id)
        else:
            # Удаляем старые сообщения только если нет активных
            async for msg in main_channel.history(limit=50):
                if msg.author == self.bot.user:
                    await msg.delete()
            async for msg in reserve_channel.history(limit=50):
                if msg.author == self.bot.user:
                    await msg.delete()
            
            main_msg = await main_channel.send(embed=embed, view=mod_view)
            reserve_msg = await reserve_channel.send(embed=embed, view=pub_view)
            mcl_manager.main_message_id = str(main_msg.id)
            mcl_manager.reserve_message_id = str(reserve_msg.id)
            print(f"🎯 [MCL] Созданы новые сообщения, active={active}")

        if session:
            db.mcl_update_session_messages(session['id'], mcl_manager.main_message_id, mcl_manager.reserve_message_id)


initializer = None

async def setup(bot):
    """Функция для вызова из bot.py"""
    global initializer
    initializer = MCLInitializer(bot)
    await initializer.initialize_all()
    return initializer