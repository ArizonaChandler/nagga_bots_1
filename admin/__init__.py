from admin.views import (
    MainView, SettingsView, MclSettingsView, GlobalSettingsView, 
    AccessView, AdminView, EventSettingsView, EventsListView, EventDetailView,
)
from admin.modals import (
    SetRoleModal, SetCaptChannelModal, SetServerModal,
    AddUserModal, RemoveUserModal, AddAdminModal, RemoveAdminModal,
    SetAlarmChannelModal, SetAnnounceChannelModal, AddEventModal, EditEventModal, TakeEventModal,
    SetAlarmChannelsModal, SetAnnounceChannelsModal, SetReminderRolesModal, SetAnnounceRolesModal,
    SetCaptAlertChannelModal, SetCaptRoleModal, SetCaptRegChannelsModal,
    SetCaptSettingsChannelModal, SetAdSettingsChannelModal
)
from capt_registration.settings_view import CaptSettingsView  # Прямой импорт

__all__ = [
    # Views
    'MainView', 'SettingsView', 'MclSettingsView',
    'GlobalSettingsView', 'AccessView', 'AdminView', 'EventSettingsView',
    'EventsListView', 'EventDetailView', 'CaptSettingsView',  # Добавлено
    
    # Modals
    'SetRoleModal', 'SetCaptChannelModal', 'SetServerModal',
    'AddUserModal', 'RemoveUserModal', 'AddAdminModal', 'RemoveAdminModal',
    'SetAlarmChannelModal', 'SetAnnounceChannelModal', 'AddEventModal', 
    'EditEventModal', 'TakeEventModal', 'SetAlarmChannelsModal',
    'SetAnnounceChannelsModal', 'SetReminderRolesModal', 'SetAnnounceRolesModal',
    'SetCaptAlertChannelModal', 'SetCaptRoleModal', 'SetCaptRegChannelsModal',
    'SetCaptSettingsChannelModal', 'SetAdSettingsChannelModal'
]