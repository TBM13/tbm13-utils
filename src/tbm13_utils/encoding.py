import base64
import os
import urllib.parse
from abc import ABC, abstractmethod
from contextlib import contextmanager
from enum import Enum
from typing import Any, Self, final, overload, override

import filelock
from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

from .display import *
from .flow import *
from .input import *

__all__ = [
    'CustomField', 'UpdateMode',
    'Serializable', 'StringSerializable',
    'BaseTextFile', 'StringSerializableFile', 'SerializableFile', 'MultiKeySerializableFile',
    'base64_decode', 'base64_encode',
    'url_decode', 'url_encode',
]

class UpdateMode(Enum):
    """Defines how a field of a `Serializable` should be updated when
    `update()` is called.
    """

    IGNORE = -1
    """Don't update this field."""
    REPLACE = 0
    """The default update mode. Replaces the value with
    the other object's value if it's not the default.
    """
    LIST_APPEND = 1
    """For fields of type `list`. Appends to this list the
    values from the other object's list.
    """
    LIST_APPEND_IF_NOT_EXISTS = 2
    """For fields of type `list`. Appends to this list the
    values from the other object's list that don't already exist.
    """
    MERGE = 3
    """For fields of type `dict`, `set` or `Serializable`.
    
    * For `Serializable` calls `update()` with the other object's value.
    * For `dict` and `set`, merges the other object's value
      into this object's value.
    """

    def validate_type(self, field_type: type, other_type: type):
        if self == UpdateMode.LIST_APPEND or self == UpdateMode.LIST_APPEND_IF_NOT_EXISTS:
            if field_type is not list or other_type is not list:
                raise TypeError(
                    'UpdateMode.LIST_APPEND can only be used with fields of type list',
                    field_type,
                    other_type
                )
        elif self == UpdateMode.MERGE:
            field_valid = field_type in (dict, set) or issubclass(field_type, Serializable)
            other_valid = other_type in (dict, set) or issubclass(other_type, Serializable)

            if not (field_valid and other_valid):
                raise TypeError(
                    'UpdateMode.MERGE can only be used with fields of type dict, set or Serializable',
                    field_type, # type: ignore
                    other_type  # type: ignore
                )
            if field_type is not other_type:
                raise TypeError(
                    'UpdateMode.MERGE requires both field types to be the same',
                    field_type, # type: ignore
                    other_type  # type: ignore
                )

def CustomField(
        update_mode: UpdateMode = UpdateMode.REPLACE,
        print: bool = True,
        print_key: str|None = None,
        print_key_style: str = '[cyan]',
        print_value_style: str = '[0]',
        **kwargs: Any
    ) -> Any:
    """Creates a Pydantic `Field` with extra json schema to 
    customize the behavior of a `Serializable`.

    Check Pydantic's `Field` to view the full list of args.
    """
    extra = kwargs.get('json_schema_extra', {})
    extra['update_mode'] = update_mode
    extra['print'] = print
    extra['print_key'] = print_key
    extra['print_key_style'] = print_key_style
    extra['print_value_style'] = print_value_style

    return Field(json_schema_extra=extra, **kwargs)

# TODO: Excluded Fields (not PrivateAttrs) should only be excluded
# from serialization, but not necessarily from update(), print(), etc.
class Serializable(BaseModel):
    """Base class for objects that can be serialized and deserialized using Pydantic.

    Equality is overridden to compare only what is defined in the model (`model_dump`).
    If the model is identical, then the objects are considered equal
    (even if they have different classes).

    You can treat this class as a normal Pydantic `BaseModel`, which means you can
    customize it as you wish (e.g., by adding a `model_config`).

    Suggestions:
    * Avoid overriding `__eq__` and `__init__`.
    * To customize `update`, use `CustomField` to define fields.
    * To customize `print`, override `get_printable_title` and/or use
    `CustomField` to define fields.
    """
    model_config = ConfigDict(strict=True, validate_assignment=True)

    def update(self, other: 'Serializable', excluded: set[str] = set()):
        """Updates the object with all the non-unset values from `other`,
        except for those in `excluded`.
        
        Fields will be updated according to their `UpdateMode`.
        """
        if type(other) is not type(self):
            raise TypeError(
                'Cannot update Serializable with different types',
                type(self), type(other)
            )

        for key, _ in other.model_dump(exclude_unset=True).items():
            if key in excluded:
                continue

            field = type(self).model_fields.get(key, None)
            extra: dict[str, Any] = {}
            if field is not None and hasattr(field, 'json_schema_extra'):
                extra = field.json_schema_extra or {}  # type: ignore

            val = getattr(self, key)
            other_val = getattr(other, key)

            update_mode: UpdateMode = extra.get('update_mode', UpdateMode.REPLACE)
            update_mode.validate_type(type(val), type(other_val))  # type: ignore
            if update_mode == UpdateMode.REPLACE:
                setattr(self, key, other_val)
            elif update_mode == UpdateMode.LIST_APPEND:
                val.extend(other_val)   # type: ignore
            elif update_mode == UpdateMode.LIST_APPEND_IF_NOT_EXISTS:
                for item in other_val:  # type: ignore
                    if item not in val: # type: ignore
                        val.append(item)   # type: ignore
            elif update_mode == UpdateMode.MERGE:
                val.update(other_val)   # type: ignore
            elif update_mode == UpdateMode.IGNORE:
                pass

    def get_printable_title(self) -> str:
        """Returns the printable title of this object, used in `print()`.
        
        Override this to customize the title (default is `[<class name>]`).
        """
        return f'[cyan][bold][{self.__class__.__name__}]'

    def __to_printable_dict(self, spaces: int, print_keys: bool, apply_style: bool) -> dict[str, str]:
        """Returns a dict with the data of this object that should be printed.
        Keys are the field names and values a printable string.
        """
        dic = {
            '_header_': ' ' * spaces + self.get_printable_title()
        }
        for key, _ in self.model_dump(exclude_unset=True).items():  # type: ignore
            value = getattr(self, key)

            field = type(self).model_fields.get(key, None)
            extra: dict[str, Any] = {}
            if field is not None and hasattr(field, 'json_schema_extra'):
                extra = field.json_schema_extra or {}  # type: ignore

            if not extra.get('print', True):
                continue

            print_key = extra.get('print_key', None)
            print_key = print_key or key.strip('_').replace('_', ' ').title()

            dic[key] = ' ' * (spaces + 2)
            if print_keys:
                if apply_style:
                    dic[key] += extra.get('print_key_style', '[cyan]')
                dic[key] += print_key + '[0]: '
            if apply_style:
                dic[key] += extra.get('print_value_style', '[0]')
            dic[key] += str(value)

        return dic
    
    def print(self, other: 'Serializable|None' = None, spaces: int = 0):
        """Prints all the keys and values from `self.model_dump(exclude_unset=True)`
        with color and style.
        
        If `other` isn't `None`, ALL the differences between this and `other` will also be printed.
        """
        lines = self.__to_printable_dict(spaces, True, True)
        other_lines = None
        if other is not None:
            other_lines = other.__to_printable_dict(
                spaces=-2, apply_style=False, print_keys=False
            )

        for var_name, line in lines.items():
            value = getattr(self, var_name, None)
            other_value = getattr(other, var_name, None)
            if var_name == '_header_' and other_lines is not None:
                value = remove_style(line).lstrip(' ')
                other_value = other_lines.get('_header_', '[invert]<Deleted>')
                other_value = remove_style(other_value).lstrip(' ')

            other_line = None
            if other_lines is not None:
                other_line = other_lines.get(var_name, '[invert]<Deleted>')
            
            if other_lines is None or value == other_value:
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
                    color_print(' ' * (spaces + 2) + f'[invert] -> [0]{other_line}')
            elif isinstance(other_value, Serializable):
                color_print(f'{line}[invert] -> [0]')
                other_value.print(spaces=spaces + 4)

            elif isinstance(value, dict) and isinstance(other_value, dict):
                if len(other_value) == 0:       # type: ignore
                    color_print(f'{line}[invert] -> [0]' + '{}')
                    continue

                line = f'{line}[invert] -> [0]' + '{'
                for key, val in other_value.items():    # type: ignore
                    if key not in value:
                        line += '[invert]'
                    line += f'{repr(key)}: '
                    if key not in value or value[key] != val:
                        line += '[invert]'
                    line += f'{repr(val)}[0], '     # type: ignore

                for key, val in value.items():      # type: ignore
                    if key in other_value:
                        continue

                    line += f'[invert]{repr(key)}: <Deleted>[0], '  # type: ignore

                color_print(line[:-2] + '}')

            elif isinstance(value, set) and isinstance(other_value, set):
                if len(other_value) == 0:       # type: ignore
                    color_print(f'{line}[invert] -> [0]' + '{}')
                    continue

                line = f'{line}[invert] -> [0]' + '{'
                for val in other_value:             # type: ignore
                    if val not in value:
                        line += '[invert]'
                    line += f'{repr(val)}[0], '     # type: ignore

                dif = len(value) - len(other_value) # type: ignore
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

                if len(other_value) == 0:       # type: ignore
                    color_print(f'{line}[invert] -> [0]{open}{close}')
                    continue

                line = f'{line}[invert] -> [0]{open}'
                for i, val in enumerate(other_value):       # type: ignore
                    if i >= len(value) or value[i] != val:  # type: ignore
                        line += '[invert]'

                    line += f'{repr(val)}[0], '         # type: ignore

                dif = len(value) - len(other_value)     # type: ignore
                if dif > 0:
                    line += f'[invert]<{dif} deleted>[0], '

                color_print(line[:-2] + close)

            else:
                color_print(f'{line}[invert] -> [0]{other_line}')

        if other is None:
            return

        other_lines = other.__to_printable_dict(spaces, True, True)
        printed_header = False
        for var_name, line in other_lines.items():
            if var_name in lines:
                continue

            if not printed_header:
                color_print('\n' + ' ' * (spaces + 2) + '[invert]Added:')
                printed_header = True

            other_value = getattr(other, var_name, None)
            if isinstance(other_value, Serializable):
                other_value.print(spaces=spaces + 2)
            else:
                color_print(line)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Serializable):
            return False

        return self.model_dump() == value.model_dump()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.model_dump(exclude_unset=True)})'

class StringSerializable(BaseModel, ABC):
    """Base class for objects that can be serialized and deserialized
    to/from string using Pydantic.
    
    * The model is frozen (immutable), so as to safely support hashing.
    * Deserialization and serialization are done using `from_string` and `to_string`
    respectively.
    * Equality and hashing are done using `to_string`.

    Suggestions:
    * `from_string` and `to_string` should be deterministic.
    * If needed, override `__str__` to return a more user-friendly representation.
    * Don't override `__hash__` nor `__eq__`.
    * Mark fields as final.
    """
    model_config = ConfigDict(strict=True, validate_assignment=True, frozen=True)

    @classmethod
    @abstractmethod
    def from_string(cls, data: str) -> Self:
        """Deserializes the given string representation
        into an instance of this class.
        """
        raise NotImplementedError()

    @abstractmethod
    @model_serializer
    def to_string(self) -> str:
        """Serializes this object into a string representation."""
        raise NotImplementedError()

    @final
    @model_validator(mode='before')
    @classmethod
    def _deserialize_from_string(cls, data: Any) -> Any:
        if isinstance(data, str):
            return cls.from_string(data)

        return data

    @overload
    @classmethod
    def input(cls, msg: str) -> Self:
        """Forces the user to input a valid string and
        creates an instance of this class from it.
        """
        ...
    @overload
    @classmethod
    def input[T](cls, msg: str, fallback: T) -> Self|T:
        """Forces the user to input a valid string and
        creates an instance of this class from it.

        Returns `fallback` as-is when the user doesn't input anything.
        """
        ...
    @classmethod
    def input[T](cls, msg: str, fallback: T = ...) -> Self|T:
        with handle_exceptions():
            input = input_str(msg, fallback=fallback)
            if input == fallback:
                return fallback

            return cls.from_string(input)   # type: ignore

        return cls.input(msg, fallback)

    @final
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StringSerializable):
            return False

        return self.to_string() == other.to_string()

    @final
    def __hash__(self) -> int:
        return hash(self.to_string())
    def __str__(self) -> str:
        return self.to_string()
    def __repr__(self):
        return f'{self.__class__.__name__}({self.to_string()})'

class BaseTextFile(ABC):
    """Base class for text files that contain objects.
    
    * The file is locked with `filelock` while reading/writing to avoid race conditions.
    """
    def __init__(self, path: str):
        """`path` is the path to the text file. It doesn't need to exist."""
        self.path = path
        self._last_mtime_ns: float|None = None
        self._last_size: int = 0
        self._lock = filelock.FileLock(path + '.lock')
        self._modify_depth = 0

        self._read()

    def _read(self):
        if self._modify_depth > 0:
            return

        with self._lock:
            if not self.modified_externally():
                return
            
            if not os.path.isfile(self.path):
                self._deserialize([])
                self._last_mtime_ns = None
                self._last_size = 0
                return

            with open(self.path, 'r', encoding='utf8') as file:
                self._deserialize(file.readlines())

                stat = os.fstat(file.fileno())
                self._last_mtime_ns = stat.st_mtime_ns
                self._last_size = stat.st_size

    def _write(self):
        if self._modify_depth > 0:
            return

        with self._lock:
            with open(self.path, 'w', encoding='utf8') as file:
                file.write(self._serialize())

                if file.tell() != 0:
                    file.seek(file.tell())
                    file.truncate()

                # Force write to disk so the OS updates the modification time
                file.flush()
                os.fsync(file.fileno())

                stats = os.fstat(file.fileno())
                self._last_mtime_ns = stats.st_mtime_ns
                self._last_size = stats.st_size

    def modified_externally(self) -> bool:
        """Returns `True` if the file was modified externally
        since the last time it was read.
        """
        if self._last_mtime_ns is None:
            # We never read the file. If it exists, we need to read it
            return os.path.isfile(self.path)

        # We read the file before. If it doesn't exist, it was deleted
        if not os.path.isfile(self.path):
            return True

        # Check if the file was modified
        stats = os.stat(self.path)
        return (
            self._last_size != stats.st_size or
            self._last_mtime_ns != stats.st_mtime_ns
        )

    @contextmanager
    def modify(self):
        """Wraps the code in a context where the file is locked 
        and read before, and it's written and unlocked after.

        If you're going to make multiple modifications,
        using this context manager will be better for performance.
        """
        self._modify_depth += 1
        if self._modify_depth == 1:
            self._lock.acquire()
            self._read()

        try:
            yield self
        finally:
            self._modify_depth -= 1
            if self._modify_depth == 0:
                self._write()
                self._lock.release()

    @abstractmethod
    def _deserialize(self, lines: list[str]) -> None:
        """Deserializes the text of the file into the internal data structure.
        
        * The lines are not stripped.
        * `lines` will be empty if the file is empty or was deleted.
        * You may want to clear the internal data structure before deserializing.
        """
        raise NotImplementedError()

    @abstractmethod
    def _serialize(self) -> str:
        """Serializes the internal data structure to
        the text that will be written to the file.
        """
        raise NotImplementedError()

class StringSerializableFile[V: StringSerializable](BaseTextFile):
    """A set-like object that represents a file where each line
    is a `StringSerializable` of type `V`.

    * Directly tied to a text file, each modification updates it.
    * Empty lines or comments (lines that start with '#') are ignored.
    * The file is locked with `filelock` while reading/writing to avoid race conditions.
    * Before every read & write the file is re-read if it was modified externally.

    This is not a thread-safe object.
    """
    def __init__(self, path: str, value_type: type[V]):
        """`path` is the path to the text file. It doesn't need to exist.

        `value_type` is the type of the objects stored in the file.
        """
        self._value_type = value_type
        self._values: set[V] = set()

        super().__init__(path)

    @override
    def _deserialize(self, lines: list[str]) -> None:
        self._values.clear()

        for line in lines:
            line = line.strip()
            if len(line) == 0 or line.startswith('#'):
                continue

            self._values.add(
                self._value_type.from_string(line)
            )

    @override
    def _serialize(self) -> str:
        return '\n'.join(
            val.to_string() for val in self._values
        )
        
    def add(self, value: V):
        """Adds `value` to the file.
        
        If it already exists, it will be ignored.
        """
        with self.modify():
            self._values.add(value)

    def remove(self, value: V):
        """Removes `value` from the file.
        
        Raises `KeyError` if it's not stored.
        """
        with self.modify():
            if value not in self._values:
                raise KeyError('Value not found', value)

            self._values.remove(value)

    def replace(self, old: V, new: V):
        """Replaces `old` with `new` in the file.
        
        If `old` is not stored, raises `KeyError`.
        """
        with self.modify():
            if old not in self._values:
                raise KeyError('Value not found', old)
            
            self._values.remove(old)
            self._values.add(new)

    def clear(self):
        """Clears all values from the file."""
        with self.modify():
            self._values.clear()

    def __len__(self) -> int:
        self._read()
        return len(self._values)
    def __contains__(self, value: V) -> bool:
        self._read()
        return value in self._values
    def __iter__(self):
        self._read()
        return (val for val in self._values)

class SerializableFile[K, V: Serializable](BaseTextFile):
    """A dictionary-like object that contains `Serializable` objects of type `V` as values.
    
    * Directly tied to a file, each modification updates it.
    * Empty lines or comments (lines that start with '#') are ignored.
    * The file is locked with `filelock` while reading/writing to avoid race conditions.
    * Before every read & write the file is re-read if it was modified externally.

    This is not a thread-safe object.
    """
    def __init__(self, path: str, key_name: str, value_type: type[V]):
        """`path` is the path to the file. It doesn't need to exist.
        
        `key_name` is the name of the object's field that will be used as the key.

        `value_type` is the type of the objects stored in the file.
        """
        self._key_name = key_name
        self._value_type = value_type
        self._dic: dict[K, V] = {}

        # Check that key_name is valid
        if key_name not in self._value_type.model_fields:
            raise ValueError(f"'{key_name}' is not a valid field for {self._value_type}")        

        super().__init__(path)

    @override
    def _deserialize(self, lines: list[str]) -> None:
        self._dic.clear()         

        for line in lines:
            line = line.strip()
            if len(line) == 0 or line.startswith('#'):
                continue

            obj = self._value_type.model_validate_json(line)
            key = getattr(obj, self._key_name)
            if key in self._dic:
                raise KeyError(f'"{self.path}" has a duplicate key', key)

            self._dic[key] = obj

    @override
    def _serialize(self) -> str:
        return '\n'.join(
            obj.model_dump_json() for obj in self._dic.values()
        )

    @overload
    def get(self, key: K) -> V:
        """Returns a deep clone of the object with the given key.
        
        Raises `KeyError` if it doesn't exist.
        """
        ...
    @overload
    def get[T](self, key: K, default: T) -> V|T:
        """Returns a deep clone of the object with the given key if it exists.

        Otherwise, returns `default` as-is.
        """
        ...
    def get[T](self, key: K, default: T = Ellipsis) -> V|T:
        self._read()
        if default is not Ellipsis:
            res = self._dic.get(key, default)
        else:
            if key not in self._dic:
                raise KeyError('Key not found', key)

            res = self._dic[key]

        if res is default:
            return default

        return res.model_copy(deep=True)    # type: ignore

    def set(self, obj: V):
        """Sets the value of the object's key to a deep clone of `obj`.

        If an object with the same key already exists, it will be replaced.
        """
        with self.modify():
            obj = obj.model_copy(deep=True)
            key = getattr(obj, self._key_name)
            self._dic[key] = obj

    def add(self, obj: V):
        """Adds a deep clone of `obj`.
        
        Raises `KeyError` if an object with the same key already exists.
        """
        with self.modify():
            obj = obj.model_copy(deep=True)
            key = getattr(obj, self._key_name)
            if key in self._dic:
                raise KeyError('Key already exists', key)

            self._dic[key] = obj

    def replace(self, old: V, new: V):
        """Replaces `old` with a deep clone of `new`.
        
        Raises an exception if:
        * `old` is not stored.
        * `old` isn't equal to the stored object.
        * `old` and `new` don't have the same key.
        """
        with self.modify():
            new = new.model_copy(deep=True)
            key = getattr(old, self._key_name)
            new_key = getattr(new, self._key_name)

            if key not in self._dic:
                raise KeyError('Key not found', key)
            if key != new_key:
                raise KeyError('Key mismatch', key, new_key)
            if old != self._dic[key]:
                raise ValueError('Given value doesn\'t match the stored value',
                                 old, self._dic[key])

            self._dic[key] = new

    @overload
    def pop(self, key: K) -> V:
        """Removes the object with the given key and returns it.
        
        Raises `KeyError` if the key doesn't exist.
        """
        ...
    @overload
    def pop(self, *, obj: V) -> V:
        """Removes the object with the same key as the given object
        and returns it.

        Raises `KeyError` if the key doesn't exist.
        """
        ...
    def pop(self, key: K|None = None, obj: V|None = None) -> V:
        with self.modify():
            if obj is not None:
                key = getattr(obj, self._key_name)

            if key not in self._dic:
                raise KeyError('Key not found', key)

            obj = self._dic.pop(key)
            return obj

    @overload
    def contains(self, key: K) -> bool:
        """Returns `True` if `key` is stored."""
        ...
    @overload
    def contains(self, *, obj: V) -> bool:
        """Returns `True` if an object with the same key as `obj` is stored."""
        ...
    def contains(self, key: K|None = None, obj: V|None = None) -> bool:
        self._read()
        if obj is not None:
            key = getattr(obj, self._key_name)

        return key in self._dic

    def keys(self):
        """Returns the dictionary's `keys()` as-is.
        
        Wrap this in `modify()` if you plan to modify the keys.
        """
        self._read()
        return self._dic.keys()

    def values(self):
        """Returns the dictionary's `values()` as-is.
        
        Wrap this in `modify()` if you plan to modify the values.
        """
        self._read()
        return self._dic.values()

    def items(self):
        """Returns the dictionary's `items()` as-is.
        
        Wrap this in `modify()` if you plan to modify the items.
        """
        self._read()
        return self._dic.items()
    
    def __len__(self) -> int:
        self._read()
        return len(self._dic)

class MultiKeySerializableFile[K, V: Serializable](BaseTextFile):
    """Just like `SerializableFile`, but different values with the same key
    are allowed (except for duplicates).
    
    A dictionary-like object that contains `Serializable` objects of type `V` as values.
    
    * Directly tied to a file, each modification updates it.
    * Empty lines or comments (lines that start with '#') are ignored.
    * The file is locked with `filelock` while reading/writing to avoid race conditions.
    * Before every read & write the file is re-read if it was modified externally.

    This is not a thread-safe object.
    """
    def __init__(self, path: str, key_name: str, value_type: type[V]):
        """`path` is the path to the file. It doesn't need to exist.
        
        `key_name` is the name of the object's field that will be used as the key.

        `value_type` is the type of the objects stored in the file.
        """
        self._key_name = key_name
        self._value_type = value_type
        self._dic: dict[K, list[V]] = {}

        # Check that key_name is valid
        if key_name not in self._value_type.model_fields:
            raise ValueError(f"'{key_name}' is not a valid field for {self._value_type}")        

        super().__init__(path)

    @override
    def _deserialize(self, lines: list[str]) -> None:
        self._dic.clear()         

        for line in lines:
            line = line.strip()
            if len(line) == 0 or line.startswith('#'):
                continue

            obj = self._value_type.model_validate_json(line)
            key = self._get_key(obj, validate=True)
            if key in self._dic:
                raise KeyError(f'"{self.path}" has a duplicate key', key)

            list = self._dic.setdefault(key, [])
            if obj in list:
                raise ValueError(f'"{self.path}" has a duplicate object for key', key, obj)

            list.append(obj)

    @override
    def _serialize(self) -> str:
        return '\n'.join(
            obj.model_dump_json() for obj_list in self._dic.values() for obj in obj_list
        )

    def _get_key(self, obj: V|list[V], validate: bool) -> K:
        if isinstance(obj, list):
            key = getattr(obj[0], self._key_name)
            if validate:
                if not all(getattr(o, self._key_name) == key for o in obj):
                    raise KeyError('Key mismatch', key, obj)

            return key

        return getattr(obj, self._key_name)

    @overload
    def get(self, key: K) -> list[V]:
        """Returns a list with deep clones of
        all the objects with the given key.
        
        Raises `KeyError` if it doesn't exist.
        """
        ...
    @overload
    def get[T](self, key: K, default: T) -> list[V]|T:
        """Returns a list with deep clones of all the
        objects with the given key if there is any.

        Otherwise, returns `default` as-is.
        """
        ...
    def get[T](self, key: K, default: T = Ellipsis) -> list[V]|T:
        self._read()
        if default is not Ellipsis:
            res = self._dic.get(key, default)
        else:
            if key not in self._dic:
                raise KeyError('Key not found', key)

            res = self._dic[key]

        if res is default:
            return default

        return [obj.model_copy(deep=True) for obj in res]    # type: ignore

    def add(self, obj: V):
        """Adds a deep clone of `obj`.
        
        Raises `ValueError` if an object equal to `obj` already exists.
        """
        with self.modify():
            obj = obj.model_copy(deep=True)
            key = self._get_key(obj, validate=False)
            if obj in self._dic.get(key, []):
                raise ValueError('Object already exists', obj)

            self._dic.setdefault(key, []).append(obj)

    def replace(self, old: V, new: V):
        """Replaces `old` with a deep clone of `new`.
        
        Raises an exception if:
        * No object equal to `old` exists.
        * `old` and `new` don't have the same key.
        * An object equal to `new` already exists.
        """
        with self.modify():
            new = new.model_copy(deep=True)
            key = self._get_key(old, validate=False)
            new_key = self._get_key(new, validate=False)

            if key not in self._dic:
                raise KeyError('Key not found', key)
            if key != new_key:
                raise KeyError('Key mismatch', key, new_key)
            
            replaced = False
            for i, obj in enumerate(self._dic[key]):
                if obj == new:
                    raise ValueError('New object already exists', new)
                
                if obj == old:
                    if replaced:
                        raise ValueError('Duplicate objects found', key, self._dic[key])

                    self._dic[key][i] = new
                    replaced = True

            if not replaced:
                raise ValueError('Object not found', old, self._dic[key])

    @overload
    def pop(self, key: K) -> list[V]:
        """Removes the objects with the same key as `key` and returns them.
        
        Raises `KeyError` if no object with that key exists.
        """
        ...
    @overload
    def pop(self, *, obj: V) -> V:
        """Removes the object that is equal to `obj`
        and returns it.
        
        Raises `KeyError` or `ValueError` if the object doesn't exist.
        """
        ...
    def pop(self, key: K|None = None, obj: V|None = None) -> list[V]|V:
        with self.modify():
            if obj is not None:
                key = self._get_key(obj, validate=False)
            if key not in self._dic:
                raise KeyError('Key not found', key)

            if obj is None:
                return self._dic.pop(key)
            
            for i, o in enumerate(self._dic[key]):
                if o == obj:
                    obj = self._dic[key].pop(i)
                    if len(self._dic[key]) == 0:
                        self._dic.pop(key)
                    
                    return obj
            
            raise ValueError('Object not found', obj, self._dic[key])

    @overload
    def contains(self, key: K) -> bool:
        """Returns `True` if any object with the given key is stored."""
        ...
    @overload
    def contains(self, *, obj: V) -> bool:
        """Returns `True` if an object equal to `obj` is stored."""
        ...
    def contains(self, key: K|None = None, obj: V|None = None) -> bool:
        self._read()

        if key is not None:
            return key in self._dic

        key = self._get_key(obj, validate=False)  # type: ignore
        return obj in self._dic.get(key, [])
    
    @overload
    def count(self, only_unique: bool) -> int:
        """Returns the real number of stored objects,
        or the number of unique keys if `only_unique` is `True`.
        """
        ...
    @overload
    def count(self, *, key: K) -> int:
        """Returns the number of stored objects with the given key."""
        ...
    def count(self, only_unique: bool = False, key: K|None = None) -> int:
        self._read()
        if key is None:
            if only_unique:
                return len(self._dic)

            res = 0
            for obj_list in self._dic.values():
                res += len(obj_list)

            return res

        if key not in self._dic:
            return 0

        return len(self._dic[key])
    
    def keys(self):
        """Returns the dictionary's `keys()` as-is.
        
        Wrap this in `modify()` if you plan to modify the keys.
        """
        self._read()
        return self._dic.keys()

    def values(self):
        """Returns the dictionary's `values()` as-is.
        
        Wrap this in `modify()` if you plan to modify the values.
        """
        self._read()
        return self._dic.values()

    def items(self):
        """Returns the dictionary's `items()` as-is.
        
        Wrap this in `modify()` if you plan to modify the items.
        """
        self._read()
        return self._dic.items()

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