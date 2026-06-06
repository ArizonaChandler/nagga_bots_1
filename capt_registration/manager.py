"""Менеджер регистрации на CAPT"""
import discord
import logging
from datetime import datetime
from core.database import db
from core.config import CONFIG, save_config

logger = logging.getLogger(__name__)


class CaptRegistrationManager:
    def __init__(self):
        self.bot = None
        self.active_session = None
        self.session_info = None
        self.main_channel_id = None
        self.reserve_channel_id = None
        self.main_message_id = None
        self.reserve_message_id = None
        self.error_channel_id = None
        self.role_id = None
        self.announcement_channel_id = None
        self._load_config()
        logger.info("✅ CaptRegistrationManager инициализирован")

    def set_bot(self, bot):
        self.bot = bot

    def _load_config(self):
        self.main_channel_id = CONFIG.get('capt_reg_main_channel')
        self.reserve_channel_id = CONFIG.get('capt_reg_reserve_channel')
        self.error_channel_id = CONFIG.get('capt_error_channel')
        self.role_id = CONFIG.get('capt_role_id')
        self.announcement_channel_id = CONFIG.get('capt_alert_channel')
        
        for attr in ['main_channel_id', 'reserve_channel_id', 'error_channel_id', 'role_id', 'announcement_channel_id']:
            value = getattr(self, attr)
            if value == 'null' or value is None:
                setattr(self, attr, None)

    def _load_message_ids(self):
        session = db.capt_get_active_session()
        if session:
            self.main_message_id = session.get('main_message_id')
            self.reserve_message_id = session.get('reserve_message_id')
            self.active_session = session['id']
            self.session_info = {
                'event_name': session.get('event_name'),
                'event_time': session.get('event_time'),
                'additional_info': session.get('additional_info'),
                'started_by_name': f"<@{session['started_by']}>"
            }
        else:
            self.main_message_id = None
            self.reserve_message_id = None
            self.active_session = None
            self.session_info = None

    def set_channels(self, main_channel_id: str, reserve_channel_id: str, updated_by: str):
        CONFIG['capt_reg_main_channel'] = main_channel_id
        CONFIG['capt_reg_reserve_channel'] = reserve_channel_id
        save_config(updated_by)
        self.main_channel_id = main_channel_id
        self.reserve_channel_id = reserve_channel_id
        return True

    async def initialize_buttons(self, bot):
        self.bot = bot
        self._load_config()
        
        if not self.main_channel_id or not self.reserve_channel_id:
            print(f"⚠️ [CAPT] Каналы не настроены: main={self.main_channel_id}, reserve={self.reserve_channel_id}")
            return False
        
        try:
            main_channel = bot.get_channel(int(self.main_channel_id))
            reserve_channel = bot.get_channel(int(self.reserve_channel_id))
        except (ValueError, TypeError) as e:
            print(f"❌ [CAPT] Ошибка получения каналов: {e}")
            return False
        
        if not main_channel or not reserve_channel:
            print(f"❌ [CAPT] Каналы не найдены: main={main_channel}, reserve={reserve_channel}")
            return False
        
        # Удаляем ВСЕ сообщения бота в каналах
        async for msg in main_channel.history(limit=50):
            if msg.author == bot.user:
                await msg.delete()
        
        async for msg in reserve_channel.history(limit=50):
            if msg.author == bot.user:
                await msg.delete()
        
        self._load_message_ids()
        
        from capt_registration.embeds import create_registration_embed
        from capt_registration.views import ModerationView, PublicView
        
        main_list = db.capt_get_registrations('main')
        reserve_list = db.capt_get_registrations('reserve')
        embed = create_registration_embed(main_list, reserve_list, None)
        
        mod_view = ModerationView()
        mod_view.update_buttons(False)
        
        pub_view = PublicView()
        pub_view.set_registration_active(False)
        
        main_msg = await main_channel.send(embed=embed, view=mod_view)
        reserve_msg = await reserve_channel.send(embed=embed, view=pub_view)
        
        self.main_message_id = str(main_msg.id)
        self.reserve_message_id = str(reserve_msg.id)
        
        print(f"✅ [CAPT] Инициализирован: main={main_channel.name}, reserve={reserve_channel.name}")
        return True

    def get_lists(self):
        return db.capt_get_registrations('main'), db.capt_get_registrations('reserve')

    def is_active(self) -> bool:
        return self.active_session is not None

    async def start_registration(self, user_id: str, user_name: str, bot, event_name: str, event_time: str, additional_info: str = None):
        self._load_config()
        self.bot = bot
        
        if self.active_session:
            db.capt_end_session(self.active_session, user_id)
        
        session_id = db.capt_create_session(
            user_id, self.main_channel_id, self.reserve_channel_id,
            event_name, event_time, additional_info
        )
        
        self.active_session = session_id
        self.session_info = {
            'event_name': event_name,
            'event_time': event_time,
            'additional_info': additional_info or "",
            'started_by_name': f"<@{user_id}>"
        }
        
        db.capt_clear_all()
        
        await self._update_views(active=True)
        await self._send_announcement(event_name, event_time, additional_info)
        
        db.log_action(user_id, "CAPT_REG_START", f"Session {session_id}")
        return True

    async def end_registration(self, user_id: str):
        if self.active_session:
            db.capt_end_session(self.active_session, user_id)
        
        self.active_session = None
        self.session_info = None
        db.capt_clear_all()
        
        for channel_id in [self.main_channel_id, self.reserve_channel_id]:
            if channel_id:
                channel = self.bot.get_channel(int(channel_id))
                if channel:
                    async for msg in channel.history(limit=100):
                        if msg.author == self.bot.user and msg.components:
                            continue
                        try:
                            await msg.delete()
                        except:
                            pass
        
        await self._update_views(active=False)
        db.log_action(user_id, "CAPT_REG_END")
        return True

    async def add_participant(self, user_id: str, user_name: str):
        if not self.active_session:
            return False, "❌ Регистрация не активна"
        
        main_list, reserve_list = self.get_lists()
        
        for reg in main_list:
            if reg[1] == user_id:
                return False, "❌ Вы уже в основном списке"
        
        for reg in reserve_list:
            if reg[1] == user_id:
                return False, "❌ Вы уже в резерве"
        
        if db.capt_add_registration(user_id, user_name, 'reserve'):
            await self._update_views(active=True)
            return True, "✅ Вы добавлены в резерв"
        
        return False, "❌ Ошибка при регистрации"

    async def remove_participant(self, user_id: str):
        main_list, reserve_list = self.get_lists()
        
        found = False
        for reg in main_list:
            if reg[1] == user_id:
                found = True
                break
        if not found:
            for reg in reserve_list:
                if reg[1] == user_id:
                    found = True
                    break
        
        if not found:
            return False, "❌ Вы не были зарегистрированы"
        
        if db.capt_remove_registration(user_id):
            await self._update_views(active=True)
            return True, "✅ Вы удалены из регистрации"
        
        return False, "❌ Ошибка при удалении"

    async def move_to_main(self, reg_id: int):
        if db.capt_move_to_main(reg_id):
            await self._update_views(active=True)
            return True, "✅ Участник перемещён в основной список"
        return False, "❌ Не найден или уже в основном"

    async def move_to_reserve(self, reg_id: int):
        if db.capt_move_to_reserve(reg_id):
            await self._update_views(active=True)
            return True, "✅ Участник переведён в резерв"
        return False, "❌ Не найден или уже в резерве"

    async def move_all_to_main(self):
        moved = db.capt_move_all_to_main()
        if moved > 0:
            await self._update_views(active=True)
            return True, f"✅ {moved} участников перемещено в основной список"
        return False, "❌ В резерве нет участников"

    async def send_bulk(self, interaction, members, event_name, event_time, message):
        from capt_registration.capt_core import capt_core
        await capt_core.send_bulk(interaction, members, event_name, event_time, message)

    async def _send_announcement(self, event_name: str, event_time: str, additional_info: str = None):
        channel_id = self.announcement_channel_id
        if not channel_id:
            print("⚠️ [CAPT] Канал для @everyone не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            print(f"❌ [CAPT] Канал {channel_id} не найден")
            return
        
        reserve_channel_mention = f"<#{self.reserve_channel_id}>" if self.reserve_channel_id else "канал регистрации"
        
        embed = discord.Embed(
            title=f"🎯 НАБОР НА {event_name}",
            description=f"Для участия нажмите кнопку **ПРИСОЕДИНИТЬСЯ** в канале {reserve_channel_mention}",
            color=0xffa500,
            timestamp=datetime.now()
        )
        embed.add_field(name="⏰ Время сбора", value=f"{event_time} МСК", inline=True)
        embed.add_field(name="📋 Мероприятие", value=event_name, inline=True)
        if additional_info:
            embed.add_field(name="📝 Дополнительно", value=additional_info, inline=False)
        embed.set_footer(text="Регистрация активна")
        
        await channel.send(content="@everyone", embed=embed)
        print(f"✅ [CAPT] Отправлен @everyone в канал #{channel.name}")

    async def _update_views(self, active: bool):
        from capt_registration.embeds import create_registration_embed
        from capt_registration.views import ModerationView, PublicView
        
        if not self.bot:
            return
        
        main_list, reserve_list = self.get_lists()
        
        if self.main_channel_id and self.main_message_id:
            try:
                channel = self.bot.get_channel(int(self.main_channel_id))
                if channel:
                    msg = await channel.fetch_message(int(self.main_message_id))
                    if active:
                        embed = create_registration_embed(main_list, reserve_list, self.session_info)
                        view = ModerationView()
                        view.update_buttons(True)
                        await msg.edit(embed=embed, view=view)
                    else:
                        embed = create_registration_embed(main_list, reserve_list, None)
                        view = ModerationView()
                        view.update_buttons(False)
                        await msg.edit(embed=embed, view=view)
            except Exception as e:
                print(f"❌ [CAPT] Ошибка обновления main канала: {e}")
        
        if self.reserve_channel_id and self.reserve_message_id:
            try:
                channel = self.bot.get_channel(int(self.reserve_channel_id))
                if channel:
                    msg = await channel.fetch_message(int(self.reserve_message_id))
                    if active:
                        embed = create_registration_embed(main_list, reserve_list, self.session_info)
                        view = PublicView()
                        view.set_registration_active(True)
                        await msg.edit(embed=embed, view=view)
                    else:
                        embed = create_registration_embed(main_list, reserve_list, None)
                        view = PublicView()
                        view.set_registration_active(False)
                        await msg.edit(embed=embed, view=view)
            except Exception as e:
                print(f"❌ [CAPT] Ошибка обновления reserve канала: {e}")

    async def stop(self):
        """Остановить систему CAPT"""
        print("🎯 [CAPT] Остановка системы CAPT...")
        await self._update_views(active=False)


capt_reg_manager = CaptRegistrationManager()