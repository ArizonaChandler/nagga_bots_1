"""Admin Modals - Модальные окна для административных настроек"""
import discord
from datetime import datetime, timedelta
from core.database import db
from core.config import CONFIG, save_config, SUPER_ADMIN_ID
from core.utils import format_mention, is_super_admin, is_admin

# ===== ОРИГИНАЛЬНЫЕ МОДАЛКИ (из CAPT, MCL и т.д.) =====

class SetRoleModal(discord.ui.Modal, title="🎭 УСТАНОВИТЬ РОЛЬ CAPT"):
    role_id = discord.ui.TextInput(label="ID роли", placeholder="123456789012345678")
    
    async def on_submit(self, interaction: discord.Interaction):
        CONFIG['capt_role_id'] = self.role_id.value
        save_config(str(interaction.user.id))
        db.log_action(str(interaction.user.id), "SET_CAPT_ROLE", f"Role ID: {self.role_id.value}")
        await interaction.response.send_message(
            f"✅ Роль CAPT: {format_mention(interaction.guild, self.role_id.value, 'role')}",
            ephemeral=True
        )


class SetCaptChannelModal(discord.ui.Modal, title="💬 УСТАНОВИТЬ ЧАТ ОШИБОК"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678")
    
    async def on_submit(self, interaction: discord.Interaction):
        CONFIG['capt_channel_id'] = self.channel_id.value
        save_config(str(interaction.user.id))
        db.log_action(str(interaction.user.id), "SET_CAPT_CHANNEL", f"Channel ID: {self.channel_id.value}")
        await interaction.response.send_message(
            f"✅ Чат ошибок: {format_mention(interaction.guild, self.channel_id.value, 'channel')}",
            ephemeral=True
        )


class SetServerModal(discord.ui.Modal, title="🌍 УСТАНОВИТЬ СЕРВЕР"):
    server_id = discord.ui.TextInput(label="ID сервера", placeholder="123456789012345678")
    
    async def on_submit(self, interaction: discord.Interaction):
        CONFIG['server_id'] = self.server_id.value
        save_config(str(interaction.user.id))
        db.log_action(str(interaction.user.id), "SET_SERVER", f"Server ID: {self.server_id.value}")
        await interaction.response.send_message(
            f"✅ Сервер: `{self.server_id.value}`",
            ephemeral=True
        )


class AddUserModal(discord.ui.Modal, title="👥 ДОБАВИТЬ ПОЛЬЗОВАТЕЛЯ"):
    user_id = discord.ui.TextInput(label="ID пользователя", placeholder="123456789012345678")
    
    async def on_submit(self, interaction: discord.Interaction):
        if db.add_user(self.user_id.value, str(interaction.user.id)):
            db.log_action(str(interaction.user.id), "ADD_USER", f"Added {self.user_id.value}")
            await interaction.response.send_message(
                f"✅ Добавлен: {format_mention(interaction.guild, self.user_id.value, 'user')}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("⚠️ Пользователь уже существует", ephemeral=True)


class RemoveUserModal(discord.ui.Modal, title="❌ УДАЛИТЬ ПОЛЬЗОВАТЕЛЯ"):
    user_id = discord.ui.TextInput(label="ID пользователя", placeholder="123456789012345678")
    
    async def on_submit(self, interaction: discord.Interaction):
        if db.remove_user(self.user_id.value):
            db.log_action(str(interaction.user.id), "REMOVE_USER", f"Removed {self.user_id.value}")
            await interaction.response.send_message(
                f"✅ Удалён: {format_mention(interaction.guild, self.user_id.value, 'user')}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("⚠️ Пользователь не найден", ephemeral=True)


class AddAdminModal(discord.ui.Modal, title="👑 ДОБАВИТЬ АДМИНИСТРАТОРА"):
    user_id = discord.ui.TextInput(label="ID пользователя", placeholder="123456789012345678")
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только супер-администратор", ephemeral=True)
            return
        
        if db.add_admin(self.user_id.value, str(interaction.user.id)):
            db.add_user(self.user_id.value, str(interaction.user.id))
            db.log_action(str(interaction.user.id), "ADD_ADMIN", f"Added admin {self.user_id.value}")
            await interaction.response.send_message(
                f"✅ Администратор: {format_mention(interaction.guild, self.user_id.value, 'user')}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("⚠️ Пользователь уже администратор", ephemeral=True)


class RemoveAdminModal(discord.ui.Modal, title="👑 УДАЛИТЬ АДМИНИСТРАТОРА"):
    user_id = discord.ui.TextInput(label="ID пользователя", placeholder="123456789012345678")
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только супер-администратор", ephemeral=True)
            return
        
        if self.user_id.value == SUPER_ADMIN_ID:
            await interaction.response.send_message("❌ Нельзя удалить супер-администратора", ephemeral=True)
            return
        
        if db.remove_admin(self.user_id.value):
            db.log_action(str(interaction.user.id), "REMOVE_ADMIN", f"Removed admin {self.user_id.value}")
            await interaction.response.send_message(
                f"✅ Администратор удалён: {format_mention(interaction.guild, self.user_id.value, 'user')}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("⚠️ Пользователь не является администратором", ephemeral=True)


# ===== НОВЫЕ МОДАЛКИ ДЛЯ СИСТЕМЫ ОПОВЕЩЕНИЙ =====

class SetAlarmChannelModal(discord.ui.Modal, title="🔔 УСТАНОВИТЬ ЧАТ НАПОМИНАНИЙ"):
    channel_id = discord.ui.TextInput(
        label="ID канала",
        placeholder="123456789012345678",
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        CONFIG['alarm_channel_id'] = self.channel_id.value
        save_config(str(interaction.user.id))
        db.log_action(str(interaction.user.id), "SET_ALARM_CHANNEL", f"Channel ID: {self.channel_id.value}")
        await interaction.response.send_message(
            f"✅ Чат напоминаний: {format_mention(interaction.guild, self.channel_id.value, 'channel')}",
            ephemeral=True
        )


class SetAnnounceChannelModal(discord.ui.Modal, title="📢 УСТАНОВИТЬ КАНАЛ ОПОВЕЩЕНИЙ"):
    channel_id = discord.ui.TextInput(
        label="ID канала",
        placeholder="123456789012345678",
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        CONFIG['announce_channel_id'] = self.channel_id.value
        save_config(str(interaction.user.id))
        db.log_action(str(interaction.user.id), "SET_ANNOUNCE_CHANNEL", f"Channel ID: {self.channel_id.value}")
        await interaction.response.send_message(
            f"✅ Канал оповещений: {format_mention(interaction.guild, self.channel_id.value, 'channel')}",
            ephemeral=True
        )


class AddEventModal(discord.ui.Modal, title="➕ ДОБАВИТЬ МЕРОПРИЯТИЕ"):
    event_name = discord.ui.TextInput(
        label="Название мероприятия",
        placeholder="Например: Штурм, Каньон, ГГ",
        max_length=100
    )
    
    weekday = discord.ui.TextInput(
        label="День недели (0-6, где 0 - Пн)",
        placeholder="1 (вторник)",
        max_length=1,
        min_length=1
    )
    
    event_time = discord.ui.TextInput(
        label="Время (МСК, ЧЧ:ММ)",
        placeholder="19:30",
        max_length=5,
        min_length=5
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        try:
            # Проверка дня недели
            try:
                weekday = int(self.weekday.value)
                if weekday < 0 or weekday > 6:
                    await interaction.response.send_message("❌ День недели должен быть от 0 до 6", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ День недели должен быть числом", ephemeral=True)
                return
            
            # Проверка времени
            try:
                datetime.strptime(self.event_time.value, "%H:%M")
            except ValueError:
                await interaction.response.send_message("❌ Неверный формат времени. Используйте ЧЧ:ММ", ephemeral=True)
                return
            
            event_id = db.add_event(
                name=self.event_name.value,
                weekday=weekday,
                event_time=self.event_time.value,
                created_by=str(interaction.user.id)
            )
            
            db.log_event_action(event_id, "created", str(interaction.user.id), 
                               f"Название: {self.event_name.value}, Время: {self.event_time.value}")
            
            days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
            embed = discord.Embed(
                title="✅ Мероприятие добавлено",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.add_field(name="📌 Название", value=self.event_name.value, inline=True)
            embed.add_field(name="📅 День", value=days[weekday], inline=True)
            embed.add_field(name="⏰ Время", value=self.event_time.value, inline=True)
            embed.add_field(name="🆔 ID", value=f"`{event_id}`", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Ошибка в AddEventModal: {e}")
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)


class EditEventModal(discord.ui.Modal, title="✏️ РЕДАКТИРОВАТЬ МЕРОПРИЯТИЕ"):
    def __init__(self, event_id: int, current_name: str, current_weekday: int, current_time: str):
        super().__init__()
        self.event_id = event_id
        
        self.event_name = discord.ui.TextInput(
            label="Название мероприятия",
            default=current_name,
            max_length=100
        )
        self.add_item(self.event_name)
        
        self.weekday = discord.ui.TextInput(
            label="День недели (0-6, где 0 - Пн)",
            default=str(current_weekday),
            max_length=1
        )
        self.add_item(self.weekday)
        
        self.event_time = discord.ui.TextInput(
            label="Время (МСК, ЧЧ:ММ)",
            default=current_time,
            max_length=5
        )
        self.add_item(self.event_time)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        try:
            weekday = int(self.weekday.value)
            if weekday < 0 or weekday > 6:
                await interaction.response.send_message("❌ День недели должен быть от 0 до 6", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ День недели должен быть числом", ephemeral=True)
            return
        
        try:
            datetime.strptime(self.event_time.value, "%H:%M")
        except ValueError:
            await interaction.response.send_message("❌ Неверный формат времени", ephemeral=True)
            return
        
        db.update_event(
            self.event_id,
            name=self.event_name.value,
            weekday=weekday,
            event_time=self.event_time.value
        )
        
        db.log_event_action(self.event_id, "edited", str(interaction.user.id),
                           f"Новое: {self.event_name.value} {self.event_time.value}")
        
        await interaction.response.send_message(f"✅ Мероприятие ID {self.event_id} обновлено", ephemeral=True)


class TakeEventModal(discord.ui.Modal, title="🎮 ВЗЯТЬ МЕРОПРИЯТИЕ"):
    def __init__(self, event_id: int, event_name: str, event_time: str, meeting_time: str = None):
        super().__init__()
        self.event_id = event_id
        self.event_name = event_name
        self.event_time = event_time
        self.meeting_time = meeting_time
        
    group_code = discord.ui.TextInput(
        label="🔢 Код группы",
        placeholder="Например: 2177, GTA5RP",
        max_length=50
    )
    
    meeting_place = discord.ui.TextInput(
        label="📍 Место сбора",
        placeholder="Например: У банка, аэропорт, мэрия",
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        from datetime import datetime, timedelta
        import pytz
        
        msk_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(msk_tz)
        today = now.date().isoformat()
        
        # Проверяем, не взято ли уже
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT taken_by FROM event_schedule 
                WHERE event_id = ? AND scheduled_date = ?
            ''', (self.event_id, today))
            result = cursor.fetchone()
            
            if result and result[0]:
                await interaction.response.send_message(
                    f"❌ Это мероприятие уже взял <@{result[0]}>",
                    ephemeral=True
                )
                return
        
        # Используем переданное время сбора или вычисляем (за 20 минут до начала)
        if self.meeting_time:
            meeting_time = self.meeting_time
        else:
            event_dt = datetime.strptime(self.event_time, "%H:%M")
            meeting_dt = (event_dt - timedelta(minutes=20)).strftime("%H:%M")
            meeting_time = meeting_dt
        
        # Записываем взятие
        take_id = db.take_event(
            event_id=self.event_id,
            user_id=str(interaction.user.id),
            user_name=interaction.user.display_name,
            group_code=self.group_code.value,
            meeting_place=self.meeting_place.value,
            event_date=today
        )
        
        db.log_event_action(self.event_id, "taken", str(interaction.user.id),
                           f"Группа: {self.group_code.value}, Место: {self.meeting_place.value}")
        
        # Отправляем в канал оповещений (или в канал напоминаний, если отдельный не настроен)
        channel_id = CONFIG.get('announce_channel_id') or CONFIG.get('alarm_channel_id')
        if channel_id:
            channel = interaction.guild.get_channel(int(channel_id))
            if channel:
                # Вычисляем unix timestamp для сбора (20 минут до начала)
                event_dt_today = datetime.strptime(f"{today} {self.event_time}", "%Y-%m-%d %H:%M")
                meeting_dt_today = event_dt_today - timedelta(minutes=20)
                meeting_timestamp = int(meeting_dt_today.timestamp())
                
                embed = discord.Embed(
                    title=f"🎮 {self.event_name}",
                    description=f"В **{self.event_time}** играем!\n"
                               f"⏰ **Сбор в {meeting_time} МСК**",
                    color=0x00ff00
                )
                embed.add_field(name="👤 Проводит", value=interaction.user.mention, inline=True)
                embed.add_field(name="📍 Место сбора", value=self.meeting_place.value, inline=True)
                embed.add_field(name="🔢 Код группы", value=self.group_code.value, inline=True)
                embed.add_field(
                    name="⏰ Сбор через",
                    value=f"<t:{meeting_timestamp}:R>",
                    inline=True
                )
                embed.set_footer(text="Всем желающим в войс, в игру и на зафул!")
                
                await channel.send(embed=embed)
        
        # Определяем время сбора для ответа пользователю
        if meeting_time:
            collection_time = meeting_time
        else:
            event_dt = datetime.strptime(self.event_time, "%H:%M")
            collection_dt = (event_dt - timedelta(minutes=20)).strftime("%H:%M")
            collection_time = collection_dt
        
        await interaction.response.send_message(
            f"✅ Ты взял МП **{self.event_name}**!\n"
            f"⏰ **Сбор в {collection_time} МСК**\n"
            f"📍 Место сбора: {self.meeting_place.value}\n"
            f"🔢 Код группы: {self.group_code.value}",
            ephemeral=True
        )