"""Auto Advertising Views - Интерфейс настроек"""
import discord
from datetime import datetime
from core.database import db
from core.menus import BaseMenuView
from advertising.modals import SetAdMessageModal, SetSleepTimeModal

class AdSettingsView(BaseMenuView):
    """Меню настроек авто-рекламы"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        # Кнопка настройки сообщения
        msg_btn = discord.ui.Button(
            label="📝 Настроить сообщение",
            style=discord.ButtonStyle.primary,
            emoji="📝",
            row=0
        )
        async def msg_cb(i):
            try:
                # НЕ ЗАГРУЖАЕМ ДАННЫЕ ЗДЕСЬ
                # Просто отправляем пустую модалку
                modal = SetAdMessageModal()
                await i.response.send_modal(modal)
            except Exception as e:
                print(f"Ошибка в msg_cb: {e}")
                await i.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)
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
            try:
                modal = SetSleepTimeModal()
                await i.response.send_modal(modal)
            except Exception as e:
                print(f"Ошибка в sleep_cb: {e}")
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
    
    async def show_stats(self, interaction):
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
        except Exception as e:
            print(f"Ошибка в show_stats: {e}")
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)
    
    async def toggle_ad(self, interaction):
        try:
            settings = db.get_active_ad()
            if not settings:
                await interaction.response.send_message("❌ Сначала настройте рекламу", ephemeral=True)
                return
            
            # Инвертируем статус
            new_status = 0 if settings['is_active'] else 1
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE auto_ad SET is_active = ? WHERE id = ?', 
                              (new_status, settings['id']))
                conn.commit()
            
            status_text = "✅ Включено" if new_status else "❌ Выключено"
            await interaction.response.send_message(f"Авто-реклама: {status_text}", ephemeral=True)
        except Exception as e:
            print(f"Ошибка в toggle_ad: {e}")
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)