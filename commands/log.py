"""Команда !log - просмотр логов (супер-админ, только ЛС)"""
import discord
from datetime import datetime
from core.database import db
from core.utils import format_mention, is_super_admin

def setup(bot):
    @bot.command(name='log')  # ✅ ИСПРАВЛЕНО: теперь 'log', а не 'info'
    async def log(ctx):
        user_id = str(ctx.author.id)
        
        if ctx.guild is not None:
            return
        
        if not await is_super_admin(user_id):
            return
        
        logs = db.get_recent_logs(20)
        if not logs:
            await ctx.author.send("📋 **Логи отсутствуют**")
            return
        
        embed = discord.Embed(
            title="📋 **ПОСЛЕДНИЕ ДЕЙСТВИЯ**",
            color=0x7289da,
            timestamp=datetime.now()
        )
        
        lines = []
        for ts, uid, act, det in logs:
            time_str = ts.split('.')[0][-8:] if '.' in ts else ts[-8:]
            user = format_mention(ctx.guild, uid, 'user')
            line = f"`[{time_str}]` {user} → **{act}**"
            if det:
                line += f" *({det})*"
            lines.append(line)
        
        embed.description = "\n".join(lines)
        embed.set_footer(text=f"Всего записей: {len(logs)}")
        
        await ctx.author.send(embed=embed)