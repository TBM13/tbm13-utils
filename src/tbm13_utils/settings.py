from typing import Type, TypeVar

from .flow import *
from .encoding import *
__all__ = [
    'Setting'
]

class RawSetting(Serializable):
    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    @classmethod
    def _create_empty(cls):
        return cls('', None)

_settings: SerializableFile[RawSetting]|None = None

T = TypeVar('T')
class Setting:
    def __init__(self, key: str, value_type: Type[T], default_value: T|None = None):
        self.key = key
        self.value_type = value_type
        self.default_value = default_value

        global _settings
        if _settings is None:
            _settings = SerializableFile('config.json', RawSetting, 'key')

    @property
    def value(self) -> T|None:
        """The value of the setting.
        Returns `default_value` if not set.

        Must always be of type `value_type`. Setting this
        to `None` will delete the setting.
        """
        if _settings.contains_key(self.key):
           return self.value_type(_settings[self.key].value)

        return self.default_value
    
    @value.setter
    def value(self, value: T|None):
        if value is None:
            if _settings.contains_key(self.key):
                _settings.remove_key(self.key)
            return

        assert type(value) is self.value_type, \
            (f'Expected {self.value_type}, got {type(value)}', self.key)

        _settings[self.key] = RawSetting(self.key, str(value))