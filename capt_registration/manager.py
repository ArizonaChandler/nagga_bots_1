"""Менеджер регистрации на CAPT"""
import asyncio
import discord
import logging
from datetime import datetime
from core.database import db
from core.config import CONFIG, save_config

logger = logging.getLogger(__name__)

async def log_action(self, bot, action: str, user_id: str, user_name: str, details: str = None, target_user_id: str = None):
    """Логирование действий в канал логов CAPT"""
    log_channel_id = CONFIG.get('capt_log_channel')
    if not log_channel_id:
        return
    
    channel = bot.get_channel(int(log_channel_id))
    if not channel:
        return
    
    # Определяем цвет в зависимости от действия
    if "НАЧАЛО" in action or "ПРИНЯЛ" in action or "ВСЕХ" in action:
        color = 0x00ff00
    elif "ОШИБКА" in action or "ОТКЛОНЕН" in action:
        color = 0xff0000
    else:
        color = 0xffa500
    
    embed = discord.Embed(
        title=f"📋 {action}",
        color=color,
        timestamp=datetime.now()
    )
    embed.add_field(name="👤 Кто нажал", value=f"<@{user_id}>")
    embed.add_field(name="🆔 ID нажавшего", value=user_id)
    
    if target_user_id:
        embed.add_field(name="👤 Целевой пользователь", value=f"<@{target_user_id}>")
    
    if details:
        embed.add_field(name="📝 Детали", value=details, inline=False)
    
    await channel.send(embed=embed)

class CaptRegistrationManager:
    def __init__(self):
        self.active_session = None
        self.main_channel_id = None
        self.reserve_channel_id = None
        self.alert_channel_id = None
        self.capt_role_id = None
        self.main_message_id = None
        self.reserve_message_id = None
        self.capt_info = None
        self._load_config()
        logger.info("✅ CaptRegistrationManager инициализирован")
    
    def _load_config(self):
        """Загрузка настроек из CONFIG"""
        self.main_channel_id = CONFIG.get('capt_reg_main_channel')
        self.reserve_channel_id = CONFIG.get('capt_reg_reserve_channel')
        self.alert_channel_id = CONFIG.get('capt_alert_channel')
        self.capt_role_id = CONFIG.get('capt_role_id')
        
        # Если в CONFIG нет, пробуем загрузить из БД напрямую
        if not self.main_channel_id or not self.reserve_channel_id or not self.alert_channel_id or not self.capt_role_id:
            from core.database import db
            settings = db.get_all_settings()
            if 'capt_reg_main_channel' in settings:
                self.main_channel_id = settings['capt_reg_main_channel']
                CONFIG['capt_reg_main_channel'] = self.main_channel_id
            if 'capt_reg_reserve_channel' in settings:
                self.reserve_channel_id = settings['capt_reg_reserve_channel']
                CONFIG['capt_reg_reserve_channel'] = self.reserve_channel_id
            if 'capt_alert_channel' in settings:
                self.alert_channel_id = settings['capt_alert_channel']
                CONFIG['capt_alert_channel'] = self.alert_channel_id
            if 'capt_role_id' in settings:
                self.capt_role_id = settings['capt_role_id']
                CONFIG['capt_role_id'] = self.capt_role_id
        
        logger.debug(f"Загружены каналы: main={self.main_channel_id}, reserve={self.reserve_channel_id}, alert={self.alert_channel_id}, role={self.capt_role_id}")
    
    def set_channels(self, main_channel_id: str, reserve_channel_id: str, updated_by: str):
        """Установка каналов для регистрации"""
        logger.info(f"Установка каналов: main={main_channel_id}, reserve={reserve_channel_id}")
        
        CONFIG['capt_reg_main_channel'] = main_channel_id
        CONFIG['capt_reg_reserve_channel'] = reserve_channel_id
        save_config(updated_by)
        
        self.main_channel_id = main_channel_id
        self.reserve_channel_id = reserve_channel_id
        
        logger.info(f"✅ Каналы сохранены в CONFIG и БД")
        return True
    
    async def initialize_buttons(self, bot):
        """Инициализация постоянных кнопок при старте бота"""
        logger.info("🔄 Инициализация постоянных кнопок CAPT регистрации")
        
        # ===== 1. ИНИЦИАЛИЗАЦИЯ КАНАЛА НАСТРОЕК =====
        settings_channel_id = CONFIG.get('capt_settings_channel')
        if settings_channel_id:
            try:
                settings_channel = bot.get_channel(int(settings_channel_id))
                if settings_channel:
                    from capt_registration.settings_view import CaptSettingsView
                    
                    # Ищем существующее сообщение с CAPT настройками
                    capt_message_exists = False
                    async for msg in settings_channel.history(limit=20):
                        if msg.author == bot.user and msg.embeds and "ПАНЕЛЬ УПРАВЛЕНИЯ CAPT" in msg.embeds[0].title:
                            capt_message_exists = True
                            # Обновляем view у существующего сообщения
                            await msg.edit(view=CaptSettingsView())
                            logger.info(f"✅ Обновлено существующее сообщение CAPT в #{settings_channel.name}")
                            break
                    
                    if not capt_message_exists:
                        # Отправляем новое сообщение
                        embed = discord.Embed(
                            title="⚙️ **ПАНЕЛЬ УПРАВЛЕНИЯ CAPT**",
                            description="Настройка всех параметров системы регистрации на CAPT",
                            color=0xff0000
                        )
                        await settings_channel.send(embed=embed, view=CaptSettingsView())
                        logger.info(f"✅ Новое сообщение CAPT отправлено в #{settings_channel.name}")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации канала настроек CAPT: {e}")
        
        # ===== 2. ПРОВЕРКА НАЛИЧИЯ ОСНОВНЫХ КАНАЛОВ =====
        if not self.main_channel_id or not self.reserve_channel_id:
            logger.warning("❌ Каналы регистрации не настроены, пропускаем инициализацию")
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
            
            # Очищаем старые сообщения бота в обоих каналах
            await self._clean_old_messages(main_channel)
            await self._clean_old_messages(reserve_channel)
            
            # ===== 3. ПРОВЕРКА АКТИВНОЙ СЕССИИ В БД =====
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, started_by, started_at, main_message_id, reserve_message_id
                    FROM capt_sessions 
                    WHERE is_active = 1 
                    ORDER BY started_at DESC LIMIT 1
                ''')
                active_session = cursor.fetchone()
                
                if active_session:
                    session_id, started_by, started_at, main_msg_id, reserve_msg_id = active_session
                    self.active_session = session_id
                    
                    # Загружаем информацию о CAPT (можно расширить позже)
                    self.capt_info = {
                        'enemy': "Восстановлено",
                        'teleport_time': "из сессии",
                        'additional_info': "Нет",
                        'started_by': f"<@{started_by}>",
                        'started_by_name': "Организатор"
                    }
                    
                    # Восстанавливаем ID сообщений
                    self.main_message_id = main_msg_id
                    self.reserve_message_id = reserve_msg_id
                    
                    logger.info(f"✅ Восстановлена активная сессия ID: {session_id}")
                else:
                    self.active_session = None
                    self.capt_info = None
                    logger.info("ℹ️ Нет активной сессии")
            
            # ===== 4. ПОЛУЧАЕМ ТЕКУЩИЕ СПИСКИ =====
            from capt_registration.embeds import create_registration_embed
            from capt_registration.views import ModerationView, PublicView
            
            main_list, reserve_list = self.get_lists()
            embed = create_registration_embed(main_list, reserve_list, self.capt_info)
            
            # Определяем, активна ли регистрация
            registration_active = self.active_session is not None
            
            # ===== 5. СОЗДАЕМ VIEW С ПРАВИЛЬНЫМ СОСТОЯНИЕМ КНОПОК =====
            moderation_view = ModerationView()
            moderation_view.update_buttons(registration_active)
            
            public_view = PublicView()
            public_view.set_registration_active(registration_active)
            
            # ===== 6. ОТПРАВЛЯЕМ НОВЫЕ СООБЩЕНИЯ =====
            main_msg = await main_channel.send(embed=embed, view=moderation_view)
            reserve_msg = await reserve_channel.send(embed=embed, view=public_view)
            
            self.main_message_id = str(main_msg.id)
            self.reserve_message_id = str(reserve_msg.id)
            
            # ===== 7. ОБНОВЛЯЕМ ID СООБЩЕНИЙ В СЕССИИ =====
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
            logger.info(f"📊 Статус регистрации: {'АКТИВНА' if registration_active else 'НЕАКТИВНА'}")
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
        
        # Отправляем оповещение @everyone
        await self._send_capt_announcement(bot)
        
        # Активируем кнопки в публичном чате
        await self._update_public_buttons(bot, active=True)
        
        # Обновляем кнопки в чате модерации
        await self._update_moderation_buttons(bot, active=True)
        
        # Обновляем embed с информацией
        await self._update_all_embeds(bot)
        
        db.log_action(user_id, "CAPT_REG_START", f"Session {session_id}")
        return True
    
    async def _send_capt_announcement(self, bot):
        """Отправить оповещение о начале CAPT"""
        if not self.capt_info:
            return
        
        alert_channel_id = CONFIG.get('capt_alert_channel')
        if not alert_channel_id:
            logger.warning("❌ Канал для оповещений CAPT не настроен")
            return
        
        try:
            channel = bot.get_channel(int(alert_channel_id))
            if not channel:
                logger.error(f"❌ Канал оповещений {alert_channel_id} не найден")
                return
            
            # Получаем публичный канал для регистрации
            reserve_channel_mention = "канал регистрации"
            if self.reserve_channel_id:
                reserve_channel = bot.get_channel(int(self.reserve_channel_id))
                if reserve_channel:
                    reserve_channel_mention = reserve_channel.mention
            
            # Создаём embed
            embed = discord.Embed(
                title="🎯 НАБОР НА CAPT",
                description=f"Для участия нажми кнопку **ПРИСОЕДИНИТЬСЯ** в канале {reserve_channel_mention}",
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
            
            embed.set_footer(text="Регистрация активна")
            
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
        self.capt_info = None
        
        # Деактивируем кнопки в публичном чате
        await self._update_public_buttons(bot, active=False)
        
        # Обновляем кнопки в чате модерации
        await self._update_moderation_buttons(bot, active=False)
        
        # Обновляем embed в обоих каналах (пустые списки)
        await self._update_all_embeds(bot, clear=True)
        
        # Очищаем чат модерации
        await self._clean_moderation_chat(bot)
        
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
    
    async def move_to_main(self, user_id: str, target_reg_id: int, bot):
        """Перевести пользователя в основной список по ID записи"""
        logger.info(f"Перевод записи {target_reg_id} в основной список от {user_id}")
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем информацию о записи
                cursor.execute('''
                    SELECT user_id, user_name, list_type FROM capt_registrations 
                    WHERE id = ? AND is_active = 1
                ''', (target_reg_id,))
                result = cursor.fetchone()
                
                if not result:
                    return False, "❌ Запись не найдена"
                
                target_user_id, target_user_name, current_list = result
                
                if current_list == 'main':
                    return False, "❌ Эта запись уже в основном списке"
                
                # Переводим в основной и ОБНОВЛЯЕМ время регистрации на текущее
                cursor.execute('''
                    UPDATE capt_registrations 
                    SET list_type = 'main', registered_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (target_reg_id,))
                
                conn.commit()
            
            # Обновляем embed
            await self._update_all_embeds(bot)
            db.log_action(user_id, "CAPT_REG_TO_MAIN", f"Registration ID {target_reg_id}")
            
            return True, f"✅ <@{target_user_id}> добавлен в основной список"
            
        except Exception as e:
            logger.error(f"Ошибка в move_to_main: {e}")
            return False, f"❌ Ошибка: {e}"

    async def move_to_reserve(self, user_id: str, target_reg_id: int, bot):
        """Перевести пользователя в резерв по ID записи"""
        logger.info(f"Перевод записи {target_reg_id} в резерв от {user_id}")
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем информацию о записи
                cursor.execute('''
                    SELECT user_id, user_name, list_type FROM capt_registrations 
                    WHERE id = ? AND is_active = 1
                ''', (target_reg_id,))
                result = cursor.fetchone()
                
                if not result:
                    return False, "❌ Запись не найдена"
                
                target_user_id, target_user_name, current_list = result
                
                if current_list == 'reserve':
                    return False, "❌ Эта запись уже в резерве"
                
                # Переводим в резерв и ОБНОВЛЯЕМ время регистрации на текущее
                cursor.execute('''
                    UPDATE capt_registrations 
                    SET list_type = 'reserve', registered_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (target_reg_id,))
                
                conn.commit()
            
            # Обновляем embed
            await self._update_all_embeds(bot)
            db.log_action(user_id, "CAPT_REG_TO_RESERVE", f"Registration ID {target_reg_id}")
            
            return True, f"✅ <@{target_user_id}> переведён в резерв"
            
        except Exception as e:
            logger.error(f"Ошибка в move_to_reserve: {e}")
            return False, f"❌ Ошибка: {e}"

    async def move_all_to_main(self, user_id: str, bot):
        """Переместить всех из резерва в основной список"""
        logger.info(f"Перемещение всех в основной список от {user_id}")
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем количество затронутых записей
                cursor.execute('''
                    UPDATE capt_registrations 
                    SET list_type = 'main'
                    WHERE is_active = 1 AND list_type = 'reserve'
                ''')
                moved_count = cursor.rowcount
                conn.commit()
            
            if moved_count > 0:
                # Обновляем embed
                await self._update_all_embeds(bot)
                db.log_action(user_id, "CAPT_REG_MOVE_ALL", f"Перемещено: {moved_count}")
                logger.info(f"✅ Перемещено в основной: {moved_count}")
                return True, f"✅ {moved_count} участников перемещено в основной список"
            else:
                return False, "❌ В резерве нет участников для перемещения"
            
        except Exception as e:
            logger.error(f"Ошибка при перемещении всех: {e}")
            return False, f"❌ Ошибка: {e}"
    
    def get_lists(self):
        """Получить текущие списки с ID записей, отсортированные по времени регистрации"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # Основной список - сортируем по registered_at (кто раньше стал в основной)
            cursor.execute('''
                SELECT id, user_id, user_name FROM capt_registrations 
                WHERE is_active = 1 AND list_type = 'main'
                ORDER BY registered_at
            ''')
            main_list = cursor.fetchall()
            
            # Резервный список - сортируем по registered_at (кто раньше стал в резерв)
            cursor.execute('''
                SELECT id, user_id, user_name FROM capt_registrations 
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
            capt_info = self.capt_info
        
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

    async def _clean_moderation_chat(self, bot):
        """Очистить чат модерации от всех сообщений кроме основного embed с кнопками"""
        if not self.main_channel_id or not self.main_message_id:
            return
        
        try:
            channel = bot.get_channel(int(self.main_channel_id))
            if not channel:
                logger.error(f"❌ Канал модерации {self.main_channel_id} не найден")
                return
            
            logger.info(f"🧹 Очистка чата модерации #{channel.name} от лишних сообщений...")
            
            # Сохраняем ID основного сообщения, которое нужно оставить
            main_message_id = int(self.main_message_id)
            deleted_count = 0
            
            # Перебираем историю сообщений
            async for message in channel.history(limit=100):
                # Пропускаем основное сообщение с кнопками
                if message.id == main_message_id:
                    continue
                
                # Удаляем всё остальное
                try:
                    await message.delete()
                    deleted_count += 1
                    await asyncio.sleep(0.5)  # asyncio уже импортирован
                except Exception as e:
                    logger.error(f"Ошибка удаления сообщения {message.id}: {e}")
            
            logger.info(f"✅ Очистка завершена. Удалено сообщений: {deleted_count}")
        except Exception as e:
            logger.error(f"Ошибка при очистке чата модерации: {e}", exc_info=True)

    async def log_action(self, bot, action: str, user_id: str, user_name: str, details: str = None, target_user_id: str = None):
        """Логирование действий в канал логов CAPT"""
        from core.config import CONFIG
        import discord
        from datetime import datetime
        
        log_channel_id = CONFIG.get('capt_log_channel')
        if not log_channel_id:
            return
        
        channel = bot.get_channel(int(log_channel_id))
        if not channel:
            return
        
        # Определяем цвет в зависимости от действия
        if "НАЧАЛО" in action or "ПРИНЯЛ" in action or "ВСЕХ" in action:
            color = 0x00ff00
        elif "ОШИБКА" in action or "ОТКЛОНЕН" in action:
            color = 0xff0000
        else:
            color = 0xffa500
        
        embed = discord.Embed(
            title=f"📋 {action}",
            color=color,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Кто нажал", value=f"<@{user_id}>")
        embed.add_field(name="🆔 ID нажавшего", value=user_id)
        
        if target_user_id:
            embed.add_field(name="👤 Целевой пользователь", value=f"<@{target_user_id}>")
        
        if details:
            embed.add_field(name="📝 Детали", value=details, inline=False)
        
        await channel.send(embed=embed)

# Глобальный экземпляр
capt_reg_manager = CaptRegistrationManager()