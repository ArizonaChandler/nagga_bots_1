"""Менеджер регистрации на MCL"""
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG, save_config
from server_stats.global_collector import get_collector


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
            print(f"⚠️ [MCL] Каналы не настроены: main={self.main_channel_id}, reserve={self.reserve_channel_id}")
            return False
        
        try:
            main_channel = bot.get_channel(int(self.main_channel_id))
            reserve_channel = bot.get_channel(int(self.reserve_channel_id))
        except (ValueError, TypeError) as e:
            print(f"❌ [MCL] Ошибка получения каналов: {e}")
            return False
        
        if not main_channel or not reserve_channel:
            print(f"❌ [MCL] Каналы не найдены: main={main_channel}, reserve={reserve_channel}")
            return False
        
        # 🔥 ПРОВЕРЯЕМ АКТИВНУЮ СЕССИЮ ДО УДАЛЕНИЯ
        session = db.mcl_get_active_session()
        active = session is not None
        
        if session:
            self.active_session = session['id']
            self.session_info = {
                'event_name': session.get('event_name'),
                'event_time': session.get('event_time'),
                'additional_info': session.get('additional_info'),
                'started_by_name': f"<@{session['started_by']}>"
            }
            self.main_message_id = session.get('main_message_id')
            self.reserve_message_id = session.get('reserve_message_id')
            print(f"🎯 [MCL] Восстановлена активная сессия #{session['id']}, active={active}")
        else:
            self.active_session = None
            self.session_info = None
            self.main_message_id = None
            self.reserve_message_id = None
            print(f"🎯 [MCL] Активных сессий нет, active={active}")
        
        from mcl_registration.embeds import create_registration_embed
        from mcl_registration.views import ModerationView, PublicView
        
        main_list = db.mcl_get_registrations('main')
        reserve_list = db.mcl_get_registrations('reserve')
        
        if active and self.session_info:
            embed = create_registration_embed(main_list, reserve_list, self.session_info)
        else:
            embed = create_registration_embed(main_list, reserve_list, None)
        
        # 🔥 СОЗДАЁМ VIEW С ПРАВИЛЬНЫМ СОСТОЯНИЕМ КНОПОК
        mod_view = ModerationView()
        mod_view.update_buttons(active)  # если active=True, кнопки управления будут АКТИВНЫ
        
        pub_view = PublicView()
        pub_view.set_registration_active(active)  # если active=True, кнопки присоединения будут АКТИВНЫ
        
        # 🔥 ИЩЕМ СУЩЕСТВУЮЩИЕ СООБЩЕНИЯ (НЕ УДАЛЯЕМ!)
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
        
        if main_msg and reserve_msg:
            # ✅ ОБНОВЛЯЕМ существующие сообщения
            await main_msg.edit(embed=embed, view=mod_view)
            await reserve_msg.edit(embed=embed, view=pub_view)
            print(f"🎯 [MCL] Обновлены существующие сообщения, active={active}")
            
            self.main_message_id = str(main_msg.id)
            self.reserve_message_id = str(reserve_msg.id)
        else:
            # ✅ Удаляем старые сообщения ТОЛЬКО если нет существующих
            async for msg in main_channel.history(limit=50):
                if msg.author == bot.user:
                    await msg.delete()
            async for msg in reserve_channel.history(limit=50):
                if msg.author == bot.user:
                    await msg.delete()
            
            main_msg = await main_channel.send(embed=embed, view=mod_view)
            reserve_msg = await reserve_channel.send(embed=embed, view=pub_view)
            self.main_message_id = str(main_msg.id)
            self.reserve_message_id = str(reserve_msg.id)
            print(f"🎯 [MCL] Созданы новые сообщения, active={active}")
        
        if session:
            db.mcl_update_session_messages(session['id'], self.main_message_id, self.reserve_message_id)
        
        print(f"✅ [MCL] Инициализирован: main={main_channel.name}, reserve={reserve_channel.name}")
        return True

    def get_lists(self):
        return db.mcl_get_registrations('main'), db.mcl_get_registrations('reserve')

    def is_active(self) -> bool:
        return self.active_session is not None

    async def start_registration(self, user_id: str, user_name: str, bot, event_name: str, event_time: str, additional_info: str = None):
        self._load_config()
        self.bot = bot
        
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
        
        await self._update_views(session_active=True)
        await self._send_announcement(event_name, event_time, additional_info)
        
        from server_stats.global_collector import get_collector
        collector = get_collector()
        if collector:
            collector.increment_mcl_registration()
        
        db.log_action(user_id, "MCL_REG_START", f"Session {session_id}")
        return True

    async def end_registration(self, user_id: str):
        if self.active_session:
            # ========== НАЧИСЛЕНИЕ БАЛЛОВ УЧАСТНИКАМ (только если модуль включён) ==========
            from core.module_manager import MODULES
            
            # Проверяем, включён ли модуль экономики
            if MODULES.get("economy", {}).get("enabled", False):
                from economy.manager import economy_manager
                
                main_list, reserve_list = self.get_lists()
                
                # Начисляем баллы участникам основного списка
                for reg in main_list:
                    _, uid, _ = reg
                    await economy_manager.award_mcl(int(uid), is_main=True)
                
                # Начисляем баллы участникам резервного списка
                for reg in reserve_list:
                    _, uid, _ = reg
                    await economy_manager.award_mcl(int(uid), is_main=False)
                
                print(f"💰 [MCL] Начислены баллы: основной={len(main_list)}, резерв={len(reserve_list)}")
            else:
                print(f"⚠️ [MCL] Модуль экономики выключен, баллы не начислены")
            
            db.mcl_end_session(self.active_session, user_id)
        
        self.active_session = None
        self.session_info = None
        db.mcl_clear_all()
        
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
        
        await self._update_views(session_active=False)
        db.log_action(user_id, "MCL_REG_END")
        return True

    async def add_participant(self, user_id: str, user_name: str):
        if not self.active_session:
            return False, "❌ Регистрация не активна"
        
        # Проверяем, не зарегистрирован ли уже
        existing = db.mcl_get_registrations()
        for reg in existing:
            if reg[1] == user_id:
                return False, "❌ Вы уже зарегистрированы"
        
        if db.mcl_add_registration(user_id, user_name, 'reserve'):
            await self._update_views(session_active=True)
            return True, "✅ Вы добавлены в резерв"
        return False, "❌ Ошибка при регистрации"

    async def remove_participant(self, user_id: str):
        if db.mcl_remove_registration(user_id):
            await self._update_views(session_active=True)
            return True, "✅ Вы удалены из регистрации"
        return False, "❌ Вы не были зарегистрированы"

    async def move_to_main(self, reg_id: int):
        """Переместить участника из резерва в основной"""
        if db.mcl_move_to_main(reg_id):
            await self._update_views(session_active=True)
            return True, "✅ Участник перемещён в основной список"
        return False, "❌ Не найден или уже в основном"

    async def move_to_reserve(self, reg_id: int):
        """Переместить участника из основного в резерв"""
        if db.mcl_move_to_reserve(reg_id):
            await self._update_views(session_active=True)
            return True, "✅ Участник переведён в резерв"
        return False, "❌ Не найден или уже в резерве"

    async def move_all_to_main(self):
        """Переместить всех из резерва в основной"""
        moved = db.mcl_move_all_to_main()
        if moved > 0:
            await self._update_views(session_active=True)
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

    async def _update_views(self, session_active: bool = False):
        from mcl_registration.embeds import create_registration_embed
        from mcl_registration.views import ModerationView, PublicView
        
        if not self.bot:
            return
        
        # Получаем свежие списки ПРЯМО ИЗ БД
        main_list = db.mcl_get_registrations('main')
        reserve_list = db.mcl_get_registrations('reserve')
        
        if self.main_channel_id and self.main_message_id:
            try:
                channel = self.bot.get_channel(int(self.main_channel_id))
                if channel:
                    msg = await channel.fetch_message(int(self.main_message_id))
                    
                    # Создаём embed с актуальными списками
                    if session_active and self.session_info:
                        embed = create_registration_embed(main_list, reserve_list, self.session_info)
                    else:
                        embed = create_registration_embed(main_list, reserve_list, None)
                    
                    view = ModerationView()
                    view.update_buttons(session_active)
                    await msg.edit(embed=embed, view=view)
                    print(f"✅ [MCL] Обновлён main канал: основной={len(main_list)}, резерв={len(reserve_list)}")
            except Exception as e:
                print(f"❌ [MCL] Ошибка обновления main канала: {e}")
        
        if self.reserve_channel_id and self.reserve_message_id:
            try:
                channel = self.bot.get_channel(int(self.reserve_channel_id))
                if channel:
                    msg = await channel.fetch_message(int(self.reserve_message_id))
                    
                    # Создаём embed с актуальными списками
                    if session_active and self.session_info:
                        embed = create_registration_embed(main_list, reserve_list, self.session_info)
                    else:
                        embed = create_registration_embed(main_list, reserve_list, None)
                    
                    view = PublicView()
                    view.set_registration_active(session_active)
                    await msg.edit(embed=embed, view=view)
                    print(f"✅ [MCL] Обновлён reserve канал: основной={len(main_list)}, резерв={len(reserve_list)}")
            except Exception as e:
                print(f"❌ [MCL] Ошибка обновления reserve канала: {e}")

    async def stop(self):
        """Остановить систему MCL (выключаем модуль полностью)"""
        print("🎯 [MCL] Остановка системы MCL...")
        from mcl_registration.embeds import create_registration_embed
        
        if self.main_channel_id and self.main_message_id:
            try:
                channel = self.bot.get_channel(int(self.main_channel_id))
                if channel:
                    msg = await channel.fetch_message(int(self.main_message_id))
                    embed = discord.Embed(
                        title="⛔ 🎯 MCL/ВЗМ Регистрация",
                        description="**Система отключена администратором**\nОбратитесь к администрации для включения.",
                        color=0x808080
                    )
                    await msg.edit(embed=embed, view=None)
            except:
                pass
        
        if self.reserve_channel_id and self.reserve_message_id:
            try:
                channel = self.bot.get_channel(int(self.reserve_channel_id))
                if channel:
                    msg = await channel.fetch_message(int(self.reserve_message_id))
                    embed = discord.Embed(
                        title="⛔ 🎯 MCL/ВЗМ Регистрация",
                        description="**Система отключена администратором**\nОбратитесь к администрации для включения.",
                        color=0x808080
                    )
                    await msg.edit(embed=embed, view=None)
            except:
                pass


mcl_manager = MCLRegistrationManager()