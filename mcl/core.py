"""DUAL MCL Core - Ожидание отправки обоих токенов"""
import aiohttp
import asyncio
import time
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG

active_mcl_tasks = set()

class DualMCLCore:
    __slots__ = (
        'sessions', 'session_locks', 'headers_cache', 'last_tokens',
        'payload_cache', 'last_messages', 'last_channel', 
        'stats', 'token_colors', 'current_sender', 'sending_lock'
    )
    
    def __init__(self):
        self.sessions = {1: None, 2: None}
        self.session_locks = {1: asyncio.Lock(), 2: asyncio.Lock()}
        self.current_sender = None
        self.sending_lock = asyncio.Lock()
        self.headers_cache = {1: None, 2: None}
        self.last_tokens = {1: None, 2: None}
        self.payload_cache = {1: None, 2: None}
        self.last_messages = {1: None, 2: None}
        self.last_channel = None
        
        self.stats = {
            1: {'success': 0, 'failed': 0, 'total_attempts': 0},
            2: {'success': 0, 'failed': 0, 'total_attempts': 0}
        }
        self.token_colors = {1: 'Pink', 2: 'Blue'}
        print("⚡ DUAL MCL Core (RELIABLE MODE) инициализирован")
    
    async def get_session(self, token_id: int):
        if self.sessions[token_id] and not self.sessions[token_id].closed:
            return self.sessions[token_id]
        
        async with self.session_locks[token_id]:
            if self.sessions[token_id] is None or self.sessions[token_id].closed:
                self.sessions[token_id] = aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(limit=0, ttl_dns_cache=3600),
                    headers={'User-Agent': 'Mozilla/5.0'},
                    timeout=aiohttp.ClientTimeout(total=3)
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
    
    async def _send_with_retry(self, token_id: int, max_attempts: int = 5):
        """Отправка с повторными попытками до успеха"""
        url = f'https://discord.com/api/v9/channels/{CONFIG["channel_id"]}/messages'
        session = await self.get_session(token_id)
        headers = self.prepare_headers(token_id)
        payload = self.prepare_payload(token_id)
        
        for attempt in range(max_attempts):
            try:
                async with session.post(url, json=payload, headers=headers) as resp:
                    self.stats[token_id]['total_attempts'] += 1
                    
                    if resp.status == 200:
                        self.stats[token_id]['success'] += 1
                        return True, attempt + 1
                    elif resp.status == 429:
                        data = await resp.json()
                        retry_after = float(data.get('retry_after', 1))
                        await asyncio.sleep(retry_after)
                    else:
                        self.stats[token_id]['failed'] += 1
                        await asyncio.sleep(0.5)
            except Exception:
                self.stats[token_id]['failed'] += 1
                await asyncio.sleep(0.5)
        
        return False, max_attempts
    
    async def send_dual(self, interaction):
        """Отправка с ожиданием обоих токенов"""
        user_id = str(interaction.user.id)
        
        async with self.sending_lock:
            if self.current_sender and self.current_sender != user_id:
                await interaction.response.send_message(
                    f"❌ MCL уже запущен: <@{self.current_sender}>",
                    ephemeral=True
                )
                return False
            self.current_sender = user_id
        
        task_id = id(asyncio.current_task())
        active_mcl_tasks.add(task_id)
        start_time = time.time()
        
        try:
            if not CONFIG['user_token_1'] or not CONFIG['user_token_2']:
                await interaction.response.send_message("❌ Нужны 2 токена", ephemeral=True)
                return False
            
            if not CONFIG['channel_id']:
                await interaction.response.send_message("❌ Канал не настроен", ephemeral=True)
                return False
            
            await interaction.response.send_message("🚀 **DUAL MCL** | Ожидание отправки...", ephemeral=True)
            
            task1 = asyncio.create_task(self._send_with_retry(1))
            task2 = asyncio.create_task(self._send_with_retry(2))
            
            result1, result2 = await asyncio.gather(task1, task2)
            
            elapsed = time.time() - start_time
            success1, attempts1 = result1
            success2, attempts2 = result2
            
            embed = discord.Embed(
                title="✅ DUAL MCL",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name=f"🎨 {self.token_colors[1]}",
                value=f"{'✅' if success1 else '❌'} (попыток: {attempts1})",
                inline=True
            )
            embed.add_field(
                name=f"🎨 {self.token_colors[2]}",
                value=f"{'✅' if success2 else '❌'} (попыток: {attempts2})",
                inline=True
            )
            embed.add_field(
                name="⚡",
                value=f"⏱️ {elapsed:.3f}с",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            db.log_command('MCL_DUAL', user_id, True, details=f'{elapsed:.3f}с')
            return True
            
        except Exception as e:
            db.log_command('MCL_DUAL', user_id, False, details=str(e))
            return False
        finally:
            active_mcl_tasks.discard(task_id)
            async with self.sending_lock:
                self.current_sender = None

dual_mcl_core = DualMCLCore()