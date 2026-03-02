from admin.views import (
    MainView, SettingsView, GlobalSettingsView,
    AccessView, AdminView, EventSettingsView,
    EventsListView, EventDetailView, CaptRegistrationSettingsView
)
from admin.modals import (
    SetRoleModal, SetCaptChannelModal, SetServerModal,
    AddUserModal, RemoveUserModal, AddAdminModal, RemoveAdminModal,
    SetAlarmChannelModal, SetAnnounceChannelModal, AddEventModal, EditEventModal, TakeEventModal,
    SetAlarmChannelsModal, SetAnnounceChannelsModal, SetReminderRolesModal, SetAnnounceRolesModal,
    SetCaptAlertChannelModal, SetCaptRoleModal, SetCaptRegChannelsModal,
    SetCaptSettingsChannelModal, SetAdSettingsChannelModal, SetEventsSettingsChannelModal
)
from capt_registration.settings_view import CaptSettingsView
from mcl.views import MclSettingsView

__all__ = [
    # Views
    'MainView', 'SettingsView', 'GlobalSettingsView',
    'AccessView', 'AdminView', 'EventSettingsView',
    'EventsListView', 'EventDetailView', 'CaptRegistrationSettingsView',
    'CaptSettingsView', 'MclSettingsView',
    
    # Modals
    'SetRoleModal', 'SetCaptChannelModal', 'SetServerModal',
    'AddUserModal', 'RemoveUserModal', 'AddAdminModal', 'RemoveAdminModal',
    'SetAlarmChannelModal', 'SetAnnounceChannelModal', 'AddEventModal', 
    'EditEventModal', 'TakeEventModal', 'SetAlarmChannelsModal',
    'SetAnnounceChannelsModal', 'SetReminderRolesModal', 'SetAnnounceRolesModal',
    'SetCaptAlertChannelModal', 'SetCaptRoleModal', 'SetCaptRegChannelsModal',
    'SetCaptSettingsChannelModal', 'SetAdSettingsChannelModal', 'SetEventsSettingsChannelModal'
]