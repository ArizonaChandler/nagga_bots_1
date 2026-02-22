"""Auto Advertising Modals - Настройка авто-рекламы"""
import discord
import traceback
from datetime import datetime
from core.database import db
from core.config import CONFIG
from core.utils import is_admin

class SetAdMessageModal(discord.ui.Modal, title="Реклама"):  # ЕЩЕ КОРОЧЕ!
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
            
            self.image_url = discord.ui.TextInput(
                label="URL картинки",
                placeholder="https://i.imgur.com/example.jpg",
                max_length=500,
                required=False
            )
            print("🔵 [SetAdMessageModal] Field 'image_url' created")
            
            self.channel_id = discord.ui.TextInput(
                label="ID канала",
                placeholder="123456789012345678",
                max_length=20,
                required=True
            )
            print("🔵 [SetAdMessageModal] Field 'channel_id' created")
            
            self.interval = discord.ui.TextInput(
                label="Интервал",
                placeholder="65",
                max_length=5,
                required=True
            )
            print("🔵 [SetAdMessageModal] Field 'interval' created")
            
            print("🔵 [SetAdMessageModal] __init__ completed")
            
        except Exception as e:
            print(f"🔴 [SetAdMessageModal] ERROR in __init__: {type(e).__name__}: {e}")
            traceback.print_exc()
            raise
    
    async def on_submit(self, interaction: discord.Interaction):
        print("🔵 [on_submit] Started")
        print(f"🔵 [on_submit] Values: text='{self.message_text.value[:50]}...', channel='{self.channel_id.value}', interval='{self.interval.value}'")
        
        try:
            if not await is_admin(str(interaction.user.id)):
                print("🔴 [on_submit] User is not admin")
                await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
                return
            
            print("🔵 [on_submit] Deferring response...")
            await interaction.response.defer(ephemeral=True)
            print("🔵 [on_submit] Deferred")
            
            # Получаем сервер
            server_id = CONFIG.get('server_id')
            print(f"🔵 [on_submit] server_id from CONFIG: {server_id}")
            
            if not server_id:
                print("🔴 [on_submit] No server_id in CONFIG")
                await interaction.followup.send("❌ Сначала установите ID сервера", ephemeral=True)
                return
            
            guild = interaction.client.get_guild(int(server_id))
            print(f"🔵 [on_submit] guild: {guild.name if guild else 'None'}")
            
            if not guild:
                print("🔴 [on_submit] Guild not found")
                await interaction.followup.send("❌ Сервер не найден", ephemeral=True)
                return
            
            # Проверяем канал
            try:
                channel_id = int(self.channel_id.value)
                print(f"🔵 [on_submit] Parsed channel_id: {channel_id}")
                
                channel = guild.get_channel(channel_id)
                if not channel:
                    channel = interaction.client.get_channel(channel_id)
                
                print(f"🔵 [on_submit] channel: {channel.name if channel else 'None'}")
                
                if not channel:
                    await interaction.followup.send("❌ Канал не найден", ephemeral=True)
                    return
                    
            except ValueError as e:
                print(f"🔴 [on_submit] Invalid channel_id format: {e}")
                await interaction.followup.send("❌ Неверный ID канала", ephemeral=True)
                return
            
            # Проверяем интервал
            try:
                interval = int(self.interval.value)
                print(f"🔵 [on_submit] Parsed interval: {interval}")
                
                if interval < 1 or interval > 1440:
                    await interaction.followup.send("❌ Интервал от 1 до 1440", ephemeral=True)
                    return
            except ValueError as e:
                print(f"🔴 [on_submit] Invalid interval format: {e}")
                await interaction.followup.send("❌ Интервал должен быть числом", ephemeral=True)
                return
            
            # Проверяем URL
            if self.image_url.value:
                if not (self.image_url.value.startswith('http://') or self.image_url.value.startswith('https://')):
                    await interaction.followup.send("❌ URL должен начинаться с http://", ephemeral=True)
                    return
                print("🔵 [on_submit] image_url format OK")
            
            # Получаем текущие настройки
            print("🔵 [on_submit] Getting current settings from DB...")
            current = db.get_active_ad()
            print(f"🔵 [on_submit] current settings: {current}")
            
            sleep_start = current.get('sleep_start', '02:00') if current else '02:00'
            sleep_end = current.get('sleep_end', '06:30') if current else '06:30'
            print(f"🔵 [on_submit] sleep: {sleep_start} - {sleep_end}")
            
            # Сохраняем
            print("🔵 [on_submit] Saving to DB...")
            success = db.save_ad_settings(
                message_text=self.message_text.value,
                image_url=self.image_url.value if self.image_url.value else None,
                channel_id=str(channel_id),
                interval=interval,
                sleep_start=sleep_start,
                sleep_end=sleep_end,
                updated_by=str(interaction.user.id)
            )
            print(f"🔵 [on_submit] save_ad_settings result: {success}")
            
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
                print("🔵 [on_submit] Success message sent")
            else:
                print("🔴 [on_submit] DB save failed")
                await interaction.followup.send("❌ Ошибка сохранения", ephemeral=True)
                
        except Exception as e:
            print(f"🔴 [on_submit] UNEXPECTED ERROR: {type(e).__name__}: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"❌ Ошибка: {str(e)}", ephemeral=True)


class SetSleepTimeModal(discord.ui.Modal, title="Сон"):  # ЕЩЕ КОРОЧЕ!
    def __init__(self):
        print("🔵 [SetSleepTimeModal] __init__ started")
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
        print("🔵 [SetSleepTimeModal] __init__ completed")
    
    async def on_submit(self, interaction: discord.Interaction):
        print("🔵 [SetSleepTimeModal] on_submit started")
        
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            from datetime import datetime
            start_time = datetime.strptime(self.sleep_start.value, "%H:%M")
            end_time = datetime.strptime(self.sleep_end.value, "%H:%M")
            print(f"🔵 [SetSleepTimeModal] Times parsed: {start_time} - {end_time}")
            
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
                await interaction.followup.send("❌ Ошибка сохранения", ephemeral=True)
                
        except ValueError as e:
            print(f"🔴 [SetSleepTimeModal] ValueError: {e}")
            await interaction.followup.send("❌ Неверный формат времени", ephemeral=True)
        except Exception as e:
            print(f"🔴 [SetSleepTimeModal] ERROR: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"❌ Ошибка: {str(e)}", ephemeral=True)