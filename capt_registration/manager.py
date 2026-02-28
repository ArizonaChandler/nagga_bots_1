"""Менеджер регистрации на CAPT"""
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG, save_config

class CaptRegistrationManager:
    def __init__(self):
        self.active_session = None
        self.main_channel_id = None
        self.reserve_channel_id = None
        self.main_message_id = None
        self.reserve_message_id = None
        self._load_config()
    
    def _load_config(self):
        """Загрузка настроек из CONFIG"""
        self.main_channel_id = CONFIG.get('capt_reg_main_channel')
        self.reserve_channel_id = CONFIG.get('capt_reg_reserve_channel')
    
    def set_channels(self, main_channel_id: str, reserve_channel_id: str, updated_by: str):
        """Установка каналов для регистрации"""
        CONFIG['capt_reg_main_channel'] = main_channel_id
        CONFIG['capt_reg_reserve_channel'] = reserve_channel_id
        save_config(updated_by)
        self.main_channel_id = main_channel_id
        self.reserve_channel_id = reserve_channel_id
    
    async def start_registration(self, user_id: str, user_name: str, bot):
        """Начать регистрацию"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Завершаем предыдущую активную сессию если есть
            cursor.execute('UPDATE capt_sessions SET is_active = 0 WHERE is_active = 1')
            
            # Создаём новую сессию
            cursor.execute('''
                INSERT INTO capt_sessions 
                (is_active, started_by, started_at, main_channel_id, reserve_channel_id)
                VALUES (1, ?, CURRENT_TIMESTAMP, ?, ?)
            ''', (user_id, self.main_channel_id, self.reserve_channel_id))
            
            session_id = cursor.lastrowid
            conn.commit()
        
        self.active_session = session_id
        
        # Отправляем начальные embed в оба канала
        await self._send_initial_embeds(bot)
        
        db.log_action(user_id, "CAPT_REG_START", f"Session {session_id}")
        return True
    
    async def end_registration(self, user_id: str, bot):
        """Завершить регистрацию (очистить всё)"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Очищаем всех участников
            cursor.execute('DELETE FROM capt_registrations WHERE is_active = 1')
            
            # Завершаем сессию
            cursor.execute('''
                UPDATE capt_sessions 
                SET is_active = 0, ended_by = ?, ended_at = CURRENT_TIMESTAMP
                WHERE is_active = 1
            ''', (user_id,))
            
            conn.commit()
        
        self.active_session = None
        
        # Обновляем embed в обоих каналах (пустые списки)
        await self._update_all_embeds(bot, clear=True)
        
        db.log_action(user_id, "CAPT_REG_END")
        return True
    
    async def add_participant(self, user_id: str, user_name: str, bot):
        """Добавить участника (всегда в резерв)"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже
            cursor.execute('SELECT 1 FROM capt_registrations WHERE user_id = ? AND is_active = 1', (user_id,))
            if cursor.fetchone():
                return False, "Ты уже зарегистрирован"
            
            # Добавляем в резерв
            cursor.execute('''
                INSERT INTO capt_registrations (user_id, user_name, list_type)
                VALUES (?, ?, 'reserve')
            ''', (user_id, user_name))
            
            conn.commit()
        
        # Обновляем embed
        await self._update_all_embeds(bot)
        
        db.log_action(user_id, "CAPT_REG_JOIN")
        return True, "✅ Ты добавлен в резерв"
    
    async def remove_participant(self, user_id: str, bot):
        """Удалить участника"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM capt_registrations 
                WHERE user_id = ? AND is_active = 1
            ''', (user_id,))
            removed = cursor.rowcount > 0
            conn.commit()
        
        if removed:
            await self._update_all_embeds(bot)
            db.log_action(user_id, "CAPT_REG_LEAVE")
            return True, "✅ Ты удалён из регистрации"
        return False, "❌ Ты не был зарегистрирован"
    
    async def move_to_main(self, user_id: str, target_user_id: str, bot):
        """Перевести пользователя в основной список"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE capt_registrations 
                SET list_type = 'main'
                WHERE user_id = ? AND is_active = 1
            ''', (target_user_id,))
            moved = cursor.rowcount > 0
            conn.commit()
        
        if moved:
            await self._update_all_embeds(bot)
            db.log_action(user_id, "CAPT_REG_TO_MAIN", f"User {target_user_id}")
            return True, f"✅ <@{target_user_id}> переведён в основной список"
        return False, "❌ Пользователь не найден"
    
    async def move_to_reserve(self, user_id: str, target_user_id: str, bot):
        """Перевести пользователя в резерв"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE capt_registrations 
                SET list_type = 'reserve'
                WHERE user_id = ? AND is_active = 1
            ''', (target_user_id,))
            moved = cursor.rowcount > 0
            conn.commit()
        
        if moved:
            await self._update_all_embeds(bot)
            db.log_action(user_id, "CAPT_REG_TO_RESERVE", f"User {target_user_id}")
            return True, f"✅ <@{target_user_id}> переведён в резерв"
        return False, "❌ Пользователь не найден"
    
    def get_lists(self):
        """Получить текущие списки"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, user_name FROM capt_registrations 
                WHERE is_active = 1 AND list_type = 'main'
                ORDER BY registered_at
            ''')
            main_list = cursor.fetchall()
            
            cursor.execute('''
                SELECT user_id, user_name FROM capt_registrations 
                WHERE is_active = 1 AND list_type = 'reserve'
                ORDER BY registered_at
            ''')
            reserve_list = cursor.fetchall()
            
            return main_list, reserve_list
    
    async def _send_initial_embeds(self, bot):
        """Отправить начальные embed в оба канала"""
        from capt_registration.embeds import create_registration_embed
        
        embed = create_registration_embed([], [])
        
        # Отправляем в канал модерации
        main_channel = bot.get_channel(int(self.main_channel_id))
        if main_channel:
            from capt_registration.views import ModerationView
            msg = await main_channel.send(embed=embed, view=ModerationView())
            self.main_message_id = str(msg.id)
        
        # Отправляем в канал для всех
        reserve_channel = bot.get_channel(int(self.reserve_channel_id))
        if reserve_channel:
            from capt_registration.views import PublicView
            msg = await reserve_channel.send(embed=embed, view=PublicView())
            self.reserve_message_id = str(msg.id)
        
        # Сохраняем ID сообщений в сессии
        if self.active_session:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE capt_sessions 
                    SET main_message_id = ?, reserve_message_id = ?
                    WHERE id = ?
                ''', (self.main_message_id, self.reserve_message_id, self.active_session))
                conn.commit()
    
    async def _update_all_embeds(self, bot, clear=False):
        """Обновить embed в обоих каналах"""
        from capt_registration.embeds import create_registration_embed
        
        if clear:
            main_list, reserve_list = [], []
        else:
            main_list, reserve_list = self.get_lists()
        
        embed = create_registration_embed(main_list, reserve_list)
        
        # Обновляем в канале модерации
        if self.main_channel_id and self.main_message_id:
            channel = bot.get_channel(int(self.main_channel_id))
            if channel:
                try:
                    msg = await channel.fetch_message(int(self.main_message_id))
                    await msg.edit(embed=embed)
                except:
                    pass
        
        # Обновляем в канале для всех
        if self.reserve_channel_id and self.reserve_message_id:
            channel = bot.get_channel(int(self.reserve_channel_id))
            if channel:
                try:
                    msg = await channel.fetch_message(int(self.reserve_message_id))
                    await msg.edit(embed=embed)
                except:
                    pass

# Глобальный экземпляр
capt_reg_manager = CaptRegistrationManager()