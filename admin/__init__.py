from admin.views import (
    MainView, SettingsView, CaptSettingsView, 
    MclSettingsView, GlobalSettingsView, AccessView, AdminView,
    EventSettingsView, EventsListView, EventDetailView,
    CaptRegistrationSettingsView
)
from admin.modals import (
    SetRoleModal, SetCaptChannelModal, SetServerModal,
    AddUserModal, RemoveUserModal, AddAdminModal, RemoveAdminModal,
    SetAlarmChannelModal, SetAnnounceChannelModal, AddEventModal, EditEventModal, TakeEventModal,
    SetAlarmChannelsModal, SetAnnounceChannelsModal, SetReminderRolesModal, SetAnnounceRolesModal,
    SetCaptAlertChannelModal, SetCaptRoleModal, SetCaptRegChannelsModal,
    SetCaptSettingsChannelModal
)

__all__ = [
    # Views
    'MainView', 'SettingsView', 'CaptSettingsView', 'MclSettingsView',
    'GlobalSettingsView', 'AccessView', 'AdminView', 'EventSettingsView',
    'EventsListView', 'EventDetailView', 'CaptRegistrationSettingsView',
    
    # Modals - старые
    'SetRoleModal', 'SetCaptChannelModal', 'SetServerModal',
    'AddUserModal', 'RemoveUserModal', 'AddAdminModal', 'RemoveAdminModal',
    
    # Modals - система оповещений
    'SetAlarmChannelModal', 'SetAnnounceChannelModal', 'AddEventModal', 
    'EditEventModal', 'TakeEventModal', 'SetAlarmChannelsModal',
    'SetAnnounceChannelsModal', 'SetReminderRolesModal', 'SetAnnounceRolesModal',
    
    # Modals - система CAPT
    'SetCaptAlertChannelModal', 'SetCaptRoleModal', 'SetCaptRegChannelsModal',
    'SetCaptSettingsChannelModal'
]