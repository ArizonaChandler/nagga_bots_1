"""DUAL MCL Core - Надёжная блокировка повторного запуска"""
import aiohttp
import asyncio
import time
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG

active_mcl_tasks = {}

class CancelView(discord.ui.View):
    """Кнопка отмены отправки (без таймаута)"""
    def __init__(self, task_id: int, user_id: str):
        super().__init__(timeout=None)
        self.task_id = task_id
        self.user_id = user_id
    
    @discord.ui.button(label="❌ ОТМЕНИТЬ", style=discord.ButtonStyle.danger, emoji="🛑")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Только запустивший может отменить", ephemeral=True)
            return
        
        if self.task_id in active_mcl_tasks:
            active_mcl_tasks[self.task_id]['cancelled'] = True
            button.disabled = True
            await interaction.response.edit_message(
                content="🛑 Отправка остановлена",
                embed=None,
                view=None
            )
        else:
            await interaction.response.send_message("❌ Задача уже завершена", ephemeral=True)

class DualMCLCore:
    __slots__ = (
        'sessions', 'session_locks', 'headers_cache', 'last_tokens',
        'payload_cache', 'last_messages', 'last_channel', 
        'stats', 'token_colors', 'current_sender', 'sending_lock',
        'sender_name', 'sending_active',  # Добавлено для надёжности
        '_connectors_initialized', '_connectors'
    )
    
    def __init__(self):
        self._connectors_initialized = False
        self._connectors = {1: None, 2: None}
        
        self.sessions = {1: None, 2: None}
        self.session_locks = {1: asyncio.Lock(), 2: asyncio.Lock()}
        
        # Блокировка отправки
        self.sending_lock = asyncio.Lock()
        self.current_sender = None  # ID текущего отправителя
        self.sender_name = None     # Имя для красивого вывода
        self.sending_active = False # Флаг активности
        
        self.headers_cache = {1: None, 2: None}
        self.last_tokens = {1: None, 2: None}
        self.payload_cache = {1: None, 2: None}
        self.last_messages = {1: None, 2: None}
        self.last_channel = None
        
        self.stats = {
            1: {'success': 0, 'failed': 0, 'total_attempts': 0},
            2: {'success': 0, 'failed': 0, 'total_attempts': 0}
        }
        self.token_colors = {1: 'Pink', 2: 'Orange'}
        print("⚡ DUAL MCL Core (LOCK FIXED) инициализирован")
    
    async def _ensure_connectors(self):
        if not self._connectors_initialized:
            self._connectors = {
                1: aiohttp.TCPConnector(limit=0, ttl_dns_cache=3600, force_close=False, ssl=False),
                2: aiohttp.TCPConnector(limit=0, ttl_dns_cache=3600, force_close=False, ssl=False)
            }
            self._connectors_initialized = True
    
    async def get_session(self, token_id: int):
        await self._ensure_connectors()
        
        if self.sessions[token_id] and not self.sessions[token_id].closed:
            return self.sessions[token_id]
        
        async with self.session_locks[token_id]:
            if self.sessions[token_id] is None or self.sessions[token_id].closed:
                self.sessions[token_id] = aiohttp.ClientSession(
                    connector=self._connectors[token_id],
                    headers={'User-Agent': 'Mozilla/5.0'},
                    timeout=aiohttp.ClientTimeout(total=10)
                )
            return self.sessions[token_id]
    
    def prepare_headers(self, token_id: int):
        token = CONFIG[f'user_token_{token_id}']
        if self.headers_cache[token_id] and self.last_tokens[token_id] == token:
            return self.headers_cache[token_id]
        
        headers = {'Authorization': token, 'Content-Type': 'application/json'}
        self.headers_cache[token_id] = headers
        self.last_tokens[token_id] = token
        return headers
    
    def prepare_payload(self, token_id: int):
        msg = CONFIG[f'message_{token_id}']
        if (self.last_messages[token_id] == msg and 
            self.last_channel == CONFIG['channel_id'] and 
            self.payload_cache[token_id]):
            return self.payload_cache[token_id]
        
        payload = {'content': msg, 'tts': False}
        self.payload_cache[token_id] = payload
        self.last_messages[token_id] = msg
        self.last_channel = CONFIG['channel_id']
        return payload
    
    async def _send_infinite(self, token_id: int, task_id: int):
        url = f'https://discord.com/api/v9/channels/{CONFIG["channel_id"]}/messages'
        session = await self.get_session(token_id)
        headers = self.prepare_headers(token_id)
        payload = self.prepare_payload(token_id)
        
        attempt = 0
        start_time = time.time()
        
        while True:
            if task_id in active_mcl_tasks and active_mcl_tasks[task_id].get('cancelled', False):
                return False, attempt, time.time() - start_time, True
            
            attempt += 1
            try:
                async with session.post(url, json=payload, headers=headers) as resp:
                    self.stats[token_id]['total_attempts'] += 1
                    
                    if resp.status == 200:
                        self.stats[token_id]['success'] += 1
                        elapsed = time.time() - start_time
                        return True, attempt, elapsed, False
                    
                    elif resp.status == 429:
                        data = await resp.json()
                        retry_after = float(data.get('retry_after', 1))
                        await asyncio.sleep(retry_after)
                    else:
                        self.stats[token_id]['failed'] += 1
                        await asyncio.sleep(0.1)
                        
            except Exception as e:
                self.stats[token_id]['failed'] += 1
                await asyncio.sleep(0.1)
    
    async def send_dual(self, interaction):
        """Отправка с надёжной блокировкой повторного запуска"""
        user_id = str(interaction.user.id)
        
        # ===== БЛОКИРОВКА ПОВТОРНОГО ЗАПУСКА =====
        async with self.sending_lock:
            # Проверяем, не запущена ли уже отправка
            if self.sending_active:
                if self.current_sender:
                    await interaction.response.send_message(
                        f"❌ MCL **УЖЕ ЗАПУЩЕН** пользователем <@{self.current_sender}>\n"
                        f"👤 Отправитель: {self.sender_name}\n"
                        f"⏳ Дождитесь завершения или отмены.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "❌ MCL уже запущен. Дождитесь завершения.",
                        ephemeral=True
                    )
                return False
            
            # Устанавливаем флаги блокировки
            self.sending_active = True
            self.current_sender = user_id
            self.sender_name = interaction.user.display_name
        
        task_id = id(asyncio.current_task())
        active_mcl_tasks[task_id] = {'cancelled': False, 'user': user_id}
        overall_start = time.time()
        
        try:
            if not CONFIG['user_token_1'] or not CONFIG['user_token_2']:
                await interaction.response.send_message("❌ Нужны 2 токена", ephemeral=True)
                return False
            
            if not CONFIG['channel_id']:
                await interaction.response.send_message("❌ Канал не настроен", ephemeral=True)
                return False
            
            # Отправляем сообщение с кнопкой отмены
            embed = discord.Embed(
                title="🚀 DUAL MCL",
                description=f"**Запущено:** {interaction.user.mention}\n"
                           f"**Статус:** Ожидание отправки...\n"
                           f"⚡ Отправка может занять некоторое время",
                color=0xffa500
            )
            cancel_view = CancelView(task_id, user_id)
            await interaction.response.send_message(embed=embed, view=cancel_view, ephemeral=True)
            
            # Запускаем бесконечные попытки
            task1 = asyncio.create_task(self._send_infinite(1, task_id))
            task2 = asyncio.create_task(self._send_infinite(2, task_id))
            
            # Ждем результаты
            results = await asyncio.gather(task1, task2)
            
            total_elapsed = time.time() - overall_start
            success1, attempts1, time1, cancelled1 = results[0]
            success2, attempts2, time2, cancelled2 = results[1]
            
            # Проверяем отмену
            if cancelled1 or cancelled2 or (task_id in active_mcl_tasks and active_mcl_tasks[task_id].get('cancelled', False)):
                result_embed = discord.Embed(
                    title="🛑 ОТПРАВКА ОСТАНОВЛЕНА",
                    description=f"Пользователь {interaction.user.mention} остановил отправку",
                    color=0xff0000,
                    timestamp=datetime.now()
                )
                result_embed.add_field(
                    name=f"🎨 {self.token_colors[1]}",
                    value=f"{'✅' if success1 else '❌'} (попыток: {attempts1})",
                    inline=True
                )
                result_embed.add_field(
                    name=f"🎨 {self.token_colors[2]}",
                    value=f"{'✅' if success2 else '❌'} (попыток: {attempts2})",
                    inline=True
                )
            else:
                result_embed = discord.Embed(
                    title="✅ DUAL MCL",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                result_embed.add_field(
                    name=f"🎨 {self.token_colors[1]}",
                    value=f"{'✅' if success1 else '❌'} (попыток: {attempts1}, ⏱️ {time1:.2f}с)",
                    inline=False
                )
                result_embed.add_field(
                    name=f"🎨 {self.token_colors[2]}",
                    value=f"{'✅' if success2 else '❌'} (попыток: {attempts2}, ⏱️ {time2:.2f}с)",
                    inline=False
                )
                result_embed.add_field(
                    name="⚡ Общее время",
                    value=f"⏱️ {total_elapsed:.3f}с",
                    inline=False
                )
            
            await interaction.edit_original_response(embed=result_embed, view=None)
            db.log_command('MCL_DUAL', user_id, True, 
                          details=f'Попытки: {attempts1}/{attempts2}, Время: {total_elapsed:.2f}с')
            return True
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ ОШИБКА",
                description=str(e),
                color=0xff0000
            )
            await interaction.edit_original_response(embed=error_embed, view=None)
            db.log_command('MCL_DUAL', user_id, False, details=str(e))
            return False
        finally:
            # ===== СНИМАЕМ БЛОКИРОВКУ =====
            if task_id in active_mcl_tasks:
                del active_mcl_tasks[task_id]
            
            async with self.sending_lock:
                self.sending_active = False
                self.current_sender = None
                self.sender_name = None

dual_mcl_core = DualMCLCore()