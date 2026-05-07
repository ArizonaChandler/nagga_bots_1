"""Кнопки для системы отпусков"""
import discord
from datetime import datetime
import pytz
from vacation.base import PermanentView
from vacation.modals import VacationModal
from vacation.manager import vacation_manager
from core.config import CONFIG

MSK_TZ = pytz.timezone('Europe/Moscow')


async def update_vacation_embed(bot, channel_id: str):
    """Обновить embed со списком отпускников"""
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return
    
    vacations = vacation_manager.get_all_vacations()
    
    # Ищем существующее сообщение
    target_message = None
    async for msg in channel.history(limit=50):
        if msg.author == bot.user and msg.embeds:
            if msg.embeds and "🏖️ СИСТЕМА ОТПУСКОВ" in msg.embeds[0].title:
                target_message = msg
                break
    
    if not target_message:
        embed = discord.Embed(
            title="🏖️ **СИСТЕМА ОТПУСКОВ**",
            description="✨ Никого нет в отпуске",
            color=0x00ff00
        )
        embed.set_footer(text="Нажмите кнопку, чтобы подать заявку")
        await channel.send(embed=embed, view=VacationPublicView())
        return
    
    if not vacations:
        embed = discord.Embed(
            title="🏖️ **СИСТЕМА ОТПУСКОВ**",
            description="✨ Никого нет в отпуске",
            color=0x00ff00
        )
    else:
        description = ""
        for vac in vacations:
            until = datetime.fromisoformat(vac['until_date'])
            until_str = until.strftime("%d.%m.%Y")
            days_left = (until - datetime.now(MSK_TZ)).days
            description += f"👤 <@{vac['user_id']}>\n"
            description += f"└ 📝 {vac['reason']}\n"
            description += f"└ 📅 до {until_str} (осталось {days_left} д.)\n\n"
        
        embed = discord.Embed(
            title="🏖️ **СИСТЕМА ОТПУСКОВ**",
            description=description,
            color=0xffa500
        )
    
    embed.set_footer(text="Нажмите кнопку, чтобы подать заявку")
    await target_message.edit(embed=embed)


class VacationPublicView(PermanentView):
    """Публичные кнопки для отпуска"""
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(
        label="🏖️ УЙТИ В ОТПУСК", 
        style=discord.ButtonStyle.primary,
        emoji="🏖️",
        custom_id="vacation_go"
    )
    async def go_vacation(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Подать заявку на отпуск"""
        await interaction.response.send_modal(VacationModal())
    
    @discord.ui.button(
        label="✅ ВЕРНУТЬСЯ", 
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="vacation_back"
    )
    async def back_vacation(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Вернуться из отпуска"""
        success, msg = await vacation_manager.return_from_vacation(
            str(interaction.user.id),
            interaction.client
        )
        
        if success:
            # Обновляем embed
            settings = vacation_manager.get_settings()
            await update_vacation_embed(interaction.client, settings.get('vacation_public_channel'))
        
        await interaction.response.send_message(msg, ephemeral=True)


class VacationModerationView(discord.ui.View):
    """Кнопки для модерации заявки на отпуск"""
    
    def __init__(self, application_id: int):
        super().__init__(timeout=None)
        self.application_id = application_id
    
    @discord.ui.button(label="✅ ПРИНЯТЬ", style=discord.ButtonStyle.success, row=0)
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Принять заявку"""
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        await self.process_approve(interaction)
    
    @discord.ui.button(label="❌ ОТКЛОНИТЬ", style=discord.ButtonStyle.danger, row=0)
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Отклонить заявку"""
        await interaction.response.send_modal(VacationRejectReasonModal(self.application_id))
    
    async def process_approve(self, interaction: discord.Interaction):
        """Обработка принятия заявки"""
        await interaction.response.defer(ephemeral=True)
        
        app = vacation_manager.get_application(self.application_id)
        if not app:
            await interaction.followup.send("❌ Заявка не найдена", ephemeral=True)
            return
        
        success = vacation_manager.approve_application(self.application_id, str(interaction.user.id))
        
        if not success:
            await interaction.followup.send("❌ Не удалось принять заявку", ephemeral=True)
            return
        
        # Выдаём роль отпуска и снимаем другие роли
        guild = interaction.guild
        member = guild.get_member(int(app['user_id']))
        
        vacation_role_id = CONFIG.get('vacation_role')
        if vacation_role_id and member:
            vacation_role = guild.get_role(int(vacation_role_id))
            if vacation_role:
                # Снимаем все роли
                roles_to_remove = [r for r in member.roles if not r.is_default()]
                for role in roles_to_remove:
                    await member.remove_roles(role)
                # Выдаём роль отпуска
                await member.add_roles(vacation_role)
        
        # Логируем
        log_channel_id = CONFIG.get('vacation_log_channel')
        if log_channel_id:
            log_channel = interaction.client.get_channel(int(log_channel_id))
            if log_channel:
                embed = discord.Embed(
                    title="✅ ЗАЯВКА ОДОБРЕНА",
                    description=f"Пользователь <@{app['user_id']}> ушёл в отпуск до {app['until_date']}",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                embed.add_field(name="👤 Модератор", value=interaction.user.mention)
                embed.add_field(name="📝 Причина", value=app['reason'])
                await log_channel.send(embed=embed)
        
        # Обновляем embed
        settings = vacation_manager.get_settings()
        await update_vacation_embed(interaction.client, settings.get('vacation_public_channel'))
        
        # Обновляем сообщение
        embed = interaction.message.embeds[0]
        embed.color = 0x00ff00
        embed.add_field(name="✅ Статус", value=f"Одобрена модератором {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=self)
        
        # Удаляем запись
        vacation_manager.delete_application_message(self.application_id)
        
        await interaction.followup.send("✅ Заявка одобрена", ephemeral=True)


class VacationRejectReasonModal(discord.ui.Modal, title="❌ ПРИЧИНА ОТКАЗА"):
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
        await interaction.response.defer(ephemeral=True)
        
        success = vacation_manager.reject_application(
            self.application_id,
            str(interaction.user.id),
            self.reason.value
        )
        
        if not success:
            await interaction.followup.send("❌ Не удалось отклонить заявку", ephemeral=True)
            return
        
        app = vacation_manager.get_application(self.application_id)
        
        if app:
            # Логируем
            log_channel_id = CONFIG.get('vacation_log_channel')
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
        message = interaction.message
        embed = message.embeds[0]
        embed.color = 0xff0000
        embed.add_field(name="❌ Статус", value=f"Отклонена модератором {interaction.user.mention}", inline=False)
        embed.add_field(name="📝 Причина", value=self.reason.value, inline=False)
        
        for child in message.components[0].children:
            child.disabled = True
        
        await message.edit(embed=embed, view=None)
        vacation_manager.delete_application_message(self.application_id)
        
        await interaction.followup.send("❌ Заявка отклонена", ephemeral=True)