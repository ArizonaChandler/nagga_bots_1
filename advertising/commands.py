"""Auto Advertising Commands - Настройка через ЛС"""
import discord
import os
from datetime import datetime, timedelta
from core.database import db
from core.utils import is_super_admin
from core.config import CONFIG

AD_TEXT_FILE = "/home/discordbot/discord-bot/ad_text.txt"
AD_CHANNEL_FILE = "/home/discordbot/discord-bot/ad_channel.txt"

def setup(bot):
    
    @bot.command(name='ad_text')
    async def set_ad_text(ctx):
        """Установить текст рекламы (только ЛС, супер-админ)"""
        if ctx.guild is not None:
            return
        
        if not await is_super_admin(str(ctx.author.id)):
            return
        
        await ctx.author.send("📝 Отправь мне текст рекламы одним сообщением. Я сохраню его в файл.")
        
        def check(m):
            return m.author.id == ctx.author.id and isinstance(m.channel, discord.DMChannel)
        
        try:
            msg = await bot.wait_for('message', timeout=120.0, check=check)
            
            with open(AD_TEXT_FILE, 'w', encoding='utf-8') as f:
                f.write(msg.content)
            
            embed = discord.Embed(
                title="✅ Текст рекламы сохранен",
                description=f"```\n{msg.content[:500]}{'...' if len(msg.content) > 500 else ''}\n```",
                color=0x00ff00
            )
            await ctx.author.send(embed=embed)
            
        except TimeoutError:
            await ctx.author.send("⏰ Время ожидания истекло. Попробуй еще раз.")
    
    @bot.command(name='ad_channel')
    async def set_ad_channel(ctx, channel_id: str = None):
        """Установить ID канала для рекламы (только ЛС, супер-админ)"""
        if ctx.guild is not None:
            return
        
        if not await is_super_admin(str(ctx.author.id)):
            return
        
        if not channel_id:
            try:
                with open(AD_CHANNEL_FILE, 'r', encoding='utf-8') as f:
                    current = f.read().strip()
                if current:
                    await ctx.author.send(f"📢 Текущий канал: ID: `{current}`")
                else:
                    await ctx.author.send("📢 Канал не установлен. Используй `!ad_channel ID_канала`")
            except:
                await ctx.author.send("📢 Канал не установлен. Используй `!ad_channel ID_канала`")
            return
        
        # Проверка формата ID
        try:
            int(channel_id)
        except ValueError:
            await ctx.author.send("❌ Неверный формат ID канала. ID должен состоять только из цифр.")
            return
        
        # Сохраняем ID канала (без проверки, так как отправка идёт от пользовательского токена)
        try:
            with open(AD_CHANNEL_FILE, 'w', encoding='utf-8') as f:
                f.write(channel_id)
            
            await ctx.author.send(f"✅ Канал для рекламы установлен. ID: `{channel_id}`\n⚠️ Убедись, что пользовательский токен имеет доступ к этому каналу.")
            
        except Exception as e:
            await ctx.author.send(f"❌ Ошибка при сохранении: {e}")
    
    @bot.command(name='ad_show')
    async def show_ad(ctx):
        """Показать текущие настройки рекламы (только ЛС, супер-админ)"""
        if ctx.guild is not None:
            return
        
        if not await is_super_admin(str(ctx.author.id)):
            return
        
        embed = discord.Embed(
            title="📊 Настройки авто-рекламы",
            color=0x00ff00
        )
        
        # Текст рекламы
        try:
            with open(AD_TEXT_FILE, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            embed.add_field(name="📝 Текст", value=f"```\n{text[:200]}{'...' if len(text) > 200 else ''}\n```", inline=False)
        except:
            embed.add_field(name="📝 Текст", value="❌ Не установлен", inline=False)
        
        # Канал
        try:
            with open(AD_CHANNEL_FILE, 'r', encoding='utf-8') as f:
                channel_id = f.read().strip()
            if channel_id:
                embed.add_field(name="📢 Канал ID", value=f"`{channel_id}`", inline=True)
            else:
                embed.add_field(name="📢 Канал", value="❌ Не установлен", inline=True)
        except:
            embed.add_field(name="📢 Канал", value="❌ Не установлен", inline=True)
        
        # Интервал
        embed.add_field(name="⏱️ Интервал", value="65 минут", inline=True)
        
        # Статус отправки
        from advertising.core import advertiser
        if advertiser and advertiser.last_sent_time:
            last = advertiser.last_sent_time.strftime("%d.%m.%Y %H:%M")
            next_time = advertiser.last_sent_time + timedelta(minutes=65)
            next_str = next_time.strftime("%H:%M")
            embed.add_field(name="🕐 Последняя отправка", value=last, inline=True)
            embed.add_field(name="⏰ Следующая", value=f"~{next_str} МСК", inline=True)
        else:
            embed.add_field(name="🕐 Статус", value="⏳ Ожидание первой отправки", inline=False)
        
        await ctx.author.send(embed=embed)
    
    @bot.command(name='ad_send')
    async def send_ad_now(ctx):
        """Отправить рекламу сейчас (тест) (только ЛС, супер-админ)"""
        if ctx.guild is not None:
            return
        
        if not await is_super_admin(str(ctx.author.id)):
            return
        
        from advertising.core import advertiser
        if not advertiser:
            await ctx.author.send("❌ Ошибка: рекламная система не инициализирована")
            return
        
        await ctx.author.send("🔄 Отправка рекламы...")
        
        try:
            await advertiser.send_ad(datetime.now())
            await ctx.author.send("✅ Реклама отправлена!")
        except Exception as e:
            await ctx.author.send(f"❌ Ошибка: {e}")