"""Менеджер регистрации на MCL"""
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG, save_config


class MCLRegistrationManager:
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

    def set_bot(self, bot):
        self.bot = bot

    def _load_config(self):
        self.main_channel_id = CONFIG.get('mcl_reg_main_channel')
        self.reserve_channel_id = CONFIG.get('mcl_reg_reserve_channel')
        self.error_channel_id = CONFIG.get('mcl_error_channel')
        self.role_id = CONFIG.get('mcl_role_id')
        self.announcement_channel_id = CONFIG.get('mcl_announcement_channel')
        
        for attr in ['main_channel_id', 'reserve_channel_id', 'error_channel_id', 'role_id', 'announcement_channel_id']:
            value = getattr(self, attr)
            if value == 'null' or value is None:
                setattr(self, attr, None)

    def _load_message_ids(self):
        session = db.mcl_get_active_session()
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
        CONFIG['mcl_reg_main_channel'] = main_channel_id
        CONFIG['mcl_reg_reserve_channel'] = reserve_channel_id
        save_config(updated_by)
        self.main_channel_id = main_channel_id
        self.reserve_channel_id = reserve_channel_id
        return True

    async def initialize_buttons(self, bot):
        self.bot = bot
        self._load_config()
        
        if not self.main_channel_id or not self.reserve_channel_id:
            return False
        
        try:
            main_channel = bot.get_channel(int(self.main_channel_id))
            reserve_channel = bot.get_channel(int(self.reserve_channel_id))
        except (ValueError, TypeError):
            return False
        
        if not main_channel or not reserve_channel:
            return False
        
        # Ищем существующие сообщения бота
        main_msg = None
        reserve_msg = None
        
        async for msg in main_channel.history(limit=50):
            if msg.author == bot.user and msg.embeds:
                main_msg = msg
                break
        
        async for msg in reserve_channel.history(limit=50):
            if msg.author == bot.user and msg.embeds:
                reserve_msg = msg
                break
        
        self._load_message_ids()
        
        from mcl_registration.embeds import create_registration_embed
        from mcl_registration.views import ModerationView, PublicView
        
        main_list = db.mcl_get_registrations('main')
        reserve_list = db.mcl_get_registrations('reserve')
        embed = create_registration_embed(main_list, reserve_list, self.session_info)
        
        if main_msg and reserve_msg:
            await main_msg.edit(embed=embed, view=ModerationView())
            await reserve_msg.edit(embed=embed, view=PublicView())
            self.main_message_id = str(main_msg.id)
            self.reserve_message_id = str(reserve_msg.id)
        else:
            main_msg = await main_channel.send(embed=embed, view=ModerationView())
            reserve_msg = await reserve_channel.send(embed=embed, view=PublicView())
            self.main_message_id = str(main_msg.id)
            self.reserve_message_id = str(reserve_msg.id)
        
        if self.active_session:
            db.mcl_update_session_messages(self.active_session, self.main_message_id, self.reserve_message_id)
        
        # Если нет активной сессии — деактивируем кнопки
        if not self.active_session:
            await self._update_views(active=False)
        
        return True

    def get_lists(self):
        return db.mcl_get_registrations('main'), db.mcl_get_registrations('reserve')

    def is_active(self) -> bool:
        return self.active_session is not None

    async def start_registration(self, user_id: str, user_name: str, event_name: str, event_time: str, additional_info: str = None):
        self._load_config()
        
        if self.active_session:
            db.mcl_end_session(self.active_session, user_id)
        
        session_id = db.mcl_create_session(
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
        
        db.mcl_clear_all()
        
        # Обновляем существующие сообщения (активируем кнопки)
        await self._update_views(active=True)
        await self._send_announcement(event_name, event_time, additional_info)
        
        db.log_action(user_id, "MCL_REG_START", f"Session {session_id}")
        return True

    async def end_registration(self, user_id: str):
        if self.active_session:
            db.mcl_end_session(self.active_session, user_id)
        
        self.active_session = None
        self.session_info = None
        db.mcl_clear_all()
        
        # Удаляем все сообщения в каналах, кроме embed с кнопками
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
        db.log_action(user_id, "MCL_REG_END")
        return True

    async def add_participant(self, user_id: str, user_name: str):
        if not self.active_session:
            return False, "❌ Регистрация не активна"
        
        if db.mcl_add_registration(user_id, user_name, 'reserve'):
            await self._update_views(active=True)
            return True, "✅ Вы добавлены в резерв"
        return False, "❌ Вы уже зарегистрированы"

    async def remove_participant(self, user_id: str):
        if db.mcl_remove_registration(user_id):
            await self._update_views(active=True)
            return True, "✅ Вы удалены из регистрации"
        return False, "❌ Вы не были зарегистрированы"

    async def move_to_main(self, reg_id: int):
        if db.mcl_move_to_main(reg_id):
            await self._update_views(active=True)
            return True, "✅ Участник перемещён в основной список"
        return False, "❌ Не найден или уже в основном"

    async def move_to_reserve(self, reg_id: int):
        if db.mcl_move_to_reserve(reg_id):
            await self._update_views(active=True)
            return True, "✅ Участник переведён в резерв"
        return False, "❌ Не найден или уже в резерве"

    async def move_all_to_main(self):
        moved = db.mcl_move_all_to_main()
        if moved > 0:
            await self._update_views(active=True)
            return True, f"✅ {moved} участников перемещено в основной список"
        return False, "❌ В резерве нет участников"

    async def send_bulk(self, interaction, members, event_name, event_time, message):
        from mcl_registration.mcl_core import mcl_core
        await mcl_core.send_bulk(interaction, members, event_name, event_time, message)

    async def _send_announcement(self, event_name: str, event_time: str, additional_info: str = None):
        channel_id = self.announcement_channel_id
        if not channel_id:
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
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

    async def _update_views(self, active: bool):
        from mcl_registration.embeds import create_registration_embed
        from mcl_registration.views import ModerationView, PublicView
        
        if not self.bot:
            return
        
        main_list, reserve_list = self.get_lists()
        embed = create_registration_embed(main_list, reserve_list, self.session_info if active else None)
        
        if self.main_channel_id and self.main_message_id:
            try:
                channel = self.bot.get_channel(int(self.main_channel_id))
                if channel:
                    msg = await channel.fetch_message(int(self.main_message_id))
                    view = ModerationView()
                    view.update_buttons(active)
                    await msg.edit(embed=embed, view=view)
            except:
                pass
        
        if self.reserve_channel_id and self.reserve_message_id:
            try:
                channel = self.bot.get_channel(int(self.reserve_channel_id))
                if channel:
                    msg = await channel.fetch_message(int(self.reserve_message_id))
                    view = PublicView()
                    view.set_active(active)
                    await msg.edit(embed=embed, view=view)
            except:
                pass

    async def stop(self):
        """Остановить систему MCL"""
        print("🎯 [MCL] Остановка системы MCL...")
        pass


mcl_manager = MCLRegistrationManager()