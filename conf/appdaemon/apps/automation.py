"""Define generic automation objects and logic."""

# pylint: disable=too-many-arguments,attribute-defined-outside-init
# pylint: disable=not-callable,protected-access,too-few-public-methods

from base import Base


class Automation(Base):
    """Define a base automation object."""

    def initialize(self) -> None:
        """Initialize."""
        super().initialize()

        self.friendly_name = self.args.get('friendly_name', None)

        if self.args.get('manager_app'):
            self.manager_app = getattr(self, self.args['manager_app'])

        for feature in self.args.get('features'):
            name = feature['name']

            feature_class = getattr(self,
                                    self.utilities.underscore_to_camel(name),
                                    None)
            if not feature_class:
                self.log('Missing class for feature: {0}'.format(name))
                continue

            feature_obj = feature_class(self, name, {
                **self.entities,
                **feature.get('entities', {})
            }, {
                **self.properties,
                **feature.get('properties', {})
            }, feature.get('constraint'))

            self.log('Initializing feature {0} (constraint: {1})'.format(
                name, feature_obj.constraint))

            feature_obj.initialize()


class Feature(object):
    """Define an automation feature."""

    def __init__(self,
                 hass: Automation,
                 name: str,
                 entities: dict = None,
                 properties: dict = None,
                 constraint_config: dict = None) -> None:
        """Initiliaze."""
        self.entities = entities
        self.hass = hass
        self.properties = properties

        if constraint_config:
            if constraint_config.get('key'):
                self.constraint = 'input_boolean.{0}_{1}'.format(
                    hass.name,
                    constraint_config['key'])
            else:
                self.constraint = 'input_boolean.{0}_{1}'.format(
                    hass.name, name)
        else:
            self.constraint = None

    def initialize(self) -> None:
        """Define an initializer method."""
        raise NotImplementedError
