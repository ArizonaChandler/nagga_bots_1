"""Панель управления мероприятиями с постоянными кнопками"""
import discord
import logging
from core.admin_views import AdminOnlyView
from core.config import CONFIG, save_config
from core.database import db
from core.utils import format_mention, is_admin
from datetime import datetime
from events.base import PermanentView

logger = logging.getLogger(__name__)


class EventsSettingsView(AdminOnlyView):
    """Постоянные кнопки для настройки системы мероприятий"""

    def __init__(self):
        super().__init__()
        self._add_buttons()
        self._add_back_button()

    def _add_buttons(self):
        self.clear_items()
        alarm_btn = discord.ui.Button(label="🔔 Каналы напоминаний", style=discord.ButtonStyle.primary, emoji="🔔", row=0, custom_id="events_alarm")
        alarm_btn.callback = self.set_alarm_channels
        self.add_item(alarm_btn)
        
        announce_btn = discord.ui.Button(label="📢 Каналы оповещений", style=discord.ButtonStyle.primary, emoji="📢", row=0, custom_id="events_announce")
        announce_btn.callback = self.set_announce_channels
        self.add_item(announce_btn)
        
        reminder_btn = discord.ui.Button(label="👥 Роли для напоминаний", style=discord.ButtonStyle.primary, emoji="👥", row=1, custom_id="events_reminder")
        reminder_btn.callback = self.set_reminder_roles
        self.add_item(reminder_btn)
        
        announce_role_btn = discord.ui.Button(label="👥 Роли для оповещений", style=discord.ButtonStyle.primary, emoji="👥", row=1, custom_id="events_announce_roles")
        announce_role_btn.callback = self.set_announce_roles
        self.add_item(announce_role_btn)
        
        add_btn = discord.ui.Button(label="➕ Добавить МП", style=discord.ButtonStyle.success, emoji="➕", row=2, custom_id="events_add")
        add_btn.callback = self.add_event
        self.add_item(add_btn)
        
        list_btn = discord.ui.Button(label="📋 Список МП", style=discord.ButtonStyle.secondary, emoji="📋", row=2, custom_id="events_list")
        list_btn.callback = self.list_events
        self.add_item(list_btn)
        
        stats_btn = discord.ui.Button(label="📊 Статистика", style=discord.ButtonStyle.secondary, emoji="📊", row=3, custom_id="events_stats")
        stats_btn.callback = self.show_stats
        self.add_item(stats_btn)

    def _add_back_button(self):
        back_btn = discord.ui.Button(
            label="◀ Назад в главное меню",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=4,
            custom_id="events_back_to_global"
        )
        
        async def back_callback(interaction: discord.Interaction):
            from core.settings_panel import GlobalSettingsPanel
            embed = discord.Embed(
                title="⚙️ **ЦЕНТР УПРАВЛЕНИЯ СИСТЕМАМИ**",
                description="Настройка всех модулей бота.\n\n"
                            "Здесь отображаются кнопки только для **включённых** систем.",
                color=0x7289da
            )
            await interaction.response.edit_message(embed=embed, view=GlobalSettingsPanel(interaction.client))
        
        back_btn.callback = back_callback
        self.add_item(back_btn)

    async def set_alarm_channels(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetAlarmChannelsSettingsModal())

    async def set_announce_channels(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetAnnounceChannelsSettingsModal())

    async def set_reminder_roles(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetReminderRolesSettingsModal())

    async def set_announce_roles(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetAnnounceRolesSettingsModal())

    async def add_event(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(AddEventSettingsModal())

    async def list_events(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        events = db.get_events(enabled_only=False)
        if not events:
            await interaction.response.send_message("📅 Нет созданных мероприятий", ephemeral=True)
            return
        view = EventPaginatedView(events, 0)
        await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)

    async def show_stats(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await send_event_stats(interaction, interaction.guild)


class EventPaginatedView(AdminOnlyView):
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
        embed = discord.Embed(title="⚙️ УПРАВЛЕНИЕ МЕРОПРИЯТИЯМИ", description=f"Всего мероприятий: **{len(self.events)}**\nСтраница {self.page + 1} из {self.total_pages}", color=0x00ff00, timestamp=datetime.now())
        days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        events_text = ""
        for i, event in enumerate(current_events, start):
            status = "✅" if event['enabled'] else "❌"
            events_text += f"{status} **{i}.** {event['name']} — {days[event['weekday']]} {event['event_time']}\n"
        if events_text:
            embed.add_field(name="📋 Список мероприятий", value=events_text[:1024], inline=False)
        active_count = sum(1 for e in self.events if e['enabled'])
        inactive_count = len(self.events) - active_count
        embed.add_field(name="✅ Активные", value=str(active_count), inline=True)
        embed.add_field(name="❌ Неактивные", value=str(inactive_count), inline=True)
        return embed

    def update_buttons(self):
        self.clear_items()
        if self.page > 0:
            prev_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary, custom_id="events_prev")
            async def prev_callback(interaction):
                self.page -= 1
                self.update_buttons()
                await interaction.response.edit_message(embed=self.get_embed(), view=self)
            prev_btn.callback = prev_callback
            self.add_item(prev_btn)
        if self.page < self.total_pages - 1:
            next_btn = discord.ui.Button(label="Вперёд ▶", style=discord.ButtonStyle.secondary, custom_id="events_next")
            async def next_callback(interaction):
                self.page += 1
                self.update_buttons()
                await interaction.response.edit_message(embed=self.get_embed(), view=self)
            next_btn.callback = next_callback
            self.add_item(next_btn)
        
        class EventSelect(discord.ui.Select):
            def __init__(self, page_events, all_events, page_num):
                options = []
                days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
                for event in page_events:
                    status = "✅" if event['enabled'] else "❌"
                    name = event['name'][:45] + "..." if len(event['name']) > 45 else event['name']
                    options.append(discord.SelectOption(label=f"{name}", description=f"{days[event['weekday']]} {event['event_time']}", value=str(event['id']), emoji="✅" if event['enabled'] else "❌"))
                super().__init__(placeholder=f"Страница {page_num + 1} - выберите мероприятие", min_values=1, max_values=1, options=options)
                self.all_events = all_events
            
            async def callback(self, interaction: discord.Interaction):
                event_id = int(self.values[0])
                event = db.get_event(event_id)
                if not event:
                    await interaction.response.send_message("❌ Мероприятие не найдено", ephemeral=True)
                    return
                days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
                view = EventManageView(event_id, event['name'], event['weekday'], event['event_time'], event['enabled'])
                embed = discord.Embed(title=f"⚙️ УПРАВЛЕНИЕ: {event['name']}", color=0xffa500)
                embed.add_field(name="📅 День", value=days[event['weekday']], inline=True)
                embed.add_field(name="⏰ Время", value=event['event_time'], inline=True)
                embed.add_field(name="📊 Статус", value="✅ Активен" if event['enabled'] else "❌ Отключен", inline=True)
                await interaction.response.edit_message(embed=embed, view=view)
        
        self.add_item(EventSelect(self.get_current_page_events(), self.events, self.page))


class EventManageView(AdminOnlyView):
    def __init__(self, event_id: int, event_name: str, weekday: int, event_time: str, enabled: bool):
        super().__init__(timeout=60)
        self.event_id = event_id
        self.event_name = event_name
        self.weekday = weekday
        self.event_time = event_time
        self.enabled = enabled
        
        edit_btn = discord.ui.Button(label="✏️ Редактировать", style=discord.ButtonStyle.primary, emoji="✏️", row=0, custom_id="event_edit")
        edit_btn.callback = self.edit_button
        self.add_item(edit_btn)
        
        toggle_btn = discord.ui.Button(label="🔄 Переключить статус", style=discord.ButtonStyle.secondary, emoji="🔄", row=0, custom_id="event_toggle")
        toggle_btn.callback = self.toggle_button
        self.add_item(toggle_btn)
        
        delete_btn = discord.ui.Button(label="🗑️ Удалить", style=discord.ButtonStyle.danger, emoji="🗑️", row=1, custom_id="event_delete")
        delete_btn.callback = self.delete_button
        self.add_item(delete_btn)

    async def edit_button(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(EditEventSettingsModal(self.event_id, self.event_name, self.weekday, self.event_time))

    async def toggle_button(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        new_status = not self.enabled
        db.update_event(self.event_id, enabled=1 if new_status else 0)
        db.log_event_action(self.event_id, "toggled", str(interaction.user.id), f"Статус: {'включен' if new_status else 'отключен'}")
        await interaction.response.send_message(f"✅ Мероприятие {'включено' if new_status else 'отключено'}", ephemeral=True)
        self.enabled = new_status

    async def delete_button(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        view = ConfirmDeleteEventView(self.event_id, self.event_name)
        await interaction.response.send_message(f"❓ Ты уверен, что хочешь удалить **{self.event_name}**?", view=view, ephemeral=True)


class ConfirmDeleteEventView(AdminOnlyView):
    def __init__(self, event_id: int, event_name: str):
        super().__init__(timeout=30)
        self.event_id = event_id
        self.event_name = event_name

    @discord.ui.button(label="✅ Да, удалить", style=discord.ButtonStyle.danger, custom_id="confirm_delete")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        success = db.delete_event(self.event_id, soft=False)
        if success:
            db.log_event_action(self.event_id, "deleted", str(interaction.user.id))
            await interaction.response.edit_message(content=f"✅ Мероприятие **{self.event_name}** удалено", view=None)
        else:
            await interaction.response.edit_message(content="❌ Не удалось удалить мероприятие", view=None)

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary, custom_id="cancel_delete")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Удаление отменено", view=None)


class SetAlarmChannelsSettingsModal(discord.ui.Modal, title="🔔 КАНАЛЫ НАПОМИНАНИЙ"):
    channels = discord.ui.TextInput(label="ID каналов (через запятую)", placeholder="123456789,987654321,456123789", style=discord.TextStyle.paragraph, max_length=200, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
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
                await interaction.response.send_message(f"❌ Каналы с ID {', '.join(invalid_channels)} не найдены", ephemeral=True)
                return
            CONFIG['alarm_channels'] = valid_channels
            save_config(str(interaction.user.id))
            await interaction.response.send_message(f"✅ Каналы напоминаний настроены: {len(valid_channels)} каналов", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetAnnounceChannelsSettingsModal(discord.ui.Modal, title="📢 КАНАЛЫ ОПОВЕЩЕНИЙ"):
    channels = discord.ui.TextInput(label="ID каналов (через запятую)", placeholder="123456789,987654321,456123789", style=discord.TextStyle.paragraph, max_length=200, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
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
                await interaction.response.send_message(f"❌ Каналы с ID {', '.join(invalid_channels)} не найдены", ephemeral=True)
                return
            CONFIG['announce_channels'] = valid_channels
            save_config(str(interaction.user.id))
            await interaction.response.send_message(f"✅ Каналы оповещений настроены: {len(valid_channels)} каналов", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetReminderRolesSettingsModal(discord.ui.Modal, title="🔔 РОЛИ ДЛЯ НАПОМИНАНИЙ"):
    roles = discord.ui.TextInput(label="ID ролей (через запятую)", placeholder="123456789,987654321", style=discord.TextStyle.paragraph, max_length=200, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
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
                await interaction.response.send_message(f"❌ Роли с ID {', '.join(invalid_roles)} не найдены", ephemeral=True)
                return
            CONFIG['reminder_roles'] = valid_roles
            save_config(str(interaction.user.id))
            await interaction.response.send_message(f"✅ Роли для напоминаний настроены: {len(valid_roles)} ролей", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetAnnounceRolesSettingsModal(discord.ui.Modal, title="📢 РОЛИ ДЛЯ ОПОВЕЩЕНИЙ"):
    roles = discord.ui.TextInput(label="ID ролей (через запятую)", placeholder="123456789,987654321", style=discord.TextStyle.paragraph, max_length=200, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
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
                await interaction.response.send_message(f"❌ Роли с ID {', '.join(invalid_roles)} не найдены", ephemeral=True)
                return
            CONFIG['announce_roles'] = valid_roles
            save_config(str(interaction.user.id))
            await interaction.response.send_message(f"✅ Роли для оповещений настроены: {len(valid_roles)} ролей", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class AddEventSettingsModal(discord.ui.Modal, title="➕ ДОБАВИТЬ МЕРОПРИЯТИЯ"):
    event_name = discord.ui.TextInput(
        label="Название мероприятия",
        placeholder="Например: Arena",
        max_length=100,
        required=True
    )
    
    weekdays = discord.ui.TextInput(
        label="Дни недели (0-6 через запятую или диапазон)",
        placeholder="0,2,4,6  или  0-6",
        max_length=20,
        required=True
    )
    
    event_times = discord.ui.TextInput(
        label="Время (ЧЧ:ММ через запятую)",
        placeholder="14:20, 19:30, 21:00",
        max_length=50,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        try:
            # Парсим дни недели
            weekdays = []
            days_input = self.weekdays.value.replace(' ', '')
            
            if not days_input:
                await interaction.response.send_message("❌ Укажите дни недели", ephemeral=True)
                return
            
            # Поддержка диапазона (например 0-6)
            if '-' in days_input and ',' not in days_input:
                parts = days_input.split('-')
                if len(parts) == 2:
                    start = int(parts[0])
                    end = int(parts[1])
                    weekdays = list(range(start, end + 1))
                else:
                    await interaction.response.send_message("❌ Неверный формат диапазона", ephemeral=True)
                    return
            else:
                # Разбираем через запятую
                for d in days_input.split(','):
                    try:
                        day = int(d)
                        if 0 <= day <= 6:
                            weekdays.append(day)
                        else:
                            await interaction.response.send_message(f"❌ День {day} должен быть от 0 до 6", ephemeral=True)
                            return
                    except ValueError:
                        await interaction.response.send_message(f"❌ Неверный день: {d}", ephemeral=True)
                        return
            
            weekdays = sorted(set(weekdays))
            
            # Парсим время
            times = []
            times_input = self.event_times.value.replace(' ', '')
            
            for t in times_input.split(','):
                try:
                    datetime.strptime(t, "%H:%M")
                    times.append(t)
                except ValueError:
                    await interaction.response.send_message(f"❌ Неверный формат времени: {t}", ephemeral=True)
                    return
            
            times = sorted(set(times))
            
            # Создаём мероприятия
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
            
            if created_ids:
                db.log_event_action(created_ids[0], "created", str(interaction.user.id), 
                                   f"Название: {self.event_name.value}, Дни: {days_str}, Времена: {times_str}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Ошибка в AddEventSettingsModal: {e}")
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)


class EditEventSettingsModal(discord.ui.Modal, title="✏️ РЕДАКТИРОВАТЬ МЕРОПРИЯТИЕ"):
    def __init__(self, event_id: int, current_name: str, current_weekday: int, current_time: str):
        super().__init__()
        self.event_id = event_id
        self.event_name = discord.ui.TextInput(label="Название мероприятия", default=current_name, max_length=100, required=True)
        self.add_item(self.event_name)
        self.weekday = discord.ui.TextInput(label="День недели (0-6, где 0 - Пн)", default=str(current_weekday), max_length=1, required=True)
        self.add_item(self.weekday)
        self.event_time = discord.ui.TextInput(label="Время (ЧЧ:ММ)", default=current_time, max_length=5, required=True)
        self.add_item(self.event_time)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            day = int(self.weekday.value)
            if day < 0 or day > 6:
                await interaction.response.send_message("❌ День недели должен быть от 0 до 6", ephemeral=True)
                return
            datetime.strptime(self.event_time.value, "%H:%M")
            db.update_event(self.event_id, name=self.event_name.value, weekday=day, event_time=self.event_time.value)
            db.log_event_action(self.event_id, "edited", str(interaction.user.id), f"Новое: {self.event_name.value} {self.event_time.value}")
            days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
            await interaction.response.send_message(f"✅ Мероприятие обновлено!\n📌 {self.event_name.value}\n📅 {days[day]} в {self.event_time.value}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Неверный формат времени", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


async def send_event_stats(interaction, guild):
    top = db.get_top_organizers(10, days=30)
    stats = db.get_event_stats_summary()
    embed = discord.Embed(title="📊 **СТАТИСТИКА МЕРОПРИЯТИЙ**", color=0x00ff00, timestamp=datetime.now())
    if top:
        top_text = ""
        for i, row in enumerate(top[:5], 1):
            user_id, user_name, count = row
            try:
                user = await guild.fetch_member(int(user_id))
                mention = user.mention
            except:
                mention = f"**{user_name}**"
            top_text += f"{i}. {mention} — **{count}** МП\n"
        embed.add_field(name="🏆 Топ организаторов (30 дней)", value=top_text or "Нет данных", inline=False)
    else:
        embed.add_field(name="🏆 Топ организаторов", value="Нет данных за 30 дней", inline=False)
    embed.add_field(name="📅 Мероприятия", value=f"Всего: `{stats['total_events']}`\nАктивных: `{stats['active_events']}`", inline=True)
    embed.add_field(name="✅ Проведено", value=f"За всё время: `{stats['total_takes']}`\nЗа 30 дней: `{stats['takes_30d']}`\nСегодня: `{stats['takes_today']}`", inline=True)
    await interaction.followup.send(embed=embed, ephemeral=True)