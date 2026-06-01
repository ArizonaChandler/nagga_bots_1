"""Менеджер регистрации на MCL"""
import discord
import logging
from core.database import db
from core.config import CONFIG, save_config

logger = logging.getLogger(__name__)


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
        self._load_config()
        logger.info("✅ MCLRegistrationManager инициализирован")
    
    def set_bot(self, bot):
        self.bot = bot
    
    def _load_config(self):
        self.main_channel_id = CONFIG.get('mcl_reg_main_channel')
        self.reserve_channel_id = CONFIG.get('mcl_reg_reserve_channel')
        self.error_channel_id = CONFIG.get('mcl_error_channel')
        self.role_id = CONFIG.get('mcl_role_id')
        
        # Преобразуем 'null' в None
        if self.main_channel_id == 'null' or self.main_channel_id is None:
            self.main_channel_id = None
        if self.reserve_channel_id == 'null' or self.reserve_channel_id is None:
            self.reserve_channel_id = None
        if self.error_channel_id == 'null' or self.error_channel_id is None:
            self.error_channel_id = None
        if self.role_id == 'null' or self.role_id is None:
            self.role_id = None
    
    def _load_message_ids(self):
        """Загрузить ID сообщений из активной сессии"""
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
            print(f"🔍 [MCL] Загружены message_id: main={self.main_message_id}, reserve={self.reserve_message_id}")
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
        """Инициализация постоянных кнопок при старте бота"""
        self.bot = bot
        logger.info("🔄 Инициализация кнопок MCL регистрации")
        
        # Перезагружаем настройки
        self._load_config()
        
        if not self.main_channel_id or not self.reserve_channel_id:
            logger.warning("❌ Каналы MCL не настроены")
            print("🎯 [MCL] Каналы MCL не настроены")
            return False
        
        try:
            main_channel = bot.get_channel(int(self.main_channel_id))
            reserve_channel = bot.get_channel(int(self.reserve_channel_id))
        except (ValueError, TypeError) as e:
            print(f"🎯 [MCL] Ошибка конвертации ID канала: {e}")
            return False
        
        if not main_channel or not reserve_channel:
            logger.error("❌ Каналы MCL не найдены")
            print(f"🎯 [MCL] main_channel: {main_channel}, reserve_channel: {reserve_channel}")
            return False
        
        # Очищаем старые сообщения бота
        for channel in [main_channel, reserve_channel]:
            async for msg in channel.history(limit=50):
                if msg.author == bot.user:
                    await msg.delete()
        
        # Загружаем активную сессию
        self._load_message_ids()
        
        from mcl_registration.embeds import create_registration_embed
        from mcl_registration.views import ModerationView, PublicView
        
        main_list = db.mcl_get_registrations('main')
        reserve_list = db.mcl_get_registrations('reserve')
        
        embed = create_registration_embed(main_list, reserve_list, self.session_info)
        
        # Если нет сохранённых ID сообщений — создаём новые
        if not self.main_message_id or not self.reserve_message_id:
            main_msg = await main_channel.send(embed=embed, view=ModerationView())
            reserve_msg = await reserve_channel.send(embed=embed, view=PublicView())
            
            self.main_message_id = str(main_msg.id)
            self.reserve_message_id = str(reserve_msg.id)
            
            print(f"🎯 [MCL] Созданы новые сообщения: main={self.main_message_id}, reserve={self.reserve_message_id}")
            
            if self.active_session:
                db.mcl_update_session_messages(self.active_session, self.main_message_id, self.reserve_message_id)
        else:
            # Обновляем существующие сообщения
            try:
                main_msg = await main_channel.fetch_message(int(self.main_message_id))
                reserve_msg = await reserve_channel.fetch_message(int(self.reserve_message_id))
                
                await main_msg.edit(embed=embed, view=ModerationView())
                await reserve_msg.edit(embed=embed, view=PublicView())
                print(f"🎯 [MCL] Обновлены существующие сообщения")
            except Exception as e:
                print(f"🎯 [MCL] Ошибка обновления сообщений: {e}")
                # Если не удалось — создаём новые
                main_msg = await main_channel.send(embed=embed, view=ModerationView())
                reserve_msg = await reserve_channel.send(embed=embed, view=PublicView())
                
                self.main_message_id = str(main_msg.id)
                self.reserve_message_id = str(reserve_msg.id)
                
                if self.active_session:
                    db.mcl_update_session_messages(self.active_session, self.main_message_id, self.reserve_message_id)
                print(f"🎯 [MCL] Созданы новые сообщения (fallback)")
        
        return True
    
    def get_lists(self):
        return db.mcl_get_registrations('main'), db.mcl_get_registrations('reserve')
    
    def is_active(self) -> bool:
        return self.active_session is not None
    
    async def start_registration(self, user_id: str, user_name: str, event_name: str, event_time: str, additional_info: str = None):
        """Начать регистрацию"""
        print(f"🎯 [MCL] start_registration вызван")
        
        # Перезагружаем настройки
        self._load_config()
        print(f"🎯 [MCL] main_channel_id = {self.main_channel_id}")
        print(f"🎯 [MCL] reserve_channel_id = {self.reserve_channel_id}")
        
        # Завершаем предыдущую сессию
        if self.active_session:
            db.mcl_end_session(self.active_session, user_id)
        
        # Создаём новую сессию
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
        
        # Очищаем старые регистрации
        db.mcl_clear_all()
        
        # Убеждаемся, что кнопки инициализированы и ID сообщений загружены
        if not self.main_message_id or not self.reserve_message_id:
            await self.initialize_buttons(self.bot)
        else:
            # Обновляем embed и кнопки
            await self._update_views(active=True)
        
        db.log_action(user_id, "MCL_REG_START", f"Session {session_id}")
        print(f"🎯 [MCL] Регистрация начата, session_id={session_id}")
        return True
    
    async def end_registration(self, user_id: str):
        """Завершить регистрацию"""
        print(f"🎯 [MCL] end_registration вызван")
        
        if self.active_session:
            db.mcl_end_session(self.active_session, user_id)
        
        self.active_session = None
        self.session_info = None
        
        db.mcl_clear_all()
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
        """Отправить массовую рассылку"""
        from mcl_registration.mcl_core import mcl_core
        await mcl_core.send_bulk(interaction, members, event_name, event_time, message)
    
    async def _update_views(self, active: bool):
        """Обновить состояние кнопок во всех каналах"""
        from mcl_registration.embeds import create_registration_embed
        from mcl_registration.views import ModerationView, PublicView
        
        if not self.bot:
            print("❌ [MCL] self.bot = None, _update_views не может работать")
            return
        
        print(f"🔍 [MCL] _update_views active={active}")
        print(f"🔍 [MCL] main_channel_id={self.main_channel_id}, main_message_id={self.main_message_id}")
        print(f"🔍 [MCL] reserve_channel_id={self.reserve_channel_id}, reserve_message_id={self.reserve_message_id}")
        
        main_list, reserve_list = self.get_lists()
        embed = create_registration_embed(main_list, reserve_list, self.session_info if active else None)
        
        # Обновляем канал модерации
        if self.main_channel_id and self.main_message_id:
            try:
                channel = self.bot.get_channel(int(self.main_channel_id))
                if channel:
                    msg = await channel.fetch_message(int(self.main_message_id))
                    view = ModerationView()
                    view.update_buttons(active)
                    await msg.edit(embed=embed, view=view)
                    print(f"✅ [MCL] Канал модерации обновлён")
                else:
                    print(f"❌ [MCL] Канал {self.main_channel_id} не найден")
            except Exception as e:
                print(f"❌ [MCL] Ошибка канала модерации: {e}")
        else:
            print(f"⚠️ [MCL] Пропускаем канал модерации")
        
        # Обновляем публичный канал
        if self.reserve_channel_id and self.reserve_message_id:
            try:
                channel = self.bot.get_channel(int(self.reserve_channel_id))
                if channel:
                    msg = await channel.fetch_message(int(self.reserve_message_id))
                    view = PublicView()
                    view.set_active(active)
                    await msg.edit(embed=embed, view=view)
                    print(f"✅ [MCL] Публичный канал обновлён")
                else:
                    print(f"❌ [MCL] Канал {self.reserve_channel_id} не найден")
            except Exception as e:
                print(f"❌ [MCL] Ошибка публичного канала: {e}")
        else:
            print(f"⚠️ [MCL] Пропускаем публичный канал")


mcl_manager = MCLRegistrationManager()