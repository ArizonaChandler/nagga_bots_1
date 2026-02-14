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


class AddEventModal(discord.ui.Modal, title="➕ ДОБАВИТЬ МЕРОПРИЯТИЯ"):
    event_name = discord.ui.TextInput(
        label="Название мероприятия",
        placeholder="Например: DROP, Штурм, Каньон",
        max_length=100
    )
    
    weekdays = discord.ui.TextInput(
        label="Дни недели (0-6 через запятую или диапазон)",
        placeholder="2 (среда) или 1,3,5 или 1-5 (Вт-Сб)",
        max_length=20
    )
    
    event_times = discord.ui.TextInput(
        label="Время (ЧЧ:ММ через запятую)",
        placeholder="20:00 или 08:00,12:00,20:00",
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        try:
            # ===== ПАРСИМ ДНИ НЕДЕЛИ =====
            weekdays = []
            days_input = self.weekdays.value.replace(' ', '')
            
            if not days_input:
                await interaction.response.send_message("❌ Укажите дни недели", ephemeral=True)
                return
            
            # Проверяем, есть ли диапазон (например "1-5")
            if '-' in days_input:
                parts = days_input.split('-')
                if len(parts) == 2:
                    try:
                        start = int(parts[0])
                        end = int(parts[1])
                        if 0 <= start <= 6 and 0 <= end <= 6 and start <= end:
                            weekdays = list(range(start, end + 1))
                        else:
                            await interaction.response.send_message(
                                "❌ Диапазон должен быть от 0 до 6 и начало <= конец", 
                                ephemeral=True
                            )
                            return
                    except ValueError:
                        await interaction.response.send_message(
                            "❌ Неверный формат диапазона. Используйте например 1-5", 
                            ephemeral=True
                        )
                        return
                else:
                    await interaction.response.send_message(
                        "❌ Неверный формат диапазона. Используйте например 1-5", 
                        ephemeral=True
                    )
                    return
            else:
                # Разбираем через запятую (может быть одно число или несколько)
                for d in days_input.split(','):
                    try:
                        day = int(d)
                        if 0 <= day <= 6:
                            weekdays.append(day)
                        else:
                            await interaction.response.send_message(
                                f"❌ День {day} должен быть от 0 до 6 (0-Пн, 6-Вс)", 
                                ephemeral=True
                            )
                            return
                    except ValueError:
                        await interaction.response.send_message(
                            f"❌ Неверный день: {d}. Должно быть число от 0 до 6", 
                            ephemeral=True
                        )
                        return
            
            # Убираем дубликаты и сортируем
            weekdays = sorted(set(weekdays))
            
            # ===== ПАРСИМ ВРЕМЯ =====
            times = []
            times_input = self.event_times.value.replace(' ', '')
            
            if not times_input:
                await interaction.response.send_message("❌ Укажите время", ephemeral=True)
                return
            
            for t in times_input.split(','):
                try:
                    # Проверяем формат времени
                    datetime.strptime(t, "%H:%M")
                    times.append(t)
                except ValueError:
                    await interaction.response.send_message(
                        f"❌ Неверный формат времени: {t}. Используйте ЧЧ:ММ (например 20:00)",
                        ephemeral=True
                    )
                    return
            
            # Убираем дубликаты времени
            times = sorted(set(times))
            
            # ===== СОЗДАЁМ МЕРОПРИЯТИЯ =====
            created_count = 0
            days_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
            created_ids = []
            
            for day in weekdays:
                for time in times:
                    event_id = db.add_event(
                        name=self.event_name.value,
                        weekday=day,
                        event_time=time,
                        created_by=str(interaction.user.id)
                    )
                    created_count += 1
                    created_ids.append(event_id)
            
            # Генерируем расписание
            db.generate_schedule(days_ahead=14)
            
            # Формируем красивое описание
            days_str = ', '.join([days_names[d] for d in weekdays])
            times_str = ', '.join(times)
            
            embed = discord.Embed(
                title="✅ Мероприятия добавлены",
                description=f"Создано **{created_count}** мероприятий",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.add_field(name="📌 Название", value=self.event_name.value, inline=True)
            embed.add_field(name="📅 Дни", value=days_str, inline=True)
            embed.add_field(name="⏰ Времена", value=times_str, inline=False)
            
            # Логируем первое мероприятие
            if created_ids:
                db.log_event_action(created_ids[0], "created", str(interaction.user.id), 
                                   f"Название: {self.event_name.value}, Дни: {days_str}, Времена: {times_str}")
            
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
    def __init__(self, event_id: int, event_name: str, event_time: str, meeting_time: str = None, reminder_view=None):
        super().__init__()
        self.event_id = event_id
        self.event_name = event_name
        self.event_time = event_time
        self.meeting_time = meeting_time
        self.reminder_view = reminder_view
        
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
        
        # ===== НОВЫЙ КОД ДЛЯ ОТПРАВКИ ВО ВСЕ КАНАЛЫ =====
        # Получаем список каналов для оповещений
        announce_channels = CONFIG.get('announce_channels', [])
        
        # Если нет отдельных каналов для оповещений, используем каналы напоминаний
        if not announce_channels:
            announce_channels = CONFIG.get('alarm_channels', [])
        
        # Получаем роли для упоминания
        announce_roles = CONFIG.get('announce_roles', [])
        role_mentions = []
        
        # Получаем сервер
        server_id = CONFIG.get('server_id')
        guild = None
        if server_id:
            guild = interaction.client.get_guild(int(server_id))
        
        if guild:
            for role_id in announce_roles:
                role = guild.get_role(int(role_id))
                if role:
                    role_mentions.append(role.mention)
        
        # Отправляем во все каналы
        if announce_channels:
            event_dt_today = datetime.strptime(f"{today} {self.event_time}", "%Y-%m-%d %H:%M")
            meeting_dt_today = event_dt_today - timedelta(minutes=20)
            meeting_timestamp = int(meeting_dt_today.timestamp())
            
            embed = discord.Embed(
                title=f"✅ СБОР НА МЕРОПРИЯТИЕ: {self.event_name}",
                description=f"Мероприятие проведёт: {interaction.user.mention}",
                color=0x00ff00
            )
            
            embed.add_field(
                name="⏱️ Сбор в",
                value=f"**{meeting_time}** МСК",
                inline=False
            )
            
            embed.add_field(
                name="📍 Место сбора",
                value=self.meeting_place.value,
                inline=True
            )
            
            embed.add_field(
                name="🔢 Код группы",
                value=self.group_code.value,
                inline=True
            )
            
            embed.add_field(
                name="Участие:",
                value="Для участия зайди в игру, в войс и приедь на место сбора",
                inline=False
            )
            
            embed.set_footer(text="Unit Management System by Nagga")
            
            # Отправляем в каждый канал
            content = ' '.join(role_mentions) if role_mentions else None
            sent_count = 0
            
            for channel_id in announce_channels:
                try:
                    channel = interaction.client.get_channel(int(channel_id))
                    if channel:
                        await channel.send(content=content, embed=embed)
                        sent_count += 1
                    else:
                        # Пробуем через guild
                        if guild:
                            channel = guild.get_channel(int(channel_id))
                            if channel:
                                await channel.send(content=content, embed=embed)
                                sent_count += 1
                except Exception as e:
                    print(f"Ошибка отправки в канал {channel_id}: {e}")
            
            print(f"✅ Отправлено в {sent_count} каналов оповещений")
        
        # ===== КОНЕЦ НОВОГО КОДА =====
        
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
        
        # Обновляем сообщение с напоминанием
        if self.reminder_view:
            await self.reminder_view.update_taken_status(
                interaction.user.id,
                interaction.user.display_name,
                self.group_code.value,
                self.meeting_place.value
            )

class SetAlarmChannelsModal(discord.ui.Modal, title="🔔 НАСТРОЙКА КАНАЛОВ НАПОМИНАНИЙ"):
    def __init__(self, guild=None):
        super().__init__()
        self.guild = guild
    
    channels = discord.ui.TextInput(
        label="ID каналов (через запятую)",
        placeholder="123456789,987654321,456123789",
        style=discord.TextStyle.paragraph,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Получаем сервер из CONFIG
            server_id = CONFIG.get('server_id')
            if not server_id:
                await interaction.response.send_message(
                    "❌ Сначала установите ID сервера в Глобальных настройках",
                    ephemeral=True
                )
                return
            
            guild = interaction.client.get_guild(int(server_id))
            if not guild:
                await interaction.response.send_message(
                    f"❌ Сервер с ID {server_id} не найден. Бот не добавлен на этот сервер?",
                    ephemeral=True
                )
                return
            
            channel_ids = [c.strip() for c in self.channels.value.split(',') if c.strip()]
            
            valid_channels = []
            invalid_channels = []
            
            for cid in channel_ids:
                try:
                    channel = guild.get_channel(int(cid))
                    if channel:
                        valid_channels.append(cid)
                    else:
                        invalid_channels.append(cid)
                except ValueError:
                    invalid_channels.append(cid)
            
            if invalid_channels:
                await interaction.response.send_message(
                    f"❌ Каналы с ID {', '.join(invalid_channels)} не найдены на сервере {guild.name}",
                    ephemeral=True
                )
                return
            
            CONFIG['alarm_channels'] = valid_channels
            save_config(str(interaction.user.id))
            
            channels_mention = []
            for cid in valid_channels[:3]:
                channel = guild.get_channel(int(cid))
                if channel:
                    channels_mention.append(channel.mention)
                else:
                    channels_mention.append(f"`{cid}`")
            
            if len(valid_channels) > 3:
                channels_mention.append(f"и ещё {len(valid_channels)-3}")
            
            await interaction.response.send_message(
                f"✅ Каналы напоминаний настроены на сервере **{guild.name}**:\n{', '.join(channels_mention)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)


class SetAnnounceChannelsModal(discord.ui.Modal, title="📢 НАСТРОЙКА КАНАЛОВ ОПОВЕЩЕНИЙ"):
    def __init__(self, guild=None):
        super().__init__()
        self.guild = guild
    
    channels = discord.ui.TextInput(
        label="ID каналов (через запятую)",
        placeholder="123456789,987654321,456123789",
        style=discord.TextStyle.paragraph,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            server_id = CONFIG.get('server_id')
            if not server_id:
                await interaction.response.send_message(
                    "❌ Сначала установите ID сервера в Глобальных настройках",
                    ephemeral=True
                )
                return
            
            guild = interaction.client.get_guild(int(server_id))
            if not guild:
                await interaction.response.send_message(
                    f"❌ Сервер с ID {server_id} не найден",
                    ephemeral=True
                )
                return
            
            channel_ids = [c.strip() for c in self.channels.value.split(',') if c.strip()]
            
            valid_channels = []
            invalid_channels = []
            
            for cid in channel_ids:
                try:
                    channel = guild.get_channel(int(cid))
                    if channel:
                        valid_channels.append(cid)
                    else:
                        invalid_channels.append(cid)
                except ValueError:
                    invalid_channels.append(cid)
            
            if invalid_channels:
                await interaction.response.send_message(
                    f"❌ Каналы с ID {', '.join(invalid_channels)} не найдены",
                    ephemeral=True
                )
                return
            
            CONFIG['announce_channels'] = valid_channels
            save_config(str(interaction.user.id))
            
            channels_mention = []
            for cid in valid_channels[:3]:
                channel = guild.get_channel(int(cid))
                if channel:
                    channels_mention.append(channel.mention)
                else:
                    channels_mention.append(f"`{cid}`")
            
            if len(valid_channels) > 3:
                channels_mention.append(f"и ещё {len(valid_channels)-3}")
            
            await interaction.response.send_message(
                f"✅ Каналы оповещений настроены:\n{', '.join(channels_mention)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)


class SetReminderRolesModal(discord.ui.Modal, title="🔔 РОЛИ ДЛЯ НАПОМИНАНИЙ"):
    def __init__(self, guild=None):
        super().__init__()
        self.guild = guild
    
    roles = discord.ui.TextInput(
        label="ID ролей (через запятую)",
        placeholder="123456789,987654321",
        style=discord.TextStyle.paragraph,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            server_id = CONFIG.get('server_id')
            if not server_id:
                await interaction.response.send_message(
                    "❌ Сначала установите ID сервера в Глобальных настройках",
                    ephemeral=True
                )
                return
            
            guild = interaction.client.get_guild(int(server_id))
            if not guild:
                await interaction.response.send_message(
                    f"❌ Сервер с ID {server_id} не найден",
                    ephemeral=True
                )
                return
            
            role_ids = [r.strip() for r in self.roles.value.split(',') if r.strip()]
            
            valid_roles = []
            invalid_roles = []
            
            for rid in role_ids:
                try:
                    role = guild.get_role(int(rid))
                    if role:
                        valid_roles.append(rid)
                    else:
                        invalid_roles.append(rid)
                except ValueError:
                    invalid_roles.append(rid)
            
            if invalid_roles:
                await interaction.response.send_message(
                    f"❌ Роли с ID {', '.join(invalid_roles)} не найдены",
                    ephemeral=True
                )
                return
            
            CONFIG['reminder_roles'] = valid_roles
            save_config(str(interaction.user.id))
            
            roles_mention = []
            for rid in valid_roles[:3]:
                role = guild.get_role(int(rid))
                if role:
                    roles_mention.append(role.mention)
                else:
                    roles_mention.append(f"`{rid}`")
            
            if len(valid_roles) > 3:
                roles_mention.append(f"и ещё {len(valid_roles)-3}")
            
            await interaction.response.send_message(
                f"✅ Роли для напоминаний:\n{', '.join(roles_mention)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)


class SetAnnounceRolesModal(discord.ui.Modal, title="📢 РОЛИ ДЛЯ ОПОВЕЩЕНИЙ"):
    def __init__(self, guild=None):
        super().__init__()
        self.guild = guild
    
    roles = discord.ui.TextInput(
        label="ID ролей (через запятую)",
        placeholder="123456789,987654321",
        style=discord.TextStyle.paragraph,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            server_id = CONFIG.get('server_id')
            if not server_id:
                await interaction.response.send_message(
                    "❌ Сначала установите ID сервера в Глобальных настройках",
                    ephemeral=True
                )
                return
            
            guild = interaction.client.get_guild(int(server_id))
            if not guild:
                await interaction.response.send_message(
                    f"❌ Сервер с ID {server_id} не найден",
                    ephemeral=True
                )
                return
            
            role_ids = [r.strip() for r in self.roles.value.split(',') if r.strip()]
            
            valid_roles = []
            invalid_roles = []
            
            for rid in role_ids:
                try:
                    role = guild.get_role(int(rid))
                    if role:
                        valid_roles.append(rid)
                    else:
                        invalid_roles.append(rid)
                except ValueError:
                    invalid_roles.append(rid)
            
            if invalid_roles:
                await interaction.response.send_message(
                    f"❌ Роли с ID {', '.join(invalid_roles)} не найдены",
                    ephemeral=True
                )
                return
            
            CONFIG['announce_roles'] = valid_roles
            save_config(str(interaction.user.id))
            
            roles_mention = []
            for rid in valid_roles[:3]:
                role = guild.get_role(int(rid))
                if role:
                    roles_mention.append(role.mention)
                else:
                    roles_mention.append(f"`{rid}`")
            
            if len(valid_roles) > 3:
                roles_mention.append(f"и ещё {len(valid_roles)-3}")
            
            await interaction.response.send_message(
                f"✅ Роли для оповещений:\n{', '.join(roles_mention)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)