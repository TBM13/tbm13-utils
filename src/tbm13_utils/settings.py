import os

from .display import *
__all__ = [
    'settings_file', 'Setting'
]

settings_file = 'config'

def _init():
    """Creates `settings_file` if it doesn't exist."""

    if not os.path.isfile(settings_file):
        open(settings_file, 'a').close()

def _read_setting(key: str) -> str | None:
    """Reads the value of `key` from `settings_file` and returns it.

    If the setting is not set, returns `None`.
    """
    _init()
    with open(settings_file) as file:
        for line in file:
            if line.startswith(f'{key}='):
                return line.rstrip()[(len(key) + 1):]

    return None

def _write_setting(key: str, value: str):
    """Writes `key` and `value` to `settings_file`."""

    _init()
    with open(settings_file, 'r+') as file:
        data = file.read()
        for line in data.split('\n'):
            if line.startswith(f'{key}='):
                # TODO: Use a better method than this
                data = data.replace(line, f'{key}={value}')

                # Reset pointer and write
                file.seek(0)
                file.truncate(0)
                file.write(data)
                return
        
        # Key not found, so add it
        file.write(f'{key}={value}\n')

class Setting():
    def __init__(self, key: str, value_type, default_value=None):
        self.key = key
        self.value_type = value_type
        self.default_value = default_value

    def read(self):
        """Reads the value of the setting, parses and returns it.
        
        If the value can't be parsed, prints error
        and returns `default_value` or `None`.

        If the setting is not set and `default_value` isn't `None`,
        sets the setting to `default_value` and returns it.

        Otherwise, returns `None`.
        """

        value = _read_setting(self.key)
        if value is None:
            if self.default_value is not None:
                self.write(self.default_value)

            return self.default_value

        try:
            if self.value_type is bool:
                value = value.lower()
                if value == 'true':
                    value = True
                elif value == 'false':
                    value = False
                else: 
                    raise ValueError('Not a boolean')
            elif self.value_type is int:
                value = int(value)
            elif self.value_type is float:
                value = float(value)
            elif self.value_type is str:
                pass
            else:
                raise ValueError(f'Unknown value type "{self.value_type}"')
        except ValueError:
            error(f'[Setting "{self.key}"] Invalid value "{self.value_type}". ' +
                  f'Returning default value "{self.default_value}"')

            value = self.default_value

        return value

    def write(self, value):
        """Sets the setting's value to `value`.
        
        Returns `True` if successful.
        """

        if not type(value) is self.value_type:
            error(f'[Setting "{self.key}"] New value "{value}" ("{type(value)}") ' +
                  f'doesn\'t match the value type "{self.value_type}"')
            return False

        _write_setting(self.key, value)
        return True