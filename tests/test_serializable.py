import dataclasses
import enum
import os
import unittest

from src.tbm13_utils.encoding import *


@dataclasses.dataclass
class TestObj(Serializable):
    id: int
    name: str = "Obj"
    price: float = 10.5
    in_stock: bool|None = None

    def __hash__(self):
        return hash(self.id)

@dataclasses.dataclass
class SpecialTestObj(Serializable):
    some_tuple: tuple[str, int] = ("a", 1)
    some_list: list[str] = dataclasses.field(default_factory=list)
    some_set: set[str] = dataclasses.field(default_factory=set)
    some_dict: dict[str, int] = dataclasses.field(default_factory=dict)
    some_serializable: TestObj = dataclasses.field(default_factory=lambda: TestObj(50))

    tuple_with_serializable: tuple[int, TestObj, int] = dataclasses.field(
        default_factory=lambda: (1, TestObj(0), 3)
    )
    serializable_list: list[TestObj] = dataclasses.field(
        default_factory=lambda: [TestObj(1), TestObj(2)]
    )
    serializable_set: set[TestObj] = dataclasses.field(default_factory=set)
    serializable_dict: dict[str, TestObj] = dataclasses.field(default_factory=dict)

@dataclasses.dataclass
class NestedTestObj(Serializable):
    nested_serializable_list: list[list[TestObj]] = dataclasses.field(default_factory=list)
    nested_serializable_list2: list[list[SpecialTestObj]] = dataclasses.field(default_factory=list)
    nested_serializable: 'NestedTestObj|None' = None

class TestEnum(enum.Enum):
    A = 1
    B = 2
    C = 3
class TestIntEnum(enum.IntEnum):
    A = 1
    B = 2
    C = 3
class TestStrEnum(enum.StrEnum):
    A = "A"
    B = "B"
    C = "C"
class TestFlagEnum(enum.Flag):
    A = 1
    B = 2
    C = 4
    D = 8

@dataclasses.dataclass
class EnumTestObj(Serializable):
    enum_value: TestEnum = TestEnum.A
    int_enum_value: TestIntEnum = TestIntEnum.A
    str_enum_value: TestStrEnum = TestStrEnum.A
    flag_enum_value: TestFlagEnum = TestFlagEnum.A
    enum_list: list[TestEnum] = dataclasses.field(default_factory=list)

@dataclasses.dataclass
class UnionTestObj(Serializable):
    multi_value: str|float|bool|TestEnum|None = None
    multi_value_list: list[str|TestEnum|None]|None = dataclasses.field(default_factory=list)

class TestSerializable(unittest.TestCase):
    def setUp(self):
        unittest.util._MAX_LENGTH = 1000

    def test_from_json(self):
        self.assertEqual(
            TestObj(1),
            TestObj.from_json('{"id": 1}'),
        )
        self.assertEqual(
            TestObj(1),
            TestObj.from_json('{"id": 1, "name": "Obj"}'),
        )
        self.assertEqual(
            TestObj(1, "asd"),
            TestObj.from_json('{"id": 1, "name": "asd"}'),
        )
        self.assertEqual(
            TestObj(1, price=20.5),
            TestObj.from_json('{"id": 1, "price": 20.5}'),
        )
        self.assertEqual(
            TestObj(1, price=20.5, in_stock=True),
            TestObj.from_json('{"id": 1, "price": 20.5, "in_stock": true}'),
        )
        self.assertEqual(
            TestObj(1, price=20.5),
            TestObj.from_json('{"id": 1, "price": 20.5, "in_stock": null}'),
        )

        self.assertEqual(
            SpecialTestObj(),
            SpecialTestObj.from_json('{}'),
        )
        self.assertEqual(
            SpecialTestObj(),
            SpecialTestObj.from_json('{"some_tuple": ["a", 1]}'),
        )
        self.assertEqual(
            SpecialTestObj(some_tuple=("asd", 0)),
            SpecialTestObj.from_json('{"some_tuple": ["asd", 0]}'),
        )
        self.assertEqual(
            SpecialTestObj(some_list=["a", "b"]),
            SpecialTestObj.from_json('{"some_list": ["a", "b"]}'),
        )
        self.assertEqual(
            SpecialTestObj(some_set={"b", "a"}),
            SpecialTestObj.from_json('{"some_set": ["a", "b"]}'),
        )
        self.assertEqual(
            SpecialTestObj(some_dict={"a": 1, "b": 2}),
            SpecialTestObj.from_json('{"some_dict": {"a": 1, "b": 2}}'),
        )
        self.assertEqual(
            SpecialTestObj(some_serializable=TestObj(9)),
            SpecialTestObj.from_json('{"some_serializable": {"id": 9}}'),
        )
        self.assertEqual(
            SpecialTestObj(tuple_with_serializable=(15, TestObj(0), 3)),
            SpecialTestObj.from_json('{"tuple_with_serializable": [15, {"id": 0}, 3]}'),
        )
        self.assertEqual(
            SpecialTestObj(),
            SpecialTestObj.from_json('{"serializable_list": [{"id": 1}, {"id": 2}]}'),
        )
        self.assertEqual(
            SpecialTestObj(serializable_list=[TestObj(10)]),
            SpecialTestObj.from_json('{"serializable_list": [{"id": 10}]}'),
        )
        self.assertEqual(
            SpecialTestObj(serializable_dict={"a": TestObj(1), "b": TestObj(2)}),
            SpecialTestObj.from_json('{"serializable_dict": {"a": {"id": 1}, "b": {"id": 2}}}'),
        )
        self.assertEqual(
            SpecialTestObj(serializable_set={TestObj(1), TestObj(2)}),
            SpecialTestObj.from_json('{"serializable_set": [{"id": 2}, {"id": 1}]}'),
        )

        self.assertEqual(
            NestedTestObj(),
            NestedTestObj.from_json('{}'),
        )
        self.assertEqual(
            NestedTestObj(),
            NestedTestObj.from_json('{"nested_serializable_list": []}'),
        )
        self.assertEqual(
            NestedTestObj(nested_serializable_list=[[TestObj(1), TestObj(2)]]),
            NestedTestObj.from_json('{"nested_serializable_list": [[{"id": 1}, {"id": 2}]]}'),
        )
        self.assertEqual(
            NestedTestObj(nested_serializable_list=[[TestObj(1), TestObj(3)], [TestObj(2)]]),
            NestedTestObj.from_json('{"nested_serializable_list": [[{"id": 1}, {"id": 3}], [{"id": 2}]]}'),
        )
        self.assertEqual(
            NestedTestObj(nested_serializable_list2=[[SpecialTestObj()], []]),
            NestedTestObj.from_json('{"nested_serializable_list2": [[{}], []]}'),
        )
        self.assertEqual(
            NestedTestObj(nested_serializable_list2=[[SpecialTestObj(some_list=["a", "b"])]]),
            NestedTestObj.from_json('{"nested_serializable_list2": [[{"some_list": ["a", "b"]}]]}'),
        )
        self.assertEqual(
            NestedTestObj(nested_serializable=NestedTestObj()),
            NestedTestObj.from_json('{"nested_serializable": {}}'),
        )
        self.assertEqual(
            NestedTestObj(nested_serializable=NestedTestObj(nested_serializable_list=[[TestObj(1)]])),
            NestedTestObj.from_json('{"nested_serializable": {"nested_serializable_list": [[{"id": 1}]]}}'),
        )
        self.assertEqual(
            NestedTestObj(nested_serializable=NestedTestObj(nested_serializable=NestedTestObj(nested_serializable=NestedTestObj()))),
            NestedTestObj.from_json('{"nested_serializable": {"nested_serializable": {"nested_serializable": {}}}}'),
        )

        self.assertEqual(
            EnumTestObj(),
            EnumTestObj.from_json('{}'),
        )
        self.assertEqual(
            EnumTestObj(),
            EnumTestObj.from_json('{"enum_value": 1}'),
        )
        self.assertEqual(
            EnumTestObj(TestEnum.B),
            EnumTestObj.from_json('{"enum_value": 2}'),
        )
        self.assertEqual(
            EnumTestObj(int_enum_value=TestIntEnum.B),
            EnumTestObj.from_json('{"int_enum_value": 2}'),
        )
        self.assertEqual(
            EnumTestObj(str_enum_value=TestStrEnum.B),
            EnumTestObj.from_json('{"str_enum_value": "B"}'),
        )
        self.assertEqual(
            EnumTestObj(flag_enum_value=TestFlagEnum.B),
            EnumTestObj.from_json('{"flag_enum_value": 2}'),
        )
        self.assertEqual(
            EnumTestObj(flag_enum_value=TestFlagEnum.B | TestFlagEnum.C),
            EnumTestObj.from_json('{"flag_enum_value": 6}'),
        )
        self.assertEqual(
            EnumTestObj(enum_list=[TestEnum.A, TestEnum.B]),
            EnumTestObj.from_json('{"enum_list": [1, 2]}'),
        )

        self.assertEqual(
            UnionTestObj(),
            UnionTestObj.from_json('{}'),
        )
        self.assertEqual(
            UnionTestObj(multi_value="test"),
            UnionTestObj.from_json('{"multi_value": "test"}'),
        )
        self.assertEqual(
            UnionTestObj(multi_value=3.14),
            UnionTestObj.from_json('{"multi_value": 3.14}'),
        )
        self.assertEqual(
            UnionTestObj(multi_value=True),
            UnionTestObj.from_json('{"multi_value": true}'),
        )
        self.assertEqual(
            UnionTestObj(multi_value=TestEnum.A),
            UnionTestObj.from_json('{"multi_value": 1}'),
        )
        self.assertEqual(
            UnionTestObj(multi_value_list=None),
            UnionTestObj.from_json('{"multi_value_list": null}'),
        )
        self.assertEqual(
            UnionTestObj(multi_value_list=["test", TestEnum.A, None]),
            UnionTestObj.from_json('{"multi_value_list": ["test", 1, null]}'),
        )

    def test_to_json(self):
        self.assertEqual(
            TestObj(1).to_json(),
            '{"id": 1}',
        )
        self.assertEqual(
            TestObj(1, "asd").to_json(),
            '{"id": 1, "name": "asd"}',
        )
        self.assertEqual(
            TestObj(1, price=20.5).to_json(),
            '{"id": 1, "price": 20.5}',
        )
        self.assertEqual(
            TestObj(1, price=20.5, in_stock=True).to_json(),
            '{"id": 1, "price": 20.5, "in_stock": true}',
        )

        self.assertEqual(
            SpecialTestObj().to_json(),
            '{}',
        )
        self.assertEqual(
            SpecialTestObj(some_tuple=("asd", 0)).to_json(),
            '{"some_tuple": ["asd", 0]}',
        )
        self.assertEqual(
            SpecialTestObj(some_list=["a", "b"]).to_json(),
            '{"some_list": ["a", "b"]}',
        )
        self.assertIn(
            SpecialTestObj(some_set={"b", "a"}).to_json(),
            ['{"some_set": ["a", "b"]}', '{"some_set": ["b", "a"]}'],
        )
        self.assertEqual(
            SpecialTestObj(some_dict={"a": 1, "b": 2}).to_json(),
            '{"some_dict": {"a": 1, "b": 2}}',
        )
        self.assertEqual(
            SpecialTestObj(some_serializable=TestObj(9)).to_json(),
            '{"some_serializable": {"id": 9}}',
        )
        self.assertEqual(
            SpecialTestObj(tuple_with_serializable=(15, TestObj(0), 3)).to_json(),
            '{"tuple_with_serializable": [15, {"id": 0}, 3]}',
        )
        self.assertEqual(
            SpecialTestObj(serializable_list=[TestObj(10)]).to_json(),
            '{"serializable_list": [{"id": 10}]}',
        )
        self.assertEqual(
            SpecialTestObj(serializable_dict={"a": TestObj(1), "b": TestObj(2)}).to_json(),
            '{"serializable_dict": {"a": {"id": 1}, "b": {"id": 2}}}',
        )
        self.assertIn(
            SpecialTestObj(serializable_set={TestObj(1), TestObj(2)}).to_json(),
            ['{"serializable_set": [{"id": 2}, {"id": 1}]}', '{"serializable_set": [{"id": 1}, {"id": 2}]}'],
        )

        self.assertEqual(
            NestedTestObj().to_json(),
            '{}',
        )
        self.assertEqual(
            NestedTestObj(nested_serializable_list=[[TestObj(1), TestObj(2)]]).to_json(),
            '{"nested_serializable_list": [[{"id": 1}, {"id": 2}]]}',
        )
        self.assertEqual(
            NestedTestObj(nested_serializable_list=[[TestObj(1), TestObj(3)], [TestObj(2)]]).to_json(),
            '{"nested_serializable_list": [[{"id": 1}, {"id": 3}], [{"id": 2}]]}',
        )
        self.assertEqual(
            NestedTestObj(nested_serializable_list2=[[SpecialTestObj()], []]).to_json(),
            '{"nested_serializable_list2": [[{}], []]}',
        )
        self.assertEqual(
            NestedTestObj(nested_serializable_list2=[[SpecialTestObj(some_list=["a", "b"])]]).to_json(),
            '{"nested_serializable_list2": [[{"some_list": ["a", "b"]}]]}',
        )
        self.assertEqual(
            NestedTestObj(nested_serializable=NestedTestObj()).to_json(),
            '{"nested_serializable": {}}',
        )
        self.assertEqual(
            NestedTestObj(nested_serializable=NestedTestObj(nested_serializable_list=[[TestObj(1)]])).to_json(),
            '{"nested_serializable": {"nested_serializable_list": [[{"id": 1}]]}}',
        )
        self.assertEqual(
            NestedTestObj(nested_serializable=NestedTestObj(nested_serializable=NestedTestObj(nested_serializable=NestedTestObj()))).to_json(),
            '{"nested_serializable": {"nested_serializable": {"nested_serializable": {}}}}',
        )

        self.assertEqual(
            EnumTestObj().to_json(),
            '{}',
        )
        self.assertEqual(
            EnumTestObj(TestEnum.B).to_json(),
            '{"enum_value": 2}',
        )
        self.assertEqual(
            EnumTestObj(int_enum_value=TestIntEnum.B).to_json(),
            '{"int_enum_value": 2}',
        )
        self.assertEqual(
            EnumTestObj(str_enum_value=TestStrEnum.B).to_json(),
            '{"str_enum_value": "B"}',
        )
        self.assertEqual(
            EnumTestObj(flag_enum_value=TestFlagEnum.B).to_json(),
            '{"flag_enum_value": 2}',
        )
        self.assertEqual(
            EnumTestObj(flag_enum_value=TestFlagEnum.B | TestFlagEnum.C).to_json(),
            '{"flag_enum_value": 6}',
        )
        self.assertEqual(
            EnumTestObj(enum_list=[TestEnum.A, TestEnum.B]).to_json(),
            '{"enum_list": [1, 2]}',
        )

        self.assertEqual(
            UnionTestObj().to_json(),
            '{}',
        )
        self.assertEqual(
            UnionTestObj(multi_value="test").to_json(),
            '{"multi_value": "test"}',
        )
        self.assertEqual(
            UnionTestObj(multi_value=3.14).to_json(),
            '{"multi_value": 3.14}',
        )
        self.assertEqual(
            UnionTestObj(multi_value=True).to_json(),
            '{"multi_value": true}',
        )
        self.assertEqual(
            UnionTestObj(multi_value=TestEnum.A).to_json(),
            '{"multi_value": 1}',
        )
        self.assertEqual(
            UnionTestObj(multi_value_list=None).to_json(),
            '{"multi_value_list": null}',
        )
        self.assertEqual(
            UnionTestObj(multi_value_list=["test", TestEnum.A, None]).to_json(),
            '{"multi_value_list": ["test", 1, null]}',
        )

        @dataclasses.dataclass
        class TestObjWithIgnoredFields(TestObj):
            def __post_init__(self):
                self._ignored_fields.add('price')
                self._ignored_fields.add('in_stock')

        self.assertEqual(
            TestObjWithIgnoredFields(1).to_json(),
            '{"id": 1}',
        )
        self.assertEqual(
            TestObjWithIgnoredFields(1, in_stock=True).to_json(),
            '{"id": 1}',
        )
        self.assertEqual(
            TestObjWithIgnoredFields(1, in_stock=True, price=99).to_json(),
            '{"id": 1}',
        )
        self.assertEqual(
            TestObjWithIgnoredFields(1, in_stock=False, price=99, name='asd').to_json(),
            '{"id": 1, "name": "asd"}',
        )

    def test_clone(self):
        obj = TestObj(1, "asd", 50.0, True)
        clone = obj.clone()
        self.assertEqual(obj, clone)
        self.assertEqual(obj.to_json(), clone.to_json())
        clone.price = 1
        self.assertNotEqual(obj, clone)
        self.assertNotEqual(obj.to_json(), clone.to_json())

        obj = SpecialTestObj()
        clone = obj.clone()
        self.assertEqual(obj, clone)
        self.assertEqual(obj.to_json(), clone.to_json())

        obj = SpecialTestObj(some_list=["a", "b"])
        clone = obj.clone()
        self.assertEqual(obj, clone)
        self.assertEqual(obj.to_json(), clone.to_json())
        clone.some_list.append("c")
        self.assertNotEqual(obj, clone)
        self.assertNotEqual(obj.to_json(), clone.to_json())

    def test_serializable_file(self):
        path = 'test_serializable_file.json'
        if os.path.exists(path):
            os.remove(path)

        file = ObjectsFile[int, TestObj](path, 'id', TestObj)
        self.assertEqual(len(file), 0)
        self.assertFalse(file.contains(1))
        self.assertFalse(file.contains(TestObj(1)))
        self.assertEqual(file.get(1, TestObj(10)), TestObj(10))
        self.assertRaises(KeyError, file.get, 1)
        self.assertRaises(KeyError, file.pop, 1)
        self.assertRaises(KeyError, file.pop, TestObj(1))
        self.assertRaises(KeyError, file.replace, TestObj(1), TestObj(1))
        
        obj = TestObj(1)
        file.add(obj)
        self.assertRaises(KeyError, file.add, obj)
        self.assertEqual(len(file), 1)
        self.assertTrue(file.contains(1))
        self.assertTrue(file.contains(obj))
        obj.name = "asd"
        self.assertTrue(file.contains(obj))
        self.assertEqual(file.get(1), TestObj(1))
        self.assertNotEqual(file.get(1), obj)

        file2 = ObjectsFile[int, TestObj](path, 'id', TestObj)
        self.assertEqual(len(file2), 1)
        self.assertTrue(file2.contains(1))
        self.assertTrue(file2.contains(obj))
        self.assertEqual(file2.get(1), TestObj(1))
        self.assertNotEqual(file2.get(1), obj)

        self.assertRaises(ValueError, file.replace, obj, TestObj(1)) # obj doesn't match the stored object
        file.replace(TestObj(1), obj)
        self.assertEqual(file.get(1), obj)
        self.assertEqual(file2.get(1), obj)
        self.assertRaises(KeyError, file.add, TestObj(1))

        self.assertEqual(file2.pop(1), obj)
        self.assertEqual(len(file2), 0)
        self.assertFalse(file2.contains(1))
        self.assertFalse(file2.contains(obj))
        self.assertRaises(KeyError, file2.pop, 1)
        self.assertEqual(len(file), 0)

        file.set(TestObj(5))
        self.assertTrue(file2.contains(5))
        self.assertEqual(file.get(5), TestObj(5))
        self.assertEqual(file2.pop(TestObj(5)), TestObj(5))
        self.assertEqual(len(file), 0)
        self.assertEqual(len(file2), 0)

        if os.path.exists(path):
            os.remove(path)

    def test_multikey_serializable_file(self):
        path = 'test_multikey_serializable_file.json'
        if os.path.exists(path):
            os.remove(path)

        file = MultiKeyObjectsFile[int, TestObj](path, 'id', TestObj)
        self.assertEqual(len(file), 0)
        self.assertFalse(file.contains(1))
        self.assertFalse(file.contains(TestObj(1)))
        self.assertEqual(file.get(1, [TestObj(10)]), [TestObj(10)])
        self.assertRaises(KeyError, file.get, 1)
        self.assertRaises(KeyError, file.pop, 1)
        self.assertRaises(KeyError, file.pop, TestObj(1))
        self.assertRaises(KeyError, file.replace, TestObj(1), TestObj(1))

        obj = TestObj(1)
        file.add(obj)
        self.assertEqual(len(file), 1)
        self.assertTrue(file.contains(1))
        self.assertTrue(file.contains(obj))
        obj.name = "asd"
        self.assertFalse(file.contains(obj))
        self.assertTrue(file.contains(1))
        self.assertEqual(file.get(1), [TestObj(1)])
        self.assertNotEqual(file.get(1), [obj])

        file2 = MultiKeyObjectsFile[int, TestObj](path, 'id', TestObj)
        self.assertEqual(len(file2), 1)
        self.assertTrue(file2.contains(1))
        self.assertTrue(file2.contains(TestObj(1)))
        self.assertFalse(file2.contains(obj))
        self.assertEqual(file2.get(1), [TestObj(1)])
        self.assertNotEqual(file2.get(1), [obj])

        self.assertRaises(ValueError, file.replace, obj, TestObj(1)) # obj doesn't match the stored object
        file.replace(TestObj(1), obj)
        self.assertEqual(file.get(1), [obj])
        self.assertEqual(file2.get(1), [obj])

        self.assertEqual(file2.pop(1), [obj])
        self.assertEqual(len(file2), 0)
        self.assertFalse(file2.contains(1))
        self.assertFalse(file2.contains(obj))
        self.assertRaises(KeyError, file2.pop, 1)
        self.assertEqual(len(file), 0)

        file.set([TestObj(5)])
        self.assertTrue(file2.contains(5))
        self.assertEqual(file.get(5), [TestObj(5)])
        self.assertEqual(file2.pop(TestObj(5)), TestObj(5))
        self.assertEqual(len(file), 0)
        self.assertEqual(len(file2), 0)

        # multi-key tests
        file.add(TestObj(5))
        self.assertRaises(ValueError, file.add, TestObj(5))
        file.add(TestObj(5, "test"))
        self.assertEqual(file2.get(5), [TestObj(5), TestObj(5, "test")])
        self.assertEqual(len(file), 1)
        self.assertEqual(file2.count(), 2)
        self.assertEqual(file2.count(5), 2)
        self.assertEqual(file2.count(1), 0)
        self.assertTrue(file.contains(5))
        self.assertTrue(file.contains(TestObj(5)))
        self.assertTrue(file.contains(TestObj(5, "test")))
        self.assertFalse(file.contains(TestObj(5, "test2")))
        self.assertRaises(ValueError, file.pop, TestObj(5, "test2"))
        file.replace(TestObj(5, "test"), TestObj(5, "replaced"))
        self.assertEqual(file2.get(5), [TestObj(5), TestObj(5, "replaced")])
        self.assertEqual(file.pop(TestObj(5)), TestObj(5))
        self.assertEqual(file2.get(5), [TestObj(5, "replaced")])
        self.assertEqual(file.pop(TestObj(5, "replaced")), TestObj(5, "replaced"))
        self.assertEqual(len(file), 0)
        self.assertEqual(file2.count(), 0)
        self.assertFalse(file2.contains(5))

        if os.path.exists(path):
            os.remove(path)