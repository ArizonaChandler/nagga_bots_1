"""MCL Core - Массовая отправка DM"""
import asyncio
import time
import discord
from core.database import db
from core.config import CONFIG

active_mcl_tasks = {}


class MCLCore:
    def __init__(self):
        self.stats = {'total_sent': 0, 'total_failed': 0, 'total_time': 0, 'fastest_speed': 0}
        print("⚡ MCL Core инициализирован")
    
    async def send_bulk(self, interaction, members, event_name, event_time, message):
        user_id = str(interaction.user.id)
        task_id = id(asyncio.current_task())
        active_mcl_tasks[task_id] = {'task': asyncio.current_task(), 'user': user_id}
        
        start_time = time.time()
        
        try:
            embed = self._create_embed(interaction.user.name, event_name, event_time, message)
            
            successful = 0
            failed = []
            
            status_msg = await interaction.followup.send(
                f"🚀 **MCL** | 0/{len(members)}", 
                ephemeral=False
            )
            
            for i, member in enumerate(members):
                if task_id not in active_mcl_tasks:
                    await status_msg.edit(content="🛑 Рассылка остановлена")
                    return
                
                try:
                    await member.send(embed=embed)
                    successful += 1
                except:
                    failed.append(member.id)
                
                if (i + 1) % 5 == 0 or i + 1 == len(members):
                    elapsed = time.time() - start_time
                    speed = int(successful / elapsed) if elapsed > 0 else 0
                    await status_msg.edit(
                        content=f"🚀 **MCL** | {successful}/{len(members)} | ⚡ {speed}/сек"
                    )
                
                await asyncio.sleep(0.2)
            
            elapsed = time.time() - start_time
            speed = int(len(members) / elapsed) if elapsed > 0 else 0
            
            result_embed = discord.Embed(
                title="✅ MCL рассылка завершена",
                description=f"**{successful}/{len(members)}** участников получили уведомление",
                color=0x00ff00
            )
            result_embed.add_field(name="⏱️ Время", value=f"`{elapsed:.1f} сек`", inline=True)
            result_embed.add_field(name="⚡ Скорость", value=f"`{speed}/сек`", inline=True)
            result_embed.add_field(name="❌ Ошибки", value=f"`{len(failed)}`", inline=True)
            
            # Отправляем список недоставленных в канал ошибок
            if failed and CONFIG.get('mcl_error_channel'):
                channel = interaction.guild.get_channel(int(CONFIG['mcl_error_channel']))
                if channel:
                    for i in range(0, len(failed), 50):
                        batch = failed[i:i+50]
                        mentions = ' '.join([f"<@{uid}>" for uid in batch])
                        await channel.send(
                            f"🚨 **НЕ ДОСТАВЛЕНО В ЛС**\n"
                            f"👥 Участники: {mentions}\n"
                            f"📋 {event_name} | ⏰ {event_time}\n"
                            f"────────────────────"
                        )
            
            await interaction.followup.send(embed=result_embed, ephemeral=True)
            db.log_command('MCL', user_id, True, successful, f'Успешно: {successful}, Ошибки: {len(failed)}')
            
        except Exception as e:
            db.log_command('MCL', user_id, False, details=str(e))
        finally:
            active_mcl_tasks.pop(task_id, None)
    
    def _create_embed(self, author, event_name, event_time, message):
        embed = discord.Embed(title=f"🚨 {event_name}", color=0xffa500)
        embed.add_field(name="⏰ Время", value=event_time, inline=True)
        embed.add_field(name="📍 Сбор", value="Мероприятие", inline=True)
        embed.add_field(name="📋 От", value=f"{author}\n{message}", inline=False)
        embed.set_footer(text=f"MCL Core | {event_time}")
        return embed


mcl_core = MCLCore()