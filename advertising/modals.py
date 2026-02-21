"""Auto Advertising Modals - Настройка авто-рекламы"""
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG
from core.utils import is_admin

class SetAdMessageModal(discord.ui.Modal, title="📢 НАСТРОЙКА РЕКЛАМЫ"):
    def __init__(self):
        super().__init__()
        
        # НЕ ЗАГРУЖАЕМ ДАННЫЕ ИЗ БД ЗДЕСЬ!
        # Просто создаём поля с пустыми значениями
        
        self.message_text = discord.ui.TextInput(
            label="📝 Текст сообщения",
            placeholder="Введите текст рекламы...",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True
        )
        
        self.image_url = discord.ui.TextInput(
            label="🖼️ URL картинки (необязательно)",
            placeholder="https://i.imgur.com/example.jpg",
            max_length=500,
            required=False
        )
        
        self.channel_id = discord.ui.TextInput(
            label="📢 ID канала",
            placeholder="123456789012345678",
            max_length=20,
            required=True
        )
        
        self.interval = discord.ui.TextInput(
            label="⏱️ Интервал (минуты)",
            placeholder="65",
            max_length=5,
            required=True
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        # ОТПРАВЛЯЕМ ПЕРВЫЙ ОТВЕТ СРАЗУ
        await interaction.response.defer(ephemeral=True)
        
        try:
            # ТЕПЕРЬ МОЖНО БЕЗОПАСНО ГРУЗИТЬ ДАННЫЕ
            settings = db.get_active_ad()
            
            # Заполняем поля значениями из БД, если они пустые
            if not self.message_text.value and settings:
                self.message_text.value = settings.get('message_text', '')
            if not self.image_url.value and settings:
                self.image_url.value = settings.get('image_url', '')
            if not self.channel_id.value and settings:
                self.channel_id.value = settings.get('channel_id', '')
            if not self.interval.value and settings:
                self.interval.value = str(settings.get('interval_minutes', 65))
            
            # Получаем сервер из CONFIG
            server_id = CONFIG.get('server_id')
            guild = None
            
            if server_id:
                guild = interaction.client.get_guild(int(server_id))
            
            if not guild and interaction.guild:
                guild = interaction.guild
            
            if not guild:
                await interaction.followup.send(
                    "❌ Не удалось определить сервер. Сначала установите ID сервера в Глобальных настройках.",
                    ephemeral=True
                )
                return
            
            # Проверяем канал
            try:
                channel = guild.get_channel(int(self.channel_id.value))
                if not channel:
                    channel = interaction.client.get_channel(int(self.channel_id.value))
                
                if not channel:
                    await interaction.followup.send(
                        f"❌ Канал с ID {self.channel_id.value} не найден на сервере {guild.name}",
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.followup.send("❌ Неверный формат ID канала", ephemeral=True)
                return
            
            # Проверяем интервал
            try:
                interval = int(self.interval.value)
                if interval < 1:
                    await interaction.followup.send("❌ Интервал должен быть больше 0", ephemeral=True)
                    return
            except ValueError:
                await interaction.followup.send("❌ Неверный формат интервала", ephemeral=True)
                return
            
            # Получаем текущие настройки для времени сна
            current_settings = db.get_active_ad()
            sleep_start = current_settings.get('sleep_start', '02:00') if current_settings else '02:00'
            sleep_end = current_settings.get('sleep_end', '06:30') if current_settings else '06:30'
            
            # Сохраняем настройки
            success = db.save_ad_settings(
                message_text=self.message_text.value,
                image_url=self.image_url.value if self.image_url.value else None,
                channel_id=self.channel_id.value,
                interval=interval,
                sleep_start=sleep_start,
                sleep_end=sleep_end,
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
                embed.add_field(name="😴 Режим сна", value=f"{sleep_start} - {sleep_end}", inline=True)
                embed.add_field(name="📝 Текст", value=self.message_text.value[:100] + "..." if len(self.message_text.value) > 100 else self.message_text.value, inline=False)
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send("❌ Ошибка сохранения", ephemeral=True)
                
        except Exception as e:
            print(f"Ошибка в SetAdMessageModal: {e}")
            await interaction.followup.send(f"❌ Ошибка: {str(e)}", ephemeral=True)


class SetSleepTimeModal(discord.ui.Modal, title="😴 НАСТРОЙКА РЕЖИМА СНА"):
    def __init__(self):
        super().__init__()
        
        self.sleep_start = discord.ui.TextInput(
            label="Начало сна (ЧЧ:ММ)",
            placeholder="02:00",
            max_length=5,
            required=True
        )
        
        self.sleep_end = discord.ui.TextInput(
            label="Конец сна (ЧЧ:ММ)",
            placeholder="06:30",
            max_length=5,
            required=True
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        # ОТПРАВЛЯЕМ ПЕРВЫЙ ОТВЕТ СРАЗУ
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Проверяем формат времени
            from datetime import datetime
            datetime.strptime(self.sleep_start.value, "%H:%M")
            datetime.strptime(self.sleep_end.value, "%H:%M")
            
            # Получаем текущие настройки
            settings = db.get_active_ad()
            if not settings:
                await interaction.followup.send(
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
                await interaction.followup.send(
                    f"✅ Режим сна установлен: {self.sleep_start.value} - {self.sleep_end.value}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send("❌ Ошибка сохранения", ephemeral=True)
                
        except ValueError:
            await interaction.followup.send("❌ Неверный формат времени. Используйте ЧЧ:ММ", ephemeral=True)