"""Панель управления и модерации заявок"""
import discord
from datetime import datetime
from core.database import db
from core.utils import format_mention, is_admin
from applications.base import PermanentView
from applications.manager import app_manager


class SetSubmitChannelModal(discord.ui.Modal, title="📝 КАНАЛ ПОДАЧИ ЗАЯВОК"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", max_length=20, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(int(self.channel_id.value))
        if not channel:
            await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
            return
        app_manager.save_setting('submit_channel', self.channel_id.value, str(interaction.user.id))
        await interaction.response.send_message(f"✅ Канал подачи заявок настроен: {channel.mention}", ephemeral=True)


class SetApplicationsChannelModal(discord.ui.Modal, title="📋 КАНАЛ АНКЕТ"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", max_length=20, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(int(self.channel_id.value))
        if not channel:
            await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
            return
        app_manager.save_setting('applications_channel', self.channel_id.value, str(interaction.user.id))
        await interaction.response.send_message(f"✅ Канал анкет настроен: {channel.mention}", ephemeral=True)


class SetLogChannelModal(discord.ui.Modal, title="📜 КАНАЛ ЛОГОВ"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", max_length=20, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(int(self.channel_id.value))
        if not channel:
            await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
            return
        app_manager.save_setting('applications_log_channel', self.channel_id.value, str(interaction.user.id))
        await interaction.response.send_message(f"✅ Канал логов настроен: {channel.mention}", ephemeral=True)


class SetRecruitRoleModal(discord.ui.Modal, title="👥 РОЛЬ РЕКРУТА"):
    role_id = discord.ui.TextInput(label="ID роли", placeholder="123456789012345678", max_length=20, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(int(self.role_id.value))
        if not role:
            await interaction.response.send_message("❌ Роль не найдена", ephemeral=True)
            return
        app_manager.save_setting('applications_recruit_role', self.role_id.value, str(interaction.user.id))
        await interaction.response.send_message(f"✅ Роль рекрута настроена: {role.mention}", ephemeral=True)


class SetSubmitTextModal(discord.ui.Modal, title="📝 ТЕКСТ НАД КНОПКОЙ"):
    text = discord.ui.TextInput(label="Текст", placeholder="Нажмите кнопку ниже, чтобы подать заявку", style=discord.TextStyle.paragraph, max_length=500, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        app_manager.save_setting('submit_text', self.text.value, str(interaction.user.id))
        from applications.initializer import update_submit_channel
        await update_submit_channel(interaction.client)
        await interaction.response.send_message("✅ Текст над кнопкой обновлён!", ephemeral=True)


class SetSubmitImageModal(discord.ui.Modal, title="🖼️ КАРТИНКА ДЛЯ ЭМБЕДА"):
    image_url = discord.ui.TextInput(label="URL картинки", placeholder="https://example.com/image.png", max_length=500, required=False)
    async def on_submit(self, interaction: discord.Interaction):
        app_manager.save_setting('submit_image', self.image_url.value or "", str(interaction.user.id))
        from applications.initializer import update_submit_channel
        await update_submit_channel(interaction.client)
        await interaction.response.send_message(f"✅ Картинка {'установлена' if self.image_url.value else 'удалена'}", ephemeral=True)


class SetWelcomeMessageModal(discord.ui.Modal, title="👋 ПРИВЕТСТВИЕ НОВЫМ"):
    message = discord.ui.TextInput(label="Текст", placeholder="Добро пожаловать! Подайте заявку в канале {channel}", style=discord.TextStyle.paragraph, max_length=1000, required=True)
    image_url = discord.ui.TextInput(label="URL картинки (опционально)", placeholder="https://example.com/image.png", max_length=500, required=False)
    async def on_submit(self, interaction: discord.Interaction):
        app_manager.save_setting('welcome_message', self.message.value, str(interaction.user.id))
        app_manager.save_setting('welcome_image', self.image_url.value or "", str(interaction.user.id))
        await interaction.response.send_message("✅ Приветствие настроено!", ephemeral=True)


class ResetUserModal(discord.ui.Modal, title="🔄 СБРОС ПОЛЬЗОВАТЕЛЯ"):
    user_id = discord.ui.TextInput(label="ID пользователя", placeholder="123456789012345678", max_length=20, required=True)
    confirm = discord.ui.TextInput(label="Подтверждение (введите 'СБРОС')", placeholder="СБРОС", max_length=10, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value != "СБРОС":
            await interaction.response.send_message("❌ Неверное подтверждение", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        success, msg = app_manager.reset_user_applications(self.user_id.value, str(interaction.user.id))
        await interaction.followup.send(msg, ephemeral=True)


class AddRewardRoleModal(discord.ui.Modal, title="➕ ДОБАВИТЬ РОЛЬ"):
    role_id = discord.ui.TextInput(label="ID роли", placeholder="123456789012345678", max_length=20, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(int(self.role_id.value))
        if not role:
            await interaction.response.send_message("❌ Роль не найдена", ephemeral=True)
            return
        db.add_reward_role(self.role_id.value, str(interaction.user.id))
        await interaction.response.send_message(f"✅ Роль {role.mention} добавлена в список выдачи", ephemeral=True)


class RemoveRewardRoleModal(discord.ui.Modal, title="➖ УДАЛИТЬ РОЛЬ"):
    role_id = discord.ui.TextInput(label="ID роли", placeholder="123456789012345678", max_length=20, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        db.remove_reward_role(self.role_id.value)
        await interaction.response.send_message(f"✅ Роль ID {self.role_id.value} удалена", ephemeral=True)


class AddFieldModal(discord.ui.Modal, title="➕ ДОБАВИТЬ ПОЛЕ"):
    field_name = discord.ui.TextInput(label="Название поля", placeholder="например: arena_link", max_length=50, required=True)
    field_description = discord.ui.TextInput(label="Описание", placeholder="Ссылка на откат с арены", max_length=100, required=True)
    placeholder = discord.ui.TextInput(label="Placeholder", placeholder="https://...", max_length=200, required=False)
    required = discord.ui.TextInput(label="Обязательное (да/нет)", placeholder="да", max_length=3, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        req = self.required.value.lower() == 'да'
        fields = db.get_application_fields()
        order = len(fields) + 1
        db.add_application_field(self.field_name.value, self.field_description.value, self.placeholder.value or "", req, order, str(interaction.user.id))
        await interaction.response.send_message(f"✅ Поле `{self.field_name.value}` добавлено!", ephemeral=True)


class RemoveFieldModal(discord.ui.Modal, title="➖ УДАЛИТЬ ПОЛЕ"):
    field_id = discord.ui.TextInput(label="ID поля", placeholder="1", max_length=5, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        db.remove_application_field(int(self.field_id.value), str(interaction.user.id))
        await interaction.response.send_message(f"✅ Поле ID {self.field_id.value} удалено!", ephemeral=True)


class ApplicationFieldsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        add_btn = discord.ui.Button(label="➕ Добавить поле", style=discord.ButtonStyle.success, row=0)
        add_btn.callback = self.add_field
        self.add_item(add_btn)
        remove_btn = discord.ui.Button(label="➖ Удалить поле", style=discord.ButtonStyle.danger, row=0)
        remove_btn.callback = self.remove_field
        self.add_item(remove_btn)
        list_btn = discord.ui.Button(label="📋 Список полей", style=discord.ButtonStyle.secondary, row=0)
        list_btn.callback = self.list_fields
        self.add_item(list_btn)
        back_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=1)
        back_btn.callback = self.back
        self.add_item(back_btn)

    async def add_field(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddFieldModal())

    async def remove_field(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RemoveFieldModal())

    async def list_fields(self, interaction: discord.Interaction):
        fields = db.get_application_fields()
        if not fields:
            await interaction.response.send_message("📭 Нет дополнительных полей", ephemeral=True)
            return
        text = ""
        for f in fields:
            req = "✅" if f['required'] else "❌"
            text += f"`{f['id']}` {req} **{f['name']}** — {f['description']}\n"
        embed = discord.Embed(title="📋 Поля заявки", description=text, color=0x00ff00)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def back(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📋 **УПРАВЛЕНИЕ И МОДЕРАЦИЯ ЗАЯВОК**",
            description="Настройка системы и управление заявками",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=ApplicationsCombinedPanel())


class ApplicationsCombinedPanel(PermanentView):
    def __init__(self):
        super().__init__()
        self._add_buttons()

    def _add_buttons(self):
        # Ряд 0: каналы (3 кнопки)
        self.add_item(discord.ui.Button(label="📝 Канал подачи", style=discord.ButtonStyle.primary, row=0, custom_id="submit_channel"))
        self.add_item(discord.ui.Button(label="📋 Канал анкет", style=discord.ButtonStyle.primary, row=0, custom_id="apps_channel"))
        self.add_item(discord.ui.Button(label="📜 Канал логов", style=discord.ButtonStyle.primary, row=0, custom_id="log_channel"))

        # Ряд 1: роли (1 кнопка)
        self.add_item(discord.ui.Button(label="👥 Роль рекрута", style=discord.ButtonStyle.primary, row=1, custom_id="recruit_role"))

        # Ряд 2: внешний вид (3 кнопки)
        self.add_item(discord.ui.Button(label="📝 Текст над кнопкой", style=discord.ButtonStyle.secondary, row=2, custom_id="submit_text"))
        self.add_item(discord.ui.Button(label="🖼️ Картинка эмбеда", style=discord.ButtonStyle.secondary, row=2, custom_id="submit_image"))
        self.add_item(discord.ui.Button(label="👋 Приветствие", style=discord.ButtonStyle.secondary, row=2, custom_id="welcome"))

        # Ряд 3: выдаваемые роли (3 кнопки)
        self.add_item(discord.ui.Button(label="➕ Добавить роль", style=discord.ButtonStyle.success, row=3, custom_id="add_role"))
        self.add_item(discord.ui.Button(label="➖ Удалить роль", style=discord.ButtonStyle.danger, row=3, custom_id="remove_role"))
        self.add_item(discord.ui.Button(label="📋 Список ролей", style=discord.ButtonStyle.secondary, row=3, custom_id="list_roles"))

        # Ряд 4: модерация и поля (4 кнопки — влезает)
        self.add_item(discord.ui.Button(label="📋 Ожидающие заявки", style=discord.ButtonStyle.success, row=4, custom_id="pending"))
        self.add_item(discord.ui.Button(label="🔄 Сбросить пользователя", style=discord.ButtonStyle.secondary, row=4, custom_id="reset"))
        self.add_item(discord.ui.Button(label="📝 Управление полями", style=discord.ButtonStyle.secondary, row=4, custom_id="fields"))
        self.add_item(discord.ui.Button(label="📊 Текущие настройки", style=discord.ButtonStyle.secondary, row=4, custom_id="settings"))

    async def interaction_check(self, interaction: discord.Interaction):
        custom_id = interaction.data.get('custom_id', '')
        if custom_id == "submit_channel":
            await interaction.response.send_modal(SetSubmitChannelModal())
        elif custom_id == "apps_channel":
            await interaction.response.send_modal(SetApplicationsChannelModal())
        elif custom_id == "log_channel":
            await interaction.response.send_modal(SetLogChannelModal())
        elif custom_id == "recruit_role":
            await interaction.response.send_modal(SetRecruitRoleModal())
        elif custom_id == "submit_text":
            await interaction.response.send_modal(SetSubmitTextModal())
        elif custom_id == "submit_image":
            await interaction.response.send_modal(SetSubmitImageModal())
        elif custom_id == "welcome":
            await interaction.response.send_modal(SetWelcomeMessageModal())
        elif custom_id == "add_role":
            await interaction.response.send_modal(AddRewardRoleModal())
        elif custom_id == "remove_role":
            await interaction.response.send_modal(RemoveRewardRoleModal())
        elif custom_id == "list_roles":
            await self.list_reward_roles(interaction)
        elif custom_id == "pending":
            await self.show_pending(interaction)
        elif custom_id == "reset":
            await interaction.response.send_modal(ResetUserModal())
        elif custom_id == "fields":
            await self.manage_fields(interaction)
        elif custom_id == "settings":
            await self.show_settings(interaction)
        return True

    async def list_reward_roles(self, interaction: discord.Interaction):
        role_ids = db.get_reward_roles()
        if not role_ids:
            await interaction.response.send_message("📭 Нет настроенных ролей", ephemeral=True)
            return
        guild = interaction.guild
        text = ""
        for rid in role_ids:
            role = guild.get_role(int(rid))
            text += f"• {role.mention if role else f'ID: {rid} (не найдена)'}\n"
        embed = discord.Embed(title="📋 Роли для выдачи", description=text, color=0x00ff00)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def show_pending(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        apps = app_manager.get_pending_applications()
        if not apps:
            await interaction.followup.send("📭 Нет ожидающих заявок", ephemeral=True)
            return
        embed = discord.Embed(title="📋 ОЖИДАЮЩИЕ ЗАЯВКИ", color=0xffa500, timestamp=datetime.now())
        for app in apps[:10]:
            embed.add_field(name=f"ID: {app['id']} - {app['nickname']}", value=f"👤 <@{app['user_id']}>\n⏰ {app['created_at'][:16]}", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def manage_fields(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📝 **УПРАВЛЕНИЕ ПОЛЯМИ ЗАЯВКИ**",
            description="Добавление, удаление и просмотр полей формы подачи заявки",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=ApplicationFieldsView())

    async def show_settings(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📊 ТЕКУЩИЕ НАСТРОЙКИ", color=0x00ff00)
        guild = interaction.guild
        settings = app_manager.get_settings()
        submit_channel = format_mention(guild, settings.get('submit_channel'), 'channel') if settings.get('submit_channel') else "`Не настроен`"
        applications_channel = format_mention(guild, settings.get('applications_channel'), 'channel') if settings.get('applications_channel') else "`Не настроен`"
        log_channel = format_mention(guild, settings.get('applications_log_channel'), 'channel') if settings.get('applications_log_channel') else "`Не настроен`"
        recruit_role = format_mention(guild, settings.get('applications_recruit_role'), 'role') if settings.get('applications_recruit_role') else "`Не настроена`"
        embed.add_field(name="📝 Канал подачи", value=submit_channel, inline=False)
        embed.add_field(name="📋 Канал анкет", value=applications_channel, inline=False)
        embed.add_field(name="📜 Канал логов", value=log_channel, inline=False)
        embed.add_field(name="👥 Роль рекрута", value=recruit_role, inline=False)
        role_ids = db.get_reward_roles()
        if role_ids:
            roles_text = ""
            for rid in role_ids:
                role = guild.get_role(int(rid))
                roles_text += f"• {role.mention if role else f'ID: {rid} (не найдена)'}\n"
            embed.add_field(name="🎭 Выдаваемые роли", value=roles_text, inline=False)
        else:
            embed.add_field(name="🎭 Выдаваемые роли", value="`Не настроены`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)