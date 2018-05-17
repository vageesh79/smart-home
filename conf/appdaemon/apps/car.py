"""Define automations for our cars."""

# pylint: disable=too-many-arguments,attribute-defined-outside-init
# pylint: disable=unused-argument

from datetime import timedelta
from typing import Tuple, Union

from automation import Automation, Feature
from lib.const import PEOPLE
from lib.decorators import callback, endpoint


class CarAutomation(Automation):
    """Define an automation for Automatic cars."""

    class DriveHomePrompt(Feature):
        """Define a feature to prompt for "Drive Home" when near."""

        def initialize(self):
            """Initialize."""
            self.hass.listen_event(
                self.response_from_push_notification,
                'ios.notification_action_fired',
                actionName='OPEN_UP',
                constrain_input_boolean=self.constraint)
            self.hass.listen_state(
                self.nearing_home,
                self.entities['car'],
                old='not_home',
                new='home',
                constrain_input_boolean=self.constraint)

        @callback
        def nearing_home(self, entity: Union[str, dict], attribute: str,
                         old: str, new: str, kwargs: dict) -> None:
            """Fire a notification when the car nears home."""
            [target] = [k for k, v in PEOPLE.items() if v.get('car') == entity]
            self.hass.notification_manager.send(
                'Open Up?',
                'Do you want to open up?',
                target=target,
                data={'push': {
                    'category': 'car_near_home'
                }})

        @callback
        def response_from_push_notification(self, event_name: str, data: dict,
                                            kwargs: dict) -> None:
            """Respond to iOS notification to open up."""
            self.hass.log('Responding to iOS request to open up')

            self.hass.call_service('scene/turn_on', entity_id='scene.drive_home')

    class NotifyEta(Feature):
        """Define a feature to notify of the vehicle's ETA to home."""

        def initialize(self):
            """Initialize."""
            self.hass.register_endpoint(self.get_eta, 'eta')

        def calculate_eta(self, travel_time: str) -> str:
            """Get an arrival time based upon travel time in minutes."""
            eta = self.hass.datetime() + timedelta(minutes=int(travel_time))
            return eta.time().strftime('%I:%M %p')

        @endpoint
        def get_eta(self, data: dict) -> Tuple[dict, int]:
            """Define an endpoint to send Aaron's ETA."""
            if self.hass.presence_manager.noone(
                    self.hass.presence_manager.HomeStates.home):
                return {
                    "status": "ok",
                    "message": 'No one home; ignoring'
                }, 200

            try:
                key = data['person']
                name = key.title()
            except KeyError:
                return {
                    'status': 'error',
                    'message': 'Missing "person" parameter'
                }, 502

            eta = self.calculate_eta(
                self.hass.get_state('sensor.{0}_travel_time'.format(key)))

            self.hass.log("Sending {0}'s ETA: {1}".format(name, eta))

            statement = '{0} is arriving around {1}.'.format(name, eta)
            self.hass.notification_manager.send(
                "Aaron's ETA", statement, target='Britt')
            return {"status": "ok", "message": statement}, 200

    class NotifyLowFuel(Feature):
        """Define a feature to notify of the vehicle's ETA to home."""

        def initialize(self):
            """Initialize."""
            self.registered = False
            self.hass.listen_state(
                self.low_fuel_found,
                self.entities['car'],
                attribute='fuel_level',
                constrain_input_boolean=self.constraint)

        @callback
        def low_fuel_found(self, entity: Union[str, dict], attribute: str,
                           old: str, new: str, kwargs: dict) -> None:
            """Creates OmniFocus todos whenever my car is low on gas."""
            name = self.hass.get_state(
                self.entities['car'], attribute='friendly_name')

            try:
                if int(new) < self.properties['fuel_threshold']:
                    if self.registered:
                        return

                    self.hass.log(
                        'Low fuel detected detected: {0}'.format(name))
                    self.hass.notification_manager.create_omnifocus_task(
                        'Get gas for {0}'.format(name))
                    self.registered = True
                else:
                    self.registered = False
            except ValueError:
                return
