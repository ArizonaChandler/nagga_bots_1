"""Панель настроек системы заявок"""
import discord
from core.admin_views import AdminOnlyView
from core.database import db
from core.config import CONFIG, save_config
from core.utils import is_admin
from applications.base import PermanentView
from applications.manager import app_manager


class ApplicationsSettingsView(AdminOnlyView):
    """Панель настроек системы заявок"""

    def __init__(self):
        super().__init__()
        self._add_buttons()
        self._add_back_button()

    def _add_buttons(self):
        self.clear_items()
        
        # Каналы
        channels_btn = discord.ui.Button(label="📡 Настройка каналов", style=discord.ButtonStyle.primary, emoji="📡", row=0, custom_id="apps_channels")
        channels_btn.callback = self.channels_menu
        self.add_item(channels_btn)
        
        # Роли
        roles_btn = discord.ui.Button(label="🎭 Настройка ролей", style=discord.ButtonStyle.primary, emoji="🎭", row=0, custom_id="apps_roles")
        roles_btn.callback = self.roles_menu
        self.add_item(roles_btn)
        
        # Поля заявки
        fields_btn = discord.ui.Button(label="📝 Настройка полей", style=discord.ButtonStyle.primary, emoji="📝", row=1, custom_id="apps_fields")
        fields_btn.callback = self.fields_menu
        self.add_item(fields_btn)
        
        # Текст подачи
        text_btn = discord.ui.Button(label="📢 Текст кнопки подачи", style=discord.ButtonStyle.secondary, emoji="📢", row=1, custom_id="apps_text")
        text_btn.callback = self.set_submit_text
        self.add_item(text_btn)
        
        # Приветствие
        welcome_btn = discord.ui.Button(label="👋 Приветственное сообщение", style=discord.ButtonStyle.secondary, emoji="👋", row=2, custom_id="apps_welcome")
        welcome_btn.callback = self.set_welcome
        self.add_item(welcome_btn)
        
        # 🔥 НОВАЯ КНОПКА — СОЗДАНИЕ ПРОФИЛЕЙ
        profile_btn = discord.ui.Button(
            label="📁 Создание профилей",
            style=discord.ButtonStyle.secondary,
            emoji="📁",
            row=2,
            custom_id="apps_profile_toggle"
        )
        profile_btn.callback = self.toggle_profiles
        self.add_item(profile_btn)
        
        # Статистика
        stats_btn = discord.ui.Button(label="📊 Статистика заявок", style=discord.ButtonStyle.secondary, emoji="📊", row=3, custom_id="apps_stats")
        stats_btn.callback = self.show_stats
        self.add_item(stats_btn)

    def _add_back_button(self):
        back_btn = discord.ui.Button(
            label="◀ Назад в главное меню",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=4,
            custom_id="apps_back_to_global"
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
        embed = discord.Embed(title="📡 **НАСТРОЙКА КАНАЛОВ ЗАЯВОК**", description="Выберите, какой канал хотите настроить:", color=0x7289da)
        view = ApplicationsChannelsView()
        await interaction.response.edit_message(embed=embed, view=view)

    async def roles_menu(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        embed = discord.Embed(title="🎭 **НАСТРОЙКА РОЛЕЙ ЗАЯВОК**", description="Выберите, какую роль хотите настроить:", color=0x7289da)
        view = ApplicationsRolesView()
        await interaction.response.edit_message(embed=embed, view=view)

    async def fields_menu(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        embed = discord.Embed(title="📝 **НАСТРОЙКА ПОЛЕЙ ЗАЯВКИ**", color=0x7289da)
        view = ApplicationsFieldsView()
        await interaction.response.edit_message(embed=embed, view=view)

    async def set_submit_text(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetSubmitTextModal())

    async def set_welcome(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetWelcomeMessageModal())

    # 🔥 НОВЫЙ МЕТОД
    async def toggle_profiles(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        current = CONFIG.get('applications_create_profiles', 'true')
        new_state = not (current == 'true')
        
        db.set_setting('applications_create_profiles', str(new_state).lower(), str(interaction.user.id))
        CONFIG['applications_create_profiles'] = str(new_state).lower()
        save_config(str(interaction.user.id))
        
        status = "включено ✅" if new_state else "выключено ❌"
        await interaction.response.send_message(f"📁 Создание профилей при принятии заявок: {status}", ephemeral=True)
        await interaction.message.edit(view=self)

    async def show_stats(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        total = len(db.get_all_applications())
        pending = len(db.get_pending_applications())
        accepted = len(db.get_accepted_applications())
        rejected = len(db.get_rejected_applications())
        
        embed = discord.Embed(title="📊 СТАТИСТИКА ЗАЯВОК", color=0x7289da)
        embed.add_field(name="📝 Всего заявок", value=f"**{total}**", inline=True)
        embed.add_field(name="⏳ Ожидают", value=f"**{pending}**", inline=True)
        embed.add_field(name="✅ Принято", value=f"**{accepted}**", inline=True)
        embed.add_field(name="❌ Отклонено", value=f"**{rejected}**", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ApplicationsChannelsView(AdminOnlyView):
    def __init__(self):
        super().__init__(timeout=60)
        
        submit_btn = discord.ui.Button(label="📝 Канал подачи заявок", style=discord.ButtonStyle.secondary, row=0, custom_id="apps_submit")
        submit_btn.callback = self.set_submit_channel
        self.add_item(submit_btn)
        
        mod_btn = discord.ui.Button(label="⚙️ Канал модерации", style=discord.ButtonStyle.secondary, row=0, custom_id="apps_mod")
        mod_btn.callback = self.set_mod_channel
        self.add_item(mod_btn)
        
        log_btn = discord.ui.Button(label="📜 Канал логов", style=discord.ButtonStyle.secondary, row=1, custom_id="apps_log")
        log_btn.callback = self.set_log_channel
        self.add_item(log_btn)
        
        settings_btn = discord.ui.Button(label="⚙️ Канал настроек", style=discord.ButtonStyle.secondary, row=1, custom_id="apps_settings")
        settings_btn.callback = self.set_settings_channel
        self.add_item(settings_btn)
        
        back_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=2, custom_id="apps_back")
        back_btn.callback = self.back
        self.add_item(back_btn)
    
    async def set_submit_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetChannelModal("submit_channel", "канал подачи заявок"))
    
    async def set_mod_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetChannelModal("applications_channel", "канал модерации заявок"))
    
    async def set_log_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetChannelModal("applications_log_channel", "канал логов заявок"))
    
    async def set_settings_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetChannelModal("applications_settings_channel", "канал настроек заявок"))
    
    async def back(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⚙️ **НАСТРОЙКИ ЗАЯВОК**", description="Настройка системы заявок в семью", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=ApplicationsSettingsView())


class ApplicationsRolesView(AdminOnlyView):
    def __init__(self):
        super().__init__(timeout=60)
        
        recruit_btn = discord.ui.Button(label="🎭 Роль рекрута", style=discord.ButtonStyle.secondary, row=0, custom_id="apps_recruit")
        recruit_btn.callback = self.set_recruit_role
        self.add_item(recruit_btn)
        
        member_btn = discord.ui.Button(label="🎭 Роль участника", style=discord.ButtonStyle.secondary, row=0, custom_id="apps_member")
        member_btn.callback = self.set_member_role
        self.add_item(member_btn)
        
        back_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=1, custom_id="apps_back")
        back_btn.callback = self.back
        self.add_item(back_btn)
    
    async def set_recruit_role(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetRoleModal("applications_recruit_role", "роль рекрута"))
    
    async def set_member_role(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetRoleModal("applications_member_role", "роль участника"))
    
    async def back(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⚙️ **НАСТРОЙКИ ЗАЯВОК**", description="Настройка системы заявок в семью", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=ApplicationsSettingsView())


class ApplicationsFieldsView(AdminOnlyView):
    def __init__(self):
        super().__init__(timeout=60)
        
        add_btn = discord.ui.Button(label="➕ Добавить поле", style=discord.ButtonStyle.success, row=0, custom_id="apps_add_field")
        add_btn.callback = self.add_field
        self.add_item(add_btn)
        
        remove_btn = discord.ui.Button(label="🗑️ Удалить поле", style=discord.ButtonStyle.danger, row=0, custom_id="apps_remove_field")
        remove_btn.callback = self.remove_field
        self.add_item(remove_btn)
        
        list_btn = discord.ui.Button(label="📋 Список полей", style=discord.ButtonStyle.secondary, row=1, custom_id="apps_list_fields")
        list_btn.callback = self.list_fields
        self.add_item(list_btn)
        
        back_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=1, custom_id="apps_back")
        back_btn.callback = self.back
        self.add_item(back_btn)
    
    async def add_field(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddFieldModal())
    
    async def remove_field(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RemoveFieldModal())
    
    async def list_fields(self, interaction: discord.Interaction):
        fields = db.get_application_fields()
        
        if not fields:
            await interaction.response.send_message("📋 Список полей пуст", ephemeral=True)
            return
        
        embed = discord.Embed(title="📋 ПОЛЯ ЗАЯВКИ", color=0x7289da)
        for field in fields:
            embed.add_field(
                name=f"{field['name']}",
                value=f"Описание: {field['description']}\nОбязательное: {'✅' if field['required'] else '❌'}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def back(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⚙️ **НАСТРОЙКИ ЗАЯВОК**", description="Настройка системы заявок в семью", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=ApplicationsSettingsView())


class SetChannelModal(discord.ui.Modal, title="📡 НАСТРОЙКА КАНАЛА"):
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
            
            # Обновляем панель в канале настроек
            settings_channel_id = CONFIG.get('applications_settings_channel')
            if settings_channel_id:
                settings_channel = interaction.guild.get_channel(int(settings_channel_id))
                if settings_channel:
                    async for msg in settings_channel.history(limit=10):
                        if msg.author == interaction.client.user and msg.embeds:
                            embed = discord.Embed(
                                title="⚙️ **НАСТРОЙКИ ЗАЯВОК**",
                                description="Настройка системы заявок в семью",
                                color=0x00ff00
                            )
                            await msg.edit(embed=embed, view=ApplicationsSettingsView())
                            break
            
            await interaction.response.send_message(f"✅ {self.channel_id.label} настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetRoleModal(discord.ui.Modal, title="🎭 НАСТРОЙКА РОЛИ"):
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


class AddFieldModal(discord.ui.Modal, title="➕ ДОБАВИТЬ ПОЛЕ"):
    field_name = discord.ui.TextInput(label="Название поля", placeholder="nickname", max_length=50, required=True)
    field_description = discord.ui.TextInput(label="Описание", placeholder="Игровой ник", max_length=200, required=True)
    placeholder = discord.ui.TextInput(label="Placeholder", placeholder="Ваш ник в игре", max_length=100, required=False)
    required = discord.ui.TextInput(label="Обязательное (да/нет)", placeholder="да", max_length=3, required=False)
    order = discord.ui.TextInput(label="Порядок", placeholder="1", max_length=3, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        required_bool = self.required.value.lower() in ['да', 'yes', 'true', '1']
        order_int = int(self.order.value) if self.order.value else 999
        
        db.add_application_field(
            self.field_name.value,
            self.field_description.value,
            self.placeholder.value or "",
            required_bool,
            order_int,
            str(interaction.user.id)
        )
        
        await interaction.response.send_message(f"✅ Поле {self.field_name.value} добавлено!", ephemeral=True)


class RemoveFieldModal(discord.ui.Modal, title="🗑️ УДАЛИТЬ ПОЛЕ"):
    field_id = discord.ui.TextInput(label="ID поля", placeholder="1", max_length=10, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        field_id = int(self.field_id.value)
        db.remove_application_field(field_id, str(interaction.user.id))
        
        await interaction.response.send_message(f"✅ Поле ID {field_id} удалено!", ephemeral=True)


class SetSubmitTextModal(discord.ui.Modal, title="📢 ТЕКСТ КНОПКИ ПОДАЧИ"):
    text = discord.ui.TextInput(
        label="Текст",
        placeholder="Нажмите кнопку ниже, чтобы подать заявку",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )
    image = discord.ui.TextInput(
        label="Ссылка на изображение (опционально)",
        placeholder="https://...",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        db.set_setting('submit_text', self.text.value, str(interaction.user.id))
        CONFIG['submit_text'] = self.text.value
        
        if self.image.value:
            db.set_setting('submit_image', self.image.value, str(interaction.user.id))
            CONFIG['submit_image'] = self.image.value
        
        save_config(str(interaction.user.id))
        
        await interaction.response.send_message("✅ Текст кнопки подачи обновлён!", ephemeral=True)


class SetWelcomeMessageModal(discord.ui.Modal, title="👋 ПРИВЕТСТВЕННОЕ СООБЩЕНИЕ"):
    message = discord.ui.TextInput(
        label="Текст приветствия",
        placeholder="Добро пожаловать в семью!",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )
    channel = discord.ui.TextInput(label="ID канала для приветствия", placeholder="123456789012345678", required=False)
    image = discord.ui.TextInput(label="Ссылка на изображение", placeholder="https://...", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        db.set_setting('welcome_message', self.message.value, str(interaction.user.id))
        CONFIG['welcome_message'] = self.message.value
        
        if self.channel.value:
            db.set_setting('welcome_channel', self.channel.value, str(interaction.user.id))
            CONFIG['welcome_channel'] = self.channel.value
        
        if self.image.value:
            db.set_setting('welcome_image', self.image.value, str(interaction.user.id))
            CONFIG['welcome_image'] = self.image.value
        
        save_config(str(interaction.user.id))
        
        await interaction.response.send_message("✅ Приветственное сообщение сохранено!", ephemeral=True)