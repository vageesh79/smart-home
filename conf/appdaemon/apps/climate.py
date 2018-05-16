"""Define automations for climate control."""

# pylint: disable=too-many-arguments,unused-argument,
# pylint: disable=attribute-defined-outside-init

from typing import Union

from app import App
from automation import Automation, Feature
from lib.decorators import callback


class ClimateManager(App):
    """Define an app to represent climate control."""

    @property
    def average_indoor_humidity(self) -> float:
        """Return the average indoor humidity based on a list of sensors."""
        return float(self.get_state(self.entities['average_indoor_humidity']))

    @property
    def average_indoor_temperature(self) -> float:
        """Return the average indoor temperature based on a list of sensors."""
        return float(
            self.get_state(self.entities['average_indoor_temperature']))

    @property
    def outside_temp(self) -> float:
        """Define a property to get the current outdoor temperature."""
        return float(self.get_state(self.entities['outside_temp']))

    @property
    def away_mode(self) -> bool:
        """Return the state of away mode."""
        return self.get_state(
            self.entities['thermostat'], attribute='away_mode') == 'on'

    @away_mode.setter
    def away_mode(self, value: Union[int, bool, str]) -> None:
        """Set the state of away mode."""
        self.call_service(
            'nest/set_mode',
            home_mode='away' if value in (1, True, 'on') else 'home')


class ClimateAutomation(Automation):
    """Define an automation to manage climate."""

    class AdjustOnProximity(Feature):
        """Define a feature to adjust climate based on proximity to home."""

        def initialize(self) -> None:
            """Initialize."""
            self.hass.listen_event(
                self.arrived_home,
                'PRESENCE_CHANGE',
                new=self.hass.presence_manager.HomeStates.just_arrived.value,
                first=True,
                constrain_input_boolean=self.constraint)
            self.hass.listen_event(
                self.proximity_changed,
                'PROXIMITY_CHANGE',
                constrain_input_boolean=self.constraint)

        @callback
        def proximity_changed(self, event_name: str, data: dict,
                              kwargs: dict) -> None:
            """Respond to "PROXIMITY_CHANGE" events."""
            if (self.hass.climate_manager.outside_temp <
                    self.properties['outside_threshold_low']
                    or self.hass.climate_manager.outside_temp >
                    self.properties['outside_threshold_high']):

                # Scenario 1: Anything -> Away (Extreme Temps)
                if (data['old'] !=
                        self.hass.presence_manager.ProximityStates.away.value
                        and data['new'] ==
                        self.hass.presence_manager.ProximityStates.away.value):
                    self.hass.log(
                        'Setting thermostat to "Away" (extreme temp)')
                    self.hass.climate_manager.away_mode = True

                # Scenario 2: Away -> Anything (Extreme Temps)
                elif (data['old'] ==
                      self.hass.presence_manager.ProximityStates.away.value
                      and data['new'] !=
                      self.hass.presence_manager.ProximityStates.away.value):
                    self.hass.log(
                        'Setting thermostat to "Home" (extreme temp)')
                    self.hass.climate_manager.away_mode = False
            else:
                # Scenario 3: Home -> Anything
                if (data['old'] ==
                        self.hass.presence_manager.ProximityStates.home.value
                        and data['new'] !=
                        self.hass.presence_manager.ProximityStates.home.value):
                    self.hass.log('Setting thermostat to "Away"')
                    self.hass.climate_manager.away_mode = True

                # Scenario 4: Anything -> Nearby
                elif (data['old'] !=
                      self.hass.presence_manager.ProximityStates.nearby.value
                      and data['new'] ==
                      self.hass.presence_manager.ProximityStates.nearby.value):
                    self.hass.log('Setting thermostat to "Home"')
                    self.hass.climate_manager.away_mode = False

        @callback
        def arrived_home(self, event_name: str, data: dict,
                         kwargs: dict) -> None:
            """Last ditch: turn the thermostat to home when someone arrives."""
            if self.hass.climate_manager.away_mode:
                self.hass.log(
                    'Last ditch: setting thermostat to "Home" (arrived)')
                self.hass.climate_manager.away_mode = False

    class NotifyBadAqi(Feature):
        """Define a feature to notify us of bad air quality."""

        @property
        def current_aqi(self) -> int:
            """Define a property to get the current AQI."""
            return int(self.hass.get_state(self.entities['aqi']))

        def initialize(self) -> None:
            """Initialize."""
            self.notification_sent = False

            self.hass.listen_state(
                self.bad_aqi_detected,
                self.entities['hvac_state'],
                new='cooling',
                constrain_input_boolean=self.constraint)

        @callback
        def bad_aqi_detected(self, entity: Union[str, dict], attribute: str,
                             old: str, new: str, kwargs: dict) -> None:
            """Send select notifications when cooling and poor AQI."""
            if (not self.notification_sent
                    and self.current_aqi > self.properties['aqi_threshold']):
                self.hass.log('Poor AQI; notifying anyone at home')

                self.hass.notification_manager.send(
                    'Poor AQI',
                    'AQI is at {0}; consider closing the humidifier vent.'.
                    format(self.current_aqi),
                    target='home')
                self.notification_sent = True
            elif (self.notification_sent
                  and self.current_aqi <= self.properties['aqi_threshold']):
                self.hass.notification_manager.send(
                    'Better AQI',
                    'AQI is at {0}; open the humidifer vent again.'.format(
                        self.current_aqi),
                    target='home')
                self.notification_sent = True
