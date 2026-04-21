"""Панель управления авто-рекламой с постоянными кнопками"""
import discord
import logging
import os
from advertising.base import PermanentView
from core.config import CONFIG, save_config
from core.database import db
from core.utils import format_mention

logger = logging.getLogger(__name__)

# Пути к файлам (как в старой системе)
AD_TEXT_FILE = "/home/discordbot/discord-bot/ad_text.txt"
AD_IMAGE_FILE = "/home/discordbot/discord-bot/ad_image.txt"
AD_CHANNEL_FILE = "/home/discordbot/discord-bot/ad_channel.txt"

class AdSettingsView(PermanentView):
    """Постоянные кнопки для настройки авто-рекламы"""
    
    def __init__(self):
        super().__init__()
        logger.debug("AdSettingsView создан")
    
    @discord.ui.button(
        label="📝 Установить текст", 
        style=discord.ButtonStyle.primary,
        emoji="📝",
        row=0,
        custom_id="ad_settings_text"
    )
    async def set_text(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Установить текст рекламы"""
        await interaction.response.send_modal(SetAdTextModal())
    
    @discord.ui.button(
        label="🖼️ Установить картинку", 
        style=discord.ButtonStyle.primary,
        emoji="🖼️",
        row=0,
        custom_id="ad_settings_image"
    )
    async def set_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Установить URL картинки"""
        await interaction.response.send_modal(SetAdImageModal())
    
    @discord.ui.button(
        label="📢 Установить канал", 
        style=discord.ButtonStyle.primary,
        emoji="📢",
        row=1,
        custom_id="ad_settings_channel"
    )
    async def set_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Установить канал для отправки"""
        await interaction.response.send_modal(SetAdChannelModal())
    
    @discord.ui.button(
        label="🚀 ЗАПУСТИТЬ СЕЙЧАС", 
        style=discord.ButtonStyle.success,
        emoji="🚀",
        row=2,
        custom_id="ad_settings_send"
    )
    async def send_ad_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Отправить рекламу сейчас"""
        logger.info(f"Нажата кнопка 'Запустить сейчас' от {interaction.user}")
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            from advertising.core import advertiser
            
            if not advertiser:
                await interaction.followup.send("❌ Ошибка: рекламная система не инициализирована", ephemeral=True)
                return
            
            # Проверяем наличие настроек
            channel_id = None
            try:
                with open(AD_CHANNEL_FILE, 'r', encoding='utf-8') as f:
                    channel_id = f.read().strip()
            except:
                pass
            
            if not channel_id:
                await interaction.followup.send(
                    "❌ Сначала настройте канал для отправки рекламы!", 
                    ephemeral=True
                )
                return
            
            await interaction.followup.send("🔄 Отправка рекламы...", ephemeral=True)
            
            from datetime import datetime
            await advertiser.send_ad(datetime.now())
            
        except Exception as e:
            logger.error(f"Ошибка при запуске рекламы: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)
    
    @discord.ui.button(
        label="📊 Текущие настройки", 
        style=discord.ButtonStyle.secondary,
        emoji="📊",
        row=3,
        custom_id="ad_settings_show"
    )
    async def show_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать текущие настройки"""
        
        embed = discord.Embed(
            title="📊 ТЕКУЩИЕ НАСТРОЙКИ АВТО-РЕКЛАМЫ",
            color=0x00ff00
        )
        
        guild = interaction.guild
        
        # Текст рекламы
        try:
            with open(AD_TEXT_FILE, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            embed.add_field(name="📝 Текст", value=f"```\n{text[:200]}{'...' if len(text) > 200 else ''}\n```", inline=False)
        except:
            embed.add_field(name="📝 Текст", value="❌ Не установлен", inline=False)
        
        # Картинка
        try:
            with open(AD_IMAGE_FILE, 'r', encoding='utf-8') as f:
                image_url = f.read().strip()
            if image_url:
                embed.add_field(name="🖼️ Картинка", value=f"[Ссылка]({image_url})", inline=True)
            else:
                embed.add_field(name="🖼️ Картинка", value="❌ Нет", inline=True)
        except:
            embed.add_field(name="🖼️ Картинка", value="❌ Нет", inline=True)
        
        # Канал
        try:
            with open(AD_CHANNEL_FILE, 'r', encoding='utf-8') as f:
                channel_id = f.read().strip()
            if channel_id:
                channel_mention = format_mention(guild, channel_id, 'channel')
                embed.add_field(name="📢 Канал", value=channel_mention, inline=True)
            else:
                embed.add_field(name="📢 Канал", value="❌ Не установлен", inline=True)
        except:
            embed.add_field(name="📢 Канал", value="❌ Не установлен", inline=True)
        
        # Интервал
        embed.add_field(name="⏱️ Интервал", value="65 минут", inline=True)
        
        # Статус отправки
        from advertising.core import advertiser
        if advertiser and advertiser.last_sent_time:
            from datetime import timedelta
            last = advertiser.last_sent_time.strftime("%d.%m.%Y %H:%M")
            next_time = advertiser.last_sent_time + timedelta(minutes=65)
            next_str = next_time.strftime("%H:%M")
            embed.add_field(name="🕐 Последняя отправка", value=last, inline=True)
            embed.add_field(name="⏰ Следующая", value=f"~{next_str} МСК", inline=True)
        else:
            embed.add_field(name="🕐 Статус", value="⏳ Ожидание первой отправки", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ===== МОДАЛКИ ДЛЯ НАСТРОЕК =====

class SetAdTextModal(discord.ui.Modal, title="📝 УСТАНОВИТЬ ТЕКСТ РЕКЛАМЫ"):
    
    text = discord.ui.TextInput(
        label="Текст рекламы",
        placeholder="Введите текст рекламного сообщения",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            with open(AD_TEXT_FILE, 'w', encoding='utf-8') as f:
                f.write(self.text.value)
            
            embed = discord.Embed(
                title="✅ Текст рекламы сохранен",
                description=f"```\n{self.text.value[:200]}{'...' if len(self.text.value) > 200 else ''}\n```",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetAdImageModal(discord.ui.Modal, title="🖼️ УСТАНОВИТЬ КАРТИНКУ"):
    
    url = discord.ui.TextInput(
        label="URL картинки",
        placeholder="https://example.com/image.jpg",
        max_length=500,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.url.value and not (self.url.value.startswith('http://') or self.url.value.startswith('https://')):
            await interaction.response.send_message(
                "❌ URL должен начинаться с http:// или https://",
                ephemeral=True
            )
            return
        
        try:
            with open(AD_IMAGE_FILE, 'w', encoding='utf-8') as f:
                f.write(self.url.value or "")
            
            if self.url.value:
                embed = discord.Embed(
                    title="✅ URL картинки сохранен",
                    description=self.url.value,
                    color=0x00ff00
                )
                embed.set_image(url=self.url.value)
            else:
                embed = discord.Embed(
                    title="✅ Картинка удалена",
                    description="Теперь реклама будет отправляться без картинки",
                    color=0x00ff00
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetAdChannelModal(discord.ui.Modal, title="📢 УСТАНОВИТЬ КАНАЛ"):
    
    channel_id = discord.ui.TextInput(
        label="ID канала",
        placeholder="123456789012345678",
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # НЕ ПРОВЕРЯЕМ существование канала через бота!
            # Просто сохраняем ID
            
            with open(AD_CHANNEL_FILE, 'w', encoding='utf-8') as f:
                f.write(self.channel_id.value)
            
            await interaction.response.send_message(
                f"✅ Канал для рекламы установлен: `{self.channel_id.value}`\n"
                f"⚠️ Убедитесь, что у пользовательского токена есть доступ к этому каналу.",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)