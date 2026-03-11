"""Кнопки для пользователей и модерации заявок"""
import discord
from datetime import datetime
from core.config import CONFIG
from applications.manager import app_manager
from applications.base import PermanentView
from applications.modals import ApplicationModal


# ===== КЛАСС 1: ПУБЛИЧНАЯ КНОПКА ДЛЯ ПОДАЧИ ЗАЯВОК =====

class ApplicationPublicView(PermanentView):
    """Публичная кнопка для подачи заявок (для пользователей)"""
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(
        label="📝 ПОДАТЬ ЗАЯВКУ", 
        style=discord.ButtonStyle.success,
        emoji="📝",
        custom_id="application_submit"
    )
    async def submit_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Открыть модалку заявки"""
        await interaction.response.send_modal(ApplicationModal())


# ===== КЛАСС 2: КНОПКИ ДЛЯ МОДЕРАЦИИ КОНКРЕТНОЙ ЗАЯВКИ =====

class ApplicationModerationView(discord.ui.View):
    """Кнопки для модерации конкретной заявки"""
    
    def __init__(self, application_id: int, user_id: str):
        super().__init__(timeout=None)  # Бесконечный таймаут
        self.application_id = application_id
        self.user_id = user_id  # ID пользователя, подавшего заявку
    
    async def check_member(self, interaction: discord.Interaction) -> bool:
        """Проверить, что пользователь всё ещё на сервере"""
        guild = interaction.guild
        member = guild.get_member(int(self.user_id))
        
        if not member:
            # Пользователь покинул сервер
            embed = discord.Embed(
                title="👋 ЗАЯВКА АВТОМАТИЧЕСКИ ЗАКРЫТА",
                description=f"Пользователь (ID: {self.user_id}) покинул сервер",
                color=0x808080,
                timestamp=datetime.now()
            )
            
            # Деактивируем кнопки
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)
            
            # Логируем
            log_channel_id = CONFIG.get('applications_log_channel')
            if log_channel_id:
                log_channel = interaction.client.get_channel(int(log_channel_id))
                if log_channel:
                    await log_channel.send(embed=embed)
            
            return False
        return True
    
    @discord.ui.button(label="✅ ПРИНЯТЬ", style=discord.ButtonStyle.success, row=0)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Принять заявку"""
        # Проверяем, на месте ли пользователь
        if not await self.check_member(interaction):
            await interaction.response.send_message("❌ Пользователь уже покинул сервер", ephemeral=True)
            return
        
        # Делаем кнопки неактивными
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        
        await self.process_accept(interaction)
    
    @discord.ui.button(label="📞 ВЫЗВАТЬ НА ОБЗВОН", style=discord.ButtonStyle.primary, row=0)
    async def interview_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Вызвать на обзвон"""
        # Проверяем, на месте ли пользователь
        if not await self.check_member(interaction):
            await interaction.response.send_message("❌ Пользователь уже покинул сервер", ephemeral=True)
            return
        
        # НЕ деактивируем кнопки - они остаются активными
        await self.process_interview(interaction)
    
    @discord.ui.button(label="❌ ОТКЛОНИТЬ", style=discord.ButtonStyle.danger, row=1)
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Отклонить заявку"""
        # Проверяем, на месте ли пользователь
        if not await self.check_member(interaction):
            await interaction.response.send_message("❌ Пользователь уже покинул сервер", ephemeral=True)
            return
        
        # Открываем модалку с причиной (кнопки остаются активными до подтверждения)
        await interaction.response.send_modal(RejectReasonModal(self.application_id, self.user_id))
    
    async def process_accept(self, interaction: discord.Interaction):
        """Обработка принятия заявки"""
        # Принимаем заявку в БД
        success = app_manager.accept_application(self.application_id, str(interaction.user.id))
        
        if not success:
            await interaction.response.send_message("❌ Не удалось принять заявку", ephemeral=True)
            return
        
        # Получаем данные заявки
        app = app_manager.get_application(self.application_id)
        if not app:
            await interaction.response.send_message("❌ Заявка не найдена", ephemeral=True)
            return
        
        # Выдаем роль участника
        guild = interaction.guild
        member_role_id = CONFIG.get('applications_member_role')
        if member_role_id and guild:
            member = guild.get_member(int(app['user_id']))
            if member:
                role = guild.get_role(int(member_role_id))
                if role:
                    await member.add_roles(role)
        
        # Отправляем ЛС пользователю
        try:
            user = await interaction.client.fetch_user(int(app['user_id']))
            if user:
                embed = discord.Embed(
                    title="✅ ЗАЯВКА ПРИНЯТА",
                    description=f"Поздравляем! Ваша заявка в семью принята.",
                    color=0x00ff00
                )
                await user.send(embed=embed)
        except:
            pass
        
        # Логируем в канал логов
        await self.log_action(interaction, "ПРИНЯТА", app)
        
        # Обновляем сообщение
        embed = interaction.message.embeds[0]
        embed.color = 0x00ff00
        embed.add_field(name="✅ Статус", value=f"Принята модератором {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Заявка принята", ephemeral=True)
    
    async def process_interview(self, interaction: discord.Interaction):
        """Обработка вызова на обзвон"""
        # Отмечаем как обзвон в БД
        success = app_manager.set_interviewing(self.application_id, str(interaction.user.id))
        
        if not success:
            await interaction.response.send_message("❌ Не удалось назначить обзвон", ephemeral=True)
            return
        
        # Получаем данные заявки
        app = app_manager.get_application(self.application_id)
        if not app:
            await interaction.response.send_message("❌ Заявка не найдена", ephemeral=True)
            return
        
        guild = interaction.guild
        member = guild.get_member(int(app['user_id']))
        
        # Создаём приватный канал
        category_name = "📞 ОБЗВОНЫ"
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
        
        channel_name = f"обзвон-{member.display_name[:20]}"
        
        # Права доступа
        recruit_role_id = CONFIG.get('applications_recruit_role')
        recruit_role = guild.get_role(int(recruit_role_id)) if recruit_role_id else None
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        if recruit_role:
            overwrites[recruit_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        interview_channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Обзвон заявки #{self.application_id}"
        )
        
        # Отправляем ЛС
        try:
            user = await interaction.client.fetch_user(int(app['user_id']))
            if user:
                embed = discord.Embed(
                    title="📞 ВЫЗОВ НА ОБЗВОН",
                    description=f"Вас готовы выслушать!",
                    color=0xffa500
                )
                embed.add_field(name="📝 Канал", value=interview_channel.mention)
                await user.send(embed=embed)
        except:
            pass
        
        # Отправляем в приватный канал
        embed = discord.Embed(
            title="📞 ОБЗВОН",
            description=f"Заявка от {member.mention}",
            color=0xffa500,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Модератор", value=interaction.user.mention)
        embed.add_field(name="🎮 Ник", value=app['nickname'])
        embed.add_field(name="🎯 Статик", value=app['static'])
        await interview_channel.send(content=f"{member.mention} {interaction.user.mention}", embed=embed)
        
        # Логируем в канал логов
        await self.log_action(interaction, "ВЫЗОВ НА ОБЗВОН", app, interview_channel.mention)
        
        await interaction.response.send_message(
            f"📞 Канал создан: {interview_channel.mention}",
            ephemeral=True
        )
    
    async def log_action(self, interaction: discord.Interaction, action: str, app: dict, details: str = None):
        """Логирование действий в канал логов"""
        log_channel_id = CONFIG.get('applications_log_channel')
        if not log_channel_id:
            return
        
        log_channel = interaction.client.get_channel(int(log_channel_id))
        if not log_channel:
            return
        
        embed = discord.Embed(
            title=f"📋 {action}",
            color=0x00ff00 if action == "ПРИНЯТА" else 0xffa500,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Пользователь", value=f"<@{app['user_id']}>")
        embed.add_field(name="👤 Модератор", value=interaction.user.mention)
        embed.add_field(name="🎮 Ник", value=app['nickname'])
        
        if details:
            embed.add_field(name="📝 Детали", value=details, inline=False)
        
        await log_channel.send(embed=embed)


# ===== КЛАСС 3: МОДАЛКА ДЛЯ ПРИЧИНЫ ОТКАЗА =====

class RejectReasonModal(discord.ui.Modal, title="❌ ПРИЧИНА ОТКАЗА"):
    """Модалка для ввода причины отказа"""
    
    reason = discord.ui.TextInput(
        label="Причина отказа",
        placeholder="Опишите причину отказа",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )
    
    def __init__(self, application_id: int, user_id: str):
        super().__init__()
        self.application_id = application_id
        self.user_id = user_id
    
    async def on_submit(self, interaction: discord.Interaction):
        # Проверяем, на месте ли пользователь
        guild = interaction.guild
        member = guild.get_member(int(self.user_id))
        
        message = interaction.message
        
        if not member:
            await interaction.response.send_message("❌ Пользователь уже покинул сервер", ephemeral=True)
            return
        
        # Отклоняем заявку в БД
        success = app_manager.reject_application(self.application_id, str(interaction.user.id), self.reason.value)
        
        if not success:
            await interaction.response.send_message("❌ Не удалось отклонить заявку", ephemeral=True)
            return
        
        # Получаем данные заявки
        app = app_manager.get_application(self.application_id)
        
        if app:
            # Отправляем ЛС пользователю
            try:
                user = await interaction.client.fetch_user(int(app['user_id']))
                if user:
                    embed = discord.Embed(
                        title="❌ ЗАЯВКА ОТКЛОНЕНА",
                        description=f"Причина: {self.reason.value}",
                        color=0xff0000
                    )
                    await user.send(embed=embed)
            except:
                pass
            
            # Логируем в канал логов
            log_channel_id = CONFIG.get('applications_log_channel')
            if log_channel_id:
                log_channel = interaction.client.get_channel(int(log_channel_id))
                if log_channel:
                    embed = discord.Embed(
                        title="❌ ЗАЯВКА ОТКЛОНЕНА",
                        description=f"Заявка от <@{app['user_id']}> отклонена",
                        color=0xff0000,
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="👤 Модератор", value=interaction.user.mention)
                    embed.add_field(name="📝 Причина", value=self.reason.value)
                    await log_channel.send(embed=embed)
        
        # Обновляем сообщение
        embed = message.embeds[0]
        embed.color = 0xff0000
        embed.add_field(name="❌ Статус", value=f"Отклонена модератором {interaction.user.mention}", inline=False)
        embed.add_field(name="📝 Причина", value=self.reason.value, inline=False)
        
        # Деактивируем кнопки
        for child in message.components[0].children:
            child.disabled = True
        
        await message.edit(embed=embed, view=None)
        await interaction.response.send_message("❌ Заявка отклонена", ephemeral=True)