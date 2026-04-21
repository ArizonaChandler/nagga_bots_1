"""Кнопки для системы AFK"""
import discord
from datetime import datetime
from afk.base import PermanentView
from afk.modals import AFKModal
from afk.manager import afk_manager


async def update_afk_embed(bot, channel_id: str):
    """Обновить embed со списком AFK пользователей (отдельная функция)"""
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return
    
    users = afk_manager.get_all_afk_users()
    
    if not users:
        embed = discord.Embed(
            title="🛌 **СИСТЕМА AFK**",
            description="✨ Никого нет в AFK",
            color=0xffa500
        )
        embed.set_footer(text="Нажмите кнопку, чтобы уйти в AFK")
    else:
        description = ""
        for user in users:
            until = datetime.fromisoformat(user['until_time'])
            until_str = until.strftime("%d.%m.%Y %H:%M")
            description += f"👤 <@{user['user_id']}>\n"
            description += f"📝 {user['reason']}\n"
            description += f"⏰ Вернётся: **{until_str}** МСК\n"
            description += "─" * 30 + "\n"
        
        embed = discord.Embed(
            title="🛌 **СИСТЕМА AFK**",
            description=description,
            color=0xffa500
        )
        embed.set_footer(text="Нажмите кнопку, чтобы уйти в AFK")
    
    # Ищем и обновляем сообщение
    async for msg in channel.history(limit=20):
        if msg.author == bot.user and msg.embeds:
            if msg.embeds and "СИСТЕМА AFK" in msg.embeds[0].title:
                await msg.edit(embed=embed)
                return


class AFKPublicView(PermanentView):
    """Публичные кнопки для AFK"""
    
    def __init__(self, bot, channel_id: str):
        super().__init__()
        self.bot = bot
        self.channel_id = channel_id
    
    @discord.ui.button(
        label="🛌 УЙТИ В AFK", 
        style=discord.ButtonStyle.primary,
        emoji="🛌",
        custom_id="afk_go"
    )
    async def go_afk(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Открыть модалку ухода в AFK"""
        await interaction.response.send_modal(AFKModal(self.bot, self.channel_id))
    
    @discord.ui.button(
        label="✅ ВЕРНУЛСЯ", 
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="afk_back"
    )
    async def back_afk(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Вернуться из AFK"""
        success, msg = afk_manager.remove_afk_user(str(interaction.user.id))
        await interaction.response.send_message(msg, ephemeral=True)
        
        # Обновляем embed
        await update_afk_embed(self.bot, self.channel_id)