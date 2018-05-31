"""Define automations for plants."""

# pylint: disable=unused-argument,too-many-arguments
# pylint: disable=attribute-defined-outside-init

from typing import Union

from automation import Automation, Feature
from lib.const import HANDLER_PLANT_NEEDS_WATER


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
            self.low_moisture = False

            self.hass.listen_state(
                self.low_moisture_detected,
                self.entities['current_moisture'],
                constrain_input_boolean=self.constraint)

        def low_moisture_detected(self, entity: Union[str, dict],
                                  attribute: str, old: str, new: str,
                                  kwargs: dict) -> None:
            """Notify when the plant's moisture is low."""
            key = HANDLER_PLANT_NEEDS_WATER.format(
                self.hass.friendly_name.lower())
            if (not (self.low_moisture)
                    and int(new) < int(self.properties['moisture_threshold'])):
                self.hass.log(
                    'Notifying people at home that plant is low on moisture')

                self.hass.notification_manager.repeat(
                    '{0} is Dry 💧'.format(self.hass.friendly_name),
                    '{0} is at {1}% moisture and needs water.'.format(
                        self.hass.friendly_name, self.current_moisture),
                    60 * 60,
                    key=key,
                    target='home')
                self.low_moisture = True
            else:
                self.low_moisture = False
                self.hass.handler_registry.deregister(key)
