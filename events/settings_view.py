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