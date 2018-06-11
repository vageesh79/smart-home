"""Define a notification mechanism for all AppDaemon apps."""

# pylint: disable=too-many-arguments,attribute-defined-outside-init

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Union

import attr

from app import App
from lib.const import BLACKOUT_END, BLACKOUT_START, PEOPLE


@attr.s  # pylint: disable=too-few-public-methods
class Notification(object):
    """Define a notification object."""

    class NotificationTypes(Enum):
        """Define an enum for notification types."""
        repeating = 1
        single = 2

    kind = attr.ib()
    title = attr.ib()
    message = attr.ib()

    blackout_end_time = attr.ib(default=None)
    blackout_start_time = attr.ib(default=None)
    data = attr.ib(default=None)
    interval = attr.ib(default=None)
    key = attr.ib(default=None)
    target = attr.ib(default=None)
    when = attr.ib(default=None)


class NotificationManager(App):
    """Define an app to act as a system-wide notifier."""

    # --- INITIALIZERS --------------------------------------------------------
    def initialize(self):
        """Initialize."""
        super().initialize()

        self.listen_event(self._notifier_test_cb, 'NOTIFIER_TEST')

    # --- HELPERS -------------------------------------------------------------
    def _adjust_for_blackout(self, notification: Notification) -> Notification:
        """Reschedule a notification's schedule for outside of blackout."""
        if self._in_blackout(notification):
            if notification.when:
                target_date = notification.when.date()
                active_time = notification.when.time()
            else:
                target_date = self.date()
                active_time = self.time()

            if not (active_time >= self.parse_time(
                    notification.blackout_start_time) and active_time <=
                    self.parse_time(notification.blackout_end_time)):
                target_date = target_date + timedelta(days=1)

            notification.when = datetime.combine(
                target_date, self.parse_time(notification.blackout_end_time))

            self.log(
                'Rescheduling notification: {0}'.format(notification.title))
        else:
            notification.when = self.datetime() + timedelta(seconds=1)

        return notification

    def _dispatch(self, notification: Notification) -> None:
        """Send a single (immediate or scheduled) notification."""
        notification = self._adjust_for_blackout(notification)

        if not notification.key:
            notification.key = uuid.uuid4()
            self.log(
                'Using random handler registry key: {0}'.format(
                    notification.key),
                level='DEBUG')

        if not notification.target:
            notification.target = 'everyone'

        if notification.kind == Notification.NotificationTypes.repeating:
            handler = self.run_every(
                self._send_cb,
                notification.when,
                notification.interval,
                notification=notification)
        else:
            handler = self.run_at(
                self._send_cb, notification.when, notification=notification)

        self.handler_registry.register(notification.key, handler)

    def _get_targets(self, target: str) -> list:
        """Get a list of targets based on input string."""
        # 1. target='not Person'
        split = target.split(' ')
        if split[0] == 'not' and split[1] in PEOPLE:
            return [
                notifier for name, attrs in PEOPLE.items()
                if name != split[1] for notifier in attrs['notifiers']
            ]

        # 2. target='Person'
        if split[0] in PEOPLE:
            return PEOPLE[target]['notifiers']

        try:
            # 3. target='home'
            return [
                notifier for name in getattr(
                    self.presence_manager, 'whos_{0}'.format(target))()
                for notifier in PEOPLE[name]['notifiers']
            ]

        except AttributeError:
            all_targets = [
                notifier for attrs in PEOPLE.values()
                for notifier in attrs['notifiers']
            ]

            # 4. target='everyone'
            if target == 'everyone':
                return all_targets

            # 5. target='person_iphone'
            if target in all_targets:
                return [target]

            self.error('Unknown notifier target: {0}'.format(target))

        return []

    def _in_blackout(self, notification: Notification) -> bool:
        """Determine whether a notification is set to send in blackout."""
        if (not notification.blackout_start_time
                or not notification.blackout_end_time):
            return False

        if notification.when:
            return self.utilities.time_is_between(
                notification.when, notification.blackout_start_time,
                notification.blackout_end_time)

        return self.now_is_between(
            notification.blackout_start_time, notification.blackout_end_time)

    # --- CALLBACKS -----------------------------------------------------------
    def _notifier_test_cb(
            self, event_name: str, data: dict, kwargs: dict) -> None:
        """Run a test."""
        try:
            kind = data['kind']
            message = data['message']
            title = data['title']
        except KeyError:
            self.error('Missing title, message, and/or kind in notifier test')
            return

        _data = data.get('data', None)
        blackout_end_time = data.get('blackout_end_time', BLACKOUT_END)
        blackout_start_time = data.get(
            'blackout_start_time', BLACKOUT_START)
        interval = data.get('interval', None)
        key = data.get('key', None)
        target = data.get('target', None)
        when = data.get('when', None)

        if kind == Notification.NotificationTypes.single.name:
            self.send(
                title,
                message,
                when=when,
                key=key,
                target=target,
                data=_data,
                blackout_start_time=blackout_start_time,
                blackout_end_time=blackout_end_time)
        elif kind == Notification.NotificationTypes.repeating.name:
            self.repeat(
                title,
                message,
                interval,
                when=when,
                key=key,
                target=target,
                data=_data,
                blackout_start_time=blackout_start_time,
                blackout_end_time=blackout_end_time)
        else:
            self.handler_registry.deregister_all()

    def _send_cb(self, kwargs: dict) -> None:
        """Send a single (immediate or scheduled) notification."""
        notification = kwargs['notification']

        if notification.kind == Notification.NotificationTypes.repeating:
            notification.when = None
            if self._in_blackout(notification):
                self.handler_registry.deregister(notification.key)
                self._dispatch(notification)
                return

        self.log('Single notification: {0}'.format(notification.title))

        for target in self._get_targets(notification.target):
            payload = {
                'message': notification.message,
                'title': notification.title
            }

            if notification.data:
                payload['data'] = notification.data

            self.call_service('notify/{0}'.format(target), **payload)

        if notification.kind == Notification.NotificationTypes.single:
            self.handler_registry.deregister(notification.key, cancel=False)

    # --- APP API -------------------------------------------------------------
    def create_omnifocus_task(self, title: str) -> None:
        """Create a task in Aaron's omnifocus."""
        self.notify(
            'created on {0}'.format(str(self.datetime())),
            title=title,
            name='omnifocus')

    def create_persistent_notification(self, title: str, message: str) -> None:
        """Create a notification in the HASS UI."""
        self.call_service(
            'persistent_notification/create', title=title, message=message)

    @staticmethod
    def get_target_from_push_id(push_id: uuid.UUID) -> Union[str, None]:
        """Return a person from a provided permanent device ID."""
        try:
            [target] = [
                k for k, v in PEOPLE.items()
                if v['push_device_id'] == push_id
            ]
        except ValueError:
            target = None

        return target

    def repeat(
            self,
            title: str,
            message: str,
            interval: int,
            when: Union[datetime, None] = None,
            key: Union[str, None] = None,
            target: Union[str, None] = None,
            data: Union[dict, None] = None,
            blackout_start_time: str = BLACKOUT_START,
            blackout_end_time: str = BLACKOUT_END) -> None:
        """Send a repeating notification to one or more targets."""
        self._dispatch(
            Notification(
                Notification.NotificationTypes.repeating,
                title,
                message,
                blackout_end_time=blackout_end_time,
                blackout_start_time=blackout_start_time,
                data=data,
                interval=interval,
                key=key,
                target=target,
                when=when))

    def send(
            self,
            title: str,
            message: str,
            when: Union[datetime, None] = None,
            key: Union[str, None] = None,
            target: Union[str, None] = None,
            data: Union[dict, None] = None,
            blackout_start_time: str = BLACKOUT_START,
            blackout_end_time: str = BLACKOUT_END) -> None:
        """Send a notification to one or more targets."""
        self._dispatch(
            Notification(
                Notification.NotificationTypes.single,
                title,
                message,
                blackout_end_time=blackout_end_time,
                blackout_start_time=blackout_start_time,
                data=data,
                key=key,
                target=target,
                when=when))
