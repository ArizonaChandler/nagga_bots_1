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
        print("🎤 [DEBUG] set_bot вызван")
    
    def get_settings(self):
        settings = {
            'temp_voice_category': CONFIG.get('temp_voice_category'),
            'temp_voice_public_channel': CONFIG.get('temp_voice_public_channel'),
            'temp_voice_log_channel': CONFIG.get('temp_voice_log_channel'),
            'temp_voice_default_slots': int(CONFIG.get('temp_voice_default_slots', 2)),
            'temp_voice_max_slots': int(CONFIG.get('temp_voice_max_slots', 10)),
            'temp_voice_delete_delay': int(CONFIG.get('temp_voice_delete_delay', 60)),
        }
        print(f"🎤 [DEBUG] get_settings: category={settings['temp_voice_category']}, delete_delay={settings['temp_voice_delete_delay']}")
        return settings
    
    def save_setting(self, key: str, value: str, updated_by: str = None):
        db.set_setting(key, value, updated_by)
        CONFIG[key] = value
        print(f"🎤 [DEBUG] save_setting: {key}={value}")
    
    def get_user_room(self, user_id: int) -> dict:
        result = db.get_temp_voice_room_by_user(str(user_id))
        print(f"🎤 [DEBUG] get_user_room({user_id}) -> {result}")
        return result
    
    def get_room_by_channel(self, channel_id: int) -> dict:
        result = db.get_temp_voice_room_by_channel(str(channel_id))
        print(f"🎤 [DEBUG] get_room_by_channel({channel_id}) -> {result}")
        return result
    
    def get_all_rooms(self) -> list:
        result = db.get_all_temp_voice_rooms()
        print(f"🎤 [DEBUG] get_all_rooms -> {len(result)} комнат")
        return result
    
    def save_room(self, channel_id: int, creator_id: int, creator_name: str, slots: int):
        db.save_temp_voice_room(str(channel_id), str(creator_id), creator_name, slots)
        print(f"🎤 [DEBUG] save_room: {channel_id} создатель={creator_name}")
    
    def delete_room_from_db(self, channel_id: int):
        db.delete_temp_voice_room(str(channel_id))
        print(f"🎤 [DEBUG] delete_room_from_db: {channel_id}")
    
    def update_room_slots(self, channel_id: int, slots: int):
        db.update_temp_voice_room_slots(str(channel_id), slots)
        print(f"🎤 [DEBUG] update_room_slots: {channel_id} -> {slots}")
    
    async def create_room(self, interaction: discord.Interaction, room_name: str) -> tuple:
        print(f"🎤 [DEBUG] create_room НАЧАЛО, пользователь={interaction.user.name}, комната={room_name}")
        
        settings = self.get_settings()
        category_id = settings.get('temp_voice_category')
        
        if not category_id:
            print(f"🎤 [DEBUG] create_room: категория не настроена")
            return False, "❌ Категория для временных комнат не настроена"
        
        category = interaction.guild.get_channel(int(category_id))
        if not category:
            print(f"🎤 [DEBUG] create_room: категория {category_id} не найдена")
            return False, "❌ Категория не найдена"
        
        existing = self.get_user_room(interaction.user.id)
        if existing:
            print(f"🎤 [DEBUG] create_room: у пользователя уже есть комната {existing['channel_id']}")
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
            print(f"🎤 [DEBUG] create_room: канал {channel.name} (ID: {channel.id}) создан")
        except Exception as e:
            print(f"🎤 [DEBUG] create_room: ошибка создания канала - {e}")
            return False, f"❌ Ошибка создания канала: {e}"
        
        await channel.set_permissions(interaction.user, connect=True, manage_channels=True)
        print(f"🎤 [DEBUG] create_room: права настроены для {interaction.user.name}")
        
        self.save_room(channel.id, interaction.user.id, interaction.user.display_name, default_slots)
        
        self.active_rooms[channel.id] = {
            'creator_id': interaction.user.id,
            'creator_name': interaction.user.display_name,
            'slots': default_slots,
            'channel': channel
        }
        print(f"🎤 [DEBUG] create_room: комната добавлена в active_rooms")
        
        # Периодическая проверка, зашёл ли создатель
        async def check_creator_join_periodic():
            print(f"🎤 [DEBUG] check_creator_join_periodic ЗАПУЩЕН для канала {channel.name}")
            for i in range(delete_delay // 5):
                await asyncio.sleep(5)
                member = interaction.guild.get_member(interaction.user.id)
                print(f"🎤 [DEBUG] проверка {i+1}/{delete_delay//5}: member={member.name if member else None}, voice={member.voice.channel.name if member and member.voice and member.voice.channel else None}")
                if member and member.voice and member.voice.channel == channel:
                    print(f"🎤 [TEMP_VOICE] Создатель зашёл в комнату, отменяем удаление")
                    return
            print(f"🎤 [DEBUG] check_creator_join_periodic: создатель не зашёл, удаляем комнату")
            room = self.get_room_by_channel(channel.id)
            if room:
                await self.delete_room(channel, f"Создатель не зашёл в комнату в течение {delete_delay} секунд")
        
        asyncio.create_task(check_creator_join_periodic())
        print(f"🎤 [DEBUG] create_room: задача проверки запущена")
        
        await self.log_action(interaction.guild, f"✅ Создана временная комната: {channel.name} (создатель: {interaction.user.mention})")
        
        return True, f"✅ Комната создана: {channel.mention}\n🔊 Войдите в неё, чтобы начать общение!"
    
    async def delete_room(self, channel: discord.VoiceChannel, reason: str = None):
        print(f"🎤 [TEMP_VOICE] delete_room ВЫЗВАН для канала {channel.name}, причина: {reason}")
        
        channel_id = channel.id
        
        if channel_id in self.delete_tasks:
            print(f"🎤 [DEBUG] delete_room: отменяем задачу удаления {channel_id}")
            self.delete_tasks[channel_id].cancel()
            del self.delete_tasks[channel_id]
        else:
            print(f"🎤 [DEBUG] delete_room: задачи удаления для {channel_id} не найдено")
        
        if channel_id in self.pending_deletions:
            print(f"🎤 [DEBUG] delete_room: удаляем из pending_deletions {channel_id}")
            del self.pending_deletions[channel_id]
        
        room = self.get_room_by_channel(channel_id)
        creator_name = room['creator_name'] if room else "Неизвестно"
        print(f"🎤 [DEBUG] delete_room: создатель комнаты = {creator_name}")
        
        self.delete_room_from_db(channel_id)
        
        if channel_id in self.active_rooms:
            del self.active_rooms[channel_id]
            print(f"🎤 [DEBUG] delete_room: удалён из active_rooms")
        
        try:
            await channel.delete(reason=reason or f"Удаление временной комнаты ({creator_name})")
            print(f"🎤 [TEMP_VOICE] ✅ КАНАЛ {channel.name} УСПЕШНО УДАЛЁН")
        except discord.Forbidden:
            print(f"❌ [TEMP_VOICE] НЕТ ПРАВ для удаления канала {channel.name}! Боту нужны права manage_channels")
        except discord.NotFound:
            print(f"⚠️ [TEMP_VOICE] Канал {channel.name} уже удалён")
        except Exception as e:
            print(f"❌ [TEMP_VOICE] Ошибка удаления канала {channel.name}: {type(e).__name__}: {e}")
        
        if self.bot:
            await self.log_action(channel.guild, f"🗑️ Удалена временная комната: {channel.name}")
    
    async def schedule_deletion(self, channel: discord.VoiceChannel, creator_id: int):
        settings = self.get_settings()
        delay = settings.get('temp_voice_delete_delay', 60)
        channel_id = channel.id
        
        print(f"🎤 [TEMP_VOICE] schedule_deletion: канал={channel.name}, задержка={delay} сек, creator_id={creator_id}")
        
        if channel_id in self.delete_tasks:
            print(f"🎤 [DEBUG] schedule_deletion: отменяем предыдущую задачу для {channel_id}")
            self.delete_tasks[channel_id].cancel()
        
        async def delete_task():
            try:
                print(f"🎤 [DEBUG] delete_task: таймер запущен для {channel.name}, ждём {delay} сек")
                await asyncio.sleep(delay)
                
                print(f"🎤 [DEBUG] delete_task: таймер сработал для {channel.name}, проверяем создателя")
                guild = channel.guild
                member = guild.get_member(creator_id)
                
                print(f"🎤 [DEBUG] delete_task: member={member.name if member else None}, voice_channel={member.voice.channel.name if member and member.voice and member.voice.channel else None}")
                
                if member and member.voice and member.voice.channel == channel:
                    print(f"🎤 [TEMP_VOICE] Создатель вернулся, отмена удаления")
                    if channel_id in self.delete_tasks:
                        del self.delete_tasks[channel_id]
                    await self.log_action(guild, f"🔄 Отмена удаления комнаты {channel.name} — создатель вернулся")
                    return
                
                print(f"🎤 [DEBUG] delete_task: создатель не вернулся, удаляем комнату")
                await self.delete_room(channel, "Создатель покинул комнату")
                
            except asyncio.CancelledError:
                print(f"🎤 [DEBUG] delete_task: задача удаления ОТМЕНЕНА для {channel.name}")
            except Exception as e:
                print(f"❌ [TEMP_VOICE] delete_task: ошибка {type(e).__name__}: {e}")
        
        task = asyncio.create_task(delete_task())
        self.delete_tasks[channel_id] = task
        self.pending_deletions[channel_id] = datetime.now()
        print(f"🎤 [DEBUG] schedule_deletion: задача создана, tasks={list(self.delete_tasks.keys())}")
        
        await self.log_action(channel.guild, f"⏰ Запланировано удаление комнаты {channel.name} через {delay} сек")
    
    async def cancel_deletion(self, channel: discord.VoiceChannel):
        channel_id = channel.id
        print(f"🎤 [DEBUG] cancel_deletion вызван для канала {channel.name}")
        
        if channel_id in self.delete_tasks:
            print(f"🎤 [DEBUG] cancel_deletion: отменяем задачу {channel_id}")
            self.delete_tasks[channel_id].cancel()
            del self.delete_tasks[channel_id]
        else:
            print(f"🎤 [DEBUG] cancel_deletion: задачи для {channel_id} не найдено")
        
        if channel_id in self.pending_deletions:
            del self.pending_deletions[channel_id]
    
    async def expand_slots(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> tuple:
        print(f"🎤 [DEBUG] expand_slots НАЧАЛО, пользователь={interaction.user.name}, канал={channel.name}")
        
        settings = self.get_settings()
        max_slots = settings.get('temp_voice_max_slots', 10)
        
        room = self.get_room_by_channel(channel.id)
        if not room:
            print(f"🎤 [DEBUG] expand_slots: комната не найдена")
            return False, "❌ Комната не найдена"
        
        current_slots = room['slots']
        print(f"🎤 [DEBUG] expand_slots: текущие слоты={current_slots}, максимум={max_slots}")
        
        if current_slots >= max_slots:
            print(f"🎤 [DEBUG] expand_slots: достигнут максимум")
            return False, f"❌ Достигнут максимум слотов: {max_slots}"
        
        new_slots = min(current_slots + 2, max_slots)
        print(f"🎤 [DEBUG] expand_slots: новые слоты={new_slots}")
        
        self.update_room_slots(channel.id, new_slots)
        await channel.edit(user_limit=new_slots)
        
        if channel.id in self.active_rooms:
            self.active_rooms[channel.id]['slots'] = new_slots
        
        await self.log_action(interaction.guild, f"📈 {interaction.user.mention} расширил комнату {channel.name} до {new_slots} слотов")
        
        return True, f"✅ Количество слотов увеличено до **{new_slots}**"
    
    async def kick_user(self, interaction: discord.Interaction, channel: discord.VoiceChannel, target_user: discord.Member) -> tuple:
        print(f"🎤 [DEBUG] kick_user НАЧАЛО, пользователь={interaction.user.name}, кикает={target_user.name}, канал={channel.name}")
        
        if target_user == interaction.user:
            print(f"🎤 [DEBUG] kick_user: нельзя кикнуть себя")
            return False, "❌ Нельзя кикнуть самого себя"
        
        if target_user not in channel.members:
            print(f"🎤 [DEBUG] kick_user: пользователь не в комнате")
            return False, "❌ Пользователь не находится в этой комнате"
        
        try:
            await target_user.move_to(None, reason=f"Кикнут создателем комнаты {interaction.user.display_name}")
            print(f"🎤 [DEBUG] kick_user: пользователь {target_user.name} кикнут")
            await self.log_action(interaction.guild, f"👢 {interaction.user.mention} кикнул {target_user.mention} из комнаты {channel.name}")
            return True, f"✅ Пользователь {target_user.mention} удалён из комнаты"
        except Exception as e:
            print(f"❌ [DEBUG] kick_user: ошибка {type(e).__name__}: {e}")
            return False, f"❌ Ошибка: {e}"
    
    async def close_room(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        print(f"🎤 [DEBUG] close_room НАЧАЛО, пользователь={interaction.user.name}, канал={channel.name}")
        await self.delete_room(channel, f"Закрыта создателем {interaction.user.display_name}")
        await self.log_action(interaction.guild, f"🔒 {interaction.user.mention} закрыл комнату {channel.name}")
    
    async def check_creator_presence(self, guild: discord.Guild):
        print(f"🎤 [DEBUG] check_creator_presence НАЧАЛО для гильдии {guild.name}")
        rooms = self.get_all_rooms()
        
        for room in rooms:
            channel = guild.get_channel(int(room['channel_id']))
            if not channel:
                print(f"🎤 [DEBUG] check_creator_presence: канал {room['channel_id']} не найден, удаляем из БД")
                self.delete_room_from_db(int(room['channel_id']))
                continue
            
            creator = guild.get_member(room['creator_id'])
            print(f"🎤 [DEBUG] check_creator_presence: канал={channel.name}, creator={creator.name if creator else None}, voice={creator.voice.channel.name if creator and creator.voice and creator.voice.channel else None}")
            
            if not creator or not creator.voice or creator.voice.channel != channel:
                print(f"🎤 [DEBUG] check_creator_presence: создатель не в комнате, удаляем")
                await self.delete_room(channel, "Создатель не в комнате после перезапуска")
            else:
                print(f"🎤 [DEBUG] check_creator_presence: создатель в комнате, добавляем в active_rooms")
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