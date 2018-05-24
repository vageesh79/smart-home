"""Define generic automation objects and logic."""

# pylint: disable=too-many-arguments,attribute-defined-outside-init
# pylint: disable=not-callable,protected-access,too-few-public-methods

from core import Base


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

            features = []  # type: ignore
            feature_obj = feature_class(self, name, {
                **self.entities,
                **feature.get('entities', {})
            }, {
                **self.properties,
                **feature.get('properties', {})
            }, feature.get('constraint'))

            if not feature_obj.repeatable and feature_obj in features:
                self.error(
                    'Refusing to reinitialize single feature: {0}'.format(
                        name))
                continue

            self.log('Initializing feature {0} (constraint: {1})'.format(
                name, feature_obj.constraint))

            features.append(feature_obj)
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
        self.name = name
        self.properties = properties

        if constraint_config:
            if constraint_config.get('key'):
                self.constraint = 'input_boolean.{0}_{1}'.format(
                    hass.name, constraint_config['key'])
            else:
                self.constraint = 'input_boolean.{0}_{1}'.format(
                    hass.name, name)
        else:
            self.constraint = None

    def __eq__(self, other):
        """Define equality based on name."""
        return self.name == other.name

    @property
    def repeatable(self) -> bool:
        """Define whether a feature can be implemented multiple times."""
        return False

    def initialize(self) -> None:
        """Define an initializer method."""
        raise NotImplementedError
