"""Точки интеграции с другими модулями"""
from economy.manager import economy_manager


def setup_integration(bot):
    """Интеграция с CAPT, MCL, Tier, Events, Applications"""
    
    # Функции для вызова из других модулей
    async def on_capt_complete(user_id: int, is_main: bool):
        await economy_manager.award_capt(user_id, is_main)
    
    async def on_mcl_complete(user_id: int, is_main: bool):
        await economy_manager.award_mcl(user_id, is_main)
    
    async def on_event_taken(user_id: int):
        await economy_manager.award_event(user_id)
    
    async def on_application_accepted(user_id: int):
        await economy_manager.award_application(user_id)
    
    async def on_tier_up(user_id: int, tier: str):
        await economy_manager.award_tier(user_id, tier)
    
    # Прикрепляем к боту
    bot.on_capt_complete = on_capt_complete
    bot.on_mcl_complete = on_mcl_complete
    bot.on_event_taken = on_event_taken
    bot.on_application_accepted = on_application_accepted
    bot.on_tier_up = on_tier_up