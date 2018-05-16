"""Provides data for trash/recycling/etc. pickups."""
from logging import getLogger
from datetime import timedelta
from math import ceil

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION, CONF_MONITORED_CONDITIONS
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = getLogger(__name__)
REQUIREMENTS = ['pyden==0.4.1']

ATTR_PICKUP_DATE = 'pickup_date'

CONF_PLACE_ID = 'recollect_place_id'

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=10)

PICKUP_TYPES = {
    'compost': ('Compost Pickup', 'mdi:food-apple'),
    'extra_trash': ('Extra Trash Pickup', 'mdi:truck'),
    'recycling': ('Recycling Pickup', 'mdi:recycle'),
    'trash': ('Trash Pickup', 'mdi:delete')
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_PLACE_ID): cv.string,
    vol.Optional(CONF_MONITORED_CONDITIONS, default=[]):
        vol.All(cv.ensure_list, [vol.In(PICKUP_TYPES)]),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the platform."""
    import pyden

    recollect_place_id = config.get(CONF_PLACE_ID)
    _LOGGER.debug('Recollect place ID: %s', recollect_place_id)

    pickups_to_watch = config.get(CONF_MONITORED_CONDITIONS)
    _LOGGER.debug('Pickup types being monitored: %s', pickups_to_watch)

    try:
        client = pyden.TrashClient(recollect_place_id)
    except pyden.exceptions.GeocodingError as exc_info:
        _LOGGER.error('An error occurred while geocoding: %s', str(exc_info))
        return False
    except pyden.exceptions.HTTPError as exc_info:
        _LOGGER.error('An HTTP error occurred: %s', str(exc_info))
        return False
    except Exception as exc_info:  # pylint: disable=broad-except
        _LOGGER.error('An unknown error occurred...')
        _LOGGER.debug(str(exc_info))
        return False

    sensors = []
    for pickup_type in pickups_to_watch:
        name, icon = PICKUP_TYPES[pickup_type]
        data = PickupData(client, pickup_type, hass.config.time_zone)
        sensors.append(DenverTrashSensor(data, name, icon))

    add_devices(sensors, True)


class DenverTrashSensor(Entity):
    """Define a class representation of the sensor."""

    def __init__(self, data, name, icon):
        """Initialize."""
        self._data = data
        self._icon = icon
        self._name = name
        self._state = None

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        if self._data:
            return {
                ATTR_ATTRIBUTION: 'City and County of Denver, CO',
                ATTR_PICKUP_DATE:
                    dt.parse_date(self._data.raw_date).strftime('%B %e, %Y')
            }

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


class PickupData(object):
    """ Define a class to deal with representations of the pickup data."""

    def __init__(self, client, pickup_type, local_tz):
        self._client = client
        self._humanized_pickup = None
        self._local_tz = local_tz
        self._pickup_type = pickup_type
        self._raw_date = None

    @property
    def humanized_pickup(self):
        """Return the humanized next pickup number."""
        return self._humanized_pickup

    @property
    def raw_date(self):
        """Return the raw date of the pickup."""
        return self._raw_date

    def _humanize_pickup(self, future_date):
        """Humanize how many pickups away this type is."""
        today = dt.now(self._local_tz).date()
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
        import pyden.exceptions as exceptions

        try:
            raw_date = self._client.next_pickup(self._pickup_type)
            next_date = dt.parse_date(raw_date)
            self._raw_date = raw_date
            self._humanized_pickup = self._humanize_pickup(next_date)
        except exceptions.HTTPError as exc_info:
            _LOGGER.error('Unable to get next %s pickup date',
                          self._pickup_type)
            _LOGGER.debug(str(exc_info))
