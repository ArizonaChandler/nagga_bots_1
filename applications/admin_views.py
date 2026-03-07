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