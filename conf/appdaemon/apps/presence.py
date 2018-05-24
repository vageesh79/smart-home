"""Define apps related to presence."""

# pylint: disable=attribute-defined-outside-init,too-many-arguments
# pylint: disable=unused-argument

from enum import Enum
from typing import Tuple, Union

from app import App
from automation import Automation, Feature
from lib.const import PEOPLE


class PresenceAutomation(Automation):
    """Define a class to represent automations for presence."""

    class BriefingWhenHome(Feature):
        """Define a feature to send a briefing when someone comes home."""

        def initialize(self) -> None:
            """Initialize."""
            self.hass.listen_event(
                self.someone_arrived,
                'PRESENCE_CHANGE',
                new=self.hass.presence_manager.HomeStates.home.value,
                constrain_input_boolean=self.constraint)

        def someone_arrived(self, event_name: str, data: dict,
                            kwargs: dict) -> None:
            """Announces any briefing items when someone is home."""
            self.hass.log('Someone arrived home; sending briefing')

            if self.hass.briefing_manager.briefings:
                self.hass.notification_manager.send(
                    'Home Briefing',
                    self.hass.briefing_manager.briefing_text,
                    target=data['person'])


class PresenceManager(App):
    """Define a class to represent a presence manager."""

    class HomeStates(Enum):
        """Define an enum for presence states."""
        away = 'Away'
        extended_away = 'Extended Away'
        home = 'Home'
        just_arrived = 'Just Arrived'
        just_left = 'Just Left'

    class ProximityStates(Enum):
        """Define an enum for proximity states."""
        away = 'away'
        edge = 'edge'
        home = 'home'
        nearby = 'nearby'

    PROXIMITY_SENSOR = 'proximity.home'

    HOME_THRESHOLD = 0
    NEARBY_THRESHOLD = 5280
    EDGE_THRESHOLD = 15840

    @property
    def proximity(self) -> int:
        """Return the current proximity."""
        try:
            return int(self.get_state(self.PROXIMITY_SENSOR))
        except ValueError:
            return 0

    # --- INITIALIZERS --------------------------------------------------------
    def initialize(self) -> None:
        """Initialize."""
        super().initialize()

        if self.proximity == self.HOME_THRESHOLD:
            self.state = self.ProximityStates.home
        elif self.HOME_THRESHOLD < self.proximity <= self.NEARBY_THRESHOLD:
            self.state = self.ProximityStates.nearby
        else:
            self.state = self.ProximityStates.away

        self.listen_state(
            self._proximity_change_cb,
            self.PROXIMITY_SENSOR,
            attribute='all',
            duration=60)

        for person, attrs in PEOPLE.items():
            # Set initial presence (so a restart can unstick it):
            if self.get_state(attrs['device_tracker']) == 'home':
                self._set_input_select(attrs['presence_manager_input_select'],
                                       self.HomeStates.home)
            else:
                self._set_input_select(attrs['presence_manager_input_select'],
                                       self.HomeStates.away)

            # Fire events when presence changes:
            self.listen_state(
                self._presence_change_cb,
                attrs['presence_manager_input_select'],
                person=person)

            # (Extended) Away -> Just Arrived
            self.listen_state(
                self._change_input_select_cb,
                attrs['device_tracker'],
                old='not_home',
                new='home',
                input_select=attrs['presence_manager_input_select'],
                target_state=self.HomeStates.just_arrived)

            # Just Arrived -> Home
            self.listen_state(
                self._change_input_select_cb,
                attrs['presence_manager_input_select'],
                new=self.HomeStates.just_arrived.value,
                duration=60 * 5,
                input_select=attrs['presence_manager_input_select'],
                target_state=self.HomeStates.home)

            # Just Left -> Just Arrived = Home
            self.listen_state(
                self._change_input_select_cb,
                attrs['presence_manager_input_select'],
                old=self.HomeStates.just_left.value,
                new=self.HomeStates.just_arrived.value,
                input_select=attrs['presence_manager_input_select'],
                target_state=self.HomeStates.home)

            # Home -> Just Left
            self.listen_state(
                self._change_input_select_cb,
                attrs['device_tracker'],
                old='home',
                new='not_home',
                input_select=attrs['presence_manager_input_select'],
                target_state=self.HomeStates.just_left)

            # Just Left -> Away
            self.listen_state(
                self._change_input_select_cb,
                attrs['presence_manager_input_select'],
                new=self.HomeStates.just_left.value,
                duration=60 * 5,
                input_select=attrs['presence_manager_input_select'],
                target_state=self.HomeStates.away)

            # Away -> Extended Away
            self.listen_state(
                self._change_input_select_cb,
                attrs['presence_manager_input_select'],
                new=self.HomeStates.away.value,
                duration=60 * 60 * 24,
                input_select=attrs['presence_manager_input_select'],
                target_state=self.HomeStates.extended_away)

    # --- CALLBACKS -----------------------------------------------------------
    def _change_input_select_cb(self, entity: Union[str, dict], attribute: str,
                                old: str, new: str, kwargs: dict) -> None:
        """Change state of a home presence input select."""
        input_select = kwargs['input_select']
        target_state = kwargs['target_state']

        self.log(
            'Presence entity change for "{0}": {1} -> {2}'.format(
                entity, old, new),
            level='DEBUG')
        self.log(
            'Changing presence input select: {0} -> {1}'.format(
                input_select, target_state.value),
            level='DEBUG')

        self._set_input_select(input_select, target_state)

    def _presence_change_cb(self, entity: Union[str, dict], attribute: str,
                            old: str, new: str, kwargs: dict) -> None:
        """Fire an event when a device tracker changes state."""
        if old == new:
            return

        new_state = self.HomeStates(new)
        if (new_state == self.HomeStates.just_arrived
                or new_state == self.HomeStates.home):
            states = [self.HomeStates.just_arrived, self.HomeStates.home]
        else:
            states = [new_state]

        person = kwargs['person']
        first = self.only_one(*states)

        self.log(
            'Presence change for {0}: {1} -> {2} (first: {3})'.format(
                person, old, new, first),
            level='DEBUG')

        self.fire_event(
            'PRESENCE_CHANGE', person=person, old=old, new=new, first=first)

    def _proximity_change_cb(self, entity: Union[str, dict], attribute: str,
                             old: dict, new: dict, kwargs: dict) -> None:
        """Lock up when we leave home."""
        if old['state'] == 'not set' or new['state'] == 'not set':
            return

        new_proximity = int(new['state'])
        old_state = self.state

        if (self.state != self.ProximityStates.home
                and new_proximity == self.HOME_THRESHOLD):
            self.state = self.ProximityStates.home
        elif (self.state != self.ProximityStates.nearby and
              self.HOME_THRESHOLD < new_proximity <= self.NEARBY_THRESHOLD):
            self.state = self.ProximityStates.nearby
        elif (self.state != self.ProximityStates.edge and
              self.NEARBY_THRESHOLD < new_proximity <= self.EDGE_THRESHOLD):
            self.state = self.ProximityStates.edge
        elif (self.state != self.ProximityStates.away
              and new_proximity > self.NEARBY_THRESHOLD):
            self.state = self.ProximityStates.away

        if self.state != old_state:
            self.log('Proximity event: {0}'.format(self.state.value))
            self.fire_event(
                'PROXIMITY_CHANGE', old=old_state.value, new=self.state.value)

    # --- HELPERS -------------------------------------------------------------
    def _set_input_select(self, input_select: str, new_value: Enum) -> None:
        """Set the value of the appropriate state input dropdown."""
        self.log(
            'Setting input select: {0} -> {1}'.format(input_select, new_value),
            level='DEBUG')
        self.call_service(
            'input_select/select_option',
            entity_id=input_select,
            option=new_value.value)

    def _whos_relative_to_home(self, *states: Enum) -> list:
        """Return a list people who are in a certain set of states."""
        state_list = [state.value for state in states]
        return [
            name for name, attrs in PEOPLE.items() if self.get_state(
                attrs['presence_manager_input_select']) in state_list
        ]

    # --- APP API -------------------------------------------------------------
    def anyone(self, *states: Enum) -> bool:
        """Determine whether *any* person is in one or more states."""
        if self._whos_relative_to_home(*states):
            return True

        return False

    def everyone(self, *states: Enum) -> bool:
        """Determine whether *every* person is in one or more states."""
        if self._whos_relative_to_home(*states) == list(PEOPLE.keys()):
            return True

        return False

    def locate(self, name: str) -> Tuple[Enum, dict]:
        """Find a person's location based on a device tracker."""
        if name not in PEOPLE:
            raise KeyError('Unknown person: {0}'.format(name))

        person = PEOPLE[name]
        return ([
            s for s in self.HomeStates if s.value == self.get_state(
                person['presence_manager_input_select'])
        ][0], self.get_state(person['geocode_sensor'], attribute='all'))

    def noone(self, *states: Enum) -> bool:
        """Determine whether *no* person is in one or more states."""
        if not self._whos_relative_to_home(*states):
            return True

        return False

    def only_one(self, *states: Enum) -> bool:
        """Determine whether *only one* person is in one or more states."""
        people = self._whos_relative_to_home(*states)
        return len(people) == 1

    def whos_away(self, include_others: bool = True) -> list:
        """Return a list of notifiers who are away."""
        if include_others:
            return self._whos_relative_to_home(self.HomeStates.away,
                                               self.HomeStates.extended_away,
                                               self.HomeStates.just_left)

        return self._whos_relative_to_home(self.HomeStates.away)

    def whos_extended_away(self) -> list:
        """Return a list of notifiers who are away."""
        return self._whos_relative_to_home(self.HomeStates.extended_away)

    def whos_home(self, include_others: bool = True) -> list:
        """Return a list of notifiers who are at home."""
        if include_others:
            return self._whos_relative_to_home(self.HomeStates.home,
                                               self.HomeStates.just_arrived)

        return self._whos_relative_to_home(self.HomeStates.home)

    def whos_just_arrived(self) -> list:
        """Return a list of notifiers who are at home."""
        return self._whos_relative_to_home(self.HomeStates.just_arrived)

    def whos_just_left(self) -> list:
        """Return a list of notifiers who are at home."""
        return self._whos_relative_to_home(self.HomeStates.just_left)
