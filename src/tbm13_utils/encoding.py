import base64
import json
import urllib.parse

from typing import Any, Union
from .display import *

__all__ = [
    'Serializable',
    'base64_decode', 'base64_encode',
    'url_decode', 'url_encode'
]

class Serializable:
    """Base class for objects that can be serialized to JSON.
    
    Implements `__eq__` and `__repr__`.
    """
    _empty_dict = None

    @classmethod
    def _create_empty(cls):
        """Returns an empty instance of the class.
        
        Override this method if `__init__` requires arguments.
        """
        return cls()
    
    @classmethod
    def __get_empty_dict(cls) -> dict[str, Any]:
        if cls._empty_dict is None:
            cls._empty_dict = cls._create_empty().__dict__
        
        return cls._empty_dict

    @classmethod
    def from_dict(cls, d: dict[str, Any], ignore_list: set[str] = set()):
        """Creates an instance of the class from a dictionary.
        
        Override this method to customize how and which values
        are deserialized from JSON, specially nested objects
        with `Serializable` instances inside.
        """
        obj = cls._create_empty()

        for key, value in d.items():
            if key in ignore_list:
                continue

            v = obj.__dict__.get(key)
            if isinstance(v, Serializable):
                value = v.from_dict(value)
            elif isinstance(v, set):
                value = set(value)

            setattr(obj, key, value)
        
        return obj
    
    @classmethod
    def from_json(cls, s: str):
        """Creates an instance of the class from a JSON string."""
        return cls.from_dict(json.loads(s))

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary that contains all non-default values.
        
        Override this method to customize how and which values 
        are serialized to JSON.

        The values of the returned dict are used in `__eq__` to compare
        two instances of this class and in various methods of this class.
        """
        empty_dic = self.__get_empty_dict()
        dic = self.__dict__.copy()

        # Delete default values from JSON
        for key, value in self.__dict__.items():
            if value == empty_dic.get(key):
                dic.pop(key)

        return dic
    
    def to_json(self) -> str:
        """Serializes the object to a JSON string that only
        contains non-default values.
        """
        def serialize(o):
            if isinstance(o, Serializable):
                return o.to_dict()
            elif isinstance(o, set):
                return list(o)

            return str(o)

        return json.dumps(self, default=serialize)
    
    def clone(self) -> 'Serializable':
        """Returns a new instance created from `self.to_json()`"""
        return self.from_json(self.to_json())

    def update(self, other: 'Serializable', ignore_list: set[str] = set()) -> 'Serializable':
        """Updates the object with the non-default values of `other`.
        
        Variables in this object will have their value replaced by those
        in `other.to_dict()`. `Serializable`, `dict` and `set`
        variables will be merged instead of replaced.
        """
        for key, other_val in other.to_dict().items():
            if key in ignore_list:
                continue

            if other_val != self.__get_empty_dict().get(key):
                val = getattr(self, key)
                if (isinstance(val, Serializable) and
                    isinstance(other_val, Serializable)):
                    val.update(other_val)
                elif isinstance(val, dict) and isinstance(other_val, dict):
                    val.update(other_val)
                elif isinstance(val, set) and isinstance(other_val, set):
                    val.update(other_val)
                else:
                    setattr(self, key, other_val)

    def _to_printable_dict(self, spaces: int, key_style: str|None = '[cyan]',
                           value_style: str = '[0]') -> dict[str, str]:
        """Returns a dict with the values of this object that should be printed.
        Keys are the name of the variables and values a printable string.

        Override this function to customize `self.print()`.
        """
        dic = {
            '_header_': ' ' * spaces + f'{key_style or ""}[bold][{self.__class__.__name__}]'
        }
        for key, value in self.to_dict().items():
            key_s = key.strip('_').replace('_', ' ').title()
            dic[key] = ' ' * (spaces + 2)
            if key_style is not None:
                dic[key] += f'{key_style}{key_s}: '
            dic[key] += value_style + str(value)

        return dic

    def print(self, other: Union['Serializable', None] = None,
               spaces: int = 0):
        """Prints the non-default values of this object with color and style.
        
        If `other` isn't `None`, the differences between this object's values
        and `other`'s will also be printed.
        """

        lines = self._to_printable_dict(spaces)
        if other is not None:
            other_lines = other._to_printable_dict(
                spaces=-2, key_style=None, value_style=''
            )

        for var_name, line in lines.items():
            value = getattr(self, var_name, None)
            other_value = getattr(other, var_name, None)
            if var_name == '_header_' and other is not None:
                value = remove_style(line).lstrip(' ')
                other_value = other_lines.get('_header_', '<Deleted>')
                other_value = remove_style(other_value).lstrip(' ')

            if other is not None:
                other_line = other_lines.get(var_name, '<Deleted>')
            
            if other is None or value == other_value:
                if isinstance(value, Serializable):
                    value.print(spaces=spaces + 2)
                else:
                    color_print(line)
                continue

            if isinstance(value, Serializable):
                if isinstance(other_value, Serializable):
                    value.print(other_value, spaces + 2)
                else:
                    value.print(spaces=spaces + 2)
                    color_print(' ' * spaces + f'  [invert]-> {other_line}')
            elif isinstance(other_value, Serializable):
                color_print(f'{line} [invert]-> ')
                other_value.print(spaces=spaces + 4)

            elif isinstance(value, dict) and isinstance(other_value, dict):
                if len(other_value) == 0:
                    color_print(f'{line} [invert]-> ' + '{}')
                    continue

                line = f'{line} [invert]->[0] ' + '{'
                for key, val in other_value.items():
                    if key not in value:
                        line += '[invert]'
                    line += f'{repr(key)}: '
                    if key not in value or value[key] != val:
                        line += '[invert]'
                    line += f'{repr(val)}[0], '

                for key, val in value.items():
                    if key in other_value:
                        continue

                    line += f'[invert]{repr(key)}: <Deleted>[0], '

                color_print(line[:-2] + '}')

            elif isinstance(value, set) and isinstance(other_value, set):
                if len(other_value) == 0:
                    color_print(f'{line} [invert]-> ' + '{}')
                    continue

                line = f'{line} [invert]->[0] ' + '{'
                for val in other_value:
                    if val not in value:
                        line += '[invert]'
                    line += f'{repr(val)}[0], '

                dif = len(value) - len(other_value)
                if dif > 0:
                    line += f'[invert]<{dif} deleted>[0], '

                color_print(line[:-2] + '}')

            elif isinstance(value, list) and isinstance(other_value, list):
                if len(other_value) == 0:
                    color_print(f'{line} [invert]-> []')
                    continue

                line = f'{line} [invert]->[0] ['
                for i, val in enumerate(other_value):
                    if i >= len(value) or value[i] != val:
                        line += '[invert]'

                    line += f'{repr(val)}[0], '

                dif = len(value) - len(other_value)
                if dif > 0:
                    line += f'[invert]<{dif} deleted>[0], '

                color_print(line[:-2] + ']')

            else:
                color_print(f'{line} [invert]-> {other_line}')

        if other is None:
            return

        other_lines = other._to_printable_dict(spaces)
        printed_header = False
        for var_name, line in other_lines.items():
            if var_name in lines:
                continue

            if not printed_header:
                color_print(' ' * (spaces + 2) + '[invert]Added:')
                printed_header = True

            other_value = getattr(other, var_name, None)
            if isinstance(other_value, Serializable):
                other_value.print(spaces=spaces)
            else:
                color_print(line)

    def __eq__(self, value):
        if not isinstance(value, self.__class__):
            return False

        return self.to_dict() == value.to_dict()
    
    def __repr__(self):
        return f'{self.__class__.__name__}({self.to_dict()})'

def base64_decode(s: str) -> str:
    """Decodes a Base64-encoded string."""

    data_bytes = base64.b64decode(s.encode('utf8'))
    return data_bytes.decode('utf8')
def base64_encode(s: str) -> str:
    """Encodes a string with Base64."""

    data_bytes = base64.b64encode(s.encode('utf8'))
    return data_bytes.decode('utf8')

def url_decode(url: str) -> str:
    """Decodes (unquotes) `url`."""
    return urllib.parse.unquote(url)
def url_encode(url: str) -> str:
    """Encodes (quotes) `url`."""
    return urllib.parse.quote(url)