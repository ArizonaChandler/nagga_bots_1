"""Базовые классы для админских панелей настроек"""
import discord
import traceback
from core.utils import is_admin
from core.database import db


class AdminOnlyView(discord.ui.View):
    """Базовый класс для всех панелей настроек — только для админов бота"""
    
    def __init__(self, timeout=None):
        # По умолчанию timeout=None — бесконечный
        super().__init__(timeout=timeout)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        error_msg = f"❌ Ошибка: {type(error).__name__}: {error}"
        print(f"🔴 [ADMIN BUTTON ERROR] {error_msg}")
        print(traceback.format_exc())
        
        db.log_action(
            str(interaction.user.id),
            "ADMIN_BUTTON_ERROR",
            f"Кнопка: {item.custom_id if hasattr(item, 'custom_id') else 'unknown'} | Ошибка: {type(error).__name__}: {error}"
        )
        
        try:
            await interaction.response.send_message(error_msg, ephemeral=True)
        except:
            await interaction.followup.send(error_msg, ephemeral=True)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message(
                "❌ **Доступ запрещён**\nТолько администраторы, добавленные в базу данных, могут управлять настройками бота.",
                ephemeral=True
            )
            return False
        
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
        try:
            if not await is_admin(str(interaction.user.id)):
                await interaction.response.send_message(
                    "❌ **Доступ запрещён**\nТолько администраторы могут изменять настройки.",
                    ephemeral=True
                )
                return
            
            modal_title = self.title if hasattr(self, 'title') else "Unknown"
            db.log_action(
                str(interaction.user.id),
                "ADMIN_MODAL_SUBMIT",
                f"Модалка: {modal_title}"
            )
            
            await self.on_submit_admin(interaction)
        except Exception as e:
            print(f"🔴 [MODAL ERROR] {e}")
            traceback.print_exc()
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)
    
    async def on_submit_admin(self, interaction: discord.Interaction):
        pass