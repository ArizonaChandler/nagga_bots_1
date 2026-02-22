"""Auto Advertising Modals - Настройка авто-рекламы"""
import discord
import traceback
from datetime import datetime
from core.database import db
from core.config import CONFIG
from core.utils import is_admin

class SetAdMessageModal(discord.ui.Modal, title="Реклама"):  # 7 символов
    def __init__(self):
        print("🔵 [SetAdMessageModal] __init__ started")
        super().__init__()
        
        try:
            self.message_text = discord.ui.TextInput(
                label="Текст",
                style=discord.TextStyle.paragraph,
                max_length=2000,
                required=True
            )
            print("🔵 [SetAdMessageModal] Field 'message_text' created")
            
            print("🔵 [SetAdMessageModal] __init__ completed")
            
        except Exception as e:
            print(f"🔴 [SetAdMessageModal] ERROR in __init__: {type(e).__name__}: {e}")
            traceback.print_exc()
            raise
    
    async def on_submit(self, interaction: discord.Interaction):
        print("🔵 [on_submit] Started")
        
        try:
            if not await is_admin(str(interaction.user.id)):
                await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
                return
            
            await interaction.response.defer(ephemeral=True)
            
            server_id = CONFIG.get('server_id')
            if not server_id:
                await interaction.followup.send("❌ Сначала установите ID сервера", ephemeral=True)
                return
            
            guild = interaction.client.get_guild(int(server_id))
            if not guild:
                await interaction.followup.send("❌ Сервер не найден", ephemeral=True)
                return
            
            current = db.get_active_ad() or {}
            sleep_start = current.get('sleep_start', '02:00')
            sleep_end = current.get('sleep_end', '06:30')
            
            success = db.save_ad_settings(
                message_text=self.message_text.value,
                image_url=None,
                channel_id="0",
                interval=65,
                sleep_start=sleep_start,
                sleep_end=sleep_end,
                updated_by=str(interaction.user.id)
            )
            
            if success:
                await interaction.followup.send("✅ Текст сохранен", ephemeral=True)
            else:
                await interaction.followup.send("❌ Ошибка", ephemeral=True)
                
        except Exception as e:
            print(f"🔴 [on_submit] ERROR: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"❌ Ошибка: {str(e)}", ephemeral=True)


class SetSleepTimeModal(discord.ui.Modal, title="Сон"):  # 4 символа
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
                await interaction.followup.send("✅ Режим сна сохранен", ephemeral=True)
            else:
                await interaction.followup.send("❌ Ошибка", ephemeral=True)
                
        except ValueError:
            await interaction.followup.send("❌ Неверный формат времени", ephemeral=True)
        except Exception as e:
            print(f"🔴 [SetSleepTimeModal] ERROR: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"❌ Ошибка: {str(e)}", ephemeral=True)