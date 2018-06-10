"""Define a mode."""

# pylint: disable=attribute-defined-outside-init,too-many-arguments

from typing import Union

import appdaemon.plugins.hass.hassapi as hass


class Mode(hass.Hass):
    """Define a mode."""

    @property
    def state(self) -> str:
        """Return the current state of the mode switch."""
        return self.get_state(self.switch)

    @state.setter
    def state(self, value: str) -> None:
        """Alter the state of the mode switch."""
        if value not in ['on', 'off']:
            self.error('Mode value undefined: {0}'.format(value))
            return

        if value == 'on':
            func = self.turn_on
        else:
            func = self.turn_off

        func(self.switch)

    # --- INITIALIZERS --------------------------------------------------------
    def initialize(self) -> None:
        """Initialize."""
        self._constraints_to_disable = []  # type: ignore
        self._constraints_to_enable = []  # type: ignore
        self.switch = 'input_boolean.mode_{0}'.format(self.name)

        self.listen_state(self.switch_toggled_cb, entity=self.switch)

    # --- APP API -------------------------------------------------------------
    def register_constraint_alteration(
            self, constraint_name: str, value: str) -> None:
        """Record how a constraint switch should respond when in this mode."""
        location = getattr(self, '_constraints_to_{0}'.format(value))
        if constraint_name in location:
            self.log(
                'Switch behavior already exists: {0}'.format(constraint_name),
                level='WARNING')
            return

        location.append(constraint_name)

    def switch_toggled_cb(
            self, entity: Union[str, dict], attribute: str, old: str, new: str,
            kwargs: dict) -> None:
        """Make alterations when a mode constraint is toggled."""
        self.fire_event('MODE_CHANGE', mode=self.name, state=new)

        if new == 'on':
            func1 = self.turn_off
            func2 = self.turn_on
        else:
            func1 = self.turn_on
            func2 = self.turn_off

        for constraint in self._constraints_to_disable:
            func1(constraint)
        for constraint in self._constraints_to_enable:
            func2(constraint)
