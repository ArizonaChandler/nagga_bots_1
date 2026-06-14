"""Панель настроек системы отпусков"""
import discord
import json
from core.admin_views import AdminOnlyView
from core.config import CONFIG, save_config
from core.database import db
from core.utils import format_mention, is_admin
from vacation.base import PermanentView
from vacation.manager import vacation_manager


class VacationSettingsView(AdminOnlyView):
    """Постоянные кнопки для настройки системы отпусков"""

    def __init__(self):
        super().__init__(timeout=None)
        self._add_buttons()
        self._add_back_button()

    def _add_buttons(self):
        self.clear_items()
        public_btn = discord.ui.Button(label="📢 Канал отпуска", style=discord.ButtonStyle.primary, emoji="📢", row=0, custom_id="vacation_public")
        public_btn.callback = self.set_public_channel
        self.add_item(public_btn)
        
        apps_btn = discord.ui.Button(label="📋 Канал заявок", style=discord.ButtonStyle.primary, emoji="📋", row=0, custom_id="vacation_apps")
        apps_btn.callback = self.set_applications_channel
        self.add_item(apps_btn)
        
        log_btn = discord.ui.Button(label="📜 Канал логов", style=discord.ButtonStyle.primary, emoji="📜", row=0, custom_id="vacation_log")
        log_btn.callback = self.set_log_channel
        self.add_item(log_btn)
        
        roles_btn = discord.ui.Button(label="👑 Роли для одобрения", style=discord.ButtonStyle.primary, emoji="👑", row=1, custom_id="vacation_roles")
        roles_btn.callback = self.set_approve_roles
        self.add_item(roles_btn)
        
        role_btn = discord.ui.Button(label="🎭 Роль отпуска", style=discord.ButtonStyle.primary, emoji="🎭", row=1, custom_id="vacation_role")
        role_btn.callback = self.set_vacation_role
        self.add_item(role_btn)
        
        days_btn = discord.ui.Button(label="⏰ Макс. дней", style=discord.ButtonStyle.primary, emoji="⏰", row=1, custom_id="vacation_days")
        days_btn.callback = self.set_max_days
        self.add_item(days_btn)
        
        show_btn = discord.ui.Button(label="📊 Текущие настройки", style=discord.ButtonStyle.secondary, emoji="📊", row=2, custom_id="vacation_show")
        show_btn.callback = self.show_settings
        self.add_item(show_btn)

    def _add_back_button(self):
        back_btn = discord.ui.Button(
            label="◀ Назад в главное меню",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=3,
            custom_id="vacation_back_to_global"
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

    async def set_public_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetVacationPublicChannelModal())

    async def set_applications_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetVacationApplicationsChannelModal())

    async def set_log_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetVacationLogChannelModal())

    async def set_approve_roles(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetVacationApproveRolesModal())

    async def set_vacation_role(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetVacationRoleModal())

    async def set_max_days(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetVacationMaxDaysModal())

    async def show_settings(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        embed = discord.Embed(title="📊 НАСТРОЙКИ СИСТЕМЫ ОТПУСКОВ", color=0x00ff00)
        guild = interaction.guild
        settings = vacation_manager.get_settings()
        public_channel = format_mention(guild, settings.get('vacation_public_channel'), 'channel') if settings.get('vacation_public_channel') else "`Не настроен`"
        applications_channel = format_mention(guild, settings.get('vacation_applications_channel'), 'channel') if settings.get('vacation_applications_channel') else "`Не настроен`"
        log_channel = format_mention(guild, settings.get('vacation_log_channel'), 'channel') if settings.get('vacation_log_channel') else "`Не настроен`"
        approve_roles = settings.get('vacation_approve_roles', [])
        approve_roles_str = ", ".join([format_mention(guild, r, 'role') for r in approve_roles]) if approve_roles else "`Не настроены`"
        vacation_role = format_mention(guild, settings.get('vacation_role'), 'role') if settings.get('vacation_role') else "`Не настроена`"
        max_days = settings.get('vacation_max_days', 30)
        embed.add_field(name="📢 Канал отпуска", value=public_channel, inline=False)
        embed.add_field(name="📋 Канал заявок", value=applications_channel, inline=False)
        embed.add_field(name="📜 Канал логов", value=log_channel, inline=False)
        embed.add_field(name="👑 Роли для одобрения", value=approve_roles_str, inline=False)
        embed.add_field(name="🎭 Роль отпуска", value=vacation_role, inline=False)
        embed.add_field(name="⏰ Максимальное дней", value=f"`{max_days}`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetVacationPublicChannelModal(discord.ui.Modal, title="📢 КАНАЛ ОТПУСКА"):
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
            vacation_manager.save_setting('vacation_public_channel', self.channel_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Канал отпуска настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetVacationApplicationsChannelModal(discord.ui.Modal, title="📋 КАНАЛ ЗАЯВОК"):
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
            vacation_manager.save_setting('vacation_applications_channel', self.channel_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Канал заявок настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetVacationLogChannelModal(discord.ui.Modal, title="📜 КАНАЛ ЛОГОВ"):
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
            vacation_manager.save_setting('vacation_log_channel', self.channel_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Канал логов настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetVacationApproveRolesModal(discord.ui.Modal, title="👑 РОЛИ ДЛЯ ОДОБРЕНИЯ"):
    roles = discord.ui.TextInput(label="ID ролей (через запятую)", placeholder="123456789,987654321", max_length=200, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            role_ids = [r.strip() for r in self.roles.value.split(',') if r.strip()]
            valid_roles = []
            for rid in role_ids:
                role = interaction.guild.get_role(int(rid))
                if role:
                    valid_roles.append(rid)
                else:
                    await interaction.response.send_message(f"❌ Роль {rid} не найдена", ephemeral=True)
                    return
            vacation_manager.save_setting('vacation_approve_roles', valid_roles, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Роли для одобрения отпусков настроены", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetVacationRoleModal(discord.ui.Modal, title="🎭 РОЛЬ ОТПУСКА"):
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
            vacation_manager.save_setting('vacation_role', self.role_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Роль отпуска настроена: {role.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetVacationMaxDaysModal(discord.ui.Modal, title="⏰ МАКСИМАЛЬНОЕ КОЛИЧЕСТВО ДНЕЙ"):
    days = discord.ui.TextInput(label="Максимальное количество дней", placeholder="30", max_length=3, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            days_num = int(self.days.value)
            if days_num <= 0:
                await interaction.response.send_message("❌ Дней должно быть больше 0", ephemeral=True)
                return
            if days_num > 365:
                await interaction.response.send_message("❌ Максимум 365 дней", ephemeral=True)
                return
            vacation_manager.save_setting('vacation_max_days', str(days_num), str(interaction.user.id))
            await interaction.response.send_message(f"✅ Максимальное количество дней отпуска: **{days_num}**", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Введите число", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)