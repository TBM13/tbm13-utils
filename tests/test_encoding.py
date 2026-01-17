import os
import shutil
import tempfile
import unittest
from typing import Final, Self, override
from unittest.mock import patch

from pydantic import Field, PrivateAttr

from tbm13_utils.encoding import *


class TestSerializable(unittest.TestCase):
    def setUp(self):
        class TestModel(Serializable):
            name: str
            value: int = 0

        class TestModel2(TestModel):
            surname: str
            _somePrivateField: str = "private"

        self.TestModel = TestModel
        self.TestModel2 = TestModel2

    def test_model_creation(self):
        obj = self.TestModel(name="test")
        self.assertEqual(obj.name, "test")
        self.assertEqual(obj.value, 0)

        obj = self.TestModel(name="test", value=42)
        self.assertEqual(obj.name, "test")
        self.assertEqual(obj.value, 42)
        obj.name = "changed"
        self.assertEqual(obj.name, "changed")

        with self.assertRaises(Exception):
            obj = self.TestModel2(name="test")  # type: ignore - Missing surname

        obj = self.TestModel2(name="test", surname="user")
        self.assertEqual(obj.name, "test")
        self.assertEqual(obj.surname, "user")
        self.assertEqual(obj._somePrivateField, "private") # type: ignore

    def test_equality(self):
        # Basic equality
        obj1 = self.TestModel(name="test")
        obj2 = self.TestModel(name="test", value=0)
        obj3 = self.TestModel(name="test", value=2)
        obj4 = self.TestModel(name="asd")
        self.assertEqual(obj1, obj2)
        self.assertNotEqual(obj1, obj3)
        self.assertNotEqual(obj1, obj4)
        self.assertNotEqual(obj2, obj4)

        # Reflexive equality
        self.assertEqual(obj1, obj1)
        # Equality with non-Serializable objects
        self.assertNotEqual(obj1, None)
        self.assertNotEqual(obj1, "string")
        self.assertNotEqual(obj1, 42)
        self.assertNotEqual(obj1, [])

        # Equality with private attributes
        counter = 0
        def get_next():
            nonlocal counter
            counter += 1
            return counter
        class TestModelChild(self.TestModel):
            _internalId: int = PrivateAttr(default_factory=get_next)

        child1 = TestModelChild(name="test")
        child2 = TestModelChild(name="test", value=0)
        child3 = TestModelChild(name="test", value=2)
        self.assertEqual(child1, child2)
        self.assertNotEqual(child1, child3)

        # Equality with different classes but same model
        class SimilarModel(Serializable):
            name: str
            value: int = 0
        self.assertEqual(obj1, child1)
        similarObj1 = SimilarModel(name="test")
        self.assertEqual(obj1, similarObj1)

        # Equality with recursion
        class RecursiveModel(Serializable):
            name: str
            child: Self | None = None

        rec1 = RecursiveModel(name="parent", child=RecursiveModel(name="child"))
        rec2 = RecursiveModel(name="parent", child=RecursiveModel(name="child"))
        rec3 = RecursiveModel(name="parent", child=RecursiveModel(name="different"))
        self.assertEqual(rec1, rec2)
        self.assertNotEqual(rec1, rec3)

        # Equality with more complex models
        class ComplexModel(Serializable):
            name: str
            values: list[int]
            tags: set[str]
            data: dict[str, int]

        comp1 = ComplexModel(name="test", values=[1, 2], tags={"a", "b"}, data={"x": 10})
        comp2 = ComplexModel(name="test", values=[1, 2], tags={"b", "a"}, data={"x": 10})
        comp3 = ComplexModel(name="test", values=[1, 2, 3], tags={"a", "b"}, data={"x": 10})
        self.assertEqual(comp1, comp2)
        self.assertNotEqual(comp1, comp3)

        class ComplexModel2(Serializable):
            name: str
            values: list[Self] = Field(default_factory=list[Self])
            data: dict[str, Self] = Field(default_factory=dict)
            internal: int = Field(default=0, exclude=True)

        cm1 = ComplexModel2(name="root", values=[ComplexModel2(name="child1")], data={"key": ComplexModel2(name="child2")})
        cm2 = ComplexModel2(name="root", values=[ComplexModel2(name="child1")], data={"key": ComplexModel2(name="child2", internal = 5)})
        cm3 = ComplexModel2(name="root", values=[ComplexModel2(name="child1")], data={"key": ComplexModel2(name="different")})
        self.assertEqual(cm1, cm2)
        self.assertNotEqual(cm1, cm3)

        # Equality with excluded public fields
        class ExcludedFieldModel(Serializable):
            name: str
            excluded_field: int = Field(exclude=True)

        ex1 = ExcludedFieldModel(name="test", excluded_field=1)
        ex2 = ExcludedFieldModel(name="test", excluded_field=2)
        ex3 = ExcludedFieldModel(name="different", excluded_field=1)
        self.assertEqual(ex1, ex2)
        self.assertNotEqual(ex1, ex3)

    def test_update(self):
        # Basic update
        obj1 = self.TestModel(name="test1", value=1)
        obj2 = self.TestModel(name="test2", value=2)
        obj1.update(obj2)
        self.assertEqual(obj1.name, "test2")
        self.assertEqual(obj1.value, 2)

        # Basic update with an excluded field
        class ExcludeTestModel(Serializable):
            name: str = CustomField(exclude_from_update=True)
            value: int
        
        obj1 = ExcludeTestModel(name="test1", value=1)
        obj2 = ExcludeTestModel(name="test2", value=2)
        obj1.update(obj2)
        self.assertEqual(obj1.name, "test1")  # Not updated
        self.assertEqual(obj1.value, 2)

        # Test merging of dictionaries
        class DictModel(Serializable):
            name: str
            data: dict[str, int] = CustomField(update_mode=UpdateMode.MERGE, default_factory=dict)

        obj1 = DictModel(name="test", data={"a": 1})
        obj2 = DictModel(name="test", data={"b": 2})
        obj1.update(obj2)
        self.assertEqual(obj1.data, {"a": 1, "b": 2})

        # Test merging of sets
        class SetModel(Serializable):
            name: str
            items: set[int] = CustomField(update_mode=UpdateMode.MERGE, default_factory=set[int])

        obj1 = SetModel(name="test", items={1, 2})
        obj2 = SetModel(name="test", items={2, 3})
        obj1.update(obj2)
        self.assertEqual(obj1.items, {1, 2, 3})

        # Test merging of a Serializable
        class ParentModel(Serializable):
            name: str
            child: SetModel = CustomField(update_mode=UpdateMode.MERGE, default_factory=lambda: SetModel(items=set(), name="child"))

        obj1 = ParentModel(name="parent", child=SetModel(name="child", items={1}))
        obj2 = ParentModel(name="parent", child=SetModel(name="child2", items={2}))
        obj1.update(obj2)
        self.assertEqual(obj1.child.name, "child2")
        self.assertEqual(obj1.child.items, {1, 2})

        # Test UpdateMode.IGNORE
        class IgnoreModel(Serializable):
            name: str
            ignored: int = CustomField(update_mode=UpdateMode.IGNORE, default=0)
        
        obj1 = IgnoreModel(name="test", ignored=1)
        obj2 = IgnoreModel(name="test", ignored=2)
        obj1.update(obj2)
        self.assertEqual(obj1.ignored, 1)

        # Test UpdateMode.LIST_APPEND
        class ListAppendModel(Serializable):
            items: list[int] = CustomField(update_mode=UpdateMode.LIST_APPEND, default_factory=list)
        
        obj1 = ListAppendModel(items=[1, 2])
        obj2 = ListAppendModel(items=[2, 3])
        obj1.update(obj2)
        self.assertEqual(obj1.items, [1, 2, 2, 3])

        # Test UpdateMode.LIST_APPEND_IF_NOT_EXISTS
        class ListAppendIfNotExistsModel(Serializable):
            items: list[int] = CustomField(update_mode=UpdateMode.LIST_APPEND_IF_NOT_EXISTS, default_factory=list)
        
        obj1 = ListAppendIfNotExistsModel(items=[1, 2])
        obj2 = ListAppendIfNotExistsModel(items=[2, 3])
        obj1.update(obj2)
        self.assertEqual(obj1.items, [1, 2, 3])

        # Test invalid UpdateMode usage (TypeError)
        class InvalidMergeModel(Serializable):
            name: str
            # An int cannot be merged
            data: int = CustomField(update_mode=UpdateMode.MERGE, default=0)

        obj1 = InvalidMergeModel(name="test", data=1)
        obj2 = InvalidMergeModel(name="test", data=2)
        with self.assertRaises(TypeError):
            obj1.update(obj2)

    def test_repr(self):
        obj = self.TestModel(name="test", value=42)
        expected = "TestModel({'name': 'test', 'value': 42})"
        self.assertEqual(repr(obj), expected)

        obj2 = self.TestModel(name="test")
        expected2 = "TestModel({'name': 'test'})"
        self.assertEqual(repr(obj2), expected2)

        obj3 = self.TestModel2(name="test", surname="user", value=10)
        expected3 = "TestModel2({'name': 'test', 'value': 10, 'surname': 'user'})"
        self.assertEqual(repr(obj3), expected3)

    def test_print(self):
        # Basic print - just test that it doesn't raise an exception
        obj = self.TestModel(name="test", value=42)
        obj.print()

        # Print with object comparison
        obj1 = self.TestModel(name="test", value=1)
        obj2 = self.TestModel(name="test", value=2)
        obj1.print(other=obj2)


class TestStringSerializable(unittest.TestCase):
    def setUp(self):
        class TestStringModel(StringSerializable):
            data: Final[str]

            @classmethod
            @override
            def from_string(cls, data: str):
                return cls(data=data)
            
            @override
            def to_string(self) -> str:
                return self.data

        self.TestStringModel = TestStringModel

    def test_validation(self):
        obj = self.TestStringModel(data="test")
        self.assertEqual(obj.data, "test")
        self.assertEqual(obj.to_string(), "test")

        # Model should be frozen
        with self.assertRaises(Exception):
            obj.data = 'Something else'  # type: ignore

    def test_input(self):
        with patch('builtins.input', return_value="input data"):
            obj = self.TestStringModel.input("Enter: ")
            self.assertEqual(obj.to_string(), "input data")
            self.assertEqual(obj.data, "input data")

        # With fallback
        with patch('builtins.input', return_value=""):
            result = self.TestStringModel.input("Enter: ", 8)
            self.assertEqual(result, 8)


class TestBaseTextFile(unittest.TestCase):
    def setUp(self):
        class ConcreteTextFile(BaseTextFile):
            """Concrete implementation that stores a list of strings."""
            def __init__(self, path: str):
                self.lines: list[str] = []
                super().__init__(path)
            
            @override
            def _deserialize(self, lines: list[str]) -> None:
                self.lines = [line.strip() for line in lines]
            
            @override
            def _serialize(self) -> str:
                return '\n'.join(self.lines)
        
        self.ConcreteTextFile = ConcreteTextFile
        
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        # Clean up temp files
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _get_temp_path(self, filename: str) -> str:
        return os.path.join(self.temp_dir, filename)
    
    def test_read(self):
        path = self._get_temp_path("existing.txt")

        # Initialize with a non-existing file
        text_file = self.ConcreteTextFile(path)
        self.assertEqual(text_file.lines, [])
        self.assertFalse(text_file.modified_externally())
        text_file._read() # type: ignore
        self.assertEqual(text_file.lines, [])
        self.assertFalse(text_file.modified_externally())

        # Create the file externally
        with open(path, 'w', encoding='utf8') as f:
            f.write("line1\nline2\nline3")
        
        self.assertTrue(text_file.modified_externally())
        text_file._read()  # type: ignore
        self.assertEqual(text_file.lines, ["line1", "line2", "line3"])
        self.assertFalse(text_file.modified_externally())

        # Modify file externally (append line)
        with open(path, 'a', encoding='utf8') as f:
            f.write("\nline4")

        self.assertTrue(text_file.modified_externally())
        text_file._read()  # type: ignore
        self.assertEqual(text_file.lines, ["line1", "line2", "line3", "line4"])
        self.assertFalse(text_file.modified_externally())

        # Initialize with an existing file
        text_file2 = self.ConcreteTextFile(path)
        self.assertEqual(text_file2.lines, ["line1", "line2", "line3", "line4"])
        self.assertFalse(text_file2.modified_externally())

        # Delete file externally
        os.remove(path)

        self.assertTrue(text_file.modified_externally())
        text_file._read()  # type: ignore
        self.assertEqual(text_file.lines, [])
        self.assertFalse(text_file.modified_externally())

    def test_read_empty_file(self):
        """Test reading an empty file."""
        path = self._get_temp_path("empty.txt")
        with open(path, 'w', encoding='utf8') as _:
            pass

        text_file = self.ConcreteTextFile(path)
        self.assertEqual(text_file.lines, [])
        self.assertFalse(text_file.modified_externally())
        text_file._read()  # type: ignore
        self.assertEqual(text_file.lines, [])
        self.assertFalse(text_file.modified_externally())

    def test_write(self):
        """Test writing to a file."""
        path = self._get_temp_path("write_test.txt")
        
        # Create non-existing file
        text_file = self.ConcreteTextFile(path)
        text_file.lines = ["hello", "world"]
        self.assertFalse(text_file.modified_externally())
        text_file._write()  # type: ignore
        self.assertFalse(text_file.modified_externally())
        
        with open(path, 'r', encoding='utf8') as f:
            content = f.read()
        self.assertEqual(content, "hello\nworld")

        # Modify existing file
        text_file.lines.append("new line")
        text_file._write()  # type: ignore
        self.assertFalse(text_file.modified_externally())

        with open(path, 'r', encoding='utf8') as f:
            content = f.read()
        self.assertEqual(content, "hello\nworld\nnew line")

        # Re-create file after it was deleted externally
        os.remove(path)
        self.assertTrue(text_file.modified_externally())
        text_file.lines.append("after delete")
        text_file._write()  # type: ignore
        self.assertFalse(text_file.modified_externally())

        with open(path, 'r', encoding='utf8') as f:
            content = f.read()
        self.assertEqual(content, "hello\nworld\nnew line\nafter delete")

    def test_two_instances(self):
        """Test two instances accessing the same file."""
        path = self._get_temp_path("two_instances.txt")
        file1 = self.ConcreteTextFile(path)
        file2 = self.ConcreteTextFile(path)

        file1.lines = ["first instance"]
        file1._write()  # type: ignore
        file2._read()   # type: ignore
        self.assertEqual(file2.lines, ["first instance"])

        file2.lines.append("second instance")
        file2._write()  # type: ignore
        file1._read()   # type: ignore
        self.assertEqual(file1.lines, ["first instance", "second instance"])

    def test_modify(self):
        path = self._get_temp_path("modify.txt")
        text_file = self.ConcreteTextFile(path)
        
        with text_file.modify():
            # Lock should be acquired
            self.assertTrue(text_file._lock.is_locked)  # type: ignore

            text_file.lines.append("line1")
        
        # Lock should be released after modify
        self.assertFalse(text_file._lock.is_locked)     # type: ignore
        # Check that the file was written
        self.assertFalse(text_file.modified_externally())
        with open(path, 'r', encoding='utf8') as f:
            content = f.read()
        self.assertEqual(content, "line1")

        with text_file.modify():
            self.assertTrue(text_file._lock.is_locked)  # type: ignore
            text_file.lines.append("line2")

            # _write should be skipped
            text_file._write()  # type: ignore

            self.assertTrue(text_file._lock.is_locked)  # type: ignore
            with open(path, 'r', encoding='utf8') as f:
                content = f.read()
            self.assertEqual(content, "line1")

        with open(path, 'r', encoding='utf8') as f:
            content = f.read()
        self.assertEqual(content, "line1\nline2")

    def test_modify_nested(self):
        path = self._get_temp_path("nested_modify.txt")
        
        text_file = self.ConcreteTextFile(path)
        text_file.lines = ["initial"]
        text_file._write()  # type: ignore
        
        with text_file.modify():
            self.assertTrue(text_file._lock.is_locked)  # type: ignore
            text_file.lines.append("first")

            with text_file.modify():
                self.assertTrue(text_file._lock.is_locked)  # type: ignore
                text_file.lines.append("second")

            # Lock should still be held
            self.assertTrue(text_file._lock.is_locked)  # type: ignore
            # Inner modify should not trigger write yet
            with open(path, 'r', encoding='utf8') as f:
                content = f.read()
            self.assertEqual(content, "initial")
        
        # Both modifications should be written
        with open(path, 'r', encoding='utf8') as f:
            content = f.read()
        self.assertEqual(content, "initial\nfirst\nsecond")


if __name__ == '__main__':
    unittest.main()
