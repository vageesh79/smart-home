"""Define automations for switches."""

# pylint: disable=unused-argument,too-many-arguments
# pylint: disable=attribute-defined-outside-init

from typing import Union

from automation import Automation, Feature
from lib.const import (
    BLACKOUT_END, BLACKOUT_START, HANDLER_SWITCH_SLEEP_TIMER,
    HANDLER_SWITCH_VACATION_MODE)


class SwitchAutomation(Automation):
    """Define an automation for switches."""

    class BaseFeature(Feature):
        """Define a base feature for all switches."""

        @property
        def state(self) -> bool:
            """Return the current state of the switch."""
            return self.hass.get_state(self.entities['switch'])

        def initialize(self) -> None:
            """Initialize."""
            raise NotImplementedError

        def toggle(self, state: str) -> None:
            """Toggle the switch state."""
            if self.state == 'off' and state == 'on':
                self.hass.log(
                    'Turning on: {0}'.format(self.entities['switch']))
                self.hass.turn_on(self.entities['switch'])
            elif self.state == 'on' and state == 'off':
                self.hass.log(
                    'Turning off: {0}'.format(self.entities['switch']))
                self.hass.turn_off(self.entities['switch'])

        def toggle_on_schedule(self, kwargs: dict) -> None:
            """Turn off the switch at a certain time."""
            self.toggle(kwargs['state'])

    class PresenceFailsafe(BaseFeature):
        """Define a feature to restrict activation when we're not home."""

        def initialize(self) -> None:
            """Initialize."""
            self.hass.listen_state(
                self.switch_activated,
                self.entities['switch'],
                new='on',
                constrain_noone='just_arrived,home',
                constrain_input_boolean=self.constraint)

        def switch_activated(
                self, entity: Union[str, dict], attribute: str, old: str,
                new: str, kwargs: dict) -> None:
            """Turn the switch off if no one is home."""
            self.hass.log('No one home; not allowing switch to activate')
            self.toggle('off')

    class SleepTimer(BaseFeature):
        """Define a feature to turn a switch off after an amount of time."""

        def initialize(self) -> None:
            """Initialize."""
            self.hass.listen_state(
                self.timer_changed,
                self.entities['timer_slider'],
                constrain_input_boolean=self.constraint)
            self.hass.listen_state(
                self.switch_turned_off,
                self.entities['switch'],
                new='off',
                constrain_input_boolean=self.constraint)

        def switch_turned_off(
                self, entity: Union[str, dict], attribute: str, old: str,
                new: str, kwargs: dict) -> None:
            """Reset the sleep timer when the switch turns off."""
            self.hass.call_service(
                'input_number/set_value',
                entity_id=self.entities['timer_slider'],
                value=0)

        def timer_changed(
                self, entity: Union[str, dict], attribute: str, old: str,
                new: str, kwargs: dict) -> None:
            """Start/stop a sleep timer for this switch."""
            key = HANDLER_SWITCH_SLEEP_TIMER.format(self.hass.name)
            minutes = int(float(new))

            if minutes == 0:
                self.hass.log('Deactivating sleep timer')

                self.toggle('off')
                self.hass.handler_registry.deregister(key)
            else:
                self.hass.log(
                    'Activating sleep timer: {0} minutes'.format(minutes))

                self.toggle('on')
                handle = self.hass.run_in(self.timer_completed, minutes * 60)
                self.hass.handler_registry.register(key, handle)

        def timer_completed(self, kwargs: dict) -> None:
            """Turn off a switch at the end of sleep timer."""
            self.hass.log('Sleep timer over; turning switch off')

            self.hass.call_service(
                'input_number/set_value',
                entity_id=self.entities['timer_slider'],
                value=0)

    class ToggleAtTime(BaseFeature):
        """Define a feature to toggle a switch at a certain time."""

        @property
        def repeatable(self) -> bool:
            """Define whether a feature can be implemented multiple times."""
            return True

        def initialize(self) -> None:
            """Initialize."""
            if self.properties['schedule_time'] in ['sunrise', 'sunset']:
                method = getattr(
                    self.hass, 'run_at_{0}'.format(
                        self.properties['schedule_time']))
                method(
                    self.toggle_on_schedule,
                    state=self.properties['state'],
                    offset=self.properties.get('seasonal_offset', False),
                    constrain_input_boolean=self.constraint,
                    constrain_anyone='just_arrived,home'
                    if self.properties.get('presence_required') else None)
            else:
                self.hass.run_daily(
                    self.toggle_on_schedule,
                    self.hass.parse_time(self.properties['schedule_time']),
                    state=self.properties['state'],
                    constrain_input_boolean=self.constraint)

    class TurnOnUponArrival(BaseFeature):
        """Define a feature to turn a switch on when one of us arrives."""

        def initialize(self) -> None:
            """Initialize."""
            self.hass.listen_event(
                self.someone_arrived,
                'PRESENCE_CHANGE',
                new=self.hass.presence_manager.HomeStates.just_arrived.value,
                first=True,
                constrain_input_boolean=self.constraint,
                constrain_sun='down')

        def someone_arrived(
                self, event_name: str, data: dict, kwargs: dict) -> None:
            """Turn on after dark when someone comes homes."""
            self.hass.log(
                'Someone came home after dark; turning on the switch')

            self.toggle('on')

    class TurnOnWhenCloudy(BaseFeature):
        """Define a feature to turn a switch on at certain cloud coverage."""

        def initialize(self) -> None:
            """Initialize."""
            if (not self.properties.get('above')
                    and not self.properties.get('below')):
                self.hass.error('Must provide an above/below threshold')
                return

            self.cloudy = False

            self.hass.listen_state(
                self.cloud_coverage_reached,
                self.entities['cloud_cover'],
                constrain_start_time=BLACKOUT_END,
                constrain_end_time=BLACKOUT_START,
                constrain_input_boolean=self.constraint,
                constrain_anyone='just_arrived,home'
                if self.properties.get('presence_required') else None)

        def cloud_coverage_reached(
                self, entity: Union[str, dict], attribute: str, old: str,
                new: str, kwargs: dict) -> None:
            """Turn on the switch when a "cloudy event" occurs."""
            try:
                cloud_cover = float(new)
            except ValueError:
                cloud_cover = 0.0

            if (self.properties.get('above') and not self.cloudy
                    and cloud_cover >= self.properties['above']):
                self.hass.log('Cloud cover above {0}%'.format(cloud_cover))

                self.toggle('on')
                self.cloudy = True
            elif (self.properties.get('below') and self.cloudy
                  and cloud_cover < self.properties['below']):
                self.hass.log('Cloud cover below {0}%'.format(cloud_cover))

                self.toggle('off')
                self.cloudy = False

    class VacationMode(BaseFeature):
        """Define a feature to simulate craziness when we're out of town."""

        def initialize(self) -> None:
            """Initialize."""
            self.hass.listen_event(
                self.vacation_mode_toggled,
                'MODE_CHANGE',
                mode='vacation_mode')

        def vacation_mode_toggled(
                self, event_name: str, data: dict, kwargs: dict) -> None:
            """Respond to changes when vacation mode gets toggled."""
            key = HANDLER_SWITCH_VACATION_MODE.format(self.hass.name)

            if data['state'] == 'on':
                on_handler = self.hass.run_at_sunset(
                    self.toggle_on_schedule,
                    state='on',
                    random_start=-60 * 60 * 1,
                    random_end=60 * 30 * 1)
                off_handler = self.hass.run_at_sunset(
                    self.toggle_on_schedule,
                    state='off',
                    random_start=60 * 60 * 2,
                    random_end=60 * 60 * 4)
                self.hass.handler_registry.register(
                    key, on_handler, off_handler)
            else:
                self.hass.handler_registry.deregister(key)
