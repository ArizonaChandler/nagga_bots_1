"""Базовые классы для админских панелей настроек"""
import discord
from core.utils import is_admin
from core.database import db


class AdminOnlyView(discord.ui.View):
    """Базовый класс для всех панелей настроек — только для админов бота"""
    
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Проверка: только администраторы бота могут нажимать кнопки"""
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message(
                "❌ **Доступ запрещён**\n"
                "Только администраторы, добавленные в базу данных, могут управлять настройками бота.\n\n"
                "Если вы считаете, что это ошибка, обратитесь к супер-администратору.",
                ephemeral=True
            )
            return False
        
        # Логируем действие администратора
        custom_id = interaction.data.get('custom_id', 'unknown')
        channel_name = interaction.channel.name if interaction.channel else "ЛС"
        
        db.log_action(
            str(interaction.user.id), 
            "ADMIN_PANEL_CLICK", 
            f"Кнопка: {custom_id} | Канал: #{channel_name}"
        )
        
        return True


class AdminOnlyModal(discord.ui.Modal):
    """Базовый класс для модалок настроек — только для админов бота"""
    
    async def on_submit(self, interaction: discord.Interaction):
        """Проверка перед обработкой"""
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message(
                "❌ **Доступ запрещён**\n"
                "Только администраторы могут изменять настройки.",
                ephemeral=True
            )
            return
        
        # Логируем действие
        modal_title = self.title if hasattr(self, 'title') else "Unknown"
        db.log_action(
            str(interaction.user.id),
            "ADMIN_MODAL_SUBMIT",
            f"Модалка: {modal_title}"
        )
        
        # Вызываем реальную обработку
        await self.on_submit_admin(interaction)
    
    async def on_submit_admin(self, interaction: discord.Interaction):
        """Переопределяемый метод для реальной логики"""
        pass