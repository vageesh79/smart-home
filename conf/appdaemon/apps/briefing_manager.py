"""Define a briefing manager."""

# pylint: disable=too-many-arguments,attribute-defined-outside-init

from enum import Enum
from typing import Tuple, Union

from app import App


class BriefingManager(App):
    """Define a class to represent the app."""

    class BriefingTypes(Enum):
        """Define an enum for briefing types."""
        one_time = 1
        recurring = 2

    @property
    def briefings(self) -> list:
        """Return a list of all active briefings."""
        return self._onetime_briefings + list(
            self._recurring_briefings.values())

    @property
    def briefing_text(self) -> Union[str, None]:
        """Return a single briefing string and clear one-time briefings."""
        briefings = "\n".join([
            '{0}. {1}'.format(i + 1, elm)
            for i, elm in enumerate(self.briefings)
        ])
        self._onetime_briefings.clear()
        return briefings

    # --- INITIALIZERS --------------------------------------------------------
    def initialize(self) -> None:
        """Initialize."""
        super().initialize()

        self._onetime_briefings = []  # type: ignore
        self._recurring_briefings = {}  # type: ignore

        self.register_endpoint(self._add_briefing_endpoint, 'briefing')

    # --- ENDPOINTS -----------------------------------------------------------
    def _add_briefing_endpoint(self, data: dict) -> Tuple[dict, int]:
        """Define an endpoint to add a one-time briefing."""
        try:
            briefing_text = data['briefing']
        except KeyError:
            return {
                'status': 'error',
                'message': 'Missing "briefing" parameter'
            }, 502

        self.register(self.BriefingTypes.one_time, briefing_text)
        return {
            'status': 'ok',
            'message': 'Successfully added brefing: {0}'.format(briefing_text)
        }, 200

    # --- HELPERS -------------------------------------------------------------
    def __contains__(self, key: str) -> bool:
        """Determine if a key exists in registry."""
        return (self._onetime_briefings.__contains__(key)
                or self._recurring_briefings.__contains__(key))

    # --- APP API -------------------------------------------------------------
    def clear_briefings(self, include_recurring: bool = True) -> None:
        """Delete all existing briefings."""
        self._onetime_briefings.clear()
        if include_recurring:
            self._recurring_briefings.clear()

    def deregister(self, key: str) -> None:
        """Deregister a one-time briefing."""
        if (key not in self._onetime_briefings
                and key not in self._recurring_briefings):
            self.error("Can't deregister missing briefing: {0}".format(key))
            return

        self.log('Deregistering briefing: {0}'.format(key))

        if key in self._onetime_briefings:
            self._onetime_briefings.remove(key)
        else:
            del self._recurring_briefings[key]

    def register(self, kind: Enum, text: str,
                 key: Union[str, None] = None) -> None:
        """Register a new briefing."""
        if kind == self.BriefingTypes.one_time:
            if text in self._onetime_briefings:
                self.log('Skipping existing briefing', level='WARNING')
                return

            self._onetime_briefings.append(text)
        else:
            if not key:
                self.error('No key for recurring briefing: {0}'.format(text))
                return

            if key in self._recurring_briefings:
                self.log('Replacing existing briefing', level='WARNING')

            self._recurring_briefings[key] = text

        self.log('Registering briefing: {0}'.format(key if key else text))
