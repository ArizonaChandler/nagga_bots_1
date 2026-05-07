"""Модалки для системы отпусков"""
import discord
from vacation.manager import vacation_manager
from core.config import CONFIG


class VacationModal(discord.ui.Modal, title="🏖️ ЗАЯВКА НА ОТПУСК"):
    """Модалка для подачи заявки на отпуск"""
    
    days = discord.ui.TextInput(
        label="📅 Количество дней",
        placeholder="Введите число дней",
        max_length=3,
        required=True
    )
    
    reason = discord.ui.TextInput(
        label="📝 Причина отпуска",
        placeholder="Укажите причину",
        max_length=500,
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        from vacation.views import VacationModerationView
        
        max_days = CONFIG.get('vacation_max_days', 30)
        user_id = str(interaction.user.id)
        
        # Проверяем формат дней
        try:
            days_num = int(self.days.value)
            if days_num <= 0:
                await interaction.response.send_message("❌ Количество дней должно быть больше 0", ephemeral=True)
                return
            if days_num > max_days:
                await interaction.response.send_message(f"❌ Максимальное количество дней: {max_days}", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите число", ephemeral=True)
            return
        
        # Проверяем, не в отпуске ли уже
        existing = vacation_manager.get_user_vacation(user_id)
        if existing:
            await interaction.response.send_message("❌ Вы уже в отпуске", ephemeral=True)
            return
        
        # Сохраняем текущие роли пользователя
        member = interaction.guild.get_member(interaction.user.id)
        saved_roles = [str(role.id) for role in member.roles if not role.is_default()]
        
        # Создаём заявку
        app_id, error = vacation_manager.create_application(
            user_id=user_id,
            user_name=interaction.user.display_name,
            days=days_num,
            reason=self.reason.value,
            roles=saved_roles
        )
        
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return
        
        # Отправляем подтверждение
        embed = discord.Embed(
            title="✅ ЗАЯВКА ОТПРАВЛЕНА",
            description="Ваша заявка на отпуск передана на рассмотрение",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Отправляем заявку в канал модерации
        settings = vacation_manager.get_settings()
        applications_channel_id = settings.get('vacation_applications_channel')
        
        if applications_channel_id:
            channel = interaction.client.get_channel(int(applications_channel_id))
            if channel:
                # Получаем роли для упоминания
                approve_roles = settings.get('vacation_approve_roles', [])
                mentions = " ".join([f"<@&{r}>" for r in approve_roles]) if approve_roles else ""
                
                embed = discord.Embed(
                    title="🏖️ ЗАЯВКА НА ОТПУСК",
                    color=0xffa500,
                    timestamp=datetime.now()
                )
                embed.add_field(name="👤 Игрок", value=interaction.user.mention, inline=True)
                embed.add_field(name="📅 Дней", value=f"{days_num}", inline=True)
                embed.add_field(name="📝 Причина", value=self.reason.value, inline=False)
                embed.set_footer(text=f"Заявка ID: {app_id}")
                
                sent_message = await channel.send(
                    content=mentions,
                    embed=embed,
                    view=VacationModerationView(app_id)
                )
                
                # Сохраняем ID сообщения
                vacation_manager.save_application_message(
                    application_id=app_id,
                    channel_id=str(channel.id),
                    message_id=str(sent_message.id),
                    user_id=user_id
                )
                print(f"✅ Заявка на отпуск #{app_id} отправлена")