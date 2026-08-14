"""Работа с шаблонами мероприятий из планировщика"""
from core.database import db


def get_event_templates(enabled_only: bool = True) -> list:
    """Получить шаблоны мероприятий из планировщика"""
    return db.get_events(enabled_only=enabled_only)


def get_event_template(event_id: int) -> dict:
    """Получить конкретный шаблон по ID"""
    return db.get_event(event_id)


def format_templates_for_select(templates: list) -> list:
    """Форматировать шаблоны для Discord Select"""
    days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    options = []
    for template in templates[:25]:
        label = f"{template['name']} ({days[template['weekday']]} {template['event_time']})"
        options.append(
            discord.SelectOption(
                label=label[:100],
                value=str(template['id'])
            )
        )
    return options