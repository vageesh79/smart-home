"""Define automations for appliances."""

# pylint: disable=attribute-defined-outside-init,too-many-arguments
# pylint: disable=unused-argument,too-many-instance-attributes

from datetime import timedelta
from enum import Enum
from typing import Union

from app import App
from automation import Automation, Feature
from lib.const import (HANDLER_DISHWASHER_CLEAN, HANDLER_VACUUM_FULL,
                       HANDLER_VACUUM_SCHEDULE)


class WasherDryer(App):
    """Define an app to represent a washer/dryer-type appliance."""

    class States(Enum):
        """Define an enum for states."""
        clean = 'Clean'
        dirty = 'Dirty'
        drying = 'Drying'
        running = 'Running'

    @property
    def state(self) -> Enum:
        """Get the state."""
        current = self.get_state(self.entities['status'])
        try:
            return self.States(current)
        except KeyError:
            self.error('Unknown dishwasher state: {0}'.format(current))
            return None

    @state.setter
    def state(self, value: Enum) -> None:
        """Set the state."""
        self.call_service(
            'input_select/select_option',
            entity_id=self.entities['status'],
            option=value.value)


class WasherDryerAutomation(Automation):
    """Define a class to represent automations for washer/dryer appliances."""

    class NotifyDone(Feature):
        """Define a feature to notify a target when the appliancer is done."""

        def initialize(self) -> None:
            """Initialize."""
            self.hass.listen_event(
                self.response_from_push_notification,
                'ios.notification_action_fired',
                actionName='APPLIANCE_EMPTIED',
                constrain_input_boolean=self.constraint)
            self.hass.listen_state(
                self.power_changed,
                self.hass.manager_app.entities['power'],
                constrain_input_boolean=self.constraint)
            self.hass.listen_state(
                self.status_changed,
                self.hass.manager_app.entities['status'],
                constrain_input_boolean=self.constraint)

        def power_changed(self, entity: Union[str, dict], attribute: str,
                          old: str, new: str, kwargs: dict) -> None:
            """Deal with changes to the power draw."""
            power = float(new)
            if (self.hass.manager_app.state !=
                    self.hass.manager_app.States.running
                    and power >= self.properties['running_threshold']):
                self.hass.log('Setting dishwasher to "Running"')

                self.hass.manager_app.state = (
                    self.hass.manager_app.States.running)
            elif (self.hass.manager_app.state ==
                  self.hass.manager_app.States.running
                  and power <= self.properties['drying_threshold']):
                self.hass.log('Setting dishwasher to "Drying"')

                self.hass.manager_app.state = (
                    self.hass.manager_app.States.drying)
            elif (self.hass.manager_app.state ==
                  self.hass.manager_app.States.drying
                  and power == self.properties['clean_threshold']):
                self.hass.log('Setting dishwasher to "Clean"')

                self.hass.manager_app.state = (
                    self.hass.manager_app.States.clean)

        def status_changed(self, entity: Union[str, dict], attribute: str,
                           old: str, new: str, kwargs: dict) -> None:
            """Deal with changes to the status."""
            if new == self.hass.manager_app.States.dirty.value:
                self.hass.briefing_manager.deregister(HANDLER_DISHWASHER_CLEAN)
            elif new == self.hass.manager_app.States.clean.value:
                self.hass.notification_manager.repeat(
                    'Dishwasher Clean',
                    "Empty it now and you won't have to do it later!",
                    60 * 60,
                    when=self.hass.datetime() + timedelta(minutes=15),
                    target='home',
                    data={'push': {
                        'category': 'appliances'
                    }})
                self.hass.briefing_manager.register(
                    self.hass.briefing_manager.BriefingTypes.recurring,
                    'The dishwasher needs to be emptied.',
                    key=HANDLER_DISHWASHER_CLEAN)

        def response_from_push_notification(self, event_name: str, data: dict,
                                            kwargs: dict) -> None:
            """Respond to iOS notification to empty the appliance."""
            self.hass.log('Responding to iOS request that dishwasher is empty')

            self.hass.manager_app.state = self.hass.manager_app.States.dirty

            target = self.hass.notification_manager.get_target_from_push_id(
                data['sourceDevicePermanentID'])
            self.hass.notification_manager.send(
                'Dishwasher Emptied',
                '{0} emptied the dishwasher.'.format(target),
                target='not {0}'.format(target))


class Vacuum(App):
    """Define an app to represent a vacuum-type appliance."""

    @property
    def bin_state(self) -> Enum:
        """Define a property to get the bin state."""
        current = self.get_state(self.entities['bin_state'])
        try:
            return self.BinStates(current)  # pylint: disable=E1136
        except KeyError:
            self.error('Unknown bin state: {0}'.format(current))
            return None

    @bin_state.setter
    def bin_state(self, value: Enum) -> None:
        """Set the bin state."""
        self.call_service(
            'input_select/select_option',
            entity_id=self.entities['bin_state'],
            option=value.value)

    class BinStates(Enum):
        """Define an enum for vacuum bin states."""
        empty = 'Empty'
        full = 'Full'

    class States(Enum):
        """Define an enum for vacuum states."""
        charger_disconnected = 'Charger disconnected'
        charging_problem = 'Charging problem'
        charging = 'Charging'
        cleaning = 'Cleaning'
        docking = 'Docking'
        error = 'Error'
        going_to_target = 'Going to target'
        idle = 'Idle'
        manual_mode = 'Manual mode'
        paused = 'Paused'
        remote_control_active = 'Remote control active'
        returning_home = 'Returning home'
        shutting_down = 'Shutting down'
        spot_cleaning = 'Spot cleaning'
        starting = 'Starting'
        updating = 'Updating'
        zoned_cleaning = 'Zoned cleaning'

    def start(self) -> None:
        """Initiate a cleaning cycle."""
        self.log('Starting vacuuming cycle')

        if self.security_system.state == self.security_system.AlarmStates.away:
            self.log('Changing alarm state to "Home"')

            self.security_system.state = self.security_system.AlarmStates.home
        else:
            self.log('Activating vacuum')

            self.turn_on(self.entities['vacuum'])


class VacuumAutomation(Automation):
    """Define a class to represent automations for vacuums."""

    class MonitorConsumables(Feature):
        """Define a feature to notify when a consumable gets low."""

        def initialize(self) -> None:
            """Initialize."""
            for consumable in self.properties['consumables']:
                self.hass.listen_state(
                    self.consumable_changed,
                    self.hass.manager_app.entities['vacuum'],
                    attribute=consumable,
                    constrain_input_boolean=self.constraint)

        def consumable_changed(self, entity: Union[str, dict], attribute: str,
                               old: str, new: str, kwargs: dict) -> None:
            """Create a task when a consumable is getting low."""
            if int(new) < self.properties['consumable_threshold']:
                self.hass.log('Consumable is low: {0}'.format(attribute))

                self.hass.notification_manager.create_omnifocus_task(
                    'Order a new Wolfie consumable: {0}'.format(attribute))

    class ScheduledCycle(Feature):
        """Define a feature to run the vacuum on a schedule."""

        @property
        def active_days(self) -> list:
            """Get the days that the vacuuming schedule should run."""
            on_days = []
            for toggle in self.properties['schedule_switches']:
                state = self.hass.get_state(toggle, attribute='all')
                if state['state'] == 'on':
                    on_days.append(state['attributes']['friendly_name'])

            return on_days

        def initialize(self) -> None:
            """Initialize."""
            self.initiated_by_app = False

            self.create_schedule()

            self.hass.listen_event(
                self.alarm_changed,
                'ALARM_CHANGE',
                constrain_input_boolean=self.constraint)
            self.hass.listen_event(
                self.start_by_switch,
                'VACUUM_START',
                constrain_input_boolean=self.constraint)
            self.hass.listen_event(
                self.response_from_push_notification,
                'ios.notification_action_fired',
                actionName='APPLIANCE_EMPTIED',
                constrain_input_boolean=self.constraint)
            self.hass.listen_state(
                self.errored,
                self.hass.manager_app.entities['status'],
                new=self.hass.manager_app.States.charger_disconnected.value,
                constrain_input_boolean=self.constraint)
            self.hass.listen_state(
                self.errored,
                self.hass.manager_app.entities['status'],
                new=self.hass.manager_app.States.error.value,
                constrain_input_boolean=self.constraint)
            self.hass.listen_state(
                self.all_done,
                self.hass.manager_app.entities['status'],
                old=self.hass.manager_app.States.returning_home.value,
                new=self.hass.manager_app.States.charging.value,
                constrain_input_boolean=self.constraint)
            self.hass.listen_state(
                self.bin_state_changed,
                self.hass.manager_app.entities['bin_state'],
                constrain_input_boolean=self.constraint)
            for toggle in self.properties['schedule_switches']:
                self.hass.listen_state(
                    self.schedule_changed,
                    toggle,
                    constrain_input_boolean=self.constraint)

        def alarm_changed(self, event_name: str, data: dict,
                          kwargs: dict) -> None:
            """Respond to 'ALARM_CHANGE' events."""
            state = self.hass.manager_app.States(
                self.hass.get_state(self.hass.manager_app.entities['status']))

            # Scenario 1: Vacuum is charging and is told to start:
            if ((self.initiated_by_app
                 and state == self.hass.manager_app.States.charging)
                    and data['state'] ==
                    self.hass.security_system.AlarmStates.home.value):
                self.hass.log('Activating vacuum (post-security)')

                self.hass.turn_on(self.hass.manager_app.entities['vacuum'])

            # Scenario 2: Vacuum is running when alarm is set to "Away":
            elif (state == self.hass.manager_app.States.cleaning
                  and data['state'] ==
                  self.hass.security_system.AlarmStates.away.value):
                self.hass.log('Security mode is "Away"; pausing until "Home"')

                self.hass.call_service(
                    'vacuum/start_pause',
                    entity_id=self.hass.manager_app.entities['vacuum'])
                self.hass.security_system.state = (
                    self.hass.security_system.AlarmStates.home)

            # Scenario 3: Vacuum is paused when alarm is set to "Home":
            elif (state == self.hass.manager_app.States.paused
                  and data['state'] ==
                  self.hass.security_system.AlarmStates.home.value):
                self.hass.log('Alarm in "Home"; resuming')

                self.hass.call_service(
                    'vacuum/start_pause',
                    entity_id=self.hass.manager_app.entities['vacuum'])

        def all_done(self, entity: Union[str, dict], attribute: str, old: str,
                     new: str, kwargs: dict) -> None:
            """Re-arm security (if needed) when done."""
            self.hass.log('Vacuuming cycle all done')

            if (self.hass.presence_manager.noone(
                    self.hass.presence_manager.HomeStates.just_arrived,
                    self.hass.presence_manager.HomeStates.home)):
                self.hass.log('Changing alarm state to "away"')

                self.hass.security_system.state = (
                    self.hass.security_system.AlarmStates.away)

            self.hass.manager_app.bin_state = (
                self.hass.manager_app.BinStates.full)
            self.initiated_by_app = False

        def bin_state_changed(self, entity: Union[str, dict], attribute: str,
                              old: str, new: str, kwargs: dict) -> None:
            """Listen for changes in bin status."""
            if new == self.hass.manager_app.BinStates.empty.value:
                self.hass.briefing_manager.deregister(HANDLER_VACUUM_FULL)
            elif new == self.hass.manager_app.BinStates.full.value:
                self.hass.notification_manager.repeat(
                    'Vacuum Full',
                    "Empty it now and you won't have to do it later!",
                    60 * 60,
                    target='home',
                    data={'push': {
                        'category': 'appliances'
                    }})
                self.hass.briefing_manager.register(
                    self.hass.briefing_manager.BriefingTypes.recurring,
                    'The vacuum needs to be emptied.',
                    key=HANDLER_VACUUM_FULL)

        def create_schedule(self) -> None:
            """Create the vacuuming schedule from the on booleans."""
            if HANDLER_VACUUM_SCHEDULE in self.hass.handler_registry:
                self.hass.handler_registry.deregister(HANDLER_VACUUM_SCHEDULE)

            self.hass.handler_registry.register(
                HANDLER_VACUUM_SCHEDULE,
                self.hass.utilities.run_on_days(
                    self.start_by_schedule,
                    self.active_days,
                    self.hass.parse_time(self.properties['schedule_time']),
                    constrain_input_boolean=self.constraint))

        def errored(self, entity: Union[str, dict], attribute: str, old: str,
                    new: str, kwargs: dict) -> None:
            """Brief when Wolfie's had an error."""
            self.hass.briefing_manager.register(
                self.hass.briefing_manager.BriefingTypes.one_time,
                'Wolfie is stuck or has come off of his charger.')

        def response_from_push_notification(self, event_name: str, data: dict,
                                            kwargs: dict) -> None:
            """Respond to iOS notification to empty vacuum."""
            self.hass.log('Responding to iOS request that vacuum is empty')

            self.hass.manager_app.bin_state = (
                self.hass.manager_app.BinStates.empty)

            target = self.hass.notification_manager.get_target_from_push_id(
                data['sourceDevicePermanentID'])
            self.hass.notification_manager.send(
                'Vacuum Emptied',
                '{0} emptied the vacuum.'.format(target),
                target='not {0}'.format(target))

        def schedule_changed(self, entity: Union[str, dict], attribute: str,
                             old: str, new: str, kwargs: dict) -> None:
            """Reload the schedule when one of the input booleans change."""
            self.create_schedule()

        def start_by_schedule(self, kwargs: dict) -> None:
            """Start cleaning via the schedule."""
            if not self.initiated_by_app:
                self.hass.manager_app.start()
                self.initiated_by_app = True

        def start_by_switch(self, event_name: str, data: dict,
                            kwargs: dict) -> None:
            """Start cleaning via the switch."""
            if not self.initiated_by_app:
                self.hass.manager_app.start()
                self.initiated_by_app = True
