"""Панель настроек системы TIER"""
import discord
from tier.base import PermanentView
from tier.manager import tier_manager
from core.config import CONFIG, save_config
from core.database import db
from core.utils import format_mention


class TierSettingsView(PermanentView):
    """Постоянные кнопки для настройки системы TIER"""
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(
        label="📝 Канал подачи заявок", 
        style=discord.ButtonStyle.primary,
        emoji="📝",
        row=0,
        custom_id="tier_submit_channel"
    )
    async def set_submit_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить канал для кнопки подачи заявок"""
        await interaction.response.send_modal(SetTierSubmitChannelModal())
    
    @discord.ui.button(
        label="📋 Канал анкет", 
        style=discord.ButtonStyle.primary,
        emoji="📋",
        row=0,
        custom_id="tier_applications_channel"
    )
    async def set_applications_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить канал, куда приходят анкеты"""
        await interaction.response.send_modal(SetTierApplicationsChannelModal())
    
    @discord.ui.button(
        label="📜 Канал логов", 
        style=discord.ButtonStyle.primary,
        emoji="📜",
        row=0,
        custom_id="tier_log_channel"
    )
    async def set_log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить канал для логов"""
        await interaction.response.send_modal(SetTierLogChannelModal())
    
    @discord.ui.button(
        label="📢 Канал информации", 
        style=discord.ButtonStyle.primary,
        emoji="📢",
        row=0,
        custom_id="tier_info_channel"
    )
    async def set_info_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить канал для информации о тирах"""
        await interaction.response.send_modal(SetTierInfoChannelModal())
    
    @discord.ui.button(
        label="👑 Роль Tier Checker", 
        style=discord.ButtonStyle.primary,
        emoji="👑",
        row=1,
        custom_id="tier_checker_role"
    )
    async def set_checker_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить роль Tier Checker"""
        await interaction.response.send_modal(SetTierCheckerRoleModal())
    
    @discord.ui.button(
        label="🟤 Роль Tier 3", 
        style=discord.ButtonStyle.primary,
        emoji="🟤",
        row=1,
        custom_id="tier3_role"
    )
    async def set_tier3_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить роль Tier 3"""
        await interaction.response.send_modal(SetTier3RoleModal())
    
    @discord.ui.button(
        label="⚪ Роль Tier 2", 
        style=discord.ButtonStyle.primary,
        emoji="⚪",
        row=1,
        custom_id="tier2_role"
    )
    async def set_tier2_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить роль Tier 2"""
        await interaction.response.send_modal(SetTier2RoleModal())
    
    @discord.ui.button(
        label="🔴 Роль Tier 1", 
        style=discord.ButtonStyle.primary,
        emoji="🔴",
        row=1,
        custom_id="tier1_role"
    )
    async def set_tier1_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить роль Tier 1"""
        await interaction.response.send_modal(SetTier1RoleModal())
    
    @discord.ui.button(
        label="📝 Требования Tier 3", 
        style=discord.ButtonStyle.secondary,
        emoji="📝",
        row=2,
        custom_id="tier3_requirements"
    )
    async def set_tier3_req(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить требования для Tier 3"""
        await interaction.response.send_modal(SetTierRequirementsModal("tier3", "🟤 TIER 3"))
    
    @discord.ui.button(
        label="📝 Требования Tier 2", 
        style=discord.ButtonStyle.secondary,
        emoji="📝",
        row=2,
        custom_id="tier2_requirements"
    )
    async def set_tier2_req(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить требования для Tier 2"""
        await interaction.response.send_modal(SetTierRequirementsModal("tier2", "⚪ TIER 2"))
    
    @discord.ui.button(
        label="📝 Требования Tier 1", 
        style=discord.ButtonStyle.secondary,
        emoji="📝",
        row=2,
        custom_id="tier1_requirements"
    )
    async def set_tier1_req(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить требования для Tier 1"""
        await interaction.response.send_modal(SetTierRequirementsModal("tier1", "🔴 TIER 1"))
    
    @discord.ui.button(
        label="📊 Текущие настройки", 
        style=discord.ButtonStyle.secondary,
        emoji="📊",
        row=3,
        custom_id="tier_settings_show"
    )
    async def show_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать текущие настройки"""
        embed = discord.Embed(
            title="📊 НАСТРОЙКИ СИСТЕМЫ TIER",
            color=0x00ff00
        )
        
        guild = interaction.guild
        settings = tier_manager.get_settings()
        
        submit_channel = format_mention(guild, settings.get('tier_submit_channel'), 'channel') if settings.get('tier_submit_channel') else "`Не настроен`"
        applications_channel = format_mention(guild, settings.get('tier_applications_channel'), 'channel') if settings.get('tier_applications_channel') else "`Не настроен`"
        log_channel = format_mention(guild, settings.get('tier_log_channel'), 'channel') if settings.get('tier_log_channel') else "`Не настроен`"
        info_channel = format_mention(guild, settings.get('tier_info_channel'), 'channel') if settings.get('tier_info_channel') else "`Не настроен`"
        checker_role = format_mention(guild, settings.get('tier_checker_role'), 'role') if settings.get('tier_checker_role') else "`Не настроена`"
        tier3_role = format_mention(guild, settings.get('tier3_role'), 'role') if settings.get('tier3_role') else "`Не настроена`"
        tier2_role = format_mention(guild, settings.get('tier2_role'), 'role') if settings.get('tier2_role') else "`Не настроена`"
        tier1_role = format_mention(guild, settings.get('tier1_role'), 'role') if settings.get('tier1_role') else "`Не настроена`"
        
        embed.add_field(name="📝 Канал подачи заявок", value=submit_channel, inline=False)
        embed.add_field(name="📋 Канал анкет", value=applications_channel, inline=False)
        embed.add_field(name="📜 Канал логов", value=log_channel, inline=False)
        embed.add_field(name="📢 Канал информации", value=info_channel, inline=False)
        embed.add_field(name="👑 Роль Tier Checker", value=checker_role, inline=False)
        embed.add_field(name="🟤 Роль Tier 3", value=tier3_role, inline=False)
        embed.add_field(name="⚪ Роль Tier 2", value=tier2_role, inline=False)
        embed.add_field(name="🔴 Роль Tier 1", value=tier1_role, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ===== МОДАЛКИ ДЛЯ НАСТРОЕК =====

class SetTierSubmitChannelModal(discord.ui.Modal, title="📝 КАНАЛ ПОДАЧИ ЗАЯВОК TIER"):
    def __init__(self):
        super().__init__()
    
    channel_id = discord.ui.TextInput(
        label="ID канала для кнопки подачи",
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
            
            tier_manager.save_setting('tier_submit_channel', self.channel_id.value, str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Канал подачи заявок TIER настроен: {channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTierApplicationsChannelModal(discord.ui.Modal, title="📋 КАНАЛ АНКЕТ TIER"):
    def __init__(self):
        super().__init__()
    
    channel_id = discord.ui.TextInput(
        label="ID канала для анкет",
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
            
            tier_manager.save_setting('tier_applications_channel', self.channel_id.value, str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Канал анкет TIER настроен: {channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTierLogChannelModal(discord.ui.Modal, title="📜 КАНАЛ ЛОГОВ TIER"):
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
            
            tier_manager.save_setting('tier_log_channel', self.channel_id.value, str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Канал логов TIER настроен: {channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTierInfoChannelModal(discord.ui.Modal, title="📢 КАНАЛ ИНФОРМАЦИИ TIER"):
    def __init__(self):
        super().__init__()
    
    channel_id = discord.ui.TextInput(
        label="ID канала для информации",
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
            
            tier_manager.save_setting('tier_info_channel', self.channel_id.value, str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Канал информации TIER настроен: {channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTierCheckerRoleModal(discord.ui.Modal, title="👑 РОЛЬ TIER CHECKER"):
    def __init__(self):
        super().__init__()
    
    role_id = discord.ui.TextInput(
        label="ID роли Tier Checker",
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
            
            tier_manager.save_setting('tier_checker_role', self.role_id.value, str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Роль Tier Checker настроена: {role.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTier3RoleModal(discord.ui.Modal, title="🟤 РОЛЬ TIER 3"):
    def __init__(self):
        super().__init__()
    
    role_id = discord.ui.TextInput(
        label="ID роли Tier 3",
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
            
            tier_manager.save_setting('tier3_role', self.role_id.value, str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Роль Tier 3 настроена: {role.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTier2RoleModal(discord.ui.Modal, title="⚪ РОЛЬ TIER 2"):
    def __init__(self):
        super().__init__()
    
    role_id = discord.ui.TextInput(
        label="ID роли Tier 2",
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
            
            tier_manager.save_setting('tier2_role', self.role_id.value, str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Роль Tier 2 настроена: {role.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTier1RoleModal(discord.ui.Modal, title="🔴 РОЛЬ TIER 1"):
    def __init__(self):
        super().__init__()
    
    role_id = discord.ui.TextInput(
        label="ID роли Tier 1",
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
            
            tier_manager.save_setting('tier1_role', self.role_id.value, str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Роль Tier 1 настроена: {role.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTierRequirementsModal(discord.ui.Modal):
    """Модалка для настройки требований к тиру"""
    
    def __init__(self, tier: str, title: str):
        super().__init__(title=f"📝 {title}")
        self.tier = tier
        
        current = tier_manager.get_tier_requirements(tier) or "Не установлены"
        
        self.requirements = discord.ui.TextInput(
            label="Требования",
            placeholder="Введите требования для получения этого тира",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True,
            default=current if current != "Не установлены" else ""
        )
        self.add_item(self.requirements)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            tier_manager.save_tier_requirements(self.tier, self.requirements.value, str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Требования для TIER обновлены!",
                ephemeral=True
            )
            
            # Обновляем embed с информацией
            from tier.views import update_tier_embed
            settings = tier_manager.get_settings()
            info_channel_id = settings.get('tier_info_channel')
            if info_channel_id:
                await update_tier_embed(interaction.client, info_channel_id)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)