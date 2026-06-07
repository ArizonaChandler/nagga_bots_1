"""Обработчики событий (голосовой онлайн)"""
import discord
from economy.manager import economy_manager


async def setup_economy_events(bot):
    
    @bot.event
    async def on_voice_state_update(member: discord.Member, before, after):
        """Начисление за голосовой онлайн"""
        await economy_manager.process_voice_update(member, before, after)