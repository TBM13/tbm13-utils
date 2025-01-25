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

_settings = SerializableFile('config.json', RawSetting, 'key')

T = TypeVar('T')
class Setting:
    def __init__(self, key: str, value_type: Type[T], default_value: T|None = None):
        self.key = key
        self.value_type = value_type
        self.default_value = default_value

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

        if not type(value) is self.value_type:
            raise AbortInterrupt(f'Setting "{self.key}"\'s value isn\'t of type "{self.value_type}"', value)

        _settings[self.key] = RawSetting(self.key, str(value))