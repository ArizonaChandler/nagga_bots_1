"""Система регистрации на CAPT"""
from capt_registration.manager import capt_reg_manager
from capt_registration.views import ModerationView, PublicView
from capt_registration.embeds import create_registration_embed

__all__ = [
    'capt_reg_manager',
    'ModerationView',
    'PublicView',
    'create_registration_embed'
]