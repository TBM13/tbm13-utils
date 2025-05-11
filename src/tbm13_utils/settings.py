import dataclasses
from typing import Type

from .encoding import *
from .flow import *

__all__ = [
    'Setting'
]

@dataclasses.dataclass
class RawSetting(Serializable):
    key: str
    value: str

_settings: ObjectsFile[str, RawSetting] = ObjectsFile('config.json', 'key', RawSetting)

class Setting[T]:
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
        if _settings.contains(self.key):
           return self.value_type(_settings.get(self.key).value)

        return self.default_value
    
    @value.setter
    def value(self, value: T|None):
        if value is None:
            if _settings.contains(self.key):
                _settings.pop(self.key)
            return

        if type(value) is not self.value_type:
            raise TypeError(
                f'Expected {self.value_type}, got {type(value)}', self.key
            )

        _settings.set(RawSetting(self.key, str(value)))