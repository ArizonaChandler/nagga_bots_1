"""Кнопки для системы AFK"""
import discord
import logging
import pytz
from datetime import datetime
from afk.base import PermanentView
from afk.modals import AFKModal
from afk.manager import afk_manager

logger = logging.getLogger(__name__)
MSK_TZ = pytz.timezone('Europe/Moscow')


async def update_afk_embed(bot, channel_id: str):
    """Обновить красивый embed со списком AFK пользователей (с полями)"""
    channel = bot.get_channel(int(channel_id))
    if not channel:
        logger.error(f"❌ Канал {channel_id} не найден для обновления embed")
        return
    
    users = afk_manager.get_all_afk_users()
    
    # Ищем существующее сообщение с кнопками AFK
    target_message = None
    async for msg in channel.history(limit=50):
        if msg.author == bot.user:
            if msg.components and len(msg.components) > 0:
                for component in msg.components:
                    for button in component.children:
                        if button.custom_id in ["afk_go", "afk_back"]:
                            target_message = msg
                            logger.info(f"✅ Найдено сообщение AFK в #{channel.name} (ID: {msg.id})")
                            break
                    if target_message:
                        break
            if target_message:
                break
    
    # Если сообщение не найдено, пробуем найти по embed заголовку
    if not target_message:
        async for msg in channel.history(limit=50):
            if msg.author == bot.user and msg.embeds:
                if msg.embeds and "СИСТЕМА AFK" in msg.embeds[0].title:
                    target_message = msg
                    logger.info(f"✅ Найдено сообщение AFK по embed в #{channel.name} (ID: {msg.id})")
                    break
    
    # Если всё равно не нашли - создаём новое сообщение
    if not target_message:
        logger.warning(f"⚠️ Не найдено сообщение AFK в канале {channel.name}, создаём новое")
        settings = afk_manager.get_settings()
        max_hours = int(settings.get('afk_max_hours', 24))
        
        embed = discord.Embed(
            title="🛌 **СИСТЕМА AFK**",
            description="✨ **Никого нет в AFK**\n\nНажмите кнопку ниже, чтобы уйти в AFK",
            color=0x2b2d31,
            timestamp=datetime.now(MSK_TZ)
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1302858797087854592.png?size=96")
        embed.set_footer(text="• Статус: Активен •", icon_url=bot.user.avatar.url if bot.user.avatar else None)
        target_message = await channel.send(embed=embed, view=AFKPublicView(bot, channel_id, max_hours))
        logger.info(f"✅ Создано новое сообщение AFK в #{channel.name}")
    
    # Обновляем embed
    if not users:
        embed = discord.Embed(
            title="🛌 **СИСТЕМА AFK**",
            description="✨ **Никого нет в AFK**\n\nНажмите кнопку ниже, чтобы уйти в AFK",
            color=0x2b2d31,
            timestamp=datetime.now(MSK_TZ)
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1302858797087854592.png?size=96")
        embed.set_footer(text="• Статус: Активен •", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    else:
        # Сортируем пользователей по времени возврата
        users_sorted = sorted(users, key=lambda x: x['until_time'])
        
        embed = discord.Embed(
            title="🛌 **СИСТЕМА AFK**",
            color=0x2b2d31,
            timestamp=datetime.now(MSK_TZ)
        )
        
        # Статистика
        total_users = len(users)
        embed.add_field(
            name="📊 **СТАТИСТИКА**",
            value=f"└ 👥 **В AFK:** {total_users} человек",
            inline=False
        )
        
        # Добавляем каждого пользователя отдельным полем
        now = datetime.now(MSK_TZ)  # aware datetime
        
        for user in users_sorted:
            # until_time из БД уже в правильном формате
            until = datetime.fromisoformat(user['until_time'])
            # Убеждаемся, что until тоже aware
            if until.tzinfo is None:
                until = MSK_TZ.localize(until)
            
            until_str = until.strftime("%d.%m.%Y в %H:%M")
            
            # Рассчитываем оставшееся время
            time_left = until - now
            hours_left = time_left.seconds // 3600
            minutes_left = (time_left.seconds % 3600) // 60
            
            if time_left.days > 0:
                time_left_str = f"{time_left.days}д {hours_left}ч"
            elif hours_left > 0:
                time_left_str = f"{hours_left}ч {minutes_left}мин"
            else:
                time_left_str = f"{minutes_left}мин"
            
            # Иконка в зависимости от оставшегося времени
            if time_left.total_seconds() < 3600:
                status_icon = "⚠️"
            elif time_left.total_seconds() < 7200:
                status_icon = "⏰"
            else:
                status_icon = "🛌"
            
            field_value = f"└ 📝 **Причина:** {user['reason']}\n"
            field_value += f"└ ⏱️ **Вернётся:** {until_str}\n"
            field_value += f"└ ⌛ **Осталось:** {time_left_str}"
            
            embed.add_field(
                name=f"{status_icon} {user['user_name']}",
                value=field_value,
                inline=False
            )
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1302858797087854592.png?size=96")
        embed.set_footer(text=f"• Обновлено: {datetime.now(MSK_TZ).strftime('%H:%M:%S')} •", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    
    await target_message.edit(embed=embed)


class AFKPublicView(PermanentView):
    """Публичные кнопки для AFK"""
    
    def __init__(self, bot, channel_id: str, max_hours: int):
        super().__init__()
        self.bot = bot
        self.channel_id = channel_id
        self.max_hours = max_hours
    
    async def log_action(self, interaction: discord.Interaction, action: str, details: str = None):
        """Логирование действий в канал логов AFK"""
        settings = afk_manager.get_settings()
        log_channel_id = settings.get('afk_log_channel')
        
        if not log_channel_id:
            return
        
        log_channel = interaction.client.get_channel(int(log_channel_id))
        if not log_channel:
            return
        
        embed = discord.Embed(
            title=f"📋 {action}",
            color=0x00ff00 if action == "ВОЗВРАТ ИЗ AFK" else 0xffa500,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Пользователь", value=interaction.user.mention)
        embed.add_field(name="🆔 ID", value=interaction.user.id)
        
        if details:
            embed.add_field(name="📝 Детали", value=details, inline=False)
        
        await log_channel.send(embed=embed)
    
    @discord.ui.button(
        label="🛌 УЙТИ В AFK", 
        style=discord.ButtonStyle.primary,
        emoji="🛌",
        custom_id="afk_go"
    )
    async def go_afk(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Открыть модалку ухода в AFK"""
        await interaction.response.send_modal(AFKModal(self.bot, self.channel_id, self.max_hours))
    
    @discord.ui.button(
        label="✅ ВЕРНУЛСЯ", 
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="afk_back"
    )
    async def back_afk(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Вернуться из AFK"""
        # Получаем информацию о пользователе до удаления (для лога)
        afk_user = afk_manager.get_afk_user(str(interaction.user.id))
        
        success, msg = afk_manager.remove_afk_user(str(interaction.user.id))
        await interaction.response.send_message(msg, ephemeral=True)
        
        # Логируем
        if success and afk_user:
            details = f"Причина ухода: {afk_user['reason']} | Был в AFK с {afk_user['until_time']}"
            await self.log_action(interaction, "ВОЗВРАТ ИЗ AFK", details)
        
        # Обновляем embed
        if success:
            await update_afk_embed(self.bot, self.channel_id)