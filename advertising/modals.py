"""Auto Advertising Modals - Настройка авто-рекламы"""
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG
from core.utils import is_admin

class SetAdMessageModal(discord.ui.Modal, title="📢 НАСТРОЙКА РЕКЛАМЫ"):
    def __init__(self):
        super().__init__()
        
        # ВСЕ LABEL ТОЧНО В ПРЕДЕЛАХ 40 СИМВОЛОВ
        self.message_text = discord.ui.TextInput(
            label="Текст рекламы",  # 13 символов ✅
            style=discord.TextStyle.paragraph,
            max_length=2000,  # Это максимум для вводимого текста
            required=True
        )
        
        self.image_url = discord.ui.TextInput(
            label="URL картинки",  # 14 символов ✅
            placeholder="https://i.imgur.com/example.jpg",
            max_length=500,
            required=False
        )
        
        self.channel_id = discord.ui.TextInput(
            label="ID канала",  # 11 символов ✅
            placeholder="123456789012345678",
            max_length=20,
            required=True
        )
        
        self.interval = discord.ui.TextInput(
            label="Интервал (мин)",  # 15 символов ✅
            placeholder="65",
            max_length=5,
            required=True
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Проверка прав
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Получаем сервер
            server_id = CONFIG.get('server_id')
            if not server_id:
                await interaction.followup.send(
                    "❌ Сначала установите ID сервера в Глобальных настройках",
                    ephemeral=True
                )
                return
            
            guild = interaction.client.get_guild(int(server_id))
            if not guild:
                await interaction.followup.send(
                    f"❌ Сервер с ID {server_id} не найден",
                    ephemeral=True
                )
                return
            
            # Проверка канала
            try:
                channel_id = int(self.channel_id.value)
                channel = guild.get_channel(channel_id)
                
                if not channel:
                    channel = interaction.client.get_channel(channel_id)
                
                if not channel:
                    await interaction.followup.send(
                        f"❌ Канал с ID {channel_id} не найден",
                        ephemeral=True
                    )
                    return
                
                permissions = channel.permissions_for(guild.me)
                if not permissions.send_messages:
                    await interaction.followup.send(
                        f"❌ Нет прав на отправку в канал {channel.mention}",
                        ephemeral=True
                    )
                    return
                    
            except ValueError:
                await interaction.followup.send(
                    "❌ Неверный формат ID канала",
                    ephemeral=True
                )
                return
            
            # Проверка интервала
            try:
                interval = int(self.interval.value)
                if interval < 1:
                    await interaction.followup.send(
                        "❌ Интервал должен быть больше 0",
                        ephemeral=True
                    )
                    return
                if interval > 1440:
                    await interaction.followup.send(
                        "❌ Интервал не может быть больше 24 часов",
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.followup.send(
                    "❌ Интервал должен быть числом",
                    ephemeral=True
                )
                return
            
            # Проверка URL картинки
            if self.image_url.value:
                if not (self.image_url.value.startswith('http://') or self.image_url.value.startswith('https://')):
                    await interaction.followup.send(
                        "❌ URL должен начинаться с http:// или https://",
                        ephemeral=True
                    )
                    return
            
            # Получаем текущие настройки
            current_settings = db.get_active_ad()
            
            sleep_start = '02:00'
            sleep_end = '06:30'
            
            if current_settings:
                sleep_start = current_settings.get('sleep_start', '02:00')
                sleep_end = current_settings.get('sleep_end', '06:30')
            
            # Сохраняем
            success = db.save_ad_settings(
                message_text=self.message_text.value,  # Здесь может быть до 2000 символов
                image_url=self.image_url.value if self.image_url.value else None,
                channel_id=str(channel_id),
                interval=interval,
                sleep_start=sleep_start,
                sleep_end=sleep_end,
                updated_by=str(interaction.user.id)
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ Настройки сохранены",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                
                embed.add_field(name="📢 Канал", value=channel.mention, inline=True)
                embed.add_field(name="⏱️ Интервал", value=f"{interval} мин", inline=True)
                embed.add_field(name="😴 Сон", value=f"{sleep_start}-{sleep_end}", inline=True)
                
                # Показываем только первые 100 символов текста
                text_preview = self.message_text.value[:100]
                if len(self.message_text.value) > 100:
                    text_preview += "..."
                embed.add_field(name="📝 Текст", value=text_preview, inline=False)
                
                if self.image_url.value:
                    embed.set_image(url=self.image_url.value)
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send("❌ Ошибка сохранения", ephemeral=True)
                
        except Exception as e:
            print(f"Ошибка: {e}")
            await interaction.followup.send(f"❌ Ошибка: {str(e)}", ephemeral=True)


class SetSleepTimeModal(discord.ui.Modal, title="😴 НАСТРОЙКА РЕЖИМА СНА"):
    def __init__(self):
        super().__init__()
        
        self.sleep_start = discord.ui.TextInput(
            label="Начало сна",  # 11 символов ✅
            placeholder="02:00",
            max_length=5,
            required=True
        )
        
        self.sleep_end = discord.ui.TextInput(
            label="Конец сна",  # 11 символов ✅
            placeholder="06:30",
            max_length=5,
            required=True
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            from datetime import datetime
            start_time = datetime.strptime(self.sleep_start.value, "%H:%M")
            end_time = datetime.strptime(self.sleep_end.value, "%H:%M")
            
            settings = db.get_active_ad()
            if not settings:
                await interaction.followup.send(
                    "❌ Сначала настройте основную рекламу",
                    ephemeral=True
                )
                return
            
            success = db.save_ad_settings(
                message_text=settings['message_text'],
                image_url=settings.get('image_url'),
                channel_id=settings['channel_id'],
                interval=settings['interval_minutes'],
                sleep_start=self.sleep_start.value,
                sleep_end=self.sleep_end.value,
                updated_by=str(interaction.user.id)
            )
            
            if success:
                start_min = start_time.hour * 60 + start_time.minute
                end_min = end_time.hour * 60 + end_time.minute
                
                if start_min < end_min:
                    duration = end_min - start_min
                else:
                    duration = (24*60 - start_min) + end_min
                
                hours = duration // 60
                minutes = duration % 60
                
                embed = discord.Embed(
                    title="😴 Режим сна настроен",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                embed.add_field(
                    name="Время сна",
                    value=f"{self.sleep_start.value} - {self.sleep_end.value}",
                    inline=True
                )
                embed.add_field(
                    name="Длительность",
                    value=f"{hours}ч {minutes}м",
                    inline=True
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send("❌ Ошибка сохранения", ephemeral=True)
                
        except ValueError:
            await interaction.followup.send(
                "❌ Неверный формат времени. Используйте ЧЧ:ММ",
                ephemeral=True
            )
        except Exception as e:
            print(f"Ошибка: {e}")
            await interaction.followup.send(f"❌ Ошибка: {str(e)}", ephemeral=True)