"""Менеджер временных голосовых комнат"""
import asyncio
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG, save_config


class TempVoiceManager:
    """Управление временными голосовыми комнатами"""
    
    def __init__(self):
        self.bot = None
        self.active_rooms = {}  # {channel_id: {'creator_id': int, 'creator_name': str, 'slots': int, 'delete_task': asyncio.Task}}
        self.delete_tasks = {}   # {channel_id: asyncio.Task}
        self.pending_deletions = {}  # {channel_id: datetime} для отслеживания
    
    def set_bot(self, bot):
        self.bot = bot
    
    def get_settings(self):
        """Получить настройки из CONFIG"""
        return {
            'temp_voice_category': CONFIG.get('temp_voice_category'),
            'temp_voice_public_channel': CONFIG.get('temp_voice_public_channel'),
            'temp_voice_log_channel': CONFIG.get('temp_voice_log_channel'),
            'temp_voice_settings_channel': CONFIG.get('temp_voice_settings_channel'),
            'temp_voice_default_slots': int(CONFIG.get('temp_voice_default_slots', 2)),
            'temp_voice_max_slots': int(CONFIG.get('temp_voice_max_slots', 10)),
            'temp_voice_delete_delay': int(CONFIG.get('temp_voice_delete_delay', 60)),
        }
    
    def save_setting(self, key: str, value: str, updated_by: str = None):
        """Сохранить настройку"""
        db.set_setting(key, value, updated_by)
        CONFIG[key] = value
    
    def get_user_room(self, user_id: int) -> dict:
        """Получить комнату пользователя"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT channel_id, creator_id, creator_name, slots, created_at FROM temp_voice_rooms WHERE creator_id = ?',
                (str(user_id),)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'channel_id': row[0],
                    'creator_id': int(row[1]),
                    'creator_name': row[2],
                    'slots': row[3],
                    'created_at': row[4]
                }
            return None
    
    def get_room_by_channel(self, channel_id: int) -> dict:
        """Получить комнату по ID канала"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT channel_id, creator_id, creator_name, slots, created_at FROM temp_voice_rooms WHERE channel_id = ?',
                (str(channel_id),)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'channel_id': row[0],
                    'creator_id': int(row[1]),
                    'creator_name': row[2],
                    'slots': row[3],
                    'created_at': row[4]
                }
            return None
    
    def get_all_rooms(self) -> list:
        """Получить все комнаты"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT channel_id, creator_id, creator_name, slots, created_at FROM temp_voice_rooms')
            rows = cursor.fetchall()
            return [{
                'channel_id': row[0],
                'creator_id': int(row[1]),
                'creator_name': row[2],
                'slots': row[3],
                'created_at': row[4]
            } for row in rows]
    
    def save_room(self, channel_id: int, creator_id: int, creator_name: str, slots: int):
        """Сохранить комнату в БД"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO temp_voice_rooms (channel_id, creator_id, creator_name, slots, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (str(channel_id), str(creator_id), creator_name, slots))
            conn.commit()
    
    def delete_room(self, channel_id: int):
        """Удалить комнату из БД"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM temp_voice_rooms WHERE channel_id = ?', (str(channel_id),))
            conn.commit()
    
    async def create_room(self, interaction: discord.Interaction, room_name: str) -> tuple:
        """Создать временную голосовую комнату"""
        settings = self.get_settings()
        category_id = settings.get('temp_voice_category')
        
        if not category_id:
            return False, "❌ Категория для временных комнат не настроена"
        
        category = interaction.guild.get_channel(int(category_id))
        if not category:
            return False, "❌ Категория не найдена"
        
        # Проверяем, нет ли уже комнаты у пользователя
        existing = self.get_user_room(interaction.user.id)
        if existing:
            return False, f"❌ У вас уже есть комната: <#{existing['channel_id']}>"
        
        default_slots = settings.get('temp_voice_default_slots', 2)
        
        # Создаём голосовой канал
        try:
            channel = await interaction.guild.create_voice_channel(
                name=room_name,
                category=category,
                user_limit=default_slots,
                reason=f"Временная комната для {interaction.user.display_name}"
            )
        except Exception as e:
            return False, f"❌ Ошибка создания канала: {e}"
        
        # Настраиваем права доступа
        await channel.set_permissions(interaction.user, connect=True, manage_channels=True)
        
        # Сохраняем в БД
        self.save_room(channel.id, interaction.user.id, interaction.user.display_name, default_slots)
        
        # Добавляем в активные комнаты
        self.active_rooms[channel.id] = {
            'creator_id': interaction.user.id,
            'creator_name': interaction.user.display_name,
            'slots': default_slots,
            'channel': channel
        }
        
        # Логируем
        await self.log_action(interaction.guild, f"✅ Создана временная комната: {channel.name} (создатель: {interaction.user.mention})")
        
        return True, f"✅ Комната создана: {channel.mention}\n🔊 Войдите в неё, чтобы начать общение!"
    
    async def delete_room(self, channel: discord.VoiceChannel, reason: str = None):
        """Удалить временную комнату"""
        channel_id = channel.id
        
        print(f"🎤 [TEMP_VOICE] delete_room вызван для {channel.name}, причина: {reason}")
        
        # Отменяем задачу удаления, если есть
        if channel_id in self.delete_tasks:
            self.delete_tasks[channel_id].cancel()
            del self.delete_tasks[channel_id]
        
        if channel_id in self.pending_deletions:
            del self.pending_deletions[channel_id]
        
        # Получаем информацию о комнате
        room = self.get_room_by_channel(channel_id)
        creator_name = room['creator_name'] if room else "Неизвестно"
        
        # Удаляем из БД
        self.delete_room(channel_id)
        
        # Удаляем из активных комнат
        if channel_id in self.active_rooms:
            del self.active_rooms[channel_id]
        
        # Удаляем канал
        try:
            await channel.delete(reason=reason or f"Удаление временной комнаты ({creator_name})")
            print(f"🎤 [TEMP_VOICE] Канал {channel.name} удалён")
        except Exception as e:
            print(f"❌ [TEMP_VOICE] Ошибка удаления канала {channel.name}: {e}")
        
        # Логируем
        if self.bot:
            await self.log_action(channel.guild, f"🗑️ Удалена временная комната: {channel.name}")
    
    async def schedule_deletion(self, channel: discord.VoiceChannel, creator_id: int):
        """Запланировать удаление комнаты через N секунд"""
        settings = self.get_settings()
        delay = settings.get('temp_voice_delete_delay', 60)
        channel_id = channel.id
        
        print(f"🎤 [TEMP_VOICE] Запланировано удаление комнаты {channel.name} через {delay} сек (создатель {creator_id} вышел)")
        
        # Если уже есть задача на удаление — отменяем
        if channel_id in self.delete_tasks:
            self.delete_tasks[channel_id].cancel()
            print(f"🎤 [TEMP_VOICE] Отменена предыдущая задача удаления для {channel.name}")
        
        async def delete_task():
            try:
                print(f"🎤 [TEMP_VOICE] Таймер запущен для {channel.name}, ждём {delay} сек...")
                await asyncio.sleep(delay)
                
                print(f"🎤 [TEMP_VOICE] Таймер сработал для {channel.name}, проверяем...")
                
                # Проверяем, не зашёл ли создатель обратно
                guild = channel.guild
                member = guild.get_member(creator_id)
                
                if member and member.voice and member.voice.channel == channel:
                    # Создатель вернулся — отменяем удаление
                    print(f"🎤 [TEMP_VOICE] Создатель {member.display_name} вернулся в {channel.name}, отмена удаления")
                    if channel_id in self.delete_tasks:
                        del self.delete_tasks[channel_id]
                    if channel_id in self.pending_deletions:
                        del self.pending_deletions[channel_id]
                    await self.log_action(guild, f"🔄 Отмена удаления комнаты {channel.name} — создатель вернулся")
                    return
                
                # Удаляем комнату
                print(f"🎤 [TEMP_VOICE] Удаляем комнату {channel.name} (создатель не вернулся)")
                await self.delete_room(channel, "Создатель покинул комнату")
                
            except asyncio.CancelledError:
                print(f"🎤 [TEMP_VOICE] Задача удаления для {channel.name} отменена")
            except Exception as e:
                print(f"❌ [TEMP_VOICE] Ошибка при удалении комнаты {channel.name}: {e}")
        
        task = asyncio.create_task(delete_task())
        self.delete_tasks[channel_id] = task
        self.pending_deletions[channel_id] = datetime.now()
        
        await self.log_action(channel.guild, f"⏰ Запланировано удаление комнаты {channel.name} через {delay} сек (создатель вышел)")
    
    async def cancel_deletion(self, channel: discord.VoiceChannel):
        """Отменить запланированное удаление"""
        channel_id = channel.id
        if channel_id in self.delete_tasks:
            self.delete_tasks[channel_id].cancel()
            del self.delete_tasks[channel_id]
            print(f"🎤 [TEMP_VOICE] Отменено удаление комнаты {channel.name} (создатель вернулся)")
        if channel_id in self.pending_deletions:
            del self.pending_deletions[channel_id]
    
    async def expand_slots(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> tuple:
        """Расширить количество слотов в комнате"""
        settings = self.get_settings()
        max_slots = settings.get('temp_voice_max_slots', 10)
        
        room = self.get_room_by_channel(channel.id)
        if not room:
            return False, "❌ Комната не найдена"
        
        current_slots = room['slots']
        if current_slots >= max_slots:
            return False, f"❌ Достигнут максимум слотов: {max_slots}"
        
        new_slots = min(current_slots + 2, max_slots)
        
        # Обновляем в БД
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE temp_voice_rooms SET slots = ? WHERE channel_id = ?', (new_slots, str(channel.id)))
            conn.commit()
        
        # Обновляем лимит канала
        await channel.edit(user_limit=new_slots)
        
        # Обновляем в активных комнатах
        if channel.id in self.active_rooms:
            self.active_rooms[channel.id]['slots'] = new_slots
        
        await self.log_action(interaction.guild, f"📈 {interaction.user.mention} расширил комнату {channel.name} до {new_slots} слотов")
        
        return True, f"✅ Количество слотов увеличено до **{new_slots}**"
    
    async def kick_user(self, interaction: discord.Interaction, channel: discord.VoiceChannel, target_user: discord.Member) -> tuple:
        """Кикнуть пользователя из комнаты"""
        if target_user == interaction.user:
            return False, "❌ Нельзя кикнуть самого себя"
        
        if target_user not in channel.members:
            return False, "❌ Пользователь не находится в этой комнате"
        
        try:
            await target_user.move_to(None, reason=f"Кикнут создателем комнаты {interaction.user.display_name}")
            await self.log_action(interaction.guild, f"👢 {interaction.user.mention} кикнул {target_user.mention} из комнаты {channel.name}")
            return True, f"✅ Пользователь {target_user.mention} удалён из комнаты"
        except Exception as e:
            return False, f"❌ Ошибка: {e}"
    
    async def close_room(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> tuple:
        """Закрыть комнату (удалить)"""
        await self.delete_room(channel, f"Закрыта создателем {interaction.user.display_name}")
        await self.log_action(interaction.guild, f"🔒 {interaction.user.mention} закрыл комнату {channel.name}")
        return True, "✅ Комната закрыта"
    
    async def check_creator_presence(self, guild: discord.Guild):
        """Проверить всех создателей комнат — в войсе ли они"""
        rooms = self.get_all_rooms()
        
        for room in rooms:
            channel = guild.get_channel(int(room['channel_id']))
            if not channel:
                # Канал не найден — удаляем из БД
                self.delete_room(int(room['channel_id']))
                continue
            
            creator = guild.get_member(room['creator_id'])
            
            if not creator or not creator.voice or creator.voice.channel != channel:
                # Создатель не в комнате — удаляем
                await self.delete_room(channel, "Создатель не в комнате после перезапуска")
            else:
                # Создатель в комнате — добавляем в активные
                self.active_rooms[channel.id] = {
                    'creator_id': room['creator_id'],
                    'creator_name': room['creator_name'],
                    'slots': room['slots'],
                    'channel': channel
                }
    
    async def log_action(self, guild: discord.Guild, message: str):
        """Отправить лог в канал логов"""
        settings = self.get_settings()
        log_channel_id = settings.get('temp_voice_log_channel')
        
        if not log_channel_id:
            return
        
        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="🎤 ВРЕМЕННЫЕ КОМНАТЫ",
            description=message,
            color=0x00bfff,
            timestamp=datetime.now()
        )
        await log_channel.send(embed=embed)
    
    async def stop(self):
        """Остановка модуля"""
        print("🎤 [TEMP_VOICE] Остановка системы временных комнат...")
        
        # Отменяем все задачи на удаление
        for task in self.delete_tasks.values():
            task.cancel()
        self.delete_tasks.clear()
        self.pending_deletions.clear()


temp_voice_manager = TempVoiceManager()