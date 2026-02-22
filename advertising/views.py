"""Auto Advertising Views - Интерфейс настроек"""
import discord
import traceback
from datetime import datetime
from core.database import db
from core.menus import BaseMenuView
from advertising.modals import SetAdMessageModal, SetSleepTimeModal

class AdSettingsView(BaseMenuView):
    """Меню настроек авто-рекламы"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        print("🔵 [AdSettingsView] __init__ started")
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        # Кнопка настройки сообщения
        msg_btn = discord.ui.Button(
            label="📝 Настроить",
            style=discord.ButtonStyle.primary,
            emoji="📝",
            row=0
        )
        async def msg_cb(i):
            print("🔵 [msg_cb] Button clicked")
            print(f"🔵 [msg_cb] User: {i.user.id}, Channel: {i.channel.id if i.channel else 'DM'}")
            try:
                print("🔵 [msg_cb] Creating SetAdMessageModal instance...")
                modal = SetAdMessageModal()
                print("🔵 [msg_cb] Modal created, sending to Discord...")
                await i.response.send_modal(modal)
                print("🔵 [msg_cb] Modal sent successfully")
            except Exception as e:
                print(f"🔴 [msg_cb] ERROR: {type(e).__name__}: {e}")
                traceback.print_exc()
                try:
                    await i.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)
                except:
                    print("🔴 [msg_cb] Failed to send error message")
        msg_btn.callback = msg_cb
        self.add_item(msg_btn)
        
        # Кнопка настройки режима сна
        sleep_btn = discord.ui.Button(
            label="😴 Режим сна",
            style=discord.ButtonStyle.secondary,
            emoji="😴",
            row=0
        )
        async def sleep_cb(i):
            print("🔵 [sleep_cb] Button clicked")
            try:
                modal = SetSleepTimeModal()
                await i.response.send_modal(modal)
            except Exception as e:
                print(f"🔴 [sleep_cb] ERROR: {e}")
                traceback.print_exc()
                await i.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)
        sleep_btn.callback = sleep_cb
        self.add_item(sleep_btn)
        
        # Кнопка просмотра статистики
        stats_btn = discord.ui.Button(
            label="📊 Статистика",
            style=discord.ButtonStyle.secondary,
            emoji="📊",
            row=1
        )
        async def stats_cb(i):
            await self.show_stats(i)
        stats_btn.callback = stats_cb
        self.add_item(stats_btn)
        
        # Кнопка включения/выключения
        toggle_btn = discord.ui.Button(
            label="⏯️ Вкл/Выкл",
            style=discord.ButtonStyle.danger,
            emoji="⏯️",
            row=1
        )
        async def toggle_cb(i):
            await self.toggle_ad(i)
        toggle_btn.callback = toggle_cb
        self.add_item(toggle_btn)
        
        self.add_back_button()
        print("🔵 [AdSettingsView] __init__ completed")
    
    async def show_stats(self, interaction):
        print("🔵 [show_stats] Started")
        try:
            embed = discord.Embed(
                title="📊 Статистика авто-рекламы",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            settings = db.get_active_ad()
            if settings:
                embed.add_field(name="📝 Текст", value=settings['message_text'][:100] + "...", inline=False)
                embed.add_field(name="⏱️ Интервал", value=f"{settings['interval_minutes']} мин", inline=True)
                embed.add_field(name="😴 Сон", value=f"{settings['sleep_start']} - {settings['sleep_end']}", inline=True)
                
                if settings['last_sent']:
                    embed.add_field(name="🕐 Последняя отправка", value=settings['last_sent'][:16], inline=False)
            
            await interaction.response.edit_message(embed=embed, view=self)
            print("🔵 [show_stats] Success")
        except Exception as e:
            print(f"🔴 [show_stats] ERROR: {e}")
            traceback.print_exc()
    
    async def toggle_ad(self, interaction):
        print("🔵 [toggle_ad] Started")
        try:
            settings = db.get_active_ad()
            if not settings:
                await interaction.response.send_message("❌ Сначала настройте рекламу", ephemeral=True)
                return
            
            new_status = 0 if settings['is_active'] else 1
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE auto_ad SET is_active = ? WHERE id = ?', 
                              (new_status, settings['id']))
                conn.commit()
            
            status_text = "✅ Включено" if new_status else "❌ Выключено"
            await interaction.response.send_message(f"Авто-реклама: {status_text}", ephemeral=True)
            print(f"🔵 [toggle_ad] Success: {status_text}")
        except Exception as e:
            print(f"🔴 [toggle_ad] ERROR: {e}")
            traceback.print_exc()