from admin.views import (
    MainView, SettingsView, CaptSettingsView, 
    MclSettingsView, GlobalSettingsView, AccessView, AdminView,
    EventSettingsView, EventsListView, EventDetailView
)
from admin.modals import (
    SetRoleModal, SetCaptChannelModal, SetServerModal,
    AddUserModal, RemoveUserModal, AddAdminModal, RemoveAdminModal,
    SetAlarmChannelModal, SetAnnounceChannelModal, AddEventModal, EditEventModal, TakeEventModal,
    SetCaptAlertChannelModal, SetCaptRoleModal  # ДОБАВЛЕНЫ новые модалки
)

__all__ = [
    'MainView', 'SettingsView', 'CaptSettingsView', 'MclSettingsView',
    'GlobalSettingsView', 'AccessView', 'AdminView', 'EventSettingsView',
    'EventsListView', 'EventDetailView', 'SetRoleModal', 'SetCaptChannelModal',
    'SetServerModal', 'AddUserModal', 'RemoveUserModal', 'AddAdminModal',
    'RemoveAdminModal', 'SetAlarmChannelModal', 'SetAnnounceChannelModal',
    'AddEventModal', 'EditEventModal', 'TakeEventModal',
    'SetCaptAlertChannelModal', 'SetCaptRoleModal'  # ДОБАВЛЕНЫ
]