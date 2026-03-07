"""Панель настроек системы заявок"""
import discord
from applications.base import PermanentView
from applications.manager import app_manager
from core.config import CONFIG, save_config
from core.database import db
from core.utils import format_mention

class ApplicationsSettingsView(PermanentView):
    """Постоянные кнопки для настройки системы заявок"""
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(
        label="📝 Канал заявок", 
        style=discord.ButtonStyle.primary,
        emoji="📝",
        row=0,
        custom_id="apps_settings_channel"
    )
    async def set_applications_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить канал для заявок"""
        await interaction.response.send_modal(SetApplicationsChannelModal())
    
    @discord.ui.button(
        label="📋 Канал логов", 
        style=discord.ButtonStyle.primary,
        emoji="📋",
        row=0,
        custom_id="apps_settings_log"
    )
    async def set_log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить канал для логов"""
        await interaction.response.send_modal(SetLogChannelModal())
    
    @discord.ui.button(
        label="👥 Роль рекрута", 
        style=discord.ButtonStyle.primary,
        emoji="👥",
        row=1,
        custom_id="apps_settings_recruit"
    )
    async def set_recruit_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить роль рекрута"""
        await interaction.response.send_modal(SetRecruitRoleModal())
    
    @discord.ui.button(
        label="👑 Роль участника", 
        style=discord.ButtonStyle.primary,
        emoji="👑",
        row=1,
        custom_id="apps_settings_member"
    )
    async def set_member_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить роль участника"""
        await interaction.response.send_modal(SetMemberRoleModal())
    
    @discord.ui.button(
        label="📊 Текущие настройки", 
        style=discord.ButtonStyle.secondary,
        emoji="📊",
        row=2,
        custom_id="apps_settings_show"
    )
    async def show_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать текущие настройки"""
        embed = discord.Embed(
            title="📊 НАСТРОЙКИ СИСТЕМЫ ЗАЯВОК",
            color=0x00ff00
        )
        
        guild = interaction.guild
        settings = app_manager.get_settings()  # Получаем настройки
        
        apps_channel = format_mention(guild, settings.get('applications_channel'), 'channel') if settings.get('applications_channel') else "`Не настроен`"
        log_channel = format_mention(guild, settings.get('applications_log_channel'), 'channel') if settings.get('applications_log_channel') else "`Не настроен`"
        recruit_role = format_mention(guild, settings.get('applications_recruit_role'), 'role') if settings.get('applications_recruit_role') else "`Не настроена`"
        member_role = format_mention(guild, settings.get('applications_member_role'), 'role') if settings.get('applications_member_role') else "`Не настроена`"
        
        embed.add_field(name="📝 Канал заявок", value=apps_channel, inline=False)
        embed.add_field(name="📋 Канал логов", value=log_channel, inline=False)
        embed.add_field(name="👥 Роль рекрута", value=recruit_role, inline=False)
        embed.add_field(name="👑 Роль участника", value=member_role, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ===== МОДАЛКИ ДЛЯ НАСТРОЕК =====

class SetApplicationsChannelModal(discord.ui.Modal, title="📝 КАНАЛ ЗАЯВОК"):
    def __init__(self):
        super().__init__()
    
    channel_id = discord.ui.TextInput(
        label="ID канала для заявок",
        placeholder="123456789012345678",
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return
            
            app_manager.save_setting('applications_channel', self.channel_id.value)
            
            await interaction.response.send_message(
                f"✅ Канал заявок настроен: {channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetLogChannelModal(discord.ui.Modal, title="📋 КАНАЛ ЛОГОВ"):
    def __init__(self):
        super().__init__()
    
    channel_id = discord.ui.TextInput(
        label="ID канала для логов",
        placeholder="123456789012345678",
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return
            
            app_manager.save_setting('applications_log_channel', self.channel_id.value)
            
            await interaction.response.send_message(
                f"✅ Канал логов настроен: {channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetRecruitRoleModal(discord.ui.Modal, title="👥 РОЛЬ РЕКРУТА"):
    def __init__(self):
        super().__init__()
    
    role_id = discord.ui.TextInput(
        label="ID роли рекрута",
        placeholder="123456789012345678",
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            role = interaction.guild.get_role(int(self.role_id.value))
            if not role:
                await interaction.response.send_message("❌ Роль не найдена", ephemeral=True)
                return
            
            app_manager.save_setting('applications_recruit_role', self.role_id.value)
            
            await interaction.response.send_message(
                f"✅ Роль рекрута настроена: {role.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetMemberRoleModal(discord.ui.Modal, title="👑 РОЛЬ УЧАСТНИКА"):
    def __init__(self):
        super().__init__()
    
    role_id = discord.ui.TextInput(
        label="ID роли участника",
        placeholder="123456789012345678",
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            role = interaction.guild.get_role(int(self.role_id.value))
            if not role:
                await interaction.response.send_message("❌ Роль не найдена", ephemeral=True)
                return
            
            app_manager.save_setting('applications_member_role', self.role_id.value)
            
            await interaction.response.send_message(
                f"✅ Роль участника настроена: {role.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)