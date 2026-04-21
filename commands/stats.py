"""Команда !stats - статистика системы"""
import discord
from datetime import datetime
from core.database import db
from core.utils import is_admin
from capt_registration.capt_core import capt_core
from core.config import CONFIG

def setup(bot):
    @bot.command(name='stats')
    async def stats(ctx):
        user_id = str(ctx.author.id)
        
        if not await is_admin(user_id):
            return
        
        embed = discord.Embed(
            title=f"📊 **СТАТИСТИКА {CONFIG.get('family_name', 'СЕМЬИ')}**",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
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
        
        events_today = len(db.get_today_events())
        events_total = len(db.get_events(enabled_only=False))
        takes_30d = len(db.get_event_takes(days=30))

        embed.add_field(
            name="📅 МЕРОПРИЯТИЯ",
            value=f"Сегодня: `{events_today}`\n"
                f"Всего: `{events_total}`\n"
                f"Проведено (30д): `{takes_30d}`",
            inline=True
        )

        await ctx.send(embed=embed)