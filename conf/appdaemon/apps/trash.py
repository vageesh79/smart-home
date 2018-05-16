"""Define automations for trash."""

# pylint: disable=attribute-defined-outside-init,unused-argument

import datetime
from enum import Enum
from math import ceil
from typing import Tuple

from app import App
from automation import Automation, Feature
from lib.decorators import callback


class TrashAutomation(Automation):
    """Define a class to trash automations."""

    class NotifyOfPickup(Feature):
        """Define a feature to notify us of low batteries."""

        def initialize(self) -> None:
            """Initialize."""
            self.hass.utilities.run_on_days(
                self.time_to_notify, ['Sunday'],
                datetime.time(20, 0, 0),
                constrain_input_boolean=self.constraint,
                constraint_anyone_home=True)

        def time_to_notify(self, kwargs: dict) -> None:
            """Schedule the next pickup notification."""
            date, friendly_str = self.hass.trash_manager.in_next_pickup_str()
            self.hass.notification_manager.send(
                'Trash Reminder',
                friendly_str,
                when=datetime.datetime.combine(
                    date - datetime.timedelta(days=1),
                    datetime.time(20, 0, 0)),
                target='home')


class TrashManager(App):
    """Define a class to represent a trash manager."""

    class PickupTypes(Enum):
        """Define an enum for pickup types."""
        extra_trash = 'Extra Trash'
        recycling = 'Recycling'
        trash = 'Trash'

    # --- INITIALIZERS --------------------------------------------------------
    def initialize(self) -> None:
        """Initialize."""
        super().initialize()

        self.sensors = {
            self.PickupTypes.extra_trash: 'sensor.extra_trash_pickup',
            self.PickupTypes.recycling: 'sensor.recycling_pickup',
            self.PickupTypes.trash: 'sensor.trash_pickup'
        }

    # --- APP API -------------------------------------------------------------
    def in_next_pickup(self) -> Tuple[datetime.datetime, list]:
        """Return a list of pickup types in the next pickup."""
        return (datetime.datetime.strptime(
            self.get_state(
                self.sensors[self.PickupTypes.trash], attribute='pickup_date'),
            '%B %d, %Y'), [
                t for t, entity in self.sensors.items()
                if 'pickups' not in self.get_state(entity)
            ])

    def in_next_pickup_str(self) -> Tuple[datetime.datetime, str]:
        """Return a human-friendly string of next pickup info."""
        date, pickup_types = self.in_next_pickup()

        delta = ceil((date - self.datetime()).total_seconds() / 60 / 60 / 24)
        if delta == 1:
            relative_date_string = 'tomorrow'
        else:
            relative_date_string = 'in {0} days'.format(delta)

        return (date,
                'The next pickup is {0} on {1}. It will include {2}.'.format(
                    relative_date_string,
                    self.utilities.suffix_strftime('%A, %B {TH}', date),
                    self.utilities.grammatical_list_join([
                        p.value.lower().replace('_', ' ') for p in pickup_types
                    ])))

    def when_next_pickup(self, pickup_type: Enum) -> str:
        """Return the relative date of next pickup for a particular type."""
        try:
            return self.get_state(self.sensors[pickup_type])  # type: ignore
        except KeyError:
            self.error('Unknown trash sensor: {0}'.format(pickup_type))
            return None
