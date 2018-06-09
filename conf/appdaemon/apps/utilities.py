"""Define helper utilities."""

# pylint: disable=no-self-use,too-many-arguments,attribute-defined-outside-init

import datetime
import re
from typing import Callable, Tuple
from unicodedata import normalize

import Levenshtein

from app import App

RE_SLUGIFY = re.compile(r'[^a-z0-9_]+')
TBL_SLUGIFY = {ord('ß'): 'ss'}


class Utilities(App):
    """Define a general utilities object w/ AppDaemon awareness."""

    # --- HELPERS -------------------------------------------------------------
    def camel_to_underscore(self, string: str) -> str:
        """Convert ThisString to this_string."""
        return re.sub('(?!^)([A-Z]+)', r'_\1', string).lower()

    def cancel_callback_list(self, callback_list: list) -> None:
        """Correctly cancel and delete callbacks in a list."""
        for i in range(len(callback_list) - 1, -1, -1):
            handle = callback_list[i]

            self.log('Canceling timer: {0}'.format(handle), level='DEBUG')

            self.cancel_timer(handle)
            del callback_list[i]

    def grammatical_list_join(self, the_list: list) -> str:
        """Return a grammatically correct list join."""
        return ', '.join(the_list[:-2] + [' and '.join(the_list[-2:])])

    def relative_search_dict(
            self, the_dict: dict, search: str,
            threshold: float = 0.3) -> Tuple[str, str]:
        """Return a key/value pair (or its closest neighbor) from a dict."""
        _search = search.lower()
        try:
            _match = [
                key for key in the_dict.keys() if key.lower() in _search
            ][0]
            match = (_match, the_dict[_match])
        except IndexError:
            try:
                _match = sorted(
                    [
                        key for key in the_dict.keys()
                        if Levenshtein.ratio(_search, key.lower()) > threshold
                    ],
                    key=lambda k: Levenshtein.ratio(_search, k.lower()),
                    reverse=True)[0]
                match = (_match, the_dict[_match])
            except IndexError:
                match = (None, None)

        return match

    def relative_search_list(
            self, the_list: list, search: str,
            threshold: float = 0.3) -> Tuple[str, str]:
        """Return an item (or its closest neighbor) from a list."""
        _search = search.lower()
        try:
            match = [value for value in the_list
                     if value.lower() in _search][0]
        except IndexError:
            try:
                _match = sorted(
                    [
                        value for value in the_list if
                        Levenshtein.ratio(_search, value.lower()) > threshold
                    ],
                    key=lambda v: Levenshtein.ratio(_search, v.lower()),
                    reverse=True)[0]
                match = _match
            except IndexError:
                match = None

        return match

    def relative_time_of_day(self) -> str:
        """Return the relative time of day based on time."""
        greeting = None
        now = self.datetime()

        if now.hour < 12:
            greeting = 'morning'
        elif 12 <= now.hour < 18:
            greeting = 'afternoon'
        else:
            greeting = 'evening'

        return greeting

    def run_on_days(
            self, callback: Callable[..., None], day_list: list,
            start: datetime.time, **kwargs: dict) -> list:
        """Run a callback on certain days (at the specified time)."""
        handle = []
        upcoming_days = []

        today = self.date()
        todays_event = datetime.datetime.combine(today, start)

        if todays_event > self.datetime():
            if today.strftime('%A') in day_list:
                upcoming_days.append(today)

        for day_number in range(1, 8):
            day = today + datetime.timedelta(days=day_number)
            if day.strftime('%A') in day_list:
                if len(upcoming_days) < len(day_list):
                    upcoming_days.append(day)

        for day in upcoming_days:
            event = datetime.datetime.combine(day, start)
            handle.append(self.run_every(callback, event, 604800, **kwargs))

        return handle

    def run_on_weekdays(
            self, callback: Callable[..., None], start: datetime.time,
            **kwargs: dict) -> list:
        """Run a callback on weekdays (at the specified time)."""
        return self.run_on_days(
            callback, ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            start, **kwargs)

    def run_on_weekend_days(
            self, callback: Callable[..., None], start: datetime.time,
            **kwargs: dict) -> list:
        """Run a callback on weekend days (at the specified time)."""
        return self.run_on_days(
            callback, ['Saturday', 'Sunday'], start, **kwargs)

    def slugify(self, text: str) -> str:
        """Slugify a given text."""
        text = normalize('NFKD', text)
        text = text.lower()
        text = text.replace(" ", "_")
        text = text.translate(TBL_SLUGIFY)
        text = RE_SLUGIFY.sub("", text)

        return text

    def suffix_strftime(self, frmt: str, input_dt: datetime.datetime) -> str:
        """Define a version of strftime() that puts a suffix on dates."""
        day_endings = {
            1: 'st',
            2: 'nd',
            3: 'rd',
            21: 'st',
            22: 'nd',
            23: 'rd',
            31: 'st'
        }
        return input_dt.strftime(frmt).replace(
            '{TH}',
            str(input_dt.day) + day_endings.get(input_dt.day, 'th'))

    def time_is_between(
            self, target_dt: datetime.datetime, start_time: str,
            end_time: str) -> bool:
        """Generalization of AppDaemon's now_is_between method."""
        start_time = self.parse_time(start_time)
        end_time = self.parse_time(end_time)
        start_dt = target_dt.replace(
            hour=start_time.hour,
            minute=start_time.minute,
            second=start_time.second)
        end_dt = target_dt.replace(
            hour=end_time.hour, minute=end_time.minute, second=end_time.second)

        if end_dt < start_dt:
            # Spans midnight
            if target_dt < start_dt and target_dt < end_dt:
                target_dt = target_dt + datetime.timedelta(days=1)
            end_dt = end_dt + datetime.timedelta(days=1)
        return start_dt <= target_dt <= end_dt

    def underscore_to_camel(self, string: str) -> str:
        """Convert this_string to ThisString."""
        return ''.join(x.capitalize() or '_' for x in string.split('_'))
