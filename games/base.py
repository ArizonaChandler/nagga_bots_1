"""Базовые классы для игр"""
import discord
from abc import ABC, abstractmethod


class BaseGame(ABC):
    """Базовый класс для всех игр"""
    
    def __init__(self, game_id: str, player1: discord.Member, player2: discord.Member, channel: discord.TextChannel):
        self.game_id = game_id
        self.player1 = player1
        self.player2 = player2
        self.channel = channel
        self.current_turn = player1
        self.winner = None
        self.game_over = False
    
    @abstractmethod
    async def make_move(self, user: discord.Member, data: dict) -> tuple:
        """Сделать ход. Возвращает (success, message, update_for_opponent)"""
        pass
    
    @abstractmethod
    def get_state(self) -> dict:
        """Получить состояние игры для сохранения"""
        pass
    
    @classmethod
    @abstractmethod
    def from_state(cls, state: dict, bot) -> 'BaseGame':
        """Восстановить игру из сохранённого состояния"""
        pass
    
    @abstractmethod
    async def get_display(self, player: discord.Member) -> tuple:
        """Получить embed и файлы для отображения игроку"""
        pass
    
    @abstractmethod
    def get_view(self, player: discord.Member):
        """Получить View для управления игрой"""
        pass
    
    def get_opponent(self, player: discord.Member) -> discord.Member:
        return self.player2 if player == self.player1 else self.player1
    
    def is_player_in_game(self, user_id: str) -> bool:
        return str(self.player1.id) == user_id or str(self.player2.id) == user_id