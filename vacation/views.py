"""Кнопки для системы отпусков"""
import discord
import traceback
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
            if msg.embeds and "🏖️ **СИСТЕМА ОТПУСКОВ**" in msg.embeds[0].title:
                target_message = msg
                break
    
    if not target_message:
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
            # Преобразуем строку в datetime с часовым поясом
            until = datetime.fromisoformat(vac['until_date'])
            until = MSK_TZ.localize(until)
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
        print(f"🔍 Нажата кнопка 'Вернуться' от {interaction.user}")
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            success, msg = await vacation_manager.return_from_vacation(
                str(interaction.user.id),
                interaction.client
            )
            
            if success:
                settings = vacation_manager.get_settings()
                public_channel_id = settings.get('vacation_public_channel')
                if public_channel_id:
                    await update_vacation_embed(interaction.client, public_channel_id)
            
            await interaction.followup.send(msg, ephemeral=True)
            
        except Exception as e:
            print(f"❌ Ошибка при возврате из отпуска: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)


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
        
        # Отправляем ЛС пользователю об одобрении
        try:
            user = await interaction.client.fetch_user(int(app['user_id']))
            if user:
                embed = discord.Embed(
                    title="✅ ЗАЯВКА НА ОТПУСК ОДОБРЕНА",
                    description=f"Ваша заявка на отпуск одобрена!\n\n"
                                f"📅 Дней: {app['days']}\n"
                                f"📝 Причина: {app['reason']}\n"
                                f"📅 Дата возврата: {app['until_date']}",
                    color=0x00ff00
                )
                await user.send(embed=embed)
                print(f"✅ ЛС отправлено пользователю {app['user_id']}")
        except Exception as e:
            print(f"❌ Ошибка отправки ЛС: {e}")
        
        # Выдаём роль отпуска и снимаем другие роли
        guild = interaction.guild
        member = guild.get_member(int(app['user_id']))
        
        vacation_role_id = CONFIG.get('vacation_role')
        print(f"🎭 Роль отпуска ID: {vacation_role_id}")
        
        if vacation_role_id and member:
            vacation_role = guild.get_role(int(vacation_role_id))
            if vacation_role:
                # Снимаем все роли (кроме @everyone)
                roles_to_remove = [r for r in member.roles if not r.is_default()]
                print(f"👥 Снимаем роли: {[r.name for r in roles_to_remove]}")
                for role in roles_to_remove:
                    await member.remove_roles(role)
                await member.add_roles(vacation_role)
                print(f"✅ Выдана роль отпуска: {vacation_role.name}")
            else:
                print(f"❌ Роль отпуска с ID {vacation_role_id} не найдена")
        else:
            print(f"❌ vacation_role_id={vacation_role_id}, member={member}")
        
        # Логируем в канал логов
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
        
        # Обновляем embed в публичном канале
        settings = vacation_manager.get_settings()
        public_channel_id = settings.get('vacation_public_channel')
        if public_channel_id:
            await update_vacation_embed(interaction.client, public_channel_id)
        
        # Обновляем сообщение с заявкой (делаем неактивным)
        embed = interaction.message.embeds[0]
        embed.color = 0x00ff00
        embed.add_field(name="✅ Статус", value=f"Одобрена модератором {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=None)  # убираем кнопки
        
        # Удаляем запись о сообщении
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
            # Отправляем ЛС пользователю об отказе
            try:
                user = await interaction.client.fetch_user(int(app['user_id']))
                if user:
                    embed = discord.Embed(
                        title="❌ ЗАЯВКА НА ОТПУСК ОТКЛОНЕНА",
                        description=f"Ваша заявка на отпуск отклонена.\n\n**Причина:** {self.reason.value}",
                        color=0xff0000
                    )
                    await user.send(embed=embed)
                    print(f"✅ ЛС отправлено пользователю {app['user_id']}")
            except Exception as e:
                print(f"❌ Ошибка отправки ЛС: {e}")
            
            # Логируем в канал логов
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
        
        # Обновляем сообщение с заявкой (делаем неактивным)
        message = interaction.message
        embed = message.embeds[0]
        embed.color = 0xff0000
        embed.add_field(name="❌ Статус", value=f"Отклонена модератором {interaction.user.mention}", inline=False)
        embed.add_field(name="📝 Причина", value=self.reason.value, inline=False)
        
        # Убираем кнопки
        await message.edit(embed=embed, view=None)
        
        # Удаляем запись о сообщении
        vacation_manager.delete_application_message(self.application_id)
        
        await interaction.followup.send("❌ Заявка отклонена", ephemeral=True)