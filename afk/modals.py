"""Модалки для системы AFK"""
import discord
import logging
from afk.manager import afk_manager
from core.config import CONFIG

logger = logging.getLogger(__name__)


class AFKModal(discord.ui.Modal, title="🛌 УХОД В AFK"):
    """Модалка для ухода в AFK"""
    
    reason = discord.ui.TextInput(
        label="📝 Причина ухода",
        placeholder="Например: Обед, Сон, Работа",
        max_length=200,
        required=True,
        style=discord.TextStyle.short
    )
    
    hours = discord.ui.TextInput(
        label="⏰ На сколько часов",
        placeholder="Введите число",
        max_length=3,
        required=True
    )
    
    def __init__(self, bot, channel_id: str, max_hours: int):
        super().__init__()
        self.bot = bot
        self.channel_id = channel_id
        # Обновляем placeholder с максимальным значением
        self.hours.placeholder = f"Введите число (макс. {max_hours})"
    
    async def on_submit(self, interaction: discord.Interaction):
        from afk.views import update_afk_embed
        from afk.views import AFKPublicView
        
        try:
            max_hours = CONFIG.get('afk_max_hours', 24)
            if isinstance(max_hours, str):
                max_hours = int(max_hours)
            
            # Проверяем формат часов
            try:
                hours_num = int(self.hours.value)
                if hours_num <= 0:
                    await interaction.response.send_message("❌ Количество часов должно быть больше 0", ephemeral=True)
                    return
                if hours_num > max_hours:
                    await interaction.response.send_message(f"❌ Максимальное время AFK: {max_hours} часов", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ Введите число часов", ephemeral=True)
                return
            
            # Проверяем, не в AFK ли уже
            existing = afk_manager.get_afk_user(str(interaction.user.id))
            if existing:
                await interaction.response.send_message("❌ Вы уже в AFK. Нажмите 'Вернулся', чтобы выйти.", ephemeral=True)
                return
            
            # Добавляем в AFK
            success, msg = afk_manager.add_afk_user(
                str(interaction.user.id),
                interaction.user.display_name,
                self.reason.value,
                hours_num
            )
            
            await interaction.response.send_message(msg, ephemeral=True)
            
            # Обновляем embed
            if success:
                await update_afk_embed(self.bot, self.channel_id)
                
                # Логируем
                view = AFKPublicView(self.bot, self.channel_id, max_hours)
                details = f"Причина: {self.reason.value} | Часов: {hours_num}"
                await view.log_action(interaction, "УХОД В AFK", details)
                
        except Exception as e:
            logger.error(f"❌ Ошибка в AFKModal: {e}", exc_info=True)
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)