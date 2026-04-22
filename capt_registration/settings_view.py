"""Панель настроек системы CAPT"""
import discord
from capt_registration.base import PermanentView
from capt_registration.manager import capt_reg_manager
from core.config import CONFIG, save_config
from core.database import db
from core.utils import format_mention


class CaptSettingsView(PermanentView):
    """Постоянные кнопки для настройки системы CAPT"""
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(
        label="🎯 Каналы CAPT", 
        style=discord.ButtonStyle.danger,
        emoji="🎯",
        row=0,
        custom_id="capt_settings_channels"
    )
    async def set_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить каналы для регистрации CAPT"""
        await interaction.response.send_modal(SetCaptRegChannelsSettingsModal())
    
    @discord.ui.button(
        label="📢 Канал @everyone", 
        style=discord.ButtonStyle.danger,
        emoji="📢",
        row=0,
        custom_id="capt_settings_alert"
    )
    async def set_alert_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить канал для оповещений @everyone"""
        await interaction.response.send_modal(SetCaptAlertChannelSettingsModal())
    
    @discord.ui.button(
        label="🎭 Роль для рассылки", 
        style=discord.ButtonStyle.danger,
        emoji="🎭",
        row=1,
        custom_id="capt_settings_role"
    )
    async def set_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить роль для рассылки в ЛС"""
        await interaction.response.send_modal(SetCaptRoleSettingsModal())
    
    @discord.ui.button(
        label="💬 Канал ошибок", 
        style=discord.ButtonStyle.danger,
        emoji="💬",
        row=1,
        custom_id="capt_settings_error_channel"
    )
    async def set_error_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить канал для ошибок доставки"""
        await interaction.response.send_modal(SetCaptErrorChannelSettingsModal())

    @discord.ui.button(
        label="📜 Канал логов CAPT", 
        style=discord.ButtonStyle.danger,
        emoji="📜",
        row=2,
        custom_id="capt_settings_log_channel"
    )
    async def set_log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить канал для логов CAPT"""
        await interaction.response.send_modal(SetCaptLogChannelModal())
    
    @discord.ui.button(
        label="📊 Текущие настройки", 
        style=discord.ButtonStyle.secondary,
        emoji="📊",
        row=2,
        custom_id="capt_settings_show"
    )
    async def show_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать текущие настройки CAPT"""
        embed = discord.Embed(
            title="📊 ТЕКУЩИЕ НАСТРОЙКИ CAPT",
            color=0x00ff00
        )
        
        guild = interaction.guild
        
        # Каналы регистрации
        main_channel_id = CONFIG.get('capt_reg_main_channel')
        reserve_channel_id = CONFIG.get('capt_reg_reserve_channel')
        
        main_channel = format_mention(guild, main_channel_id, 'channel') if main_channel_id else "`Не настроен`"
        reserve_channel = format_mention(guild, reserve_channel_id, 'channel') if reserve_channel_id else "`Не настроен`"
        
        embed.add_field(name="🎯 Канал модерации", value=main_channel, inline=False)
        embed.add_field(name="🎯 Канал пользователей", value=reserve_channel, inline=False)
        
        # Канал оповещений
        alert_channel_id = CONFIG.get('capt_alert_channel')
        alert_channel = format_mention(guild, alert_channel_id, 'channel') if alert_channel_id else "`Не настроен`"
        embed.add_field(name="📢 Канал @everyone", value=alert_channel, inline=False)
        
        # Роль для рассылки
        role_id = CONFIG.get('capt_role_id')
        role = format_mention(guild, role_id, 'role') if role_id else "`Не настроена`"
        embed.add_field(name="🎭 Роль для рассылки", value=role, inline=False)
        
        # Канал ошибок
        error_channel_id = CONFIG.get('capt_channel_id')
        error_channel = format_mention(guild, error_channel_id, 'channel') if error_channel_id else "`Не настроен`"
        embed.add_field(name="💬 Канал ошибок", value=error_channel, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ===== МОДАЛКИ ДЛЯ НАСТРОЕК =====

class SetCaptRegChannelsSettingsModal(discord.ui.Modal, title="🎯 НАСТРОЙКА КАНАЛОВ CAPT"):
    def __init__(self):
        super().__init__()
    
    main_channel = discord.ui.TextInput(
        label="🔴 Канал для модерации",
        placeholder="ID канала где будут кнопки управления",
        max_length=20,
        required=True
    )
    
    reserve_channel = discord.ui.TextInput(
        label="🟡 Канал для всех пользователей",
        placeholder="ID канала где будут кнопки 'Присоединиться'",
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        from capt_registration.manager import capt_reg_manager
        
        try:
            guild = interaction.guild
            
            main_channel = guild.get_channel(int(self.main_channel.value))
            if not main_channel:
                await interaction.response.send_message(
                    f"❌ Канал {self.main_channel.value} не найден",
                    ephemeral=True
                )
                return
            
            reserve_channel = guild.get_channel(int(self.reserve_channel.value))
            if not reserve_channel:
                await interaction.response.send_message(
                    f"❌ Канал {self.reserve_channel.value} не найден",
                    ephemeral=True
                )
                return
            
            CONFIG['capt_reg_main_channel'] = self.main_channel.value
            CONFIG['capt_reg_reserve_channel'] = self.reserve_channel.value
            db.set_setting('capt_reg_main_channel', self.main_channel.value, str(interaction.user.id))
            db.set_setting('capt_reg_reserve_channel', self.reserve_channel.value, str(interaction.user.id))
            save_config(str(interaction.user.id))
            
            capt_reg_manager.main_channel_id = self.main_channel.value
            capt_reg_manager.reserve_channel_id = self.reserve_channel.value
            
            await interaction.response.send_message(
                f"✅ Каналы CAPT настроены!\n"
                f"🔴 Модерация: {main_channel.mention}\n"
                f"🟡 Пользователи: {reserve_channel.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetCaptAlertChannelSettingsModal(discord.ui.Modal, title="📢 КАНАЛ ДЛЯ @EVERYONE"):
    def __init__(self):
        super().__init__()
    
    channel_id = discord.ui.TextInput(
        label="📢 Канал для оповещений",
        placeholder="ID канала куда будет приходить @everyone",
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        from capt_registration.manager import capt_reg_manager
        
        try:
            guild = interaction.guild
            channel = guild.get_channel(int(self.channel_id.value))
            
            if not channel:
                await interaction.response.send_message(
                    f"❌ Канал {self.channel_id.value} не найден",
                    ephemeral=True
                )
                return
            
            CONFIG['capt_alert_channel'] = self.channel_id.value
            db.set_setting('capt_alert_channel', self.channel_id.value, str(interaction.user.id))
            save_config(str(interaction.user.id))
            
            capt_reg_manager.alert_channel_id = self.channel_id.value
            
            await interaction.response.send_message(
                f"✅ Канал оповещений настроен: {channel.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetCaptRoleSettingsModal(discord.ui.Modal, title="🎭 РОЛЬ ДЛЯ РАССЫЛКИ"):
    def __init__(self):
        super().__init__()
    
    role_id = discord.ui.TextInput(
        label="🎭 ID роли для рассылки",
        placeholder="ID роли для рассылки в ЛС",
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        from capt_registration.manager import capt_reg_manager
        
        try:
            guild = interaction.guild
            role = guild.get_role(int(self.role_id.value))
            
            if not role:
                await interaction.response.send_message(
                    f"❌ Роль {self.role_id.value} не найдена",
                    ephemeral=True
                )
                return
            
            CONFIG['capt_role_id'] = self.role_id.value
            db.set_setting('capt_role_id', self.role_id.value, str(interaction.user.id))
            save_config(str(interaction.user.id))
            
            capt_reg_manager.capt_role_id = self.role_id.value
            
            await interaction.response.send_message(
                f"✅ Роль для рассылки настроена: {role.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetCaptErrorChannelSettingsModal(discord.ui.Modal, title="💬 КАНАЛ ОШИБОК CAPT"):
    def __init__(self):
        super().__init__()
    
    channel_id = discord.ui.TextInput(
        label="ID канала для ошибок",
        placeholder="ID канала куда будут приходить отчёты о недоставленных сообщениях",
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
            channel = guild.get_channel(int(self.channel_id.value))
            
            if not channel:
                await interaction.response.send_message(
                    f"❌ Канал {self.channel_id.value} не найден",
                    ephemeral=True
                )
                return
            
            CONFIG['capt_channel_id'] = self.channel_id.value
            db.set_setting('capt_channel_id', self.channel_id.value, str(interaction.user.id))
            save_config(str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Канал ошибок CAPT настроен: {channel.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetCaptLogChannelModal(discord.ui.Modal, title="📜 КАНАЛ ЛОГОВ CAPT"):
    def __init__(self):
        super().__init__()
    
    channel_id = discord.ui.TextInput(
        label="ID канала для логов CAPT",
        placeholder="123456789012345678",
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        from core.config import CONFIG, save_config
        from core.database import db
        
        try:
            guild = interaction.guild
            channel = guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return
            
            CONFIG['capt_log_channel'] = self.channel_id.value
            db.set_setting('capt_log_channel', self.channel_id.value, str(interaction.user.id))
            save_config(str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Канал логов CAPT настроен: {channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)