"""CAPT Core - Массовая отправка DM (перенесено из capt)"""
import asyncio
import time
import discord
from core.database import db
from core.config import CONFIG

active_capt_tasks = {}

class CAPTCore:
    def __init__(self):
        self.stats = {'total_sent': 0, 'total_failed': 0, 'total_time': 0, 'fastest_speed': 0}
        print("⚡ CAPT Core (новая система) инициализирован")
    
    async def send_bulk(self, interaction, members, time_str, message):
        user_id = str(interaction.user.id)
        task_id = id(asyncio.current_task())
        active_capt_tasks[task_id] = {'task': asyncio.current_task(), 'user': user_id}
        
        start_time = time.time()
        
        try:
            embed = self._create_embed(interaction.user.name, time_str, message)
            
            successful = 0
            failed = []
            
            status_msg = await interaction.followup.send(
                f"🚀 **CAPT** | 0/{len(members)}", 
                ephemeral=False
            )
            
            for i, member in enumerate(members):
                if task_id not in active_capt_tasks:
                    await status_msg.edit(content="🛑 Рассылка остановлена")
                    return
                
                try:
                    await member.send(embed=embed)
                    successful += 1
                except discord.Forbidden:
                    failed.append(member.id)
                except Exception:
                    failed.append(member.id)
                
                if (i + 1) % 5 == 0 or i + 1 == len(members):
                    elapsed = time.time() - start_time
                    speed = int(successful / elapsed) if elapsed > 0 else 0
                    await status_msg.edit(
                        content=f"🚀 **CAPT** | {successful}/{len(members)} | ⚡ {speed}/сек"
                    )
                
                await asyncio.sleep(0.2)
            
            elapsed = time.time() - start_time
            speed = int(len(members) / elapsed) if elapsed > 0 else 0
            
            self.stats['total_sent'] += successful
            self.stats['total_failed'] += len(failed)
            self.stats['total_time'] += elapsed
            if speed > self.stats['fastest_speed']:
                self.stats['fastest_speed'] = speed
            
            if failed and CONFIG['capt_channel_id']:
                channel = interaction.guild.get_channel(int(CONFIG['capt_channel_id']))
                if channel:
                    for i in range(0, len(failed), 50):
                        batch = failed[i:i+50]
                        mentions = ' '.join([f"<@{uid}>" for uid in batch])
                        await channel.send(
                            f"🚨 **НЕ ДОСТАВЛЕНО В ЛС**\n"
                            f"👥 **Участники:** {mentions}\n"
                            f"⏰ **Время сбора:** {time_str}\n"
                            f"📋 **Сообщение:** {message}\n"
                            f"────────────────────"
                        )
            
            result_embed = discord.Embed(
                title="✅ CAPT завершена",
                description=f"**{successful}/{len(members)}** участников получили уведомление",
                color=0x00ff00
            )
            result_embed.add_field(name="⏱️ Время", value=f"`{elapsed:.1f} сек`", inline=True)
            result_embed.add_field(name="⚡ Скорость", value=f"`{speed}/сек`", inline=True)
            result_embed.add_field(name="❌ Ошибки", value=f"`{len(failed)}`", inline=True)
            
            await interaction.followup.send(embed=result_embed, ephemeral=True)
            db.log_command('CAPT', user_id, True, successful, 
                          f'Успешно: {successful}, Ошибки: {len(failed)}, Скорость: {speed}/сек')
            
        except Exception as e:
            db.log_command('CAPT', user_id, False, details=str(e))
        finally:
            active_capt_tasks.pop(task_id, None)
    
    def _create_embed(self, author, time_str, message):
        embed = discord.Embed(title="🚨 ОБЩИЙ СБОР!", color=0xff0000)
        embed.add_field(name="⏰ Время", value=time_str, inline=True)
        embed.add_field(name="📍 Мероприятие", value="Телепорт на **CAPT**", inline=True)
        embed.add_field(name="📋 От", value=f"{author}\n{message}", inline=False)
        embed.set_footer(text=f"CAPT Core | {time_str}")
        return embed

# Глобальный экземпляр
capt_core = CAPTCore()