import base64
import json
import urllib.parse

__all__ = [
    'JsonSerializable',
    'base64_decode', 'base64_encode',
    'url_decode', 'url_encode'
]

class JsonSerializable:
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
    def __get_empty_dict(cls) -> dict:
        if cls._empty_dict is None:
            cls._empty_dict = cls._create_empty().__dict__
        
        return cls._empty_dict

    @classmethod
    def from_dict(cls, d: dict):
        """Creates an instance of the class from a dictionary.
        
        Override this method to customize how and which values
        are deserialized from JSON, specially nested objects
        with `JsonSerializable` instances inside.
        """
        obj = cls._create_empty()

        for key, value in d.items():
            v = obj.__dict__.get(key)
            if isinstance(v, JsonSerializable):
                value = v.from_dict(value)

            setattr(obj, key, value)
        
        return obj
    
    @classmethod
    def from_json(cls, s: str):
        """Creates an instance of the class from a JSON string."""
        return cls.from_dict(json.loads(s))

    def to_dict(self) -> dict:
        """Returns a dictionary that contains all non-default values.
        
        Override this method to customize how and which values 
        are serialized to JSON.

        The values of the returned dict are used in `__eq__` to compare
        two instances of this class.
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
            if isinstance(o, JsonSerializable):
                return o.to_dict()

            return str(o)

        return json.dumps(self, default=serialize)
    
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