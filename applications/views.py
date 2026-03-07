"""Кнопки для пользователей"""
import discord
from applications.base import PermanentView
from applications.modals import ApplicationModal
from applications.manager import app_manager
from datetime import datetime
from core.config import CONFIG

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
        
        # Делаем кнопки неактивными сразу
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        
        # Обрабатываем обзвон
        await self.process_interview(interaction)
    
    @discord.ui.button(label="❌ ОТКЛОНИТЬ", style=discord.ButtonStyle.danger, row=1)
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Отклонить заявку (открывает модалку с причиной)"""
        await interaction.response.send_modal(RejectReasonModal(self.application_id))
    
    async def process_accept(self, interaction: discord.Interaction):
        """Обработка принятия заявки"""
        from core.config import CONFIG
        
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
        from core.config import CONFIG
        
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
        
        # Отправляем ЛС пользователю
        try:
            user = await interaction.client.fetch_user(int(app['user_id']))
            if user:
                embed = discord.Embed(
                    title="📞 ВЫЗОВ НА ОБЗВОН",
                    description=f"Вас готовы выслушать в голосовом канале!",
                    color=0xffa500
                )
                await user.send(embed=embed)
        except:
            pass
        
        # Отправляем сообщение в сервер с упоминанием
        guild = interaction.guild
        recruit_role_id = CONFIG.get('applications_recruit_role')
        recruit_mention = f"<@&{recruit_role_id}>" if recruit_role_id else "@everyone"
        
        channel = interaction.channel
        embed = discord.Embed(
            title="📞 ВЫЗОВ НА ОБЗВОН",
            description=f"Пользователь <@{app['user_id']}> вызван на обзвон",
            color=0xffa500
        )
        await channel.send(content=recruit_mention, embed=embed)
        
        # Создаем приватный чат (опционально)
        # ...
        
        # Обновляем сообщение
        embed = interaction.message.embeds[0]
        embed.color = 0xffa500
        embed.add_field(name="📞 Статус", value=f"Вызван на обзвон модератором {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("📞 Вызов на обзвон отправлен", ephemeral=True)


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
            for child in self.children:
                child.disabled = True
            
            await message.edit(embed=embed, view=None)
            await interaction.response.send_message("❌ Заявка отклонена", ephemeral=True)