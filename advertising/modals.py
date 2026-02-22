"""Auto Advertising Modals - Настройка авто-рекламы"""
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG
from core.utils import is_admin

class SetAdMessageModal(discord.ui.Modal, title="Настройка рекламы"):  # БЕЗ эмодзи
    def __init__(self):
        super().__init__()
        
        self.message_text = discord.ui.TextInput(
            label="Текст сообщения",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True
        )
        
        self.image_url = discord.ui.TextInput(
            label="URL картинки",
            placeholder="https://i.imgur.com/example.jpg",
            max_length=500,
            required=False
        )
        
        self.channel_id = discord.ui.TextInput(
            label="ID канала",
            placeholder="123456789012345678",
            max_length=20,
            required=True
        )
        
        self.interval = discord.ui.TextInput(
            label="Интервал (мин)",
            placeholder="65",
            max_length=5,
            required=True
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            server_id = CONFIG.get('server_id')
            if not server_id:
                await interaction.followup.send(
                    "❌ Сначала установите ID сервера",
                    ephemeral=True
                )
                return
            
            guild = interaction.client.get_guild(int(server_id))
            if not guild:
                await interaction.followup.send(
                    f"❌ Сервер не найден",
                    ephemeral=True
                )
                return
            
            try:
                channel_id = int(self.channel_id.value)
                channel = guild.get_channel(channel_id)
                
                if not channel:
                    channel = interaction.client.get_channel(channel_id)
                
                if not channel:
                    await interaction.followup.send(
                        f"❌ Канал не найден",
                        ephemeral=True
                    )
                    return
                    
            except ValueError:
                await interaction.followup.send(
                    "❌ Неверный ID канала",
                    ephemeral=True
                )
                return
            
            try:
                interval = int(self.interval.value)
                if interval < 1 or interval > 1440:
                    await interaction.followup.send(
                        "❌ Интервал от 1 до 1440",
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.followup.send(
                    "❌ Интервал должен быть числом",
                    ephemeral=True
                )
                return
            
            if self.image_url.value:
                if not (self.image_url.value.startswith('http://') or self.image_url.value.startswith('https://')):
                    await interaction.followup.send(
                        "❌ URL должен начинаться с http://",
                        ephemeral=True
                    )
                    return
            
            current = db.get_active_ad()
            sleep_start = current.get('sleep_start', '02:00') if current else '02:00'
            sleep_end = current.get('sleep_end', '06:30') if current else '06:30'
            
            success = db.save_ad_settings(
                message_text=self.message_text.value,
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
                
                preview = self.message_text.value[:100]
                if len(self.message_text.value) > 100:
                    preview += "..."
                embed.add_field(name="📝 Текст", value=preview, inline=False)
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send("❌ Ошибка сохранения", ephemeral=True)
                
        except Exception as e:
            print(f"Ошибка: {e}")
            await interaction.followup.send(f"❌ Ошибка: {str(e)}", ephemeral=True)


class SetSleepTimeModal(discord.ui.Modal, title="Режим сна"):  # БЕЗ эмодзи
    def __init__(self):
        super().__init__()
        
        self.sleep_start = discord.ui.TextInput(
            label="Начало",
            placeholder="02:00",
            max_length=5,
            required=True
        )
        
        self.sleep_end = discord.ui.TextInput(
            label="Конец",
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
                    "❌ Сначала настройте рекламу",
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
                    name="Время",
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
                "❌ Неверный формат времени",
                ephemeral=True
            )
        except Exception as e:
            print(f"Ошибка: {e}")
            await interaction.followup.send(f"❌ Ошибка: {str(e)}", ephemeral=True)