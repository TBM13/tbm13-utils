from typing import Type

from .encoding import *
from .flow import *

__all__ = [
    'Setting'
]

class RawSetting(Serializable):
    key: str
    value: str

_settings: SerializableFile[str, RawSetting] = SerializableFile('config.json', 'key', RawSetting)

class Setting[T]:
    def __init__(self, key: str, value_type: Type[T], default_value: T|None = None):
        self.key = key
        self.value_type = value_type
        self.default_value = default_value

    @property
    def value(self) -> T|None:
        """The value of the setting.
        Returns `default_value` if not set.

        Must always be of type `T`. Setting this to `None`
        will delete the setting, making this return the default value
        or `None`.
        """
        if _settings.contains(self.key):
           return self.value_type(_settings.get(self.key).value)  # type: ignore

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

        _settings.set(
            RawSetting(key=self.key, value=str(value))
        )