"""Auto Advertising Modals - Настройка авто-рекламы"""
import discord
import traceback
from datetime import datetime
from core.database import db
from core.config import CONFIG
from core.utils import is_admin

class SetAdMessageModal(discord.ui.Modal, title="Реклама"):
    def __init__(self):
        super().__init__()
        print("🔵 [Modal] __init__")
        
        self.message_text = discord.ui.TextInput(
            label="Текст",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True
        )
        
        self.channel_id = discord.ui.TextInput(
            label="Канал",
            placeholder="ID канала",
            max_length=20,
            required=True
        )
        
        self.interval = discord.ui.TextInput(
            label="Интервал",
            placeholder="65",
            max_length=5,
            required=True
        )
        
        self.image_url = discord.ui.TextInput(
            label="Картинка",
            placeholder="https://...",
            max_length=500,
            required=False
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        print("🔵 [Modal] on_submit")
        
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Нет прав", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            server_id = CONFIG.get('server_id')
            if not server_id:
                await interaction.followup.send("❌ Нет ID сервера", ephemeral=True)
                return
            
            guild = interaction.client.get_guild(int(server_id))
            if not guild:
                await interaction.followup.send("❌ Сервер не найден", ephemeral=True)
                return
            
            channel = guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.followup.send("❌ Канал не найден", ephemeral=True)
                return
            
            interval = int(self.interval.value)
            if interval < 1 or interval > 1440:
                await interaction.followup.send("❌ Интервал 1-1440", ephemeral=True)
                return
            
            current = db.get_active_ad() or {}
            
            success = db.save_ad_settings(
                message_text=self.message_text.value,
                image_url=self.image_url.value or None,
                channel_id=self.channel_id.value,
                interval=interval,
                sleep_start=current.get('sleep_start', '02:00'),
                sleep_end=current.get('sleep_end', '06:30'),
                updated_by=str(interaction.user.id)
            )
            
            if success:
                await interaction.followup.send("✅ Сохранено", ephemeral=True)
            else:
                await interaction.followup.send("❌ Ошибка", ephemeral=True)
                
        except Exception as e:
            print(f"🔴 [Modal] ERROR: {e}")
            await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)


class SetSleepTimeModal(discord.ui.Modal, title="Сон"):
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
            await interaction.response.send_message("❌ Нет прав", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            from datetime import datetime
            datetime.strptime(self.sleep_start.value, "%H:%M")
            datetime.strptime(self.sleep_end.value, "%H:%M")
            
            settings = db.get_active_ad()
            if not settings:
                await interaction.followup.send("❌ Сначала настройте рекламу", ephemeral=True)
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
                await interaction.followup.send("✅ Сохранено", ephemeral=True)
            else:
                await interaction.followup.send("❌ Ошибка", ephemeral=True)
                
        except ValueError:
            await interaction.followup.send("❌ Неверный формат времени", ephemeral=True)
        except Exception as e:
            print(f"🔴 [SleepModal] ERROR: {e}")
            await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)