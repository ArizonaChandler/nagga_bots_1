"""Команда !stats - статистика системы"""
import discord
from datetime import datetime
from core.database import db
from core.utils import is_admin
from mcl.core import dual_mcl_core
from capt.core import capt_core

def setup(bot):
    @bot.command(name='stats')
    async def stats(ctx):
        user_id = str(ctx.author.id)
        
        if not await is_admin(user_id):
            return
        
        embed = discord.Embed(
            title="📊 **СТАТИСТИКА СИСТЕМЫ**",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        mcl_stats = dual_mcl_core.stats
        mcl_text = f"✅ Успешно: `{mcl_stats[1]['success'] + mcl_stats[2]['success']}`\n"
        mcl_text += f"📨 Попыток: `{mcl_stats[1]['total_attempts'] + mcl_stats[2]['total_attempts']}`\n"
        mcl_text += f"🎨 Токен 1: `{dual_mcl_core.token_colors[1]}` ({mcl_stats[1]['success']})\n"
        mcl_text += f"🎨 Токен 2: `{dual_mcl_core.token_colors[2]}` ({mcl_stats[2]['success']})"
        
        embed.add_field(name="🎨 DUAL MCL", value=mcl_text, inline=True)
        
        capt_text = f"✅ Отправлено: `{capt_core.stats['total_sent']}`\n"
        capt_text += f"❌ Ошибок: `{capt_core.stats['total_failed']}`\n"
        if capt_core.stats['total_time'] > 0:
            avg_speed = int(capt_core.stats['total_sent'] / capt_core.stats['total_time'])
            capt_text += f"⚡ Средняя скорость: `{avg_speed}/сек`"
        else:
            capt_text += f"⚡ Скорость: `0/сек`"
        
        embed.add_field(name="🚨 CAPT", value=capt_text, inline=True)
        
        users = db.get_users()
        admins = [uid for uid in users if db.is_admin(uid)]
        embed.add_field(
            name="👥 ПОЛЬЗОВАТЕЛИ",
            value=f"Всего: `{len(users)}`\nАдминов: `{len(admins)}`",
            inline=True
        )
        
        await ctx.send(embed=embed)