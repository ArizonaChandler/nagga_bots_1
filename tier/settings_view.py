"""Панель настроек системы TIER"""
import discord
from core.admin_views import AdminOnlyView
from core.config import CONFIG, save_config
from core.database import db
from core.utils import format_mention, is_admin
from tier.base import PermanentView
from tier.manager import tier_manager


class TierSettingsView(AdminOnlyView):
    """Постоянные кнопки для настройки системы TIER"""

    def __init__(self):
        super().__init__()
        self._add_buttons()
        self._add_back_button()

    def _add_buttons(self):
        self.clear_items()
        # Ряд 0
        submit_btn = discord.ui.Button(label="📝 Канал подачи заявок", style=discord.ButtonStyle.primary, emoji="📝", row=0, custom_id="tier_submit")
        submit_btn.callback = self.set_submit_channel
        self.add_item(submit_btn)
        
        apps_btn = discord.ui.Button(label="📋 Канал анкет", style=discord.ButtonStyle.primary, emoji="📋", row=0, custom_id="tier_apps")
        apps_btn.callback = self.set_applications_channel
        self.add_item(apps_btn)
        
        log_btn = discord.ui.Button(label="📜 Канал логов", style=discord.ButtonStyle.primary, emoji="📜", row=0, custom_id="tier_log")
        log_btn.callback = self.set_log_channel
        self.add_item(log_btn)
        
        # Ряд 1
        info_btn = discord.ui.Button(label="📢 Канал информации", style=discord.ButtonStyle.primary, emoji="📢", row=1, custom_id="tier_info")
        info_btn.callback = self.set_info_channel
        self.add_item(info_btn)
        
        checker_btn = discord.ui.Button(label="👑 Роль Tier Checker", style=discord.ButtonStyle.primary, emoji="👑", row=1, custom_id="tier_checker")
        checker_btn.callback = self.set_checker_role
        self.add_item(checker_btn)
        
        # Ряд 2
        tier3_btn = discord.ui.Button(label="🟤 Роль Tier 3", style=discord.ButtonStyle.primary, emoji="🟤", row=2, custom_id="tier3")
        tier3_btn.callback = self.set_tier3_role
        self.add_item(tier3_btn)
        
        tier2_btn = discord.ui.Button(label="⚪ Роль Tier 2", style=discord.ButtonStyle.primary, emoji="⚪", row=2, custom_id="tier2")
        tier2_btn.callback = self.set_tier2_role
        self.add_item(tier2_btn)
        
        tier1_btn = discord.ui.Button(label="🔴 Роль Tier 1", style=discord.ButtonStyle.primary, emoji="🔴", row=2, custom_id="tier1")
        tier1_btn.callback = self.set_tier1_role
        self.add_item(tier1_btn)
        
        # Ряд 3
        req3_btn = discord.ui.Button(label="📝 Требования Tier 3", style=discord.ButtonStyle.secondary, emoji="📝", row=3, custom_id="req3")
        req3_btn.callback = self.set_tier3_req
        self.add_item(req3_btn)
        
        req2_btn = discord.ui.Button(label="📝 Требования Tier 2", style=discord.ButtonStyle.secondary, emoji="📝", row=3, custom_id="req2")
        req2_btn.callback = self.set_tier2_req
        self.add_item(req2_btn)
        
        req1_btn = discord.ui.Button(label="📝 Требования Tier 1", style=discord.ButtonStyle.secondary, emoji="📝", row=3, custom_id="req1")
        req1_btn.callback = self.set_tier1_req
        self.add_item(req1_btn)
        
        # Ряд 4
        show_btn = discord.ui.Button(label="📊 Текущие настройки", style=discord.ButtonStyle.secondary, emoji="📊", row=4, custom_id="tier_show")
        show_btn.callback = self.show_settings
        self.add_item(show_btn)
    
    def _add_back_button(self):
        back_btn = discord.ui.Button(
            label="◀ Назад в главное меню",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=4,
            custom_id="tier_back_to_global"
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

    async def set_submit_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTierSubmitChannelModal())

    async def set_applications_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTierApplicationsChannelModal())

    async def set_log_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTierLogChannelModal())

    async def set_info_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTierInfoChannelModal())

    async def set_checker_role(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTierCheckerRoleModal())

    async def set_tier3_role(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTier3RoleModal())

    async def set_tier2_role(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTier2RoleModal())

    async def set_tier1_role(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTier1RoleModal())

    async def set_tier3_req(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTierRequirementsModal("tier3", "🟤 TIER 3"))

    async def set_tier2_req(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTierRequirementsModal("tier2", "⚪ TIER 2"))

    async def set_tier1_req(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetTierRequirementsModal("tier1", "🔴 TIER 1"))

    async def show_settings(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        embed = discord.Embed(title="📊 НАСТРОЙКИ СИСТЕМЫ TIER", color=0x00ff00)
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


class SetTierSubmitChannelModal(discord.ui.Modal, title="📝 КАНАЛ ПОДАЧИ ЗАЯВОК TIER"):
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
            tier_manager.save_setting('tier_submit_channel', self.channel_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Канал подачи заявок TIER настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTierApplicationsChannelModal(discord.ui.Modal, title="📋 КАНАЛ АНКЕТ TIER"):
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
            tier_manager.save_setting('tier_applications_channel', self.channel_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Канал анкет TIER настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTierLogChannelModal(discord.ui.Modal, title="📜 КАНАЛ ЛОГОВ TIER"):
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
            tier_manager.save_setting('tier_log_channel', self.channel_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Канал логов TIER настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTierInfoChannelModal(discord.ui.Modal, title="📢 КАНАЛ ИНФОРМАЦИИ TIER"):
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
            tier_manager.save_setting('tier_info_channel', self.channel_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Канал информации TIER настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTierCheckerRoleModal(discord.ui.Modal, title="👑 РОЛЬ TIER CHECKER"):
    role_id = discord.ui.TextInput(label="ID роли", placeholder="123456789012345678", max_length=20, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            role = interaction.guild.get_role(int(self.role_id.value))
            if not role:
                await interaction.response.send_message("❌ Роль не найдена", ephemeral=True)
                return
            tier_manager.save_setting('tier_checker_role', self.role_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Роль Tier Checker настроена: {role.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTier3RoleModal(discord.ui.Modal, title="🟤 РОЛЬ TIER 3"):
    role_id = discord.ui.TextInput(label="ID роли", placeholder="123456789012345678", max_length=20, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            role = interaction.guild.get_role(int(self.role_id.value))
            if not role:
                await interaction.response.send_message("❌ Роль не найдена", ephemeral=True)
                return
            tier_manager.save_setting('tier3_role', self.role_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Роль Tier 3 настроена: {role.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTier2RoleModal(discord.ui.Modal, title="⚪ РОЛЬ TIER 2"):
    role_id = discord.ui.TextInput(label="ID роли", placeholder="123456789012345678", max_length=20, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            role = interaction.guild.get_role(int(self.role_id.value))
            if not role:
                await interaction.response.send_message("❌ Роль не найдена", ephemeral=True)
                return
            tier_manager.save_setting('tier2_role', self.role_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Роль Tier 2 настроена: {role.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTier1RoleModal(discord.ui.Modal, title="🔴 РОЛЬ TIER 1"):
    role_id = discord.ui.TextInput(label="ID роли", placeholder="123456789012345678", max_length=20, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            role = interaction.guild.get_role(int(self.role_id.value))
            if not role:
                await interaction.response.send_message("❌ Роль не найдена", ephemeral=True)
                return
            tier_manager.save_setting('tier1_role', self.role_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Роль Tier 1 настроена: {role.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTierRequirementsModal(discord.ui.Modal):
    def __init__(self, tier: str, title: str):
        super().__init__(title=f"📝 {title}")
        self.tier = tier
        current = tier_manager.get_tier_requirements(tier) or "Не установлены"
        self.requirements = discord.ui.TextInput(label="Требования", placeholder="Введите требования для получения этого тира", style=discord.TextStyle.paragraph, max_length=1000, required=True, default=current if current != "Не установлены" else "")
        self.add_item(self.requirements)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            tier_manager.save_tier_requirements(self.tier, self.requirements.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Требования для TIER обновлены!", ephemeral=True)
            from tier.views import update_tier_embed
            settings = tier_manager.get_settings()
            info_channel_id = settings.get('tier_info_channel')
            if info_channel_id:
                await update_tier_embed(interaction.client, info_channel_id)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)