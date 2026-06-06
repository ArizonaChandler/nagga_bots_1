"""Панель настроек системы AFK"""
import discord
from core.admin_views import AdminOnlyView
from core.config import CONFIG, save_config
from core.database import db
from core.utils import format_mention, is_admin
from afk.base import PermanentView
from afk.manager import afk_manager


class AFKSettingsView(AdminOnlyView):
    """Постоянные кнопки для настройки системы AFK"""

    def __init__(self):
        super().__init__()
        self._add_buttons()
        self._add_back_button()

    def _add_buttons(self):
        self.clear_items()
        channel_btn = discord.ui.Button(label="📢 Канал AFK", style=discord.ButtonStyle.primary, emoji="📢", row=0, custom_id="afk_channel")
        channel_btn.callback = self.set_afk_channel
        self.add_item(channel_btn)
        
        log_btn = discord.ui.Button(label="📜 Канал логов AFK", style=discord.ButtonStyle.primary, emoji="📜", row=0, custom_id="afk_log")
        log_btn.callback = self.set_log_channel
        self.add_item(log_btn)
        
        hours_btn = discord.ui.Button(label="⏰ Макс. часов AFK", style=discord.ButtonStyle.primary, emoji="⏰", row=1, custom_id="afk_hours")
        hours_btn.callback = self.set_max_hours
        self.add_item(hours_btn)
        
        show_btn = discord.ui.Button(label="📊 Текущие настройки", style=discord.ButtonStyle.secondary, emoji="📊", row=1, custom_id="afk_show")
        show_btn.callback = self.show_settings
        self.add_item(show_btn)

    def _add_back_button(self):
        back_btn = discord.ui.Button(
            label="◀ Назад в главное меню",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=2,
            custom_id="afk_back_to_global"
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

    async def set_afk_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetAFKChannelModal())

    async def set_log_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetAFKLogChannelModal())

    async def set_max_hours(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetAFKMaxHoursModal())

    async def show_settings(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        embed = discord.Embed(title="📊 НАСТРОЙКИ СИСТЕМЫ AFK", color=0x00ff00)
        guild = interaction.guild
        settings = afk_manager.get_settings()
        afk_channel = format_mention(guild, settings.get('afk_channel'), 'channel') if settings.get('afk_channel') else "`Не настроен`"
        log_channel = format_mention(guild, settings.get('afk_log_channel'), 'channel') if settings.get('afk_log_channel') else "`Не настроен`"
        max_hours = settings.get('afk_max_hours', 24)
        embed.add_field(name="📢 Канал AFK", value=afk_channel, inline=False)
        embed.add_field(name="📜 Канал логов AFK", value=log_channel, inline=False)
        embed.add_field(name="⏰ Максимальное время AFK", value=f"`{max_hours} часов`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetAFKChannelModal(discord.ui.Modal, title="📢 КАНАЛ AFK"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", max_length=20, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            channel = interaction.guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return
            afk_manager.save_setting('afk_channel', self.channel_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Канал AFK настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetAFKLogChannelModal(discord.ui.Modal, title="📜 КАНАЛ ЛОГОВ AFK"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", max_length=20, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            channel = interaction.guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return
            afk_manager.save_setting('afk_log_channel', self.channel_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Канал логов AFK настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetAFKMaxHoursModal(discord.ui.Modal, title="⏰ МАКСИМАЛЬНОЕ ВРЕМЯ AFK"):
    hours = discord.ui.TextInput(label="Максимальное количество часов", placeholder="24", max_length=3, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            hours_num = int(self.hours.value)
            if hours_num <= 0:
                await interaction.response.send_message("❌ Часов должно быть больше 0", ephemeral=True)
                return
            if hours_num > 168:
                await interaction.response.send_message("❌ Максимум 168 часов (7 дней)", ephemeral=True)
                return
            CONFIG['afk_max_hours'] = str(hours_num)
            db.set_setting('afk_max_hours', str(hours_num), str(interaction.user.id))
            save_config(str(interaction.user.id))
            await interaction.response.send_message(f"✅ Максимальное время AFK установлено: **{hours_num} часов**", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Введите число", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)