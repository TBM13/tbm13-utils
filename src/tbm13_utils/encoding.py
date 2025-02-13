import base64
import filelock
import json
import os
import urllib.parse

from typing import Any, Union, Type
from .display import *
from .flow import *

__all__ = [
    'Serializable', 'SerializableFile',
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
            elif isinstance(v, tuple):
                value = tuple(value)
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

            elif ((isinstance(value, list) and isinstance(other_value, list))
                  or (isinstance(value, tuple) and isinstance(other_value, tuple))):
                open = '['
                close = ']'
                if isinstance(value, tuple):
                    open = '('
                    close = ')'

                if len(other_value) == 0:
                    color_print(f'{line} [invert]-> {open}{close}')
                    continue

                line = f'{line} [invert]->[0] {open}'
                for i, val in enumerate(other_value):
                    if i >= len(value) or value[i] != val:
                        line += '[invert]'

                    line += f'{repr(val)}[0], '

                dif = len(value) - len(other_value)
                if dif > 0:
                    line += f'[invert]<{dif} deleted>[0], '

                color_print(line[:-2] + close)

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
                other_value.print(spaces=spaces + 2)
            else:
                color_print(line)

    def __eq__(self, value):
        if not isinstance(value, self.__class__):
            return False

        return self.to_dict() == value.to_dict()
    
    def __repr__(self):
        return f'{self.__class__.__name__}({self.to_dict()})'

class SerializableFile[T: Serializable]:
    """A dictionary-like object that contains `Serializable` objects as values.

    It's directly tied to a json file, and each modification updates it.
    Empty lines or comments (lines that start with '#') are ignored.
    
    The file is locked with `filelock` while reading/writing to avoid race conditions.
    On every read & write the file and dict is reloaded if it was modified by another process.
    """
    def __init__(self, path: str, type: Type[T], key_name: str,
                 allow_duplicate_keys: bool = False):
        """`type` is the `Serializable` subclass that this object will contain.

        `key_name` is the name of a variable in `type` that will be used as the dictionary's key.

        If `allow_duplicate_keys` is `True`, duplicate keys will be allowed and the values of
        the dictionary will be a `list[Serializable]` with all the objects with the same respective key.
        """
        self.path = path
        self.type = type
        self._key_name: str = key_name
        self._allow_duplicate_keys = allow_duplicate_keys

        assert key_name in type._create_empty().__dict__, ('Key name not found', key_name)

        self._dic: dict[Any, T|list[T]] = None
        self._last_modification: float = None
        self._lock = filelock.FileLock(path + '.lock')

        self._read()

    def _read(self):
        """If needed, clears the dictionary and loads the objects from the file."""

        with self._lock:
            if self._dic is not None and self._last_modification == os.path.getmtime(self.path):
                return

            self._dic = {}
            # Create file if it doesn't exist
            if not os.path.isfile(self.path):
                open(self.path, 'w').close()
                self._last_modification = os.path.getmtime(self.path)
                return
            
            # Load `Serializable` objects from file
            with open(self.path, 'r', encoding='utf8') as file:
                for line in file.readlines():
                    line = line.strip()
                    if len(line) == 0 or line.startswith('#'):
                        continue

                    obj = self.type.from_json(line)
                    key = getattr(obj, self._key_name)
                    if not self._allow_duplicate_keys:
                        assert not key in self._dic, ('Key already exists', key)
                        self._dic[key] = obj
                    else:
                        self._dic.setdefault(key, []).append(obj)

            self._last_modification = os.path.getmtime(self.path)

    def write(self):
        """Overwrites the file with the current dictionary's values.
        
        Call this if you modified the dictionary's items manually.
        """
        with self._lock:
            with open(self.path, 'w', encoding='utf8') as file:
                for obj in self._dic.values():
                    if self._allow_duplicate_keys:
                        for o in obj:
                            file.write(o.to_json() + '\n')
                    else:
                        file.write(obj.to_json() + '\n')

                # remove last newline & everything after
                file.seek(file.tell() - 1)
                file.truncate()

            self._last_modification = os.path.getmtime(self.path)

    def __getitem__(self, key: Any) -> T|list[T]:
        self._read()
        return self._dic[key]

    def get(self, key: Any, default: T) -> T|list[T]:
        """Returns the value of `key`.
        
        If `key` isn't found, returns `default`.

        Remember to call `write` if you modify the values directly.
        """
        self._read()
        if not key in self._dic:
            return default

        return self._dic[key]

    def __setitem__(self, key: Any, value: T):
        assert not self._allow_duplicate_keys, \
            'Cannot set items directly when duplicate keys are allowed. Use `add`/`replace` instead.'

        assert key == getattr(value, self._key_name), ('Key mismatch', key)
        with self._lock:
            self._read()
            self._dic[key] = value
            self.write()

    def add(self, value: T):
        """Adds a cloned `value` to the dictionary, if not already present."""
        value = value.clone()

        with self._lock:
            self._read()
            key = getattr(value, self._key_name)

            if self._allow_duplicate_keys:
                self._dic.setdefault(key, [])
                assert not value in self._dic[key], ('Value already exists', value, key)
                
                self._dic[key].append(value)
            else:
                assert not key in self._dic, ('Key already exists', key)
                self._dic[key] = value

            self.write()

    def replace(self, old: T, new: T):
        """Replaces `old` with a cloned `new` in the dictionary.
        
        If `old` isn't found, raises `AssertionError`.
        """
        new = new.clone()

        with self._lock:
            self._read()
            key = getattr(old, self._key_name)
            new_key = getattr(new, self._key_name)
            assert key == new_key, \
                ('Replacing with different keys isn\'t supported', key, new_key)

            if self._allow_duplicate_keys:
                assert key in self._dic, ('Key not found', key)

                found = False
                for i, obj in enumerate(self._dic[key]):
                    if obj == old:
                        self._dic[key][i] = new
                        self.write()
                        found = True
                        break

                assert found, ('Value not found', old)
            else:
                assert key in self._dic, ('Key not found', key)
                assert self._dic[key] == old, ('Value mismatch', old)

                self._dic[key] = new
                self.write()

    def remove_key(self, key: Any):
        """Removes `key` from the dictionary.
        
        Can only be used when `allow_duplicate_keys` is `False`.
        """
        assert not self._allow_duplicate_keys, \
            'Cannot remove key directly when duplicate keys are allowed. Use `remove_value` instead.'

        with self._lock:
            self._read()
            assert key in self._dic, ('Key not found', key)

            self._dic.pop(key)
            self.write()

    def remove_value(self, value: T):
        """Removes `value` from the dictionary.
        
        If `value` isn't found, raises `AssertionError`.
        """
        with self._lock:
            self._read()
            key = getattr(value, self._key_name)

            if self._allow_duplicate_keys:
                assert key in self._dic, ('Key not found', key)

                found = False
                for i, obj in enumerate(self._dic[key]):
                    if obj == value:
                        self._dic[key].pop(i)
                        if len(self._dic[key]) == 0:
                            self._dic.pop(key)

                        self.write()
                        found = True
                        break

                assert found, ('Value not found', value)
            else:
                assert key in self._dic, ('Key not found', key)
                assert self._dic[key] == value, ('Value mismatch', value)

                self._dic.pop(key)
                self.write()

    def contains_key(self, key: Any) -> bool:
        """Returns `True` if `key` is in the dictionary."""
        self._read()
        return key in self._dic
    
    def contains_value(self, value: T) -> bool:
        """Returns `True` if `value` is in the dictionary."""
        self._read()
        key = getattr(value, self._key_name)
        if self._allow_duplicate_keys:
            return key in self._dic and value in self._dic[key]

        return key in self._dic and self._dic[key] == value
    
    def items(self):
        """Returns the dictionary's `items()`.
        
        Remember to call `write` if you modify the items directly.
        """
        self._read()
        return self._dic.items()
    
    def keys(self):
        """Returns the dictionary's `keys()`.
        
        Remember to call `write` if you modify the keys directly.
        """
        self._read()
        return self._dic.keys()
    
    def values(self):
        """Returns the dictionary's `values()`.
        
        Remember to call `write` if you modify the values directly.
        """
        self._read()
        return self._dic.values()
    
    def __len__(self) -> int:
        self._read()
        return len(self._dic)

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