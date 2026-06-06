"""Панель настроек системы CAPT"""
import discord
from core.admin_views import AdminOnlyView
from core.config import CONFIG, save_config
from core.database import db
from core.utils import format_mention, is_admin
from capt_registration.base import PermanentView
from capt_registration.manager import capt_reg_manager


class CaptSettingsView(AdminOnlyView):
    """Постоянные кнопки для настройки системы CAPT"""
    
    def __init__(self):
        super().__init__()
        self._add_buttons()
        self._add_back_button()
    
    def _add_buttons(self):
        self.clear_items()
        # 🎯 Каналы CAPT
        channels_btn = discord.ui.Button(label="🎯 Каналы CAPT", style=discord.ButtonStyle.danger, emoji="🎯", row=0, custom_id="capt_channels")
        channels_btn.callback = self.set_channels
        self.add_item(channels_btn)
        
        # 📢 Канал оповещений
        alert_btn = discord.ui.Button(label="📢 Канал @everyone", style=discord.ButtonStyle.danger, emoji="📢", row=0, custom_id="capt_alert")
        alert_btn.callback = self.set_alert_channel
        self.add_item(alert_btn)
        
        # 🎭 Роль для рассылки
        role_btn = discord.ui.Button(label="🎭 Роль для ЛС", style=discord.ButtonStyle.danger, emoji="🎭", row=1, custom_id="capt_role")
        role_btn.callback = self.set_role
        self.add_item(role_btn)
        
        # 💬 Канал ошибок
        error_btn = discord.ui.Button(label="💬 Канал ошибок", style=discord.ButtonStyle.danger, emoji="💬", row=1, custom_id="capt_error")
        error_btn.callback = self.set_error_channel
        self.add_item(error_btn)
        
        # 📜 Канал логов
        log_btn = discord.ui.Button(label="📜 Канал логов", style=discord.ButtonStyle.danger, emoji="📜", row=2, custom_id="capt_log")
        log_btn.callback = self.set_log_channel
        self.add_item(log_btn)
        
        # 📊 Текущие настройки
        show_btn = discord.ui.Button(label="📊 Текущие настройки", style=discord.ButtonStyle.secondary, emoji="📊", row=2, custom_id="capt_show")
        show_btn.callback = self.show_settings
        self.add_item(show_btn)

    def _add_back_button(self):
        back_btn = discord.ui.Button(
            label="◀ Назад в главное меню",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=4,
            custom_id="capt_back_to_global"
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
    
    async def set_channels(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetCaptRegChannelsSettingsModal())
    
    async def set_alert_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetCaptAlertChannelSettingsModal())
    
    async def set_role(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetCaptRoleSettingsModal())
    
    async def set_error_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetCaptErrorChannelSettingsModal())
    
    async def set_log_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetCaptLogChannelModal())
    
    async def show_settings(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        embed = discord.Embed(title="📊 ТЕКУЩИЕ НАСТРОЙКИ CAPT", color=0x00ff00)
        guild = interaction.guild
        main_channel = format_mention(guild, CONFIG.get('capt_reg_main_channel'), 'channel') if CONFIG.get('capt_reg_main_channel') else "`Не настроен`"
        reserve_channel = format_mention(guild, CONFIG.get('capt_reg_reserve_channel'), 'channel') if CONFIG.get('capt_reg_reserve_channel') else "`Не настроен`"
        alert_channel = format_mention(guild, CONFIG.get('capt_alert_channel'), 'channel') if CONFIG.get('capt_alert_channel') else "`Не настроен`"
        role = format_mention(guild, CONFIG.get('capt_role_id'), 'role') if CONFIG.get('capt_role_id') else "`Не настроена`"
        error_channel = format_mention(guild, CONFIG.get('capt_channel_id'), 'channel') if CONFIG.get('capt_channel_id') else "`Не настроен`"
        embed.add_field(name="🎯 Канал модерации", value=main_channel, inline=False)
        embed.add_field(name="🎯 Канал пользователей", value=reserve_channel, inline=False)
        embed.add_field(name="📢 Канал @everyone", value=alert_channel, inline=False)
        embed.add_field(name="🎭 Роль для рассылки", value=role, inline=False)
        embed.add_field(name="💬 Канал ошибок", value=error_channel, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetCaptRegChannelsSettingsModal(discord.ui.Modal, title="🎯 НАСТРОЙКА КАНАЛОВ CAPT"):
    main_channel = discord.ui.TextInput(label="🔴 Канал модерации", placeholder="123456789012345678", max_length=20, required=True)
    reserve_channel = discord.ui.TextInput(label="🟡 Публичный канал", placeholder="123456789012345678", max_length=20, required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            guild = interaction.guild
            main_channel = guild.get_channel(int(self.main_channel.value))
            if not main_channel:
                await interaction.response.send_message(f"❌ Канал {self.main_channel.value} не найден", ephemeral=True)
                return
            reserve_channel = guild.get_channel(int(self.reserve_channel.value))
            if not reserve_channel:
                await interaction.response.send_message(f"❌ Канал {self.reserve_channel.value} не найден", ephemeral=True)
                return
            CONFIG['capt_reg_main_channel'] = self.main_channel.value
            CONFIG['capt_reg_reserve_channel'] = self.reserve_channel.value
            db.set_setting('capt_reg_main_channel', self.main_channel.value, str(interaction.user.id))
            db.set_setting('capt_reg_reserve_channel', self.reserve_channel.value, str(interaction.user.id))
            save_config(str(interaction.user.id))
            capt_reg_manager.main_channel_id = self.main_channel.value
            capt_reg_manager.reserve_channel_id = self.reserve_channel.value
            await interaction.response.send_message(f"✅ Каналы CAPT настроены!\n🔴 {main_channel.mention}\n🟡 {reserve_channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetCaptAlertChannelSettingsModal(discord.ui.Modal, title="📢 КАНАЛ ДЛЯ @EVERYONE"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", max_length=20, required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            guild = interaction.guild
            channel = guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message(f"❌ Канал {self.channel_id.value} не найден", ephemeral=True)
                return
            CONFIG['capt_alert_channel'] = self.channel_id.value
            db.set_setting('capt_alert_channel', self.channel_id.value, str(interaction.user.id))
            save_config(str(interaction.user.id))
            capt_reg_manager.alert_channel_id = self.channel_id.value
            await interaction.response.send_message(f"✅ Канал оповещений CAPT настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetCaptRoleSettingsModal(discord.ui.Modal, title="🎭 РОЛЬ ДЛЯ РАССЫЛКИ"):
    role_id = discord.ui.TextInput(label="ID роли", placeholder="123456789012345678", max_length=20, required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            guild = interaction.guild
            role = guild.get_role(int(self.role_id.value))
            if not role:
                await interaction.response.send_message(f"❌ Роль {self.role_id.value} не найдена", ephemeral=True)
                return
            CONFIG['capt_role_id'] = self.role_id.value
            db.set_setting('capt_role_id', self.role_id.value, str(interaction.user.id))
            save_config(str(interaction.user.id))
            capt_reg_manager.capt_role_id = self.role_id.value
            await interaction.response.send_message(f"✅ Роль для рассылки CAPT настроена: {role.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetCaptErrorChannelSettingsModal(discord.ui.Modal, title="💬 КАНАЛ ОШИБОК CAPT"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", max_length=20, required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            guild = interaction.guild
            channel = guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message(f"❌ Канал {self.channel_id.value} не найден", ephemeral=True)
                return
            CONFIG['capt_channel_id'] = self.channel_id.value
            db.set_setting('capt_channel_id', self.channel_id.value, str(interaction.user.id))
            save_config(str(interaction.user.id))
            await interaction.response.send_message(f"✅ Канал ошибок CAPT настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetCaptLogChannelModal(discord.ui.Modal, title="📜 КАНАЛ ЛОГОВ CAPT"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", max_length=20, required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            guild = interaction.guild
            channel = guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return
            CONFIG['capt_log_channel'] = self.channel_id.value
            db.set_setting('capt_log_channel', self.channel_id.value, str(interaction.user.id))
            save_config(str(interaction.user.id))
            await interaction.response.send_message(f"✅ Канал логов CAPT настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)