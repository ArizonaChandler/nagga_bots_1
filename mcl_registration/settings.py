"""Панель управления системой MCL (в канале настроек)"""
import discord
from core.database import db
from core.utils import is_admin
from core.config import CONFIG, save_config
from core.admin_views import AdminOnlyView
from mcl_registration.base import PermanentView


class MCLSettingsView(AdminOnlyView):
    """Панель управления системой MCL"""

    def __init__(self):
        super().__init__()
        self._add_buttons()

    def _add_buttons(self):
        self.clear_items()
        
        channels_btn = discord.ui.Button(label="📡 Настройка каналов MCL", style=discord.ButtonStyle.primary, emoji="📡", row=0, custom_id="mcl_channels")
        channels_btn.callback = self.channels_menu
        self.add_item(channels_btn)
        
        role_btn = discord.ui.Button(label="🎭 Роль для рассылки", style=discord.ButtonStyle.primary, emoji="🎭", row=1, custom_id="mcl_role")
        role_btn.callback = self.set_role
        self.add_item(role_btn)
        
        error_btn = discord.ui.Button(label="💬 Канал ошибок", style=discord.ButtonStyle.primary, emoji="💬", row=1, custom_id="mcl_error")
        error_btn.callback = self.set_error_channel
        self.add_item(error_btn)
        
        announcement_btn = discord.ui.Button(label="📢 Канал оповещений", style=discord.ButtonStyle.primary, emoji="📢", row=2, custom_id="mcl_announcement")
        announcement_btn.callback = self.set_announcement_channel
        self.add_item(announcement_btn)

    def _add_back_button(self):
        back_btn = discord.ui.Button(
            label="◀ Назад в главное меню",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=3,
            custom_id="mcl_back_to_global"
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

    async def channels_menu(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        embed = discord.Embed(title="📡 **НАСТРОЙКА КАНАЛОВ MCL**", description="Выберите, какой канал хотите настроить:", color=0x7289da)
        view = MCLChannelsView()
        await interaction.response.edit_message(embed=embed, view=view)

    async def set_role(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetMCLRoleModal())

    async def set_error_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetMCLErrorChannelModal())

    async def set_announcement_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetMCLAnnouncementChannelModal())


class MCLChannelsView(AdminOnlyView):
    def __init__(self):
        super().__init__(timeout=60)

        main_btn = discord.ui.Button(label="🔴 Канал модерации", style=discord.ButtonStyle.secondary, row=0, custom_id="mcl_main")
        main_btn.callback = self.set_main_channel
        self.add_item(main_btn)

        reserve_btn = discord.ui.Button(label="🟡 Публичный канал", style=discord.ButtonStyle.secondary, row=0, custom_id="mcl_reserve")
        reserve_btn.callback = self.set_reserve_channel
        self.add_item(reserve_btn)

        back_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=1, custom_id="mcl_back")
        back_btn.callback = self.back
        self.add_item(back_btn)

    async def set_main_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetMCLChannelModal("mcl_reg_main_channel", "канал модерации MCL"))

    async def set_reserve_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetMCLChannelModal("mcl_reg_reserve_channel", "публичный канал MCL"))

    async def back(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⚙️ **УПРАВЛЕНИЕ СИСТЕМОЙ MCL**", description="Настройка системы MCL/ВЗМ", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=MCLSettingsView())


class SetMCLChannelModal(discord.ui.Modal, title="📡 НАСТРОЙКА КАНАЛА"):
    def __init__(self, setting_key: str, description: str):
        super().__init__()
        self.setting_key = setting_key
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
            db.set_setting(self.setting_key, self.channel_id.value, str(interaction.user.id))
            CONFIG[self.setting_key] = self.channel_id.value
            save_config(str(interaction.user.id))
            await interaction.response.send_message(f"✅ {self.channel_id.label} настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetMCLRoleModal(discord.ui.Modal, title="🎭 РОЛЬ ДЛЯ РАССЫЛКИ MCL"):
    role_id = discord.ui.TextInput(label="ID роли", placeholder="123456789012345678", max_length=20, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        role = interaction.guild.get_role(int(self.role_id.value))
        if not role:
            await interaction.response.send_message("❌ Роль не найдена", ephemeral=True)
            return
        db.set_setting('mcl_role_id', self.role_id.value, str(interaction.user.id))
        CONFIG['mcl_role_id'] = self.role_id.value
        save_config(str(interaction.user.id))
        await interaction.response.send_message(f"✅ Роль {role.mention} настроена для рассылки MCL", ephemeral=True)


class SetMCLErrorChannelModal(discord.ui.Modal, title="💬 КАНАЛ ОШИБОК MCL"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", max_length=20, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        channel = interaction.guild.get_channel(int(self.channel_id.value))
        if not channel:
            await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
            return
        db.set_setting('mcl_error_channel', self.channel_id.value, str(interaction.user.id))
        CONFIG['mcl_error_channel'] = self.channel_id.value
        save_config(str(interaction.user.id))
        await interaction.response.send_message(f"✅ Канал ошибок MCL настроен: {channel.mention}", ephemeral=True)


class SetMCLAnnouncementChannelModal(discord.ui.Modal, title="📢 КАНАЛ ОПОВЕЩЕНИЙ MCL"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", max_length=20, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        channel = interaction.guild.get_channel(int(self.channel_id.value))
        if not channel:
            await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
            return
        db.set_setting('mcl_announcement_channel', self.channel_id.value, str(interaction.user.id))
        CONFIG['mcl_announcement_channel'] = self.channel_id.value
        save_config(str(interaction.user.id))
        await interaction.response.send_message(f"✅ Канал оповещений MCL настроен: {channel.mention}", ephemeral=True)