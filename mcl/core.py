"""DUAL MCL Core - Скорость + защита от 429"""
import aiohttp
import asyncio
import time
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG

active_mcl_tasks = set()

class RateLimiter:
    """Только для 429, без лишних задержек"""
    __slots__ = ('retry_after',)
    
    def __init__(self):
        self.retry_after = 0  # 0 = можно отправлять
    
    async def wait_if_needed(self):
        """Ждать только если есть 429"""
        if self.retry_after > 0:
            await asyncio.sleep(self.retry_after)
            self.retry_after = 0

class DualMCLCore:
    __slots__ = (
        'sessions', 'session_locks', 'headers_cache', 'last_tokens',
        'payload_cache', 'last_messages', 'last_channel', 
        'stats', 'token_colors', 'rate_limiters'
    )
    
    def __init__(self):
        self.sessions = {1: None, 2: None}
        self.session_locks = {1: asyncio.Lock(), 2: asyncio.Lock()}
        
        # Rate limiters только для 429
        self.rate_limiters = {1: RateLimiter(), 2: RateLimiter()}
        
        self.headers_cache = {1: None, 2: None}
        self.last_tokens = {1: None, 2: None}
        self.payload_cache = {1: None, 2: None}
        self.last_messages = {1: None, 2: None}
        self.last_channel = None
        
        self.stats = {
            1: {'success': 0, 'failed': 0, 'rate_limited': 0, 'total_attempts': 0},
            2: {'success': 0, 'failed': 0, 'rate_limited': 0, 'total_attempts': 0}
        }
        self.token_colors = {1: 'Pink', 2: 'Blue'}
        print("⚡ DUAL MCL Core (RACE READY) инициализирован")
    
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
    
    async def _send(self, session, url, payload, headers, token_id):
        """Отправка с обработкой 429"""
        try:
            # Ждем если был предыдущий 429
            await self.rate_limiters[token_id].wait_if_needed()
            
            async with session.post(url, json=payload, headers=headers) as resp:
                self.stats[token_id]['total_attempts'] += 1
                
                if resp.status == 200:
                    self.stats[token_id]['success'] += 1
                    return True
                    
                elif resp.status == 429:
                    self.stats[token_id]['rate_limited'] += 1
                    # Получаем время ожидания
                    data = await resp.json()
                    retry_after = float(data.get('retry_after', 1))
                    # Сохраняем в rate limiter
                    self.rate_limiters[token_id].retry_after = retry_after
                    return False
                    
                else:
                    self.stats[token_id]['failed'] += 1
                    return False
                    
        except Exception as e:
            self.stats[token_id]['failed'] += 1
            return False
    
    async def send_dual(self, interaction):
        """Максимально быстрая отправка"""
        user_id = str(interaction.user.id)
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
            
            await interaction.response.send_message("🚀 **DUAL MCL**", ephemeral=True)
            
            url = f'https://discord.com/api/v9/channels/{CONFIG["channel_id"]}/messages'
            
            # Параллельный запуск
            session1 = await self.get_session(1)
            session2 = await self.get_session(2)
            
            # Запускаем одновременно
            task1 = asyncio.create_task(
                self._send(session1, url, self.prepare_payload(1), self.prepare_headers(1), 1)
            )
            task2 = asyncio.create_task(
                self._send(session2, url, self.prepare_payload(2), self.prepare_headers(2), 2)
            )
            
            # Ждем результаты
            results = await asyncio.gather(task1, task2, return_exceptions=True)
            
            elapsed = time.time() - start_time
            
            # Если первый раз не удался из-за 429 - пробуем еще раз (только 1 раз)
            for i, token_id in enumerate([1, 2]):
                if results[i] is False and self.rate_limiters[token_id].retry_after > 0:
                    # Ждем сколько сказал Discord
                    await asyncio.sleep(self.rate_limiters[token_id].retry_after)
                    # Очищаем retry_after
                    self.rate_limiters[token_id].retry_after = 0
                    
                    # Повторная отправка
                    session = await self.get_session(token_id)
                    results[i] = await self._send(
                        session, url, 
                        self.prepare_payload(token_id), 
                        self.prepare_headers(token_id), 
                        token_id
                    )
            
            embed = discord.Embed(
                title="✅ DUAL MCL",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name=f"🎨 {self.token_colors[1]}",
                value=f"{'✅' if results[0] is True else '❌'}",
                inline=True
            )
            embed.add_field(
                name=f"🎨 {self.token_colors[2]}",
                value=f"{'✅' if results[1] is True else '❌'}",
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
    
    async def close(self):
        for i in [1, 2]:
            if self.sessions[i] and not self.sessions[i].closed:
                await self.sessions[i].close()

dual_mcl_core = DualMCLCore()