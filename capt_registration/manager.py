"""Менеджер регистрации на CAPT"""
import discord
import logging
from datetime import datetime
from core.database import db
from core.config import CONFIG, save_config

logger = logging.getLogger(__name__)

class CaptRegistrationManager:
    def __init__(self):
        self.active_session = None
        self.main_channel_id = None
        self.reserve_channel_id = None
        self.alert_channel_id = None
        self.main_message_id = None
        self.reserve_message_id = None
        self.capt_info = None
        self._load_config()
        logger.info("✅ CaptRegistrationManager инициализирован")
    
    def _load_config(self):
        """Загрузка настроек из CONFIG"""
        self.main_channel_id = CONFIG.get('capt_reg_main_channel')
        self.reserve_channel_id = CONFIG.get('capt_reg_reserve_channel')
        self.alert_channel_id = CONFIG.get('capt_alert_channel')  # Добавляем
        
        # Если в CONFIG нет, пробуем загрузить из БД напрямую
        if not self.main_channel_id or not self.reserve_channel_id or not self.alert_channel_id:
            from core.database import db
            settings = db.get_all_settings()
            if 'capt_reg_main_channel' in settings:
                self.main_channel_id = settings['capt_reg_main_channel']
                CONFIG['capt_reg_main_channel'] = self.main_channel_id
            if 'capt_reg_reserve_channel' in settings:
                self.reserve_channel_id = settings['capt_reg_reserve_channel']
                CONFIG['capt_reg_reserve_channel'] = self.reserve_channel_id
            if 'capt_alert_channel' in settings:  # Добавляем
                self.alert_channel_id = settings['capt_alert_channel']
                CONFIG['capt_alert_channel'] = self.alert_channel_id
        
        logger.debug(f"Загружены каналы: main={self.main_channel_id}, reserve={self.reserve_channel_id}, alert={self.alert_channel_id}")
    
    def set_channels(self, main_channel_id: str, reserve_channel_id: str, updated_by: str):
        """Установка каналов для регистрации"""
        logger.info(f"Установка каналов: main={main_channel_id}, reserve={reserve_channel_id}")
        
        # Сохраняем в CONFIG
        CONFIG['capt_reg_main_channel'] = main_channel_id
        CONFIG['capt_reg_reserve_channel'] = reserve_channel_id
        
        # Сохраняем в БД
        save_config(updated_by)
        
        # Обновляем локальные переменные
        self.main_channel_id = main_channel_id
        self.reserve_channel_id = reserve_channel_id
        
        logger.info(f"✅ Каналы сохранены в CONFIG и БД")
        return True
    
    async def initialize_buttons(self, bot):
        """Инициализация постоянных кнопок при старте бота"""
        logger.info("🔄 Инициализация постоянных кнопок CAPT регистрации")
        
        if not self.main_channel_id or not self.reserve_channel_id:
            logger.warning("❌ Каналы не настроены, пропускаем инициализацию")
            return False
        
        try:
            main_channel = bot.get_channel(int(self.main_channel_id))
            reserve_channel = bot.get_channel(int(self.reserve_channel_id))
            
            if not main_channel:
                logger.error(f"❌ Канал модерации {self.main_channel_id} не найден")
                return False
            
            if not reserve_channel:
                logger.error(f"❌ Публичный канал {self.reserve_channel_id} не найден")
                return False
            
            logger.info(f"✅ Каналы найдены: #{main_channel.name} и #{reserve_channel.name}")
            
            # Очищаем старые сообщения бота
            await self._clean_old_messages(main_channel)
            await self._clean_old_messages(reserve_channel)
            
            # Получаем текущие списки
            from capt_registration.embeds import create_registration_embed
            from capt_registration.views import ModerationView, PublicView
            
            main_list, reserve_list = self.get_lists()
            embed = create_registration_embed(main_list, reserve_list)
            
            # Отправляем новые сообщения
            main_msg = await main_channel.send(embed=embed, view=ModerationView())
            reserve_msg = await reserve_channel.send(embed=embed, view=PublicView())
            
            self.main_message_id = str(main_msg.id)
            self.reserve_message_id = str(reserve_msg.id)
            
            # Если есть активная сессия, обновляем ID сообщений
            if self.active_session:
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE capt_sessions 
                        SET main_message_id = ?, reserve_message_id = ?
                        WHERE id = ?
                    ''', (self.main_message_id, self.reserve_message_id, self.active_session))
                    conn.commit()
            
            logger.info(f"✅ Постоянные кнопки отправлены: main_msg={main_msg.id}, reserve_msg={reserve_msg.id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации кнопок: {e}", exc_info=True)
            return False
    
    async def _clean_old_messages(self, channel):
        """Очистка старых сообщений бота в канале"""
        try:
            async for msg in channel.history(limit=20):
                if msg.author == channel.guild.me:
                    await msg.delete()
            logger.debug(f"Очищены старые сообщения в #{channel.name}")
        except Exception as e:
            logger.error(f"Ошибка очистки канала {channel.name}: {e}")
    
    async def start_registration(self, user_id: str, user_name: str, bot, enemy: str = None, teleport_time: str = None, additional_info: str = None):
        """Начать регистрацию с информацией о CAPT"""
        logger.info(f"Старт регистрации от {user_name} ({user_id})")
        
        # Сохраняем информацию о CAPT
        self.capt_info = {
            'enemy': enemy,
            'teleport_time': teleport_time,
            'additional_info': additional_info or "Нет",
            'started_by': f"<@{user_id}>",
            'started_by_name': user_name
        }
        
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
        logger.info(f"✅ Сессия создана: {session_id}")
        
        # Отправляем оповещение @everyone в публичный канал
        await self._send_capt_announcement(bot)
        
        # Активируем кнопки в публичном чате
        await self._update_public_buttons(bot, active=True)
        
        # Обновляем кнопки в чате модерации
        await self._update_moderation_buttons(bot, active=True)
        
        db.log_action(user_id, "CAPT_REG_START", f"Session {session_id}")
        return True

    async def _send_capt_announcement(self, bot):
        """Отправить оповещение о начале CAPT в настроенный канал"""
        if not self.capt_info:
            return
        
        # Получаем ID канала для оповещений из CONFIG
        alert_channel_id = CONFIG.get('capt_alert_channel')
        if not alert_channel_id:
            logger.warning("❌ Канал для оповещений CAPT не настроен")
            return
        
        try:
            channel = bot.get_channel(int(alert_channel_id))
            if not channel:
                logger.error(f"❌ Канал оповещений {alert_channel_id} не найден")
                return
            
            # Создаём красивое оповещение
            embed = discord.Embed(
                title="🎯 **НАБОР НА CAPT**",
                description=f"Для участия нажми кнопку **ПРИСОЕДИНИТЬСЯ** в канале {channel.mention if channel else 'для регистрации'}",
                color=0xff0000,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="👊 Противник",
                value=self.capt_info['enemy'],
                inline=True
            )
            
            embed.add_field(
                name="⏰ Время телепорта",
                value=f"{self.capt_info['teleport_time']} МСК",
                inline=True
            )
            
            if self.capt_info['additional_info'] and self.capt_info['additional_info'] != "Нет":
                embed.add_field(
                    name="📝 Дополнительно",
                    value=self.capt_info['additional_info'],
                    inline=False
                )
            
            embed.add_field(
                name="👤 Набрал",
                value=self.capt_info['started_by'],
                inline=True
            )
            
            # Получаем публичный канал для ссылки
            if self.reserve_channel_id:
                reserve_channel = bot.get_channel(int(self.reserve_channel_id))
                if reserve_channel:
                    embed.add_field(
                        name="📍 Канал регистрации",
                        value=reserve_channel.mention,
                        inline=True
                    )
            
            embed.set_footer(text="Нажми кнопку в канале регистрации чтобы участвовать")
            
            # Отправляем с @everyone
            await channel.send(
                content="@everyone",
                embed=embed
            )
            
            logger.info(f"✅ Оповещение о CAPT отправлено в {channel.name}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки оповещения: {e}")
    
    async def end_registration(self, user_id: str, bot):
        """Завершить регистрацию (очистить всё)"""
        logger.info(f"Завершение регистрации от {user_id}")
        
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
        
        # Деактивируем кнопки в публичном чате
        await self._update_public_buttons(bot, active=False)
        
        # Обновляем кнопки в чате модерации
        await self._update_moderation_buttons(bot, active=False)
        
        # Обновляем embed в обоих каналах (пустые списки)
        await self._update_all_embeds(bot, clear=True)
        
        db.log_action(user_id, "CAPT_REG_END")
        logger.info("✅ Регистрация завершена")
        return True
    
    async def add_participant(self, user_id: str, user_name: str, bot):
        """Добавить участника (всегда в резерв)"""
        logger.debug(f"Добавление участника {user_name} ({user_id})")
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли уже
                cursor.execute('SELECT 1 FROM capt_registrations WHERE user_id = ? AND is_active = 1', (user_id,))
                if cursor.fetchone():
                    return False, "❌ Ты уже зарегистрирован"
                
                # Добавляем в резерв
                cursor.execute('''
                    INSERT INTO capt_registrations (user_id, user_name, list_type)
                    VALUES (?, ?, 'reserve')
                ''', (user_id, user_name))
                
                conn.commit()
            
            # Обновляем embed
            await self._update_all_embeds(bot)
            
            db.log_action(user_id, "CAPT_REG_JOIN")
            logger.info(f"✅ Участник {user_name} добавлен в резерв")
            return True, "✅ Ты добавлен в резерв"
            
        except Exception as e:
            logger.error(f"Ошибка добавления участника: {e}")
            return False, f"❌ Ошибка: {e}"
    
    async def remove_participant(self, user_id: str, bot):
        """Удалить участника"""
        logger.debug(f"Удаление участника {user_id}")
        
        try:
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
                logger.info(f"✅ Участник {user_id} удалён")
                return True, "✅ Ты удалён из регистрации"
            
            logger.debug(f"❌ Участник {user_id} не найден")
            return False, "❌ Ты не был зарегистрирован"
            
        except Exception as e:
            logger.error(f"Ошибка удаления участника: {e}")
            return False, f"❌ Ошибка: {e}"
    
    async def move_to_main(self, user_id: str, target_user_id: str, bot):
        """Перевести пользователя в основной список"""
        logger.info(f"Перевод {target_user_id} в основной список от {user_id}")
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли пользователь
                cursor.execute('SELECT list_type FROM capt_registrations WHERE user_id = ? AND is_active = 1', (target_user_id,))
                result = cursor.fetchone()
                
                if not result:
                    return False, "❌ Пользователь не найден в списках"
                
                if result[0] == 'main':
                    return False, "❌ Пользователь уже в основном списке"
                
                # Обновляем
                cursor.execute("UPDATE capt_registrations SET list_type = 'main' WHERE user_id = ? AND is_active = 1", (target_user_id,))
                conn.commit()
            
            # Обновляем embed
            await self._update_all_embeds(bot)
            db.log_action(user_id, "CAPT_REG_TO_MAIN", f"User {target_user_id}")
            
            return True, f"✅ <@{target_user_id}> добавлен в основной список"
            
        except Exception as e:
            logger.error(f"Ошибка в move_to_main: {e}")
            return False, f"❌ Ошибка: {e}"
    
    async def move_to_reserve(self, user_id: str, target_user_id: str, bot):
        """Перевести пользователя в резерв"""
        logger.info(f"Перевод {target_user_id} в резерв от {user_id}")
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли пользователь
                cursor.execute('SELECT list_type FROM capt_registrations WHERE user_id = ? AND is_active = 1', (target_user_id,))
                result = cursor.fetchone()
                
                if not result:
                    return False, "❌ Пользователь не найден в списках"
                
                if result[0] == 'reserve':
                    return False, "❌ Пользователь уже в резерве"
                
                # Обновляем
                cursor.execute("UPDATE capt_registrations SET list_type = 'reserve' WHERE user_id = ? AND is_active = 1", (target_user_id,))
                conn.commit()
            
            # Обновляем embed
            await self._update_all_embeds(bot)
            db.log_action(user_id, "CAPT_REG_TO_RESERVE", f"User {target_user_id}")
            
            return True, f"✅ <@{target_user_id}> переведён в резерв"
            
        except Exception as e:
            logger.error(f"Ошибка в move_to_reserve: {e}")
            return False, f"❌ Ошибка: {e}"
    
    def get_lists(self):
        """Получить текущие списки, отсортированные по времени регистрации"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # Основной список - сортируем по registered_at (кто раньше зарегистрировался в основном)
            cursor.execute('''
                SELECT user_id, user_name FROM capt_registrations 
                WHERE is_active = 1 AND list_type = 'main'
                ORDER BY registered_at
            ''')
            main_list = cursor.fetchall()
            
            # Резервный список - сортируем по registered_at (кто раньше зарегистрировался в резерве)
            cursor.execute('''
                SELECT user_id, user_name FROM capt_registrations 
                WHERE is_active = 1 AND list_type = 'reserve'
                ORDER BY registered_at
            ''')
            reserve_list = cursor.fetchall()
            
            return main_list, reserve_list
    
    def is_registration_active(self) -> bool:
        """Проверить, активна ли регистрация"""
        return self.active_session is not None
    
    async def _update_public_buttons(self, bot, active: bool):
        """Активировать/деактивировать кнопки в публичном чате"""
        if not self.reserve_channel_id or not self.reserve_message_id:
            return
        
        try:
            channel = bot.get_channel(int(self.reserve_channel_id))
            if not channel:
                return
            
            msg = await channel.fetch_message(int(self.reserve_message_id))
            if not msg:
                return
            
            # Создаём новый view с активированными/деактивированными кнопками
            from capt_registration.views import PublicView
            view = PublicView()
            view.set_registration_active(active)
            
            await msg.edit(view=view)
            logger.info(f"✅ Кнопки в публичном чате {'активированы' if active else 'деактивированы'}")
            
        except Exception as e:
            logger.error(f"Ошибка обновления кнопок: {e}")
    
    async def _update_moderation_buttons(self, bot, active: bool):
        """Обновить состояние кнопок в чате модерации"""
        if not self.main_channel_id or not self.main_message_id:
            return
        
        try:
            channel = bot.get_channel(int(self.main_channel_id))
            if not channel:
                return
            
            msg = await channel.fetch_message(int(self.main_message_id))
            if not msg:
                return
            
            # Создаём новый view с обновлённым состоянием кнопок
            from capt_registration.views import ModerationView
            view = ModerationView()
            view.update_buttons(active)
            
            await msg.edit(view=view)
            logger.info(f"✅ Кнопки в чате модерации {'активированы' if active else 'деактивированы'}")
            
        except Exception as e:
            logger.error(f"Ошибка обновления кнопок модерации: {e}")
    
    async def _update_all_embeds(self, bot, clear=False):
        """Обновить embed в обоих каналах"""
        from capt_registration.embeds import create_registration_embed
        
        if clear:
            main_list, reserve_list = [], []
            capt_info = None
        else:
            main_list, reserve_list = self.get_lists()
            capt_info = self.capt_info  # Добавляем информацию о CAPT
        
        embed = create_registration_embed(main_list, reserve_list, capt_info)
        
        # Обновляем в канале модерации
        if self.main_channel_id and self.main_message_id:
            await self._update_embed(bot, self.main_channel_id, self.main_message_id, embed)
        
        # Обновляем в канале для всех
        if self.reserve_channel_id and self.reserve_message_id:
            await self._update_embed(bot, self.reserve_channel_id, self.reserve_message_id, embed)
    
    async def _update_embed(self, bot, channel_id: str, message_id: str, embed):
        """Обновить embed в конкретном канале"""
        try:
            channel = bot.get_channel(int(channel_id))
            if not channel:
                return
            
            msg = await channel.fetch_message(int(message_id))
            if msg:
                await msg.edit(embed=embed)
                logger.debug(f"Embed обновлён в канале {channel_id}")
        except Exception as e:
            logger.error(f"Ошибка обновления embed в {channel_id}: {e}")

# Глобальный экземпляр
capt_reg_manager = CaptRegistrationManager()