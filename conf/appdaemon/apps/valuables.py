"""Define automations for our valuables."""

# pylint: disable=unused-argument

from automation import Automation, Feature
from lib.decorators import callback


class TileAutomation(Automation):
    """Define an automation for Tiles."""

    class LeftSomewhere(Feature):
        """Define a feature to notify when a Tile has been left somewhere."""

        def initialize(self) -> None:
            """Initialize."""
            self.hass.listen_event(
                self.arrived_home,
                'PRESENCE_CHANGE',
                person=self.properties['target'],
                new=self.hass.presence_manager.HomeStates.home.value,
                constrain_input_boolean=self.constraint)

        @callback
        def arrived_home(self, event_name: str, data: dict,
                         kwargs: dict) -> None:
            """Check for missing Tiles once we're home."""
            tile = self.hass.get_state(self.entities['tile'], attribute='all')
            if tile['state'] == 'home':
                return

            self.hass.notification_manager.send(
                "Missing Valuable",
                'Is {0} at home?'.format(tile['attributes']['friendly_name']),
                target=self.properties['target'],
                data={
                    'push': {
                        'category': 'map'
                    },
                    'action_data': {
                        'latitude': str(tile['attributes']['latitude']),
                        'longitude': str(tile['attributes']['longitude'])
                    }
                })
