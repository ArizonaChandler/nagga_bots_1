"""Команда !info - главное меню с кнопками"""
import discord
from core.database import db
from core.utils import has_access
from admin.views import MainView

def setup(bot):
    @bot.command(name='info')
    async def info(ctx):
        user_id = str(ctx.author.id)
        
        if not await has_access(user_id):
            db.log_action(user_id, "INFO_DENIED")
            return
        
        db.update_last_used(user_id)
        
        embed = discord.Embed(
            title="🤖 **UNIT MANAGEMENT SYSTEM**",
            color=0x7289da
        )
        embed.set_footer(text="Выберите действие")
        
        view = MainView(user_id, ctx.guild)
        
        if ctx.guild is None:
            await ctx.author.send(embed=embed, view=view)
        else:
            await ctx.channel.send(embed=embed, view=view)
        
        db.log_action(user_id, "INFO_SENT", "Успешно")