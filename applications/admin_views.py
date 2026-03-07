"""Панель модерации заявок (постоянные кнопки)"""
import discord
from applications.base import PermanentView
from applications.manager import app_manager
from datetime import datetime

class ApplicationsModerationPanel(PermanentView):
    """Панель модерации заявок"""
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(
        label="📋 Ожидающие заявки", 
        style=discord.ButtonStyle.primary,
        emoji="📋",
        row=0,
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
        row=1,
        custom_id="apps_reset_user"
    )
    async def reset_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Сбросить все заявки пользователя"""
        await interaction.response.send_modal(ResetUserModal())


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
        if self.confirm.value != "СБРОС":
            await interaction.response.send_message("❌ Неверное подтверждение", ephemeral=True)
            return
        
        # Проверяем, что ID состоит из цифр
        if not self.user_id.value.isdigit():
            await interaction.response.send_message("❌ ID должен содержать только цифры", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        success, message = app_manager.reset_user_applications(
            self.user_id.value, 
            str(interaction.user.id)
        )
        
        await interaction.followup.send(message, ephemeral=True)