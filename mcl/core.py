"""DUAL MCL Core - Параллельная отправка с двух токенов"""
import aiohttp
import asyncio
import time
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG

active_mcl_tasks = set()

class RateLimiter:
    def __init__(self):
        self.min_interval = 0.02
        self.last_request_time = 0
        self.current_backoff = 0
        self.backoff_multiplier = 1.5
    
    async def wait_if_needed(self):
        now = time.time()
        if self.last_request_time > 0:
            elapsed = now - self.last_request_time
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
        if self.current_backoff > 0:
            await asyncio.sleep(self.current_backoff)
            self.current_backoff = 0
        self.last_request_time = time.time()
    
    async def handle_rate_limit(self, retry_after: float):
        self.current_backoff = retry_after * self.backoff_multiplier
        self.backoff_multiplier = min(self.backoff_multiplier * 1.5, 10.0)
        await asyncio.sleep(retry_after)

class DualMCLCore:
    def __init__(self):
        self.sessions = {1: None, 2: None}
        self.session_locks = {1: asyncio.Lock(), 2: asyncio.Lock()}
        self.headers_cache = {1: None, 2: None}
        self.last_tokens = {1: None, 2: None}
        self.payload_cache = {1: None, 2: None}
        self.last_messages = {1: None, 2: None}
        self.last_channel = None
        self.rate_limiters = {1: RateLimiter(), 2: RateLimiter()}
        self.stats = {
            1: {'success': 0, 'failed': 0, 'rate_limited': 0, 'total_attempts': 0},
            2: {'success': 0, 'failed': 0, 'rate_limited': 0, 'total_attempts': 0}
        }
        self.token_colors = {1: 'Pink', 2: 'Blue'}
        print("🎨 DUAL MCL Core инициализирован")
    
    async def get_session(self, token_id: int):
        async with self.session_locks[token_id]:
            if self.sessions[token_id] is None or self.sessions[token_id].closed:
                connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
                self.sessions[token_id] = aiohttp.ClientSession(
                    connector=connector,
                    headers={'User-Agent': 'Mozilla/5.0', 'Connection': 'keep-alive'}
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
    
    async def send_dual(self, interaction):
        user_id = str(interaction.user.id)
        task_id = id(asyncio.current_task())
        active_mcl_tasks.add(task_id)
        
        start_time = time.time()
        
        try:
            if not CONFIG['user_token_1'] or not CONFIG['user_token_2']:
                await interaction.response.send_message("❌ Требуется два токена в .env", ephemeral=True)
                return False
            
            if not CONFIG['channel_id']:
                await interaction.response.send_message("❌ Канал MCL не настроен", ephemeral=True)
                return False
            
            await interaction.response.send_message(f"🚀 **DUAL MCL** | Отправка...", ephemeral=True)
            
            headers_1 = self.prepare_headers(1)
            headers_2 = self.prepare_headers(2)
            payload_1 = self.prepare_payload(1)
            payload_2 = self.prepare_payload(2)
            url = f'https://discord.com/api/v9/channels/{CONFIG["channel_id"]}/messages'
            
            session_1 = await self.get_session(1)
            session_2 = await self.get_session(2)
            
            successes = {1: False, 2: False}
            attempts = {1: 1, 2: 1}
            
            while not (successes[1] and successes[2]):
                if task_id not in active_mcl_tasks:
                    return False
                
                tasks = []
                if not successes[1]:
                    await self.rate_limiters[1].wait_if_needed()
                    tasks.append(self._send_request(session_1, url, payload_1, headers_1, 1))
                if not successes[2]:
                    await self.rate_limiters[2].wait_if_needed()
                    tasks.append(self._send_request(session_2, url, payload_2, headers_2, 2))
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    idx = 0
                    if not successes[1]:
                        if results[idx] is True:
                            successes[1] = True
                            self.stats[1]['success'] += 1
                        else:
                            attempts[1] += 1
                        idx += 1
                    if not successes[2]:
                        if results[idx] is True:
                            successes[2] = True
                            self.stats[2]['success'] += 1
                        else:
                            attempts[2] += 1
                
                await asyncio.sleep(0.01)
            
            elapsed = time.time() - start_time
            
            embed = discord.Embed(
                title="✅ DUAL MCL отправлен!",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.add_field(
                name=f"🎨 Токен 1 ({self.token_colors[1]})",
                value=f"✅ Успех за {attempts[1]} попыток",
                inline=True
            )
            embed.add_field(
                name=f"🎨 Токен 2 ({self.token_colors[2]})",
                value=f"✅ Успех за {attempts[2]} попыток",
                inline=True
            )
            embed.add_field(
                name="⚡ Производительность",
                value=f"⏱️ Время: `{elapsed:.2f}с`\n📨 Канал: <#{CONFIG['channel_id']}>",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            db.log_command('MCL_DUAL', user_id, True, details=f'Попытки: {attempts[1]}/{attempts[2]}, Время: {elapsed:.1f}с')
            return True
            
        except Exception as e:
            db.log_command('MCL_DUAL', user_id, False, details=str(e))
            return False
        finally:
            active_mcl_tasks.discard(task_id)
    
    async def _send_request(self, session, url, payload, headers, token_id):
        try:
            async with session.post(url, json=payload, headers=headers) as resp:
                self.stats[token_id]['total_attempts'] += 1
                if resp.status == 200:
                    return True
                elif resp.status == 429:
                    self.stats[token_id]['rate_limited'] += 1
                    retry_after = await self._get_retry_time(resp)
                    await self.rate_limiters[token_id].handle_rate_limit(retry_after)
                    return False
                else:
                    self.stats[token_id]['failed'] += 1
                    return False
        except:
            self.stats[token_id]['failed'] += 1
            return False
    
    async def _get_retry_time(self, response):
        try:
            data = await response.json()
            return float(data.get('retry_after', 1))
        except:
            return 1.0
    
    async def close(self):
        for i in [1, 2]:
            if self.sessions[i] and not self.sessions[i].closed:
                await self.sessions[i].close()

dual_mcl_core = DualMCLCore()