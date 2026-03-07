"""Панель управления мероприятиями с постоянными кнопками"""
import discord
import logging
from events.base import PermanentView
from core.config import CONFIG, save_config
from core.database import db
from core.utils import format_mention
from datetime import datetime

logger = logging.getLogger(__name__)

class EventsSettingsView(PermanentView):
    """Постоянные кнопки для настройки системы мероприятий"""
    
    def __init__(self):
        super().__init__()
        logger.debug("EventsSettingsView создан")
    
    @discord.ui.button(
        label="🔔 Каналы напоминаний", 
        style=discord.ButtonStyle.primary,
        emoji="🔔",
        row=0,
        custom_id="events_settings_alarm_channels"
    )
    async def set_alarm_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить каналы для напоминаний"""
        await interaction.response.send_modal(SetAlarmChannelsSettingsModal())
    
    @discord.ui.button(
        label="📢 Каналы оповещений", 
        style=discord.ButtonStyle.primary,
        emoji="📢",
        row=0,
        custom_id="events_settings_announce_channels"
    )
    async def set_announce_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить каналы для оповещений"""
        await interaction.response.send_modal(SetAnnounceChannelsSettingsModal())
    
    @discord.ui.button(
        label="👥 Роли для напоминаний", 
        style=discord.ButtonStyle.primary,
        emoji="👥",
        row=1,
        custom_id="events_settings_reminder_roles"
    )
    async def set_reminder_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить роли для напоминаний"""
        await interaction.response.send_modal(SetReminderRolesSettingsModal())
    
    @discord.ui.button(
        label="👥 Роли для оповещений", 
        style=discord.ButtonStyle.primary,
        emoji="👥",
        row=1,
        custom_id="events_settings_announce_roles"
    )
    async def set_announce_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить роли для оповещений"""
        await interaction.response.send_modal(SetAnnounceRolesSettingsModal())
    
    @discord.ui.button(
        label="➕ Добавить МП", 
        style=discord.ButtonStyle.success,
        emoji="➕",
        row=2,
        custom_id="events_settings_add_event"
    )
    async def add_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Добавить новое мероприятие"""
        await interaction.response.send_modal(AddEventSettingsModal())
    
    @discord.ui.button(
        label="📋 Список МП", 
        style=discord.ButtonStyle.secondary,
        emoji="📋",
        row=2,
        custom_id="events_settings_list_events"
    )
    async def list_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать список мероприятий"""
        await interaction.response.defer(ephemeral=True)
        
        events = db.get_events(enabled_only=True)
        
        if not events:
            await interaction.followup.send("📅 Нет активных мероприятий", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📋 СПИСОК МЕРОПРИЯТИЙ",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        
        for event in events[:10]:
            status = "✅" if event['enabled'] else "❌"
            embed.add_field(
                name=f"{status} {event['name']}",
                value=f"ID: `{event['id']}` | {days[event['weekday']]} {event['event_time']}",
                inline=False
            )
        
        if len(events) > 10:
            embed.set_footer(text=f"Показано 10 из {len(events)} мероприятий")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="⚙️ Управление МП", 
        style=discord.ButtonStyle.primary,
        emoji="⚙️",
        row=3,
        custom_id="events_settings_manage"
    )
    async def manage_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Управление существующими мероприятиями"""
        # Получаем ВСЕ мероприятия
        events = db.get_events(enabled_only=False)
        
        if not events:
            await interaction.response.send_message("📅 Нет созданных мероприятий", ephemeral=True)
            return
        
        # Создаем пагинированное меню
        view = EventPaginatedView(events, 0)
        await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)


    class EventPaginatedView(discord.ui.View):
        """Пагинированное меню для выбора мероприятия"""
        
        def __init__(self, events, page):
            super().__init__(timeout=60)
            self.events = events
            self.page = page
            self.items_per_page = 25
            self.total_pages = (len(events) + self.items_per_page - 1) // self.items_per_page
            
            self.update_buttons()
        
        def get_current_page_events(self):
            start = self.page * self.items_per_page
            end = start + self.items_per_page
            return self.events[start:end]
        
        def get_embed(self):
            current_events = self.get_current_page_events()
            start = self.page * self.items_per_page + 1
            end = min((self.page + 1) * self.items_per_page, len(self.events))
            
            embed = discord.Embed(
                title="⚙️ УПРАВЛЕНИЕ МЕРОПРИЯТИЯМИ",
                description=f"Всего мероприятий: **{len(self.events)}**\nСтраница {self.page + 1} из {self.total_pages}",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
            
            events_text = ""
            for i, event in enumerate(current_events, start):
                status = "✅" if event['enabled'] else "❌"
                events_text += f"{status} **{i}.** {event['name']} — {days[event['weekday']]} {event['event_time']}\n"
            
            if events_text:
                embed.add_field(name="📋 Список мероприятий", value=events_text[:1024], inline=False)
            
            # Статистика
            active_count = sum(1 for e in self.events if e['enabled'])
            inactive_count = len(self.events) - active_count
            embed.add_field(name="✅ Активные", value=str(active_count), inline=True)
            embed.add_field(name="❌ Неактивные", value=str(inactive_count), inline=True)
            
            return embed
        
        def update_buttons(self):
            self.clear_items()
            
            # Кнопки пагинации
            if self.page > 0:
                prev_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
                async def prev_callback(interaction):
                    self.page -= 1
                    self.update_buttons()
                    await interaction.response.edit_message(embed=self.get_embed(), view=self)
                prev_btn.callback = prev_callback
                self.add_item(prev_btn)
            
            if self.page < self.total_pages - 1:
                next_btn = discord.ui.Button(label="Вперёд ▶", style=discord.ButtonStyle.secondary)
                async def next_callback(interaction):
                    self.page += 1
                    self.update_buttons()
                    await interaction.response.edit_message(embed=self.get_embed(), view=self)
                next_btn.callback = next_callback
                self.add_item(next_btn)
            
            # Добавляем Select меню для текущей страницы
            class EventSelect(discord.ui.Select):
                def __init__(self, page_events, all_events, page_num):
                    options = []
                    days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
                    
                    for event in page_events:
                        status = "✅" if event['enabled'] else "❌"
                        name = event['name'][:45] + "..." if len(event['name']) > 45 else event['name']
                        
                        options.append(
                            discord.SelectOption(
                                label=f"{name}",
                                description=f"{days[event['weekday']]} {event['event_time']}",
                                value=str(event['id']),
                                emoji="✅" if event['enabled'] else "❌"
                            )
                        )
                    
                    super().__init__(
                        placeholder=f"Страница {page_num + 1} - выберите мероприятие",
                        min_values=1,
                        max_values=1,
                        options=options
                    )
                    self.all_events = all_events
                
                async def callback(self, interaction: discord.Interaction):
                    event_id = int(self.values[0])
                    event = db.get_event(event_id)
                    
                    if not event:
                        await interaction.response.send_message("❌ Мероприятие не найдено", ephemeral=True)
                        return
                    
                    days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
                    
                    view = EventManageView(event_id, event['name'], event['weekday'], event['event_time'], event['enabled'])
                    embed = discord.Embed(
                        title=f"⚙️ УПРАВЛЕНИЕ: {event['name']}",
                        color=0xffa500
                    )
                    embed.add_field(name="📅 День", value=days[event['weekday']], inline=True)
                    embed.add_field(name="⏰ Время", value=event['event_time'], inline=True)
                    embed.add_field(name="📊 Статус", value="✅ Активен" if event['enabled'] else "❌ Отключен", inline=True)
                    
                    await interaction.response.edit_message(embed=embed, view=view)
            
            self.add_item(EventSelect(self.get_current_page_events(), self.events, self.page))
    
    @discord.ui.button(
        label="📊 Статистика", 
        style=discord.ButtonStyle.secondary,
        emoji="📊",
        row=3,
        custom_id="events_settings_stats"
    )
    async def show_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать статистику мероприятий"""
        await interaction.response.defer(ephemeral=True)
        
        top = db.get_top_organizers(10, days=30)
        stats = db.get_event_stats_summary()
        
        embed = discord.Embed(
            title="📊 СТАТИСТИКА МЕРОПРИЯТИЙ",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        if top:
            top_text = ""
            for i, row in enumerate(top[:5], 1):
                user_id, user_name, count = row
                top_text += f"{i}. <@{user_id}> — **{count}** МП\n"
            embed.add_field(name="🏆 Топ организаторов (30 дней)", value=top_text, inline=False)
        
        embed.add_field(
            name="📅 Всего МП",
            value=f"Активных: `{stats['active_events']}`\nВсего: `{stats['total_events']}`",
            inline=True
        )
        
        embed.add_field(
            name="✅ Проведено",
            value=f"За всё время: `{stats['total_takes']}`\nЗа 30 дней: `{stats['takes_30d']}`",
            inline=True
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class EventManageView(discord.ui.View):
    """Управление конкретным мероприятием"""
    
    def __init__(self, event_id: int, event_name: str, weekday: int, event_time: str, enabled: bool):
        super().__init__(timeout=60)
        self.event_id = event_id
        self.event_name = event_name
        self.weekday = weekday
        self.event_time = event_time
        self.enabled = enabled
    
    @discord.ui.button(label="✏️ Редактировать", style=discord.ButtonStyle.primary, emoji="✏️", row=0)
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Редактировать мероприятие"""
        modal = EditEventSettingsModal(self.event_id, self.event_name, self.weekday, self.event_time)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🔄 Переключить статус", style=discord.ButtonStyle.secondary, emoji="🔄", row=0)
    async def toggle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Включить/выключить мероприятие"""
        new_status = not self.enabled
        db.update_event(self.event_id, enabled=1 if new_status else 0)
        db.log_event_action(self.event_id, "toggled", str(interaction.user.id), 
                           f"Статус: {'включен' if new_status else 'отключен'}")
        
        await interaction.response.send_message(
            f"✅ Мероприятие {'включено' if new_status else 'отключено'}",
            ephemeral=True
        )
        
        # Обновляем кнопку
        self.enabled = new_status
    
    @discord.ui.button(label="🗑️ Удалить", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Удалить мероприятие"""
        # Создаем подтверждение
        view = ConfirmDeleteEventView(self.event_id, self.event_name)
        await interaction.response.send_message(
            f"❓ Ты уверен, что хочешь удалить **{self.event_name}**?",
            view=view,
            ephemeral=True
        )


class ConfirmDeleteEventView(discord.ui.View):
    """Подтверждение удаления мероприятия"""
    
    def __init__(self, event_id: int, event_name: str):
        super().__init__(timeout=30)
        self.event_id = event_id
        self.event_name = event_name
    
    @discord.ui.button(label="✅ Да, удалить", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        success = db.delete_event(self.event_id, soft=False)
        
        if success:
            db.log_event_action(self.event_id, "deleted", str(interaction.user.id))
            await interaction.response.edit_message(
                content=f"✅ Мероприятие **{self.event_name}** удалено",
                view=None
            )
        else:
            await interaction.response.edit_message(
                content="❌ Не удалось удалить мероприятие",
                view=None
            )
    
    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Удаление отменено", view=None)


# ===== МОДАЛКИ ДЛЯ НАСТРОЕК =====

class SetAlarmChannelsSettingsModal(discord.ui.Modal, title="🔔 КАНАЛЫ НАПОМИНАНИЙ"):
    def __init__(self):
        super().__init__()
    
    channels = discord.ui.TextInput(
        label="ID каналов (через запятую)",
        placeholder="123456789,987654321,456123789",
        style=discord.TextStyle.paragraph,
        max_length=200,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
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
                f"✅ Каналы напоминаний настроены:\n{', '.join(channels_mention)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetAnnounceChannelsSettingsModal(discord.ui.Modal, title="📢 КАНАЛЫ ОПОВЕЩЕНИЙ"):
    def __init__(self):
        super().__init__()
    
    channels = discord.ui.TextInput(
        label="ID каналов (через запятую)",
        placeholder="123456789,987654321,456123789",
        style=discord.TextStyle.paragraph,
        max_length=200,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
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
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetReminderRolesSettingsModal(discord.ui.Modal, title="🔔 РОЛИ ДЛЯ НАПОМИНАНИЙ"):
    def __init__(self):
        super().__init__()
    
    roles = discord.ui.TextInput(
        label="ID ролей (через запятую)",
        placeholder="123456789,987654321",
        style=discord.TextStyle.paragraph,
        max_length=200,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
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
                f"✅ Роли для напоминаний настроены:\n{', '.join(roles_mention)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetAnnounceRolesSettingsModal(discord.ui.Modal, title="📢 РОЛИ ДЛЯ ОПОВЕЩЕНИЙ"):
    def __init__(self):
        super().__init__()
    
    roles = discord.ui.TextInput(
        label="ID ролей (через запятую)",
        placeholder="123456789,987654321",
        style=discord.TextStyle.paragraph,
        max_length=200,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
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
                f"✅ Роли для оповещений настроены:\n{', '.join(roles_mention)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class AddEventSettingsModal(discord.ui.Modal, title="➕ ДОБАВИТЬ МЕРОПРИЯТИЕ"):
    def __init__(self):
        super().__init__()
    
    event_name = discord.ui.TextInput(
        label="Название мероприятия",
        placeholder="Например: Arena",
        max_length=100,
        required=True
    )
    
    weekday = discord.ui.TextInput(
        label="День недели (0-6, где 0 - Пн)",
        placeholder="0",
        max_length=1,
        required=True
    )
    
    event_time = discord.ui.TextInput(
        label="Время (ЧЧ:ММ)",
        placeholder="19:30",
        max_length=5,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Проверяем день недели
            try:
                day = int(self.weekday.value)
                if day < 0 or day > 6:
                    await interaction.response.send_message("❌ День недели должен быть от 0 до 6", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ День недели должен быть числом", ephemeral=True)
                return
            
            # Проверяем время
            try:
                from datetime import datetime
                datetime.strptime(self.event_time.value, "%H:%M")
            except ValueError:
                await interaction.response.send_message("❌ Неверный формат времени", ephemeral=True)
                return
            
            # Создаём мероприятие
            event_id = db.add_event(
                name=self.event_name.value,
                weekday=day,
                event_time=self.event_time.value,
                created_by=str(interaction.user.id)
            )
            
            db.generate_schedule(days_ahead=14)
            
            days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
            
            await interaction.response.send_message(
                f"✅ Мероприятие добавлено!\n"
                f"📌 {self.event_name.value}\n"
                f"📅 {days[day]} в {self.event_time.value}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class EditEventSettingsModal(discord.ui.Modal, title="✏️ РЕДАКТИРОВАТЬ МЕРОПРИЯТИЕ"):
    def __init__(self, event_id: int, current_name: str, current_weekday: int, current_time: str):
        super().__init__()
        self.event_id = event_id
        
        self.event_name = discord.ui.TextInput(
            label="Название мероприятия",
            default=current_name,
            max_length=100,
            required=True
        )
        self.add_item(self.event_name)
        
        self.weekday = discord.ui.TextInput(
            label="День недели (0-6, где 0 - Пн)",
            default=str(current_weekday),
            max_length=1,
            required=True
        )
        self.add_item(self.weekday)
        
        self.event_time = discord.ui.TextInput(
            label="Время (ЧЧ:ММ)",
            default=current_time,
            max_length=5,
            required=True
        )
        self.add_item(self.event_time)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Проверяем день недели
            try:
                day = int(self.weekday.value)
                if day < 0 or day > 6:
                    await interaction.response.send_message("❌ День недели должен быть от 0 до 6", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ День недели должен быть числом", ephemeral=True)
                return
            
            # Проверяем время
            try:
                from datetime import datetime
                datetime.strptime(self.event_time.value, "%H:%M")
            except ValueError:
                await interaction.response.send_message("❌ Неверный формат времени", ephemeral=True)
                return
            
            # Обновляем мероприятие
            db.update_event(
                self.event_id,
                name=self.event_name.value,
                weekday=day,
                event_time=self.event_time.value
            )
            
            db.log_event_action(self.event_id, "edited", str(interaction.user.id),
                               f"Новое: {self.event_name.value} {self.event_time.value}")
            
            days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
            
            await interaction.response.send_message(
                f"✅ Мероприятие обновлено!\n"
                f"📌 {self.event_name.value}\n"
                f"📅 {days[day]} в {self.event_time.value}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)