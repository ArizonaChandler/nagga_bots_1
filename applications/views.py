"""Кнопки для пользователей"""
import discord
from datetime import datetime
from core.config import CONFIG
from applications.base import PermanentView
from applications.modals import ApplicationModal
from applications.manager import app_manager

class ApplicationPublicView(PermanentView):
    """Публичная кнопка для подачи заявок"""
    
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


class ApplicationModerationView(discord.ui.View):
    """Кнопки для модерации конкретной заявки"""
    
    def __init__(self, application_id: int):
        super().__init__(timeout=None)
        self.application_id = application_id
    
    @discord.ui.button(label="✅ ПРИНЯТЬ", style=discord.ButtonStyle.success, row=0)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Принять заявку"""
        # Делаем кнопки неактивными сразу
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        
        # Обрабатываем заявку
        await self.process_accept(interaction)
    
    @discord.ui.button(label="📞 ВЫЗВАТЬ НА ОБЗВОН", style=discord.ButtonStyle.primary, row=0)
    async def interview_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Вызвать на обзвон"""
        # НЕ деактивируем кнопки - они должны оставаться активными
        # Обрабатываем обзвон
        await self.process_interview(interaction)
    
    @discord.ui.button(label="❌ ОТКЛОНИТЬ", style=discord.ButtonStyle.danger, row=1)
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Отклонить заявку (открывает модалку с причиной)"""
        await interaction.response.send_modal(RejectReasonModal(self.application_id))
    
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
        
        # Логируем в канал
        log_channel_id = CONFIG.get('applications_log_channel')
        if log_channel_id:
            log_channel = interaction.client.get_channel(int(log_channel_id))
            if log_channel:
                embed = discord.Embed(
                    title="✅ ЗАЯВКА ПРИНЯТА",
                    description=f"Заявка от <@{app['user_id']}> принята",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                embed.add_field(name="👤 Модератор", value=interaction.user.mention, inline=True)
                await log_channel.send(embed=embed)
        
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
        
        # ===== НОВЫЙ КОД: СОЗДАЁМ ПРИВАТНЫЙ КАНАЛ =====
        guild = interaction.guild
        member = guild.get_member(int(app['user_id']))
        mod = interaction.user
        
        if not member:
            await interaction.response.send_message("❌ Пользователь не найден на сервере", ephemeral=True)
            return
        
        # Получаем роль рекрута
        recruit_role_id = CONFIG.get('applications_recruit_role')
        recruit_role = guild.get_role(int(recruit_role_id)) if recruit_role_id else None
        
        # Создаём категорию для заявок (если нет)
        category_name = "📝 ЗАЯВКИ"
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
        
        # Создаём приватный канал
        channel_name = f"заявка-{member.display_name[:20]}"
        
        # Права доступа
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            mod: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Добавляем роль рекрута
        if recruit_role:
            overwrites[recruit_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # Создаём канал
        interview_channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Обзвон заявки от {member.display_name} | ID: {self.application_id}"
        )
        
        # ===== ОТПРАВКА ЛС =====
        try:
            user = await interaction.client.fetch_user(int(app['user_id']))
            if user:
                embed = discord.Embed(
                    title="📞 ВЫЗОВ НА ОБЗВОН",
                    description=f"Вас готовы выслушать в голосовом канале!",
                    color=0xffa500
                )
                embed.add_field(
                    name="📝 Приватный чат",
                    value=f"Создан канал {interview_channel.mention} для обсуждения",
                    inline=False
                )
                await user.send(embed=embed)
        except:
            pass
        
        # ===== ОТПРАВКА В ПРИВАТНЫЙ КАНАЛ =====
        embed = discord.Embed(
            title="📞 ВЫЗОВ НА ОБЗВОН",
            description=f"Заявка от {member.mention}",
            color=0xffa500,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Модератор", value=mod.mention, inline=True)
        embed.add_field(name="🎮 Игровой ник", value=app['nickname'], inline=True)
        embed.add_field(name="🎯 Статик", value=app['static'], inline=True)
        embed.add_field(name="⏰ Прайм-тайм", value=app['prime_time'], inline=True)
        embed.add_field(name="📊 Часов в день", value=app['hours_per_day'], inline=True)
        
        if app['previous_families'] and app['previous_families'] != "Не указано":
            embed.add_field(name="🏠 Предыдущие семьи", value=app['previous_families'], inline=False)
        
        await interview_channel.send(content=f"{mod.mention} {member.mention}", embed=embed)
        
        # ===== ОТПРАВКА В ОСНОВНОЙ ЧАТ =====
        channel = interaction.channel
        embed = discord.Embed(
            title="📞 ВЫЗОВ НА ОБЗВОН",
            description=f"Пользователь {member.mention} вызван на обзвон",
            color=0xffa500
        )
        embed.add_field(name="📝 Канал", value=interview_channel.mention, inline=False)
        
        recruit_mention = recruit_role.mention if recruit_role else "@everyone"
        await channel.send(content=recruit_mention, embed=embed)
        
        # ===== НЕ ОБНОВЛЯЕМ СООБЩЕНИЕ - КНОПКИ ОСТАЮТСЯ =====
        await interaction.response.send_message(
            f"📞 Вызов на обзвон создан в канале {interview_channel.mention}",
            ephemeral=True
        )


class RejectReasonModal(discord.ui.Modal, title="❌ ПРИЧИНА ОТКАЗА"):
    """Модалка для ввода причины отказа"""
    
    reason = discord.ui.TextInput(
        label="Причина отказа",
        placeholder="Опишите причину отказа",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )
    
    def __init__(self, application_id: int):
        super().__init__()
        self.application_id = application_id
    
    async def on_submit(self, interaction: discord.Interaction):
        from applications.manager import app_manager
        from core.config import CONFIG
        
        # Делаем кнопки в исходном сообщении неактивными
        message = interaction.message
        if message and message.embeds:
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
                
                # Логируем в канал
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
                        embed.add_field(name="👤 Модератор", value=interaction.user.mention, inline=True)
                        embed.add_field(name="📝 Причина", value=self.reason.value, inline=False)
                        await log_channel.send(embed=embed)
            
            # Обновляем сообщение
            embed = message.embeds[0]
            embed.color = 0xff0000
            embed.add_field(name="❌ Статус", value=f"Отклонена модератором {interaction.user.mention}", inline=False)
            embed.add_field(name="📝 Причина", value=self.reason.value, inline=False)
            
            # Деактивируем все кнопки в исходном сообщении
            await message.edit(embed=embed, view=None)
            await interaction.response.send_message("❌ Заявка отклонена", ephemeral=True)