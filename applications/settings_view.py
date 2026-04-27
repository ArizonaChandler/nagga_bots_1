"""Панель управления и модерации заявок"""
import discord
from applications.base import PermanentView
from applications.manager import app_manager
from core.config import CONFIG, save_config
from core.database import db
from core.utils import format_mention
from datetime import datetime

class ApplicationsCombinedPanel(PermanentView):
    """Объединенная панель для настройки и модерации заявок"""
    
    def __init__(self):
        super().__init__()
    
    # ===== РЯД 0: НАСТРОЙКИ КАНАЛОВ (максимум 5 кнопок) =====
    @discord.ui.button(
        label="📝 Канал подачи", 
        style=discord.ButtonStyle.primary,
        emoji="📝",
        row=0,
        custom_id="apps_submit_channel"
    )
    async def set_submit_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить канал для кнопки подачи заявок"""
        await interaction.response.send_modal(SetSubmitChannelModal())

    @discord.ui.button(
        label="📋 Канал анкет", 
        style=discord.ButtonStyle.primary,
        emoji="📋",
        row=0,
        custom_id="apps_applications_channel"
    )
    async def set_applications_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить канал, куда приходят анкеты"""
        await interaction.response.send_modal(SetApplicationsChannelModal())

    @discord.ui.button(
        label="📜 Канал логов", 
        style=discord.ButtonStyle.primary,
        emoji="📜",
        row=0,
        custom_id="apps_log_channel"
    )
    async def set_log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить канал для логов"""
        await interaction.response.send_modal(SetLogChannelModal())

    @discord.ui.button(
        label="👥 Роль рекрута", 
        style=discord.ButtonStyle.primary,
        emoji="👥",
        row=0,
        custom_id="apps_settings_recruit"
    )
    async def set_recruit_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить роль рекрута"""
        await interaction.response.send_modal(SetRecruitRoleModal())

    @discord.ui.button(
        label="👑 Роль участника", 
        style=discord.ButtonStyle.primary,
        emoji="👑",
        row=0,
        custom_id="apps_settings_member"
    )
    async def set_member_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить роль участника"""
        await interaction.response.send_modal(SetMemberRoleModal())

    # ===== РЯД 1: НАСТРОЙКИ ВНЕШНЕГО ВИДА =====
    @discord.ui.button(
        label="📝 Текст над кнопкой", 
        style=discord.ButtonStyle.secondary,
        emoji="📝",
        row=1,
        custom_id="apps_submit_text"
    )
    async def set_submit_text(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить текст над кнопкой подачи заявок"""
        await interaction.response.send_modal(SetSubmitTextModal())

    @discord.ui.button(
        label="🖼️ Картинка эмбеда", 
        style=discord.ButtonStyle.secondary,
        emoji="🖼️",
        row=1,
        custom_id="apps_submit_image"
    )
    async def set_submit_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить картинку для эмбеда подачи заявок"""
        await interaction.response.send_modal(SetSubmitImageModal())

    @discord.ui.button(
        label="👋 Приветствие новым", 
        style=discord.ButtonStyle.secondary,
        emoji="👋",
        row=1,
        custom_id="apps_welcome"
    )
    async def set_welcome_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить приветственное сообщение для новых участников"""
        await interaction.response.send_modal(SetWelcomeMessageModal())

    # ===== РЯД 2: МОДЕРАЦИЯ =====
    @discord.ui.button(
        label="📋 Ожидающие заявки", 
        style=discord.ButtonStyle.success,
        emoji="📋",
        row=2,
        custom_id="apps_pending"
    )
    async def show_pending(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать список ожидающих заявок"""
        await interaction.response.defer(ephemeral=True)
        
        apps = app_manager.get_pending_applications()
        
        if not apps:
            await interaction.followup.send("📭 Нет ожидающих заявок", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📋 ОЖИДАЮЩИЕ ЗАЯВКИ",
            color=0xffa500,
            timestamp=datetime.now()
        )
        
        for app in apps[:10]:
            embed.add_field(
                name=f"ID: {app['id']} - {app['nickname']}",
                value=f"👤 <@{app['user_id']}>\n⏰ {app['created_at'][:16]}",
                inline=False
            )
        
        if len(apps) > 10:
            embed.set_footer(text=f"Показано 10 из {len(apps)} заявок")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(
        label="🔄 Сбросить пользователя", 
        style=discord.ButtonStyle.secondary,
        emoji="🔄",
        row=2,
        custom_id="apps_reset_user"
    )
    async def reset_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Сбросить все заявки пользователя"""
        await interaction.response.send_modal(ResetUserModal())
    
    # ===== РЯД 3: ИНФОРМАЦИЯ =====
    @discord.ui.button(
        label="📊 Текущие настройки", 
        style=discord.ButtonStyle.secondary,
        emoji="📊",
        row=3,
        custom_id="apps_settings_show"
    )
    async def show_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать текущие настройки"""
        embed = discord.Embed(
            title="📊 НАСТРОЙКИ СИСТЕМЫ ЗАЯВОК",
            color=0x00ff00
        )
        
        guild = interaction.guild
        settings = app_manager.get_settings()
        
        submit_channel = format_mention(guild, settings.get('submit_channel'), 'channel') if settings.get('submit_channel') else "`Не настроен`"
        applications_channel = format_mention(guild, settings.get('applications_channel'), 'channel') if settings.get('applications_channel') else "`Не настроен`"
        log_channel = format_mention(guild, settings.get('applications_log_channel'), 'channel') if settings.get('applications_log_channel') else "`Не настроен`"
        recruit_role = format_mention(guild, settings.get('applications_recruit_role'), 'role') if settings.get('applications_recruit_role') else "`Не настроена`"
        member_role = format_mention(guild, settings.get('applications_member_role'), 'role') if settings.get('applications_member_role') else "`Не настроена`"
        
        embed.add_field(name="📝 Канал подачи заявок", value=submit_channel, inline=False)
        embed.add_field(name="📋 Канал анкет", value=applications_channel, inline=False)
        embed.add_field(name="📜 Канал логов", value=log_channel, inline=False)
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
            
            app_manager.save_setting('applications_channel', self.channel_id.value, str(interaction.user.id))
            
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
            
            app_manager.save_setting('applications_log_channel', self.channel_id.value, str(interaction.user.id))
            
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
            
            app_manager.save_setting('applications_recruit_role', self.role_id.value, str(interaction.user.id))
            
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
            
            app_manager.save_setting('applications_member_role', self.role_id.value, str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Роль участника настроена: {role.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class ResetUserModal(discord.ui.Modal, title="🔄 СБРОС ПОЛЬЗОВАТЕЛЯ"):
    """Модалка для сброса всех заявок пользователя"""
    
    user_id = discord.ui.TextInput(
        label="ID пользователя",
        placeholder="123456789012345678",
        max_length=20,
        required=True
    )
    
    confirm = discord.ui.TextInput(
        label="Подтверждение (введите 'СБРОС')",
        placeholder="СБРОС",
        max_length=10,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        print(f"🔍 Начало сброса пользователя {self.user_id.value}")
        
        if self.confirm.value != "СБРОС":
            print(f"❌ Неверное подтверждение: {self.confirm.value}")
            await interaction.response.send_message("❌ Неверное подтверждение", ephemeral=True)
            return
        
        if not self.user_id.value.isdigit():
            print(f"❌ ID не является числом: {self.user_id.value}")
            await interaction.response.send_message("❌ ID должен содержать только цифры", ephemeral=True)
            return
        
        # Отвечаем сразу, чтобы не было ошибки взаимодействия
        await interaction.response.defer(ephemeral=True)
        print("✅ Взаимодействие отложено")
        
        try:
            print(f"🔄 Вызов app_manager.reset_user_applications({self.user_id.value})")
            success, message = app_manager.reset_user_applications(
                self.user_id.value, 
                str(interaction.user.id)
            )
            
            print(f"📊 Результат: success={success}, message={message}")
            
            await interaction.followup.send(message, ephemeral=True)
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)

class SetSubmitChannelModal(discord.ui.Modal, title="📝 КАНАЛ ПОДАЧИ ЗАЯВОК"):
    """Канал, где будет кнопка 'ПОДАТЬ ЗАЯВКУ'"""
    
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
            
            app_manager.save_setting('submit_channel', self.channel_id.value, str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Канал для кнопки подачи заявок настроен: {channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetApplicationsChannelModal(discord.ui.Modal, title="📋 КАНАЛ АНКЕТ"):
    """Канал, куда приходят анкеты с кнопками модерации"""
    
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
            
            app_manager.save_setting('applications_channel', self.channel_id.value, str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Канал для анкет настроен: {channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

class SetSubmitTextModal(discord.ui.Modal, title="📝 ТЕКСТ НАД КНОПКОЙ"):
    
    text = discord.ui.TextInput(
        label="Текст над кнопкой",
        placeholder="Нажмите кнопку ниже, чтобы подать заявку",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            app_manager.save_setting('submit_text', self.text.value, str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Текст над кнопкой обновлён!",
                ephemeral=True
            )
            
            # Обновляем сообщение в канале подачи заявок
            await update_submit_channel(interaction.client)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetSubmitImageModal(discord.ui.Modal, title="🖼️ КАРТИНКА ДЛЯ ЭМБЕДА"):
    
    image_url = discord.ui.TextInput(
        label="URL картинки",
        placeholder="https://example.com/image.png",
        max_length=500,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            app_manager.save_setting('submit_image', self.image_url.value or "", str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Картинка для эмбеда {'установлена' if self.image_url.value else 'удалена'}!",
                ephemeral=True
            )
            
            # Обновляем сообщение в канале подачи заявок
            await update_submit_channel(interaction.client)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetWelcomeMessageModal(discord.ui.Modal, title="👋 ПРИВЕТСТВИЕ НОВЫМ УЧАСТНИКАМ"):
    
    message = discord.ui.TextInput(
        label="Текст приветствия",
        placeholder="Добро пожаловать! Подайте заявку в канале {channel}",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )
    
    image_url = discord.ui.TextInput(
        label="URL картинки (опционально)",
        placeholder="https://example.com/image.png",
        max_length=500,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            app_manager.save_setting('welcome_message', self.message.value, str(interaction.user.id))
            app_manager.save_setting('welcome_image', self.image_url.value or "", str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Приветственное сообщение настроено!",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)