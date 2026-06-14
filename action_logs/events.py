"""Функции для логирования событий (вызываются из bot.py)"""
from datetime import datetime
from action_logs.manager import action_logs_manager


async def log_voice_state(member, before, after):
    """Логирование голосовых событий"""
    if not before.channel and after.channel:
        await action_logs_manager.log(
            guild_id=str(member.guild.id),
            event_type='voice_join',
            user_id=str(member.id),
            details=f"Вошёл в канал: {after.channel.name}"
        )
    elif before.channel and not after.channel:
        await action_logs_manager.log(
            guild_id=str(member.guild.id),
            event_type='voice_leave',
            user_id=str(member.id),
            details=f"Вышел из канала: {before.channel.name}"
        )
    elif before.channel and after.channel and before.channel != after.channel:
        await action_logs_manager.log(
            guild_id=str(member.guild.id),
            event_type='voice_move',
            user_id=str(member.id),
            details=f"Перемещён из {before.channel.name} в {after.channel.name}"
        )


async def log_message_edit(before, after):
    """Логирование редактирования сообщений (с сохранением что было и что стало)"""
    if before.author.bot:
        return
    if before.content == after.content:
        return
    
    before_text = before.content[:500] if before.content else "(пусто)"
    after_text = after.content[:500] if after.content else "(пусто)"
    
    await action_logs_manager.log(
        guild_id=str(before.guild.id),
        event_type='message_edit',
        user_id=str(before.author.id),
        details=f"Канал: {before.channel.mention} | [Перейти к сообщению]({before.jump_url})",
        before=before_text,
        after=after_text
    )


async def log_message_delete(message):
    """Логирование удаления сообщений"""
    if message.author.bot:
        return
    
    await action_logs_manager.log(
        guild_id=str(message.guild.id),
        event_type='message_delete',
        user_id=str(message.author.id),
        details=f"Канал: {message.channel.mention}\nСодержание: {message.content[:500] if message.content else '(пусто)'}"
    )


async def log_channel_create(channel):
    """Логирование создания канала"""
    await action_logs_manager.log(
        guild_id=str(channel.guild.id),
        event_type='channel_create',
        user_id='system',
        details=f"Создан канал: {channel.name} (тип: {channel.type})"
    )


async def log_channel_delete(channel):
    """Логирование удаления канала"""
    await action_logs_manager.log(
        guild_id=str(channel.guild.id),
        event_type='channel_delete',
        user_id='system',
        details=f"Удалён канал: {channel.name} (тип: {channel.type})"
    )


async def log_channel_update(before, after):
    """Логирование изменения канала"""
    changes = []
    if before.name != after.name:
        changes.append(f"название: {before.name} → {after.name}")
    if hasattr(before, 'topic') and hasattr(after, 'topic') and before.topic != after.topic:
        changes.append(f"тема: {before.topic[:50] if before.topic else 'нет'} → {after.topic[:50] if after.topic else 'нет'}")
    
    if changes:
        await action_logs_manager.log(
            guild_id=str(before.guild.id),
            event_type='channel_update',
            user_id='system',
            details=f"Изменён канал {before.name}: {', '.join(changes)}"
        )


async def log_member_join(member):
    """Логирование присоединения участника"""
    await action_logs_manager.log(
        guild_id=str(member.guild.id),
        event_type='member_join',
        user_id=str(member.id),
        details=f"Пользователь присоединился к серверу"
    )


async def log_member_remove(member):
    """Логирование ухода участника"""
    await action_logs_manager.log(
        guild_id=str(member.guild.id),
        event_type='member_leave',
        user_id=str(member.id),
        details=f"Пользователь покинул сервер"
    )


async def log_member_update(before, after):
    """Логирование изменения профиля участника"""
    changes = []
    
    if before.nick != after.nick:
        changes.append(f"ник: {before.nick or 'нет'} → {after.nick or 'нет'}")
    
    before_roles = set(before.roles)
    after_roles = set(after.roles)
    
    for role in after_roles - before_roles:
        if not role.is_default():
            await action_logs_manager.log(
                guild_id=str(before.guild.id),
                event_type='role_grant',
                user_id=str(before.id),
                target_id=str(role.id),
                details=f"Выдана роль: {role.name}"
            )
    
    for role in before_roles - after_roles:
        if not role.is_default():
            await action_logs_manager.log(
                guild_id=str(before.guild.id),
                event_type='role_revoke',
                user_id=str(before.id),
                target_id=str(role.id),
                details=f"Снята роль: {role.name}"
            )
    
    if changes:
        await action_logs_manager.log(
            guild_id=str(before.guild.id),
            event_type='member_update',
            user_id=str(before.id),
            details=f"Изменён профиль: {', '.join(changes)}"
        )


async def log_role_create(role):
    """Логирование создания роли"""
    await action_logs_manager.log(
        guild_id=str(role.guild.id),
        event_type='role_create',
        user_id='system',
        details=f"Создана роль: {role.name}"
    )


async def log_role_delete(role):
    """Логирование удаления роли"""
    await action_logs_manager.log(
        guild_id=str(role.guild.id),
        event_type='role_delete',
        user_id='system',
        details=f"Удалена роль: {role.name}"
    )


async def log_member_ban(guild, user, reason=None, moderator=None):
    """Логирование бана участника"""
    await action_logs_manager.log(
        guild_id=str(guild.id),
        event_type='member_ban',
        user_id=str(user.id),
        target_id=str(moderator.id) if moderator else None,
        details=f"Забанен участник: {user.name} (ID: {user.id})\nПричина: {reason if reason else 'Не указана'}"
    )


async def log_member_unban(guild, user, moderator=None):
    """Логирование разбана участника"""
    await action_logs_manager.log(
        guild_id=str(guild.id),
        event_type='member_unban',
        user_id=str(user.id),
        target_id=str(moderator.id) if moderator else None,
        details=f"Разбанен участник: {user.name} (ID: {user.id})"
    )


async def log_member_kick(member, moderator=None, reason=None):
    """Логирование кика участника"""
    await action_logs_manager.log(
        guild_id=str(member.guild.id),
        event_type='member_kick',
        user_id=str(member.id),
        target_id=str(moderator.id) if moderator else None,
        details=f"Кикнут участник: {member.name} (ID: {member.id})\nМодератор: {moderator.name if moderator else 'Система'}\nПричина: {reason if reason else 'Не указана'}"
    )


async def log_member_timeout(member, moderator=None, until=None, reason=None):
    """Логирование тайм-аута участника"""
    duration = (until - datetime.now()).total_seconds() // 60 if until else 0
    await action_logs_manager.log(
        guild_id=str(member.guild.id),
        event_type='member_timeout',
        user_id=str(member.id),
        target_id=str(moderator.id) if moderator else None,
        details=f"Тайм-аут участника: {member.name}\nМодератор: {moderator.name if moderator else 'Система'}\nДлительность: {int(duration)} минут\nДо: {until.strftime('%d.%m.%Y %H:%M') if until else 'Не указано'}\nПричина: {reason if reason else 'Не указана'}"
    )