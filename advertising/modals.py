"""Auto Advertising Modals - Настройка авто-рекламы"""
import discord
from core.database import db
from core.config import CONFIG, save_config
from core.utils import is_admin

class SetAdMessageModal(discord.ui.Modal, title="📢 НАСТРОЙКА РЕКЛАМЫ"):
    def __init__(self, current_settings=None):
        super().__init__()
        self.current_settings = current_settings or {}
    
    message_text = discord.ui.TextInput(
        label="Текст сообщения",
        placeholder="Введите текст рекламы...",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True
    )
    
    image_url = discord.ui.TextInput(
        label="URL картинки (необязательно)",
        placeholder="https://i.imgur.com/example.jpg",
        max_length=500,
        required=False
    )
    
    channel_id = discord.ui.TextInput(
        label="ID канала",
        placeholder="123456789012345678",
        max_length=20,
        required=True
    )
    
    interval = discord.ui.TextInput(
        label="Интервал (минуты)",
        placeholder="65",
        max_length=5,
        default="65",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        try:
            # Проверяем канал
            channel = interaction.guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return
            
            # Проверяем интервал
            interval = int(self.interval.value)
            if interval < 1:
                await interaction.response.send_message("❌ Интервал должен быть больше 0", ephemeral=True)
                return
            
            # Сохраняем настройки
            success = db.save_ad_settings(
                message_text=self.message_text.value,
                image_url=self.image_url.value if self.image_url.value else None,
                channel_id=self.channel_id.value,
                interval=interval,
                updated_by=str(interaction.user.id)
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ Настройки рекламы сохранены",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                embed.add_field(name="📢 Канал", value=channel.mention, inline=True)
                embed.add_field(name="⏱️ Интервал", value=f"{interval} мин", inline=True)
                embed.add_field(name="📝 Текст", value=self.message_text.value[:100] + "...", inline=False)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Ошибка сохранения", ephemeral=True)
                
        except ValueError:
            await interaction.response.send_message("❌ Неверный формат интервала", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetSleepTimeModal(discord.ui.Modal, title="😴 НАСТРОЙКА РЕЖИМА СНА"):
    sleep_start = discord.ui.TextInput(
        label="Начало сна (ЧЧ:ММ)",
        placeholder="02:00",
        max_length=5,
        default="02:00",
        required=True
    )
    
    sleep_end = discord.ui.TextInput(
        label="Конец сна (ЧЧ:ММ)",
        placeholder="06:30",
        max_length=5,
        default="06:30",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        try:
            # Проверяем формат времени
            from datetime import datetime
            datetime.strptime(self.sleep_start.value, "%H:%M")
            datetime.strptime(self.sleep_end.value, "%H:%M")
            
            # Получаем текущие настройки
            settings = db.get_active_ad()
            if not settings:
                await interaction.response.send_message(
                    "❌ Сначала настройте основную рекламу", 
                    ephemeral=True
                )
                return
            
            # Обновляем настройки со временем сна
            success = db.save_ad_settings(
                message_text=settings['message_text'],
                image_url=settings['image_url'],
                channel_id=settings['channel_id'],
                interval=settings['interval_minutes'],
                sleep_start=self.sleep_start.value,
                sleep_end=self.sleep_end.value,
                updated_by=str(interaction.user.id)
            )
            
            if success:
                await interaction.response.send_message(
                    f"✅ Режим сна установлен: {self.sleep_start.value} - {self.sleep_end.value}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("❌ Ошибка сохранения", ephemeral=True)
                
        except ValueError:
            await interaction.response.send_message("❌ Неверный формат времени. Используйте ЧЧ:ММ", ephemeral=True)