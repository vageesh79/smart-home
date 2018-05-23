"""Provides data for trash/recycling/etc. pickups."""
from logging import getLogger
from datetime import timedelta
from math import ceil

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION, CONF_MONITORED_CONDITIONS
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.util.dt import now, parse_date

_LOGGER = getLogger(__name__)
REQUIREMENTS = ['pyden==0.4.1']

ATTR_PICKUP_DATE = 'pickup_date'

CONF_PLACE_ID = 'recollect_place_id'

DEFAULT_ATTR = 'City and County of Denver, CO'

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=10)

PICKUP_TYPES = {
    'compost': ('Compost Pickup', 'mdi:food-apple'),
    'extra_trash': ('Extra Trash Pickup', 'mdi:truck'),
    'recycling': ('Recycling Pickup', 'mdi:recycle'),
    'trash': ('Trash Pickup', 'mdi:delete')
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_PLACE_ID): cv.string,
    vol.Optional(CONF_MONITORED_CONDITIONS, default=list(PICKUP_TYPES)):
        vol.All(cv.ensure_list, [vol.In(PICKUP_TYPES)]),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the platform."""
    from pyden import TrashClient
    from pyden.exceptions import GeocodingError, HTTPError

    try:
        client = TrashClient(config[CONF_PLACE_ID])
    except GeocodingError as exc:
        _LOGGER.error('An error occurred while geocoding: %s', exc)
        return False
    except HTTPError as exc:
        _LOGGER.error('An HTTP error occurred: %s', exc)
        return False

    sensors = []
    for pickup_type in config[CONF_MONITORED_CONDITIONS]:
        name, icon = PICKUP_TYPES[pickup_type]
        data = PickupData(client, pickup_type, hass.config.time_zone)
        sensors.append(DenverTrashSensor(data, name, icon))

    add_devices(sensors, True)

    return True


class DenverTrashSensor(Entity):
    """Define a class representation of the sensor."""

    def __init__(self, data, name, icon):
        """Initialize."""
        self._attrs = {ATTR_ATTRIBUTION: DEFAULT_ATTR}
        self._data = data
        self._icon = icon
        self._name = name
        self._state = None

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attrs

    @property
    def icon(self):
        """Return the icon of the pickup type."""
        return self._icon

    @property
    def name(self):
        """Return the name of the pickup type."""
        return self._name

    @property
    def state(self):
        """Return the next pickup date of the pickup type."""
        return self._state

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update the status."""
        _LOGGER.debug('Updating sensor: %s', self._name)

        self._data.update()
        self._state = self._data.humanized_pickup
        self._attrs.update({ATTR_PICKUP_DATE: self._data.raw_date})


class PickupData(object):  # pylint: disable=too-few-public-methods
    """ Define a class to deal with representations of the pickup data."""

    def __init__(self, client, pickup_type, local_tz):
        self._client = client
        self._local_tz = local_tz
        self._pickup_type = pickup_type
        self.humanized_pickup = None
        self.raw_date = None

    def _humanize_pickup(self, future_date):
        """Humanize how many pickups away this type is."""
        today = now(self._local_tz).date()
        delta_days = (future_date - today).days

        if delta_days < 1:
            return "in today's pickup"

        if delta_days < 2:
            return "in tomorrow's pickup"

        if delta_days <= 7:
            return 'in the next pickup'

        return 'in {0} pickups'.format(ceil(delta_days / 7))

    def update(self):
        """Update the data for the pickup."""
        from pyden.exceptions import HTTPError

        try:
            next_date = parse_date(self._client.next_pickup(self._pickup_type))
            self.humanized_pickup = self._humanize_pickup(next_date)
            self.raw_date = next_date.strftime('%B %e, %Y')
        except HTTPError as exc:
            _LOGGER.error('Unable to get next %s pickup date: %s',
                          self._pickup_type, exc)
