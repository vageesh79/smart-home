"""Define automations for plants."""

# pylint: disable=unused-argument,too-many-arguments

from typing import Union

from automation import Automation, Feature
from lib.const import HANDLER_PLANT_NEEDS_WATER
from lib.decorators import callback


class PlantAutomation(Automation):
    """Define an automation for plants."""

    class LowMoisture(Feature):
        """Define a feature to notify us of low moisture."""

        @property
        def current_moisture(self) -> int:
            """Define a property to get the current moisture."""
            return int(self.hass.get_state(self.entities['current_moisture']))

        def initialize(self) -> None:
            """Initialize."""
            self.hass.listen_state(
                self.low_moisture_detected,
                self.entities['current_moisture'],
                constrain_input_boolean=self.constraint)

        @callback
        def low_moisture_detected(self, entity: Union[str, dict],
                                  attribute: str, old: str, new: str,
                                  kwargs: dict) -> None:
            """Notify when the plant's moisture is low."""
            key = HANDLER_PLANT_NEEDS_WATER.format(self.hass.friendly_name)
            if int(new) < int(self.properties['moisture_threshold']):
                self.hass.log(
                    'Notifying people at home that plant is low on moisture')

                message = '{0} is at {1}% moisture and needs water.'.format(
                    self.hass.friendly_name, self.current_moisture),
                self.hass.notification_manager.send(
                    '{0} is Dry'.format(self.hass.friendly_name),
                    message,
                    target='home')
                self.hass.briefing_manager.register(
                    self.hass.briefing_manager.BriefingTypes.recurring,
                    message,
                    key=key)
            else:
                if key in self.hass.briefing_manager:
                    self.hass.briefing_manager.deregister(key)
