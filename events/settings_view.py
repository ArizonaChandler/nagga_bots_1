"""Панель настроек системы мероприятий"""
import discord
from core.admin_views import AdminOnlyView
from core.database import db
from core.config import CONFIG, save_config
from core.utils import is_admin
from events.manager import events_manager


class EventsSettingsView(AdminOnlyView):
    
    def __init__(self):
        super().__init__(timeout=None)
        self._add_buttons()
        self._add_back_button()
    
    def _add_buttons(self):
        self.clear_items()
        
        mod_btn = discord.ui.Button(
            label="📋 Канал модерации",
            style=discord.ButtonStyle.primary,
            emoji="📋",
            row=0,
            custom_id="events_mod_channel"
        )
        mod_btn.callback = self.set_moderation_channel
        self.add_item(mod_btn)
        
        part_btn = discord.ui.Button(
            label="📢 Канал сбора участников",
            style=discord.ButtonStyle.primary,
            emoji="📢",
            row=0,
            custom_id="events_part_channel"
        )
        part_btn.callback = self.set_participant_channel
        self.add_item(part_btn)
        
        log_btn = discord.ui.Button(
            label="📜 Канал логов",
            style=discord.ButtonStyle.primary,
            emoji="📜",
            row=1,
            custom_id="events_log_channel"
        )
        log_btn.callback = self.set_log_channel
        self.add_item(log_btn)
        
        time_btn = discord.ui.Button(
            label="⏱️ Время сбора по умолчанию",
            style=discord.ButtonStyle.secondary,
            emoji="⏱️",
            row=1,
            custom_id="events_default_time"
        )
        time_btn.callback = self.set_default_collect_time
        self.add_item(time_btn)
    
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
                description="Настройка всех модулей бота.",
                color=0x7289da
            )
            await interaction.response.edit_message(embed=embed, view=GlobalSettingsPanel(interaction.client))
        
        back_btn.callback = back_callback
        self.add_item(back_btn)
    
    async def set_moderation_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetEventsChannelModal("events_moderation_channel", "канал модерации"))
    
    async def set_participant_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetEventsChannelModal("events_participant_channel", "канал сбора участников"))
    
    async def set_log_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetEventsChannelModal("events_log_channel", "канал логов"))
    
    async def set_default_collect_time(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetEventsDefaultTimeModal())


class SetEventsChannelModal(discord.ui.Modal, title="📡 НАСТРОЙКА КАНАЛА"):
    def __init__(self, setting_key: str, description: str):
        super().__init__()
        self.setting_key = setting_key
        self.description = description
        self.channel_id = discord.ui.TextInput(label=f"ID {description}", placeholder="123456789012345678", max_length=20, required=True)
        self.add_item(self.channel_id)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            channel = interaction.guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return
            events_manager.save_setting(self.setting_key, self.channel_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ {self.description} настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetEventsDefaultTimeModal(discord.ui.Modal, title="⏱️ ВРЕМЯ СБОРА ПО УМОЛЧАНИЮ"):
    time = discord.ui.TextInput(label="Минуты", placeholder="20", max_length=3, required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            minutes = int(self.time.value)
            if minutes < 1:
                await interaction.response.send_message("❌ Минимум 1 минута", ephemeral=True)
                return
            if minutes > 120:
                await interaction.response.send_message("❌ Максимум 120 минут", ephemeral=True)
                return
            events_manager.save_setting('events_default_collect_time', str(minutes), str(interaction.user.id))
            await interaction.response.send_message(f"✅ Время сбора по умолчанию: **{minutes}** минут", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Введите число", ephemeral=True)