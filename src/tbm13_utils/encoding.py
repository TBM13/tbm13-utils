import base64
import dataclasses
import enum
import inspect
import json
import os
import pydoc
import time
import types
import urllib.parse
from typing import Any, Self, Union, get_args, get_origin, overload, override

import filelock

from .display import *
from .flow import *

__all__ = [
    'Serializable', 'SerializableError',
    'ObjectsFile', 'MultiKeyObjectsFile',
    'json_serialize', 'json_deserialize',
    'base64_decode', 'base64_encode',
    'url_decode', 'url_encode',
]

class InheritReprEqMeta(type):
    def __new__(cls, name, bases, dct):
        new_cls = super().__new__(cls, name, bases, dct)
        
        # Avoid @dataclass decorator from overriding __repr__ and __eq__
        # on subclasses that don't override it explicitly
        methods = ['__repr__', '__eq__']
        for method in methods:
            if dataclasses.is_dataclass(new_cls) and method not in dct:
                for base in bases:
                    if hasattr(base, method) and getattr(base, method) is not getattr(object, method):
                        setattr(new_cls, method, getattr(base, method))
                        break
        
        return new_cls

class SerializableError(Exception):
    pass

@dataclasses.dataclass
class Serializable(metaclass=InheritReprEqMeta):
    """Base class for objects that can be serialized to and from JSON.
    Subclasses are expected to be dataclasses.
    
    Field types are mandatory. The following types are supported:
    `str`, `int`, `float`, `bool`, `None`, `enum.Enum` (and subclasses), `Serializable` (and subclasses).

    Field types can also be `list`/`tuple`/`set`/`dict` of any previously mentioned type
    (except dictionary keys, they can only be `str`).

    Unions of all these types are also supported. This includes combinations like `list[Serializable|int|None]`.

    Options:
    - `_ignored_fields`: Fields added here won't be serialized to JSON, won't be checked in `__eq__`
    & will be ignored on `clone()`, `update()` and `print()`.

    Overrideable methods:
    - `_to_printable_dict()`: Override to customize `print()`.

    """
    _ignored_fields: set[str] = dataclasses.field(
        default_factory=lambda: set(['_ignored_fields']), init=False)

    @classmethod
    def _from_dict(cls, d: dict[str, Any], ignore_list: set[str] = set()):
        d = d.copy()
        
        field_names = {field.name for field in dataclasses.fields(cls)}
        for key, _ in d.items():
            if key in ignore_list:
                d.pop(key)
                continue

            if not key in field_names:
                raise SerializableError(
                    f'Field not found in dataclass', key, cls.__name__
                )
        
        return cls(**d)

    @classmethod
    def from_json(cls, s: str) -> Self:
        """Creates an instance of the class from a JSON string."""
        caller = inspect.currentframe().f_back
        return json_deserialize(cls, s, caller.f_locals, caller.f_globals)

    def _to_dict(self) -> dict[str, Any]:
        """Returns a dictionary that contains all non-default & non-ignored fields."""

        res = {}
        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            if (
                value == field.default
                or (field.default_factory is not dataclasses.MISSING and value == field.default_factory())
                or field.name in self._ignored_fields
            ):
                continue
            elif isinstance(self.__dict__[field.name], Serializable):
                res[field.name] = self.__dict__[field.name]._to_dict()
            else:
                res[field.name] = self.__dict__[field.name]

        return res
    
    def to_json(self) -> str:
        """Serializes the object to a JSON string that only
        contains non-default & non-ignored fields.
        """
        return json_serialize(self._to_dict())
    
    def clone(self) -> Self:
        """Returns an exact clone of this object, except for the ignored fields."""
        return self.from_json(self.to_json())
    
    def update(self, other: Self, ignore_list: set[str] = set()):
        """Updates the object with the non-default & non-ignored fields of `other`.
        
        Fields of type `Serializable`, `dict` & `set` will be merged instead of replaced.
        """
        for key, other_val in other._to_dict().items():
            if key in ignore_list:
                continue

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
        """Returns a dict with the data of this object that should be printed.
        Keys are the field names and values a printable string.
        """
        dic = {
            '_header_': ' ' * spaces + f'{key_style or ""}[bold][{self.__class__.__name__}]'
        }
        for key, value in self._to_dict().items():
            key_s = key.strip('_').replace('_', ' ').title()
            dic[key] = ' ' * (spaces + 2)
            if key_style is not None:
                dic[key] += f'{key_style}{key_s}: '
            dic[key] += value_style + str(value)

        return dic
    
    def print(self, other: Union['Serializable', None] = None,
               spaces: int = 0):
        """Prints the non-default & non-ignored fields of this object with color and style.
        
        If `other` isn't `None`, the differences between this and `other` will also be printed.
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

        return self._to_dict() == value._to_dict()

    def __repr__(self):
        return f'{self.__class__.__name__}({self._to_dict()})'

class ObjectsFile[K, V: object]:
    """A dictionary-like object that contains objects of type V as values.

    It's directly tied to a json file, and each modification updates it.
    Empty lines or comments (lines that start with '#') are ignored.
    
    The file is locked with `filelock` while reading/writing to avoid race conditions.
    Before every read & write the file is re-read if it was modified externally.
    """
    def __init__(self, path: str, key_name: str, obj_type: type[V]):
        """`path` is the path to the JSON file that will be used to read/write the objects from/to.
        It doesn't need to exist.
        
        `key_name` is the name of the object's field that will be used as the key.

        `obj_type` is the type of the objects that will be stored.
        """
        self.path = path
        self._key_name: str = key_name
        self._obj_type = obj_type
        self._dic: dict[K, V] = {}
        self._last_modification: float = None
        self._lock = filelock.FileLock(path + '.lock')

        self._read()
    
    def _get_key(self, obj: V) -> K:
        """Returns the key of the object."""
        return getattr(obj, self._key_name)

    def _clone_object(self, obj: V) -> V:
        """Clones the object."""
        return json_deserialize(
            self._obj_type, json_serialize(obj), locals(), globals()
        )

    def _add_from_json(self, data: str):
        obj = json_deserialize(self._obj_type, data, locals(), globals())
        key = self._get_key(obj)
        if key in self._dic:
            raise KeyError('Key already exists', key)

        self._dic[key] = obj

    def _read(self):
        """If needed, clears the dictionary and loads the objects from the file."""

        with self._lock:
            if not os.path.isfile(self.path):
                return
            if self._last_modification is not None and self._last_modification == os.path.getmtime(self.path):
                return

            self._dic.clear()         
            with open(self.path, 'r', encoding='utf8') as file:
                for line in file.readlines():
                    line = line.strip()
                    if len(line) == 0 or line.startswith('#'):
                        continue

                    self._add_from_json(line)

            self._last_modification = os.path.getmtime(self.path)

    def _obj_to_json_line(self, obj: V) -> str:
        return json_serialize(obj) + '\n'

    def write(self):
        """Overwrites the JSON file with the stored objects.
        
        Call this method only if you modified one or more objects directly (by reference).
        """
        with self._lock:
            # Just in case we or some other ObjectsFile instance recently read the file.
            # If we write to it immediately, the file's modification time
            # won't change and thus instance won't detect the changes
            time.sleep(0.01)

            with open(self.path, 'w', encoding='utf8') as file:
                for obj in self._dic.values():
                    file.write(self._obj_to_json_line(obj))

                if file.tell() != 0:
                    # remove last newline & everything after
                    file.seek(file.tell() - 1)
                    file.truncate()

            # Wait for OS to update file modification time
            slept = 0
            while os.path.getmtime(self.path) == self._last_modification:
                if slept > 0.5:
                    raise TimeoutError('Timeout waiting for OS to update file modification time', self.path)

                sleep = 0.005
                slept += sleep
                time.sleep(sleep)

            self._last_modification = os.path.getmtime(self.path)

    @overload
    def get(self, key: K) -> V:
        """Returns a clone of the object with the given key."""
        ...
    @overload
    def get(self, key: K, default: V) -> V:
        """Returns a clone of the object with the given key if it exists.

        Otherwise, returns `default` as-is.
        """
        ...
    def get(self, key: K, default: V = None) -> V:
        self._read()
        if default is not None:
            return self._dic.get(key, default)
        
        if key not in self._dic:
            raise KeyError('Key not found', key)

        return self._clone_object(self._dic[key])

    def set(self, obj: V):
        """Sets the value of the object's key to a clone of `obj`.

        If an object with the same key already exists, it will be replaced.
        """
        obj = self._clone_object(obj)
        key = self._get_key(obj)
        with self._lock:
            self._read()
            self._dic[key] = obj
            self.write()

    def add(self, obj: V):
        """Adds a clone of `obj`.
        
        Will raise `KeyError` if an object with the same key already exists.
        """
        obj = self._clone_object(obj)
        key = self._get_key(obj)
        with self._lock:
            self._read()
            if key in self._dic:
                raise KeyError('Key already exists', key)

            self._dic[key] = obj
            self.write()

    def replace(self, old: V, new: V):
        """Replaces the object `old` with a clone of the object `new`.
        
        `old` and `new` must have the same key. Additionally, `old` must be
        equal to the stored object.
        """
        new = self._clone_object(new)

        with self._lock:
            self._read()
            key = self._get_key(old)
            new_key = self._get_key(new)

            if key not in self._dic:
                raise KeyError('Key not found', key)
            if key != new_key:
                raise KeyError('Key mismatch', key, new_key)
            if old != self._dic[key]:
                raise ValueError('Value mismatch', old, self._dic[key])

            self._dic[key] = new
            self.write()

    @overload
    def pop(self, key: K) -> V:
        """Removes the object with the same key as `key` and returns it."""
        ...
    @overload
    def pop(self, obj: V) -> V:
        """Removes the object with the same key as the given object.
        
        Returns the removed object.
        """
        ...
    def pop(self, val: K|V) -> V:
        with self._lock:
            self._read()
            if isinstance(val, self._obj_type):
                key = self._get_key(val)
            else:
                key = val

            if key not in self._dic:
                raise KeyError('Key not found', key)

            obj = self._dic.pop(key)
            self.write()
            return obj

    @overload
    def contains(self, key: K) -> bool:
        """Returns `True` if `key` is stored."""
        ...
    @overload
    def contains(self, obj: V) -> bool:
        """Returns `True` if an object with the same key as `obj` is stored."""
        ...
    def contains(self, val: K|V) -> bool:
        self._read()
        if isinstance(val, self._obj_type):
            key = self._get_key(val)
        else:
            key = val

        return key in self._dic

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

class MultiKeyObjectsFile[K, V: object](ObjectsFile[K, list[V]]):
    """Just like `ObjectsFile`, but allows multiple objects with the same key."""

    @override
    def __init__(self, path, key_name, obj_type):
        self._actual_obj_type = obj_type
        super().__init__(path, key_name, list[obj_type])

    @override
    def _get_key(self, obj: V|list[V]) -> K:
        if isinstance(obj, list):
            key = getattr(obj[0], self._key_name)
            if not all(getattr(o, self._key_name) == key for o in obj):
                raise KeyError('Key mismatch', key, obj)

            return key

        return getattr(obj, self._key_name)

    def _clone_actual_object(self, obj: V) -> V:
        return json_deserialize(
            self._actual_obj_type, json_serialize(obj), locals(), globals()
        )

    @override
    def _add_from_json(self, data):
        obj = json_deserialize(self._actual_obj_type, data, locals(), globals())
        key = self._get_key(obj)
        self._dic.setdefault(key, []).append(obj)

    @override
    def _obj_to_json_line(self, obj):
        res = ''
        for o in obj:
            res += json_serialize(o) + '\n'

        return res

    @override
    def add(self, obj: V):
        """Adds a clone of `obj`.
        
        Raises `ValueError` if an object equal to `obj` already exists.
        """
        obj = self._clone_actual_object(obj)
        key = self._get_key(obj)
        with self._lock:
            self._read()

            if obj in self._dic.get(key, []):
                raise ValueError('Object already exists', obj)

            self._dic.setdefault(key, []).append(obj)
            self.write()

    @override
    def replace(self, old: V, new: V):
        new = self._clone_actual_object(new)

        with self._lock:
            self._read()
            key = self._get_key(old)
            new_key = self._get_key(new)

            if key not in self._dic:
                raise KeyError('Key not found', key)
            if key != new_key:
                raise KeyError('Key mismatch', key, new_key)
            if old not in self._dic[key]:
                raise ValueError('Old object not found', old, self._dic[key])
            if new in self._dic[key]:
                raise ValueError('New object already exists', new)

            for i, obj in enumerate(self._dic[key]):
                if obj == old:
                    self._dic[key][i] = new
                    break
            else:
                raise ValueError('Value not found', old, self._dic[key])

            self.write()

    @overload
    def pop(self, key: K) -> list[V]:
        """Removes the objects with the same key as `key` and returns them."""
        ...
    @overload
    def pop(self, obj: V) -> V:
        """Removes the object that is equal to `obj`.
        
        Returns the removed object.
        """
        ...
    @override
    def pop(self, val: K|V) -> V|list[V]:
        with self._lock:
            self._read()
            if isinstance(val, self._actual_obj_type):
                key = self._get_key(val)
            else:
                key = val

            if key not in self._dic:
                raise KeyError('Key not found', key)

            if isinstance(val, self._actual_obj_type):
                for i, obj in enumerate(self._dic[key]):
                    if obj == val:
                        obj = self._dic[key].pop(i)
                        if len(self._dic[key]) == 0:
                            self._dic.pop(key)
                        break
                else:
                    raise ValueError('Value not found', val, self._dic[key])
            else:
                obj = self._dic.pop(key)

            self.write()
            return obj

    @overload
    def contains(self, key: K) -> bool:
        """Returns `True` if at least one of object with the given key is stored."""
        ...
    @overload
    def contains(self, obj: V) -> bool:
        """Returns `True` if an object equal to `obj` is stored."""
        ...
    @override
    def contains(self, val: K|V) -> bool:
        self._read()
        if isinstance(val, self._actual_obj_type):
            key = self._get_key(val)
            return key in self._dic and any(obj == val for obj in self._dic[key])
        else:
            key = val

        return key in self._dic
    
    @overload
    def count(self) -> int:
        """Returns the number of stored objects."""
        ...
    @overload
    def count(self, key: K) -> int:
        """Returns the number of stored objects that have the given key."""
        ...
    def count(self, key: K|None = None) -> int:
        self._read()
        if key is None:
            res = 0
            for obj_list in self._dic.values():
                res += len(obj_list)

            return res
        else:
            if key not in self._dic:
                return 0

            return len(self._dic[key])

def json_serialize(obj: Any) -> str:
    """Serializes the object to a JSON string."""
    def serialize(o):
        if isinstance(o, Serializable):
            return o._to_dict()
        elif isinstance(o, set):
            return list(o)
        elif isinstance(o, enum.Enum):
            return o.value

        return str(o)

    return json.dumps(obj, default=serialize)

def json_deserialize[T](obj_type: type[T], data: str, caller_locals: dict, caller_globals: dict) -> T:
    """Deserializes the object from a JSON string."""
    def get_value(expected_type: type, value: Any) -> Any:
        def assert_type(expected_type, value):
            if not isinstance(value, expected_type):
                raise TypeError(f'Expected {expected_type}, got {type(value)}', data)

        if expected_type is None:
            if value is not None:
                raise TypeError(f'Expected None, got {type(value)}', data)

            return None
        elif isinstance(expected_type, str):
            # We are likely dealing with a type like 'SelfClass|SomethingElse'
            for t in expected_type.split('|'):
                if t == 'None':
                    actual_type = None
                else:
                    actual_type = (
                        pydoc.locate(t) or caller_locals.get(t, None) or caller_globals.get(t, None)
                    )
                    if actual_type is None:
                        raise Exception('Type not found', t, data)

                try:
                    return get_value(actual_type, value)
                except TypeError:
                    continue
                
            raise TypeError(
                f'Value "{type(value)}" not compatible with any of the types in "{expected_type}"',
                value
            )

        if (origin := get_origin(expected_type)) is not None:
            if origin is types.UnionType:
                for union_type in get_args(expected_type):
                    try:
                        return get_value(union_type, value)
                    except TypeError:
                        continue

                raise TypeError(
                    f'Value of type "{type(value)}" not compatible with any of the types in "{expected_type}"',
                    value
                )

            if origin is list:
                expected_value_type = get_args(expected_type)[0]
                value = [get_value(expected_value_type, x) for x in value]
            elif origin is dict:
                expected_key_type, expected_value_type = get_args(expected_type)
                if expected_key_type is not str:
                    raise TypeError(
                        f'Dicts with non-string keys aren\'t supported',
                        expected_key_type, data
                    )

                value = {
                    get_value(expected_key_type, k): get_value(expected_value_type, v) 
                    for k, v in value.items()
                }
            elif origin is set:
                expected_value_type = get_args(expected_type)[0]
                value = set(get_value(expected_value_type, x) for x in value)
            elif origin is tuple:
                args = []
                for i, expected_value_type in enumerate(get_args(expected_type)):
                    args.append(get_value(expected_value_type, value[i]))

                value = tuple(args)

            assert_type(origin, value)

        elif issubclass(expected_type, enum.Enum):
            if issubclass(expected_type, enum.StrEnum):
                assert_type(str, value)
            else:
                assert_type(int, value)

            value = expected_type(value)
            assert_type(expected_type, value)

        elif dataclasses.is_dataclass(expected_type):
            assert_type(dict, value)
            for field in dataclasses.fields(expected_type):
                if field.name in value:
                    value[field.name] = get_value(field.type, value[field.name])
                else:
                    assert (field.default is not dataclasses.MISSING) or (field.default_factory is not dataclasses.MISSING), \
                        ("Required field not found in JSON", field.name, data)

            value = expected_type._from_dict(value)
            assert_type(expected_type, value)

        else:
            assert_type(expected_type, value)

        return value

    return get_value(obj_type, json.loads(data))

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