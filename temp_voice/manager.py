"""Менеджер временных голосовых комнат"""
import asyncio
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG


class TempVoiceManager:
    """Управление временными голосовыми комнатами"""
    
    def __init__(self):
        self.bot = None
        self.active_rooms = {}
        self.delete_tasks = {}
        self.pending_deletions = {}
    
    def set_bot(self, bot):
        self.bot = bot
    
    def get_settings(self):
        """Получить настройки из CONFIG"""
        return {
            'temp_voice_category': CONFIG.get('temp_voice_category'),
            'temp_voice_public_channel': CONFIG.get('temp_voice_public_channel'),
            'temp_voice_log_channel': CONFIG.get('temp_voice_log_channel'),
            'temp_voice_default_slots': int(CONFIG.get('temp_voice_default_slots', 2)),
            'temp_voice_max_slots': int(CONFIG.get('temp_voice_max_slots', 10)),
            'temp_voice_delete_delay': int(CONFIG.get('temp_voice_delete_delay', 60)),
        }
    
    def save_setting(self, key: str, value: str, updated_by: str = None):
        db.set_setting(key, value, updated_by)
        CONFIG[key] = value
    
    def get_user_room(self, user_id: int) -> dict:
        return db.get_temp_voice_room_by_user(str(user_id))
    
    def get_room_by_channel(self, channel_id: int) -> dict:
        return db.get_temp_voice_room_by_channel(str(channel_id))
    
    def get_all_rooms(self) -> list:
        return db.get_all_temp_voice_rooms()
    
    def save_room(self, channel_id: int, creator_id: int, creator_name: str, slots: int):
        db.save_temp_voice_room(str(channel_id), str(creator_id), creator_name, slots)
    
    def delete_room_from_db(self, channel_id: int):
        db.delete_temp_voice_room(str(channel_id))
    
    def update_room_slots(self, channel_id: int, slots: int):
        db.update_temp_voice_room_slots(str(channel_id), slots)
    
    async def create_room(self, interaction: discord.Interaction, room_name: str) -> tuple:
        settings = self.get_settings()
        category_id = settings.get('temp_voice_category')
        
        if not category_id:
            return False, "❌ Категория для временных комнат не настроена"
        
        category = interaction.guild.get_channel(int(category_id))
        if not category:
            return False, "❌ Категория не найдена"
        
        existing = self.get_user_room(interaction.user.id)
        if existing:
            return False, f"❌ У вас уже есть комната: <#{existing['channel_id']}>"
        
        default_slots = settings.get('temp_voice_default_slots', 2)
        delete_delay = settings.get('temp_voice_delete_delay', 60)
        
        try:
            channel = await interaction.guild.create_voice_channel(
                name=room_name,
                category=category,
                user_limit=default_slots,
                reason=f"Временная комната для {interaction.user.display_name}"
            )
        except Exception as e:
            return False, f"❌ Ошибка создания канала: {e}"
        
        await channel.set_permissions(interaction.user, connect=True, manage_channels=True)
        
        self.save_room(channel.id, interaction.user.id, interaction.user.display_name, default_slots)
        
        self.active_rooms[channel.id] = {
            'creator_id': interaction.user.id,
            'creator_name': interaction.user.display_name,
            'slots': default_slots,
            'channel': channel
        }
        
        # Таймер на случай, если создатель не зайдёт в комнату (используем настройку)
        async def check_creator_join():
            await asyncio.sleep(delete_delay)
            room = self.get_room_by_channel(channel.id)
            if room:
                member = interaction.guild.get_member(interaction.user.id)
                if not member or not member.voice or member.voice.channel != channel:
                    await self.delete_room(channel, f"Создатель не зашёл в комнату в течение {delete_delay} секунд")
        
        asyncio.create_task(check_creator_join())
        
        await self.log_action(interaction.guild, f"✅ Создана временная комната: {channel.name} (создатель: {interaction.user.mention})")
        
        return True, f"✅ Комната создана: {channel.mention}\n🔊 Войдите в неё, чтобы начать общение!"
    
    async def delete_room(self, channel: discord.VoiceChannel, reason: str = None):
        channel_id = channel.id
        
        print(f"🎤 [TEMP_VOICE] delete_room вызван для {channel.name}, причина: {reason}")
        
        if channel_id in self.delete_tasks:
            self.delete_tasks[channel_id].cancel()
            del self.delete_tasks[channel_id]
        
        if channel_id in self.pending_deletions:
            del self.pending_deletions[channel_id]
        
        self.delete_room_from_db(channel_id)
        
        if channel_id in self.active_rooms:
            del self.active_rooms[channel_id]
        
        try:
            await channel.delete(reason=reason or "Удаление временной комнаты")
            print(f"🎤 [TEMP_VOICE] Канал {channel.name} удалён")
        except Exception as e:
            print(f"❌ [TEMP_VOICE] Ошибка удаления канала {channel.name}: {e}")
        
        if self.bot:
            await self.log_action(channel.guild, f"🗑️ Удалена временная комната: {channel.name}")
    
    async def schedule_deletion(self, channel: discord.VoiceChannel, creator_id: int):
        settings = self.get_settings()
        delay = settings.get('temp_voice_delete_delay', 60)
        channel_id = channel.id
        
        print(f"🎤 [TEMP_VOICE] Запланировано удаление комнаты {channel.name} через {delay} сек")
        
        if channel_id in self.delete_tasks:
            self.delete_tasks[channel_id].cancel()
        
        async def delete_task():
            try:
                await asyncio.sleep(delay)
                
                guild = channel.guild
                member = guild.get_member(creator_id)
                
                if member and member.voice and member.voice.channel == channel:
                    print(f"🎤 [TEMP_VOICE] Создатель вернулся, отмена удаления")
                    if channel_id in self.delete_tasks:
                        del self.delete_tasks[channel_id]
                    await self.log_action(guild, f"🔄 Отмена удаления комнаты {channel.name} — создатель вернулся")
                    return
                
                await self.delete_room(channel, "Создатель покинул комнату")
                
            except asyncio.CancelledError:
                print(f"🎤 [TEMP_VOICE] Задача удаления отменена")
            except Exception as e:
                print(f"❌ [TEMP_VOICE] Ошибка: {e}")
        
        task = asyncio.create_task(delete_task())
        self.delete_tasks[channel_id] = task
        self.pending_deletions[channel_id] = datetime.now()
        
        await self.log_action(channel.guild, f"⏰ Запланировано удаление комнаты {channel.name} через {delay} сек")
    
    async def cancel_deletion(self, channel: discord.VoiceChannel):
        channel_id = channel.id
        if channel_id in self.delete_tasks:
            self.delete_tasks[channel_id].cancel()
            del self.delete_tasks[channel_id]
            print(f"🎤 [TEMP_VOICE] Отменено удаление комнаты {channel.name}")
        if channel_id in self.pending_deletions:
            del self.pending_deletions[channel_id]
    
    async def expand_slots(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> tuple:
        settings = self.get_settings()
        max_slots = settings.get('temp_voice_max_slots', 10)
        
        room = self.get_room_by_channel(channel.id)
        if not room:
            return False, "❌ Комната не найдена"
        
        current_slots = room['slots']
        if current_slots >= max_slots:
            return False, f"❌ Достигнут максимум слотов: {max_slots}"
        
        new_slots = min(current_slots + 2, max_slots)
        
        self.update_room_slots(channel.id, new_slots)
        await channel.edit(user_limit=new_slots)
        
        if channel.id in self.active_rooms:
            self.active_rooms[channel.id]['slots'] = new_slots
        
        await self.log_action(interaction.guild, f"📈 {interaction.user.mention} расширил комнату {channel.name} до {new_slots} слотов")
        
        return True, f"✅ Количество слотов увеличено до **{new_slots}**"
    
    async def kick_user(self, interaction: discord.Interaction, channel: discord.VoiceChannel, target_user: discord.Member) -> tuple:
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
    
    async def close_room(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        await self.delete_room(channel, f"Закрыта создателем {interaction.user.display_name}")
        await self.log_action(interaction.guild, f"🔒 {interaction.user.mention} закрыл комнату {channel.name}")
    
    async def check_creator_presence(self, guild: discord.Guild):
        """Проверить всех создателей комнат — в войсе ли они"""
        rooms = self.get_all_rooms()
        
        for room in rooms:
            channel = guild.get_channel(int(room['channel_id']))
            if not channel:
                self.delete_room_from_db(int(room['channel_id']))
                continue
            
            creator = guild.get_member(room['creator_id'])
            
            if not creator or not creator.voice or creator.voice.channel != channel:
                await self.delete_room(channel, "Создатель не в комнате после перезапуска")
            else:
                self.active_rooms[channel.id] = {
                    'creator_id': room['creator_id'],
                    'creator_name': room['creator_name'],
                    'slots': room['slots'],
                    'channel': channel
                }
    
    async def log_action(self, guild: discord.Guild, message: str):
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
        print("🎤 [TEMP_VOICE] Остановка системы...")
        for task in self.delete_tasks.values():
            task.cancel()
        self.delete_tasks.clear()
        self.pending_deletions.clear()


temp_voice_manager = TempVoiceManager()