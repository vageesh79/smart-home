"""Define a base object that all apps and automations inherit from."""

# pylint: disable=unused-argument,attribute-defined-outside-init

from typing import Union

import appdaemon.plugins.hass.hassapi as hass

from lib.const import BLACKOUT_START, BLACKOUT_END


class Base(hass.Hass):
    """Define a base automation object."""

    def initialize(self) -> None:
        """Initialize."""
        self.entities = self.args.get('entities', {})
        self.properties = self.args.get('properties', {})

        # Take every dependecy and create a reference to it:
        for app in self.args.get('dependencies', []):
            if not getattr(self, app, None):
                setattr(self, app, self.get_app(app))

        # Have every app and automation register its cancel_timer():
        self.handler_registry.cancel_timer_methods.append(self.cancel_timer)

        # Register custom constraints:
        self.register_constraint('constrain_anyone')
        self.register_constraint('constrain_everyone')
        self.register_constraint('constrain_noone')
        self.register_constraint('constrain_out_of_blackout')
        self.register_constraint('constrain_sun')

    def _constrain_presence(self, method: str,
                            value: Union[str, None]) -> bool:
        """Constrain presence in a generic fashion."""
        if not value:
            return True

        return getattr(self.presence_manager, method)(
            *[self.presence_manager.HomeStates[s] for s in value.split(',')])

    def constrain_anyone(self, value: Union[str, None]) -> bool:
        """Constrain execution to whether anyone is in a state."""
        return self._constrain_presence('anyone', value)

    def constrain_everyone(self, value: Union[str, None]) -> bool:
        """Constrain execution to whether everyone is in a state."""
        return self._constrain_presence('everyone', value)

    def constrain_noone(self, value: Union[str, None]) -> bool:
        """Constrain execution to whether no one is in a state."""
        return self._constrain_presence('noone', value)

    def constrain_out_of_blackout(self, required: bool) -> bool:
        """Constrain execution to whether anyone is home."""
        return (not required
                or not self.now_is_between(BLACKOUT_START, BLACKOUT_END))

    def constrain_sun(self, position: str) -> bool:
        """Constrain execution to the location of the sun."""
        if ((position == 'up' and self.sun_up())
                or (position == 'down' and self.sun_down())):
            return True

        return False
