"""Панель настроек системы TIER"""
import discord
import re
from datetime import datetime
from core.admin_views import AdminOnlyView
from core.database import db
from core.config import CONFIG, save_config
from core.utils import is_admin
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
        
        # Каналы
        channels_btn = discord.ui.Button(label="📡 Настройка каналов", style=discord.ButtonStyle.primary, emoji="📡", row=0, custom_id="tier_channels")
        channels_btn.callback = self.channels_menu
        self.add_item(channels_btn)
        
        # Роли
        roles_btn = discord.ui.Button(label="🎭 Настройка ролей", style=discord.ButtonStyle.primary, emoji="🎭", row=0, custom_id="tier_roles")
        roles_btn.callback = self.roles_menu
        self.add_item(roles_btn)
        
        # Требования
        req_btn = discord.ui.Button(label="📝 Настройка требований", style=discord.ButtonStyle.primary, emoji="📝", row=1, custom_id="tier_req")
        req_btn.callback = self.requirements_menu
        self.add_item(req_btn)
        
        # 🔥 КНОПКА — УДАЛЕНИЕ ПРОФИЛЯ ПРИ ВЫДАЧЕ TIER (с отображением статуса)
        delete_profile_state = CONFIG.get('tier_delete_profile', 'false') == 'true'
        delete_profile_status = "🟢 ВКЛЮЧЕНО" if delete_profile_state else "🔴 ВЫКЛЮЧЕНО"
        delete_profile_btn = discord.ui.Button(
            label=f"🗑️ Удаление профиля ({delete_profile_status})",
            style=discord.ButtonStyle.success if delete_profile_state else discord.ButtonStyle.secondary,
            emoji="🗑️",
            row=1,
            custom_id="tier_delete_profile"
        )
        delete_profile_btn.callback = self.toggle_delete_profile
        self.add_item(delete_profile_btn)
        
        # 🔥 КНОПКА — СОЗДАНИЕ ПРОФИЛЯ ПРИ ВЫДАЧЕ TIER (с отображением статуса)
        create_profile_state = CONFIG.get('tier_create_profile', 'false') == 'true'
        create_profile_status = "🟢 ВКЛЮЧЕНО" if create_profile_state else "🔴 ВЫКЛЮЧЕНО"
        create_profile_btn = discord.ui.Button(
            label=f"📁 Создание профиля ({create_profile_status})",
            style=discord.ButtonStyle.success if create_profile_state else discord.ButtonStyle.secondary,
            emoji="📁",
            row=2,
            custom_id="tier_create_profile"
        )
        create_profile_btn.callback = self.toggle_create_profile
        self.add_item(create_profile_btn)
        
        # Статистика
        stats_btn = discord.ui.Button(label="📊 Статистика заявок", style=discord.ButtonStyle.secondary, emoji="📊", row=2, custom_id="tier_stats")
        stats_btn.callback = self.show_stats
        self.add_item(stats_btn)

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

    async def channels_menu(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        embed = discord.Embed(title="📡 **НАСТРОЙКА КАНАЛОВ TIER**", description="Выберите, какой канал хотите настроить:", color=0x7289da)
        view = TierChannelsView()
        await interaction.response.edit_message(embed=embed, view=view)

    async def roles_menu(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        embed = discord.Embed(title="🎭 **НАСТРОЙКА РОЛЕЙ TIER**", description="Выберите, какую роль хотите настроить:", color=0x7289da)
        view = TierRolesView()
        await interaction.response.edit_message(embed=embed, view=view)

    async def requirements_menu(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        embed = discord.Embed(title="📝 **НАСТРОЙКА ТРЕБОВАНИЙ**", description="Выберите уровень для настройки:", color=0x7289da)
        view = TierRequirementsView()
        await interaction.response.edit_message(embed=embed, view=view)

    async def toggle_delete_profile(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        current = CONFIG.get('tier_delete_profile', 'false')
        new_state = not (current == 'true')
        
        db.set_setting('tier_delete_profile', str(new_state).lower(), str(interaction.user.id))
        CONFIG['tier_delete_profile'] = str(new_state).lower()
        save_config(str(interaction.user.id))
        
        # Обновляем кнопки
        self._add_buttons()
        await interaction.message.edit(view=self)
        
        status = "включено ✅" if new_state else "выключено ❌"
        await interaction.response.send_message(f"🗑️ Удаление профилей при выдаче Tier: {status}", ephemeral=True)

    async def toggle_create_profile(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        current = CONFIG.get('tier_create_profile', 'false')
        new_state = not (current == 'true')
        
        db.set_setting('tier_create_profile', str(new_state).lower(), str(interaction.user.id))
        CONFIG['tier_create_profile'] = str(new_state).lower()
        save_config(str(interaction.user.id))
        
        # Обновляем кнопки
        self._add_buttons()
        await interaction.message.edit(view=self)
        
        status = "включено ✅" if new_state else "выключено ❌"
        await interaction.response.send_message(f"📁 Создание профиля при выдаче Tier: {status}", ephemeral=True)

    async def show_stats(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        pending = len(tier_manager.get_pending_applications())
        
        embed = discord.Embed(title="📊 СТАТИСТИКА TIER", color=0x7289da)
        embed.add_field(name="⏳ Ожидают рассмотрения", value=f"**{pending}**", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class TierChannelsView(AdminOnlyView):
    def __init__(self):
        super().__init__(timeout=60)
        
        submit_btn = discord.ui.Button(label="📝 Канал подачи заявок", style=discord.ButtonStyle.secondary, row=0, custom_id="tier_submit")
        submit_btn.callback = self.set_submit_channel
        self.add_item(submit_btn)
        
        mod_btn = discord.ui.Button(label="⚙️ Канал модерации", style=discord.ButtonStyle.secondary, row=0, custom_id="tier_mod")
        mod_btn.callback = self.set_mod_channel
        self.add_item(mod_btn)
        
        log_btn = discord.ui.Button(label="📜 Канал логов", style=discord.ButtonStyle.secondary, row=1, custom_id="tier_log")
        log_btn.callback = self.set_log_channel
        self.add_item(log_btn)
        
        info_btn = discord.ui.Button(label="📢 Канал информации", style=discord.ButtonStyle.secondary, row=1, custom_id="tier_info")
        info_btn.callback = self.set_info_channel
        self.add_item(info_btn)
        
        profiles_btn = discord.ui.Button(label="📁 Категория профилей Tier", style=discord.ButtonStyle.secondary, row=2, custom_id="tier_profiles_category")
        profiles_btn.callback = self.set_profiles_category
        self.add_item(profiles_btn)
        
        back_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=3, custom_id="tier_back")
        back_btn.callback = self.back
        self.add_item(back_btn)
    
    async def set_submit_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetTierChannelModal("tier_submit_channel", "канал подачи заявок TIER"))
    
    async def set_mod_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetTierChannelModal("tier_applications_channel", "канал модерации TIER"))
    
    async def set_log_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetTierChannelModal("tier_log_channel", "канал логов TIER"))
    
    async def set_info_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetTierChannelModal("tier_info_channel", "канал информации TIER"))
    
    async def set_profiles_category(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetTierCategoryModal("tier_profiles_category", "категория для профилей Tier"))
    
    async def back(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⚙️ **НАСТРОЙКИ TIER**", description="Настройка системы повышения уровня", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=TierSettingsView())


class TierRolesView(AdminOnlyView):
    def __init__(self):
        super().__init__(timeout=60)
        
        checker_btn = discord.ui.Button(label="👑 Роль Tier Checker", style=discord.ButtonStyle.secondary, row=0, custom_id="tier_checker")
        checker_btn.callback = self.set_checker_role
        self.add_item(checker_btn)
        
        tier1_btn = discord.ui.Button(label="🔴 Роль Tier 1", style=discord.ButtonStyle.secondary, row=0, custom_id="tier1")
        tier1_btn.callback = self.set_tier1_role
        self.add_item(tier1_btn)
        
        tier2_btn = discord.ui.Button(label="⚪ Роль Tier 2", style=discord.ButtonStyle.secondary, row=1, custom_id="tier2")
        tier2_btn.callback = self.set_tier2_role
        self.add_item(tier2_btn)
        
        tier3_btn = discord.ui.Button(label="🟤 Роль Tier 3", style=discord.ButtonStyle.secondary, row=1, custom_id="tier3")
        tier3_btn.callback = self.set_tier3_role
        self.add_item(tier3_btn)
        
        back_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=2, custom_id="tier_back")
        back_btn.callback = self.back
        self.add_item(back_btn)
    
    async def set_checker_role(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetTierRoleModal("tier_checker_role", "роль Tier Checker"))
    
    async def set_tier1_role(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetTierRoleModal("tier1_role", "роль Tier 1"))
    
    async def set_tier2_role(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetTierRoleModal("tier2_role", "роль Tier 2"))
    
    async def set_tier3_role(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetTierRoleModal("tier3_role", "роль Tier 3"))
    
    async def back(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⚙️ **НАСТРОЙКИ TIER**", description="Настройка системы повышения уровня", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=TierSettingsView())


class TierRequirementsView(AdminOnlyView):
    def __init__(self):
        super().__init__(timeout=60)
        
        tier1_btn = discord.ui.Button(label="🔴 Требования Tier 1", style=discord.ButtonStyle.secondary, row=0, custom_id="tier1_req")
        tier1_btn.callback = self.set_tier1_req
        self.add_item(tier1_btn)
        
        tier2_btn = discord.ui.Button(label="⚪ Требования Tier 2", style=discord.ButtonStyle.secondary, row=0, custom_id="tier2_req")
        tier2_btn.callback = self.set_tier2_req
        self.add_item(tier2_btn)
        
        tier3_btn = discord.ui.Button(label="🟤 Требования Tier 3", style=discord.ButtonStyle.secondary, row=1, custom_id="tier3_req")
        tier3_btn.callback = self.set_tier3_req
        self.add_item(tier3_btn)
        
        back_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=1, custom_id="tier_back")
        back_btn.callback = self.back
        self.add_item(back_btn)
    
    async def set_tier1_req(self, interaction: discord.Interaction):
        current = tier_manager.get_tier_requirements("tier1") or "Не установлены"
        await interaction.response.send_modal(SetTierRequirementsModal("tier1", "TIER 1", current))
    
    async def set_tier2_req(self, interaction: discord.Interaction):
        current = tier_manager.get_tier_requirements("tier2") or "Не установлены"
        await interaction.response.send_modal(SetTierRequirementsModal("tier2", "TIER 2", current))
    
    async def set_tier3_req(self, interaction: discord.Interaction):
        current = tier_manager.get_tier_requirements("tier3") or "Не установлены"
        await interaction.response.send_modal(SetTierRequirementsModal("tier3", "TIER 3", current))
    
    async def back(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⚙️ **НАСТРОЙКИ TIER**", description="Настройка системы повышения уровня", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=TierSettingsView())


class SetTierChannelModal(discord.ui.Modal, title="📡 НАСТРОЙКА КАНАЛА"):
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


class SetTierCategoryModal(discord.ui.Modal, title="📁 НАСТРОЙКА КАТЕГОРИИ"):
    def __init__(self, setting_key: str, description: str):
        super().__init__()
        self.setting_key = setting_key
        self.category_id = discord.ui.TextInput(label=f"ID {description}", placeholder="123456789012345678", max_length=20, required=True)
        self.add_item(self.category_id)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            category = interaction.guild.get_channel(int(self.category_id.value))
            if not category or not isinstance(category, discord.CategoryChannel):
                await interaction.response.send_message("❌ Категория не найдена", ephemeral=True)
                return
            db.set_setting(self.setting_key, self.category_id.value, str(interaction.user.id))
            CONFIG[self.setting_key] = self.category_id.value
            save_config(str(interaction.user.id))
            await interaction.response.send_message(f"✅ {self.category_id.label} настроена: {category.name}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTierRoleModal(discord.ui.Modal, title="🎭 НАСТРОЙКА РОЛИ"):
    def __init__(self, setting_key: str, description: str):
        super().__init__()
        self.setting_key = setting_key
        self.role_id = discord.ui.TextInput(label=f"ID {description}", placeholder="123456789012345678", max_length=20, required=True)
        self.add_item(self.role_id)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            role = interaction.guild.get_role(int(self.role_id.value))
            if not role:
                await interaction.response.send_message("❌ Роль не найдена", ephemeral=True)
                return
            db.set_setting(self.setting_key, self.role_id.value, str(interaction.user.id))
            CONFIG[self.setting_key] = self.role_id.value
            save_config(str(interaction.user.id))
            await interaction.response.send_message(f"✅ {self.role_id.label} настроена: {role.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetTierRequirementsModal(discord.ui.Modal, title="📝 НАСТРОЙКА ТРЕБОВАНИЙ"):
    def __init__(self, tier: str, tier_name: str, current: str):
        super().__init__(title=f"📝 Требования {tier_name}")
        self.tier = tier
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
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            tier_manager.save_tier_requirements(self.tier, self.requirements.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Требования для {self.tier.upper()} обновлены!", ephemeral=True)
            
            # Обновляем embed в канале информации
            info_channel_id = CONFIG.get('tier_info_channel')
            if info_channel_id:
                from tier.views import update_tier_embed
                await update_tier_embed(interaction.client, info_channel_id)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)