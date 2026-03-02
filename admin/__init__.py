from admin.views import (
    MainView, SettingsView,  # Убрали MclSettingsView, так как его нет
    GlobalSettingsView, AccessView, AdminView,
    EventSettingsView, EventsListView, EventDetailView,
)
from admin.modals import (
    SetRoleModal, SetCaptChannelModal, SetServerModal,
    AddUserModal, RemoveUserModal, AddAdminModal, RemoveAdminModal,
    SetAlarmChannelModal, SetAnnounceChannelModal, AddEventModal, EditEventModal, TakeEventModal,
    SetAlarmChannelsModal, SetAnnounceChannelsModal, SetReminderRolesModal, SetAnnounceRolesModal,
    SetCaptAlertChannelModal, SetCaptRoleModal, SetCaptRegChannelsModal,
    SetCaptSettingsChannelModal, SetAdSettingsChannelModal
)
from capt_registration.settings_view import CaptSettingsView
from mcl.views import MclSettingsView  # Импортируем из правильного места

__all__ = [
    # Views
    'MainView', 'SettingsView',
    'GlobalSettingsView', 'AccessView', 'AdminView', 'EventSettingsView',
    'EventsListView', 'EventDetailView', 'CaptSettingsView', 'MclSettingsView',
    
    # Modals
    'SetRoleModal', 'SetCaptChannelModal', 'SetServerModal',
    'AddUserModal', 'RemoveUserModal', 'AddAdminModal', 'RemoveAdminModal',
    'SetAlarmChannelModal', 'SetAnnounceChannelModal', 'AddEventModal', 
    'EditEventModal', 'TakeEventModal', 'SetAlarmChannelsModal',
    'SetAnnounceChannelsModal', 'SetReminderRolesModal', 'SetAnnounceRolesModal',
    'SetCaptAlertChannelModal', 'SetCaptRoleModal', 'SetCaptRegChannelsModal',
    'SetCaptSettingsChannelModal', 'SetAdSettingsChannelModal'
]