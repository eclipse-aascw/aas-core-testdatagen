# pylint: disable=missing-docstring

"""Test tuples, sets and named unions on a toy meta-model."""

import collections
import pathlib
import re
import tempfile
import textwrap
import unittest
from typing import ClassVar, List, Optional

import aas_core_codegen.infer_for_schema
import aas_core_codegen.run
from aas_core_codegen import intermediate
from aas_core_codegen.common import Identifier

from aas_core_testdatagen import (
    common,
    generation,
    jsoning,
    preseria,
    verification,
    xmling,
)

_TOY_META_MODEL = textwrap.dedent(
    '''\
    """Toy meta-model."""
    from typing import Set, Tuple, Union
    from aas_core_meta.marker import verification

    __xml_namespace__ = "https://example.com/toy/1/0"
    __version__ = "V1.0"

    class A:
        x: int

        def __init__(self, x: int) -> None:
            self.x = x

    class B:
        y: str

        def __init__(self, y: str) -> None:
            self.y = y

    Either = Union[A, B]

    class Holder:
        either: Either
        pair: Tuple[int, str]
        tags: Set[str]

        def __init__(
            self, either: Either, pair: Tuple[int, str], tags: Set[str]
        ) -> None:
            self.either = either
            self.pair = pair
            self.tags = tags
    '''
)


class _ToyGenerator(generation.InstanceGenerator):
    def generate_minimal_concrete_instance(
        self, path_hash: common.CanHash, cls: intermediate.ConcreteClass
    ) -> preseria.Instance:
        return self._generate_minimal_concrete_instance_by_schema(path_hash, cls)


def _inst(cls_name: str, **props: preseria.ValueUnion) -> preseria.Instance:
    return preseria.Instance(
        class_name=Identifier(cls_name),
        properties=collections.OrderedDict(
            (Identifier(k), v) for k, v in props.items()
        ),
    )


class TestToyMetaModel(unittest.TestCase):
    symbol_table: ClassVar[intermediate.SymbolTable]
    verificator: ClassVar[verification.Verificator]

    @classmethod
    def setUpClass(cls) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "toy.py"
            path.write_text(_TOY_META_MODEL, encoding="utf-8")
            loaded, error = aas_core_codegen.run.load_model(path)
            assert error is None, error
            assert loaded is not None
            cls.symbol_table, _ = loaded

        constraints, errors = (
            aas_core_codegen.infer_for_schema.infer_constraints_by_class(
                symbol_table=cls.symbol_table
            )
        )
        assert errors is None, errors
        assert constraints is not None
        cls.verificator = verification.Verificator(
            symbol_table=cls.symbol_table,
            constraints_by_class=verification.reorganize_schema_constraints_by_properties(
                constraints_by_class=constraints
            ),
        )

    def _errors(
        self, instance: preseria.Instance
    ) -> Optional[List[verification.Error]]:
        return verification.check_structural_constraints(
            instance=instance,
            symbol_table=self.symbol_table,
            constraints_by_class=self.verificator.constraints_by_class,
        )

    @staticmethod
    def _holder(
        either: preseria.ValueUnion,
        pair: preseria.ValueUnion,
        tags: preseria.ValueUnion,
    ) -> preseria.Instance:
        return _inst("Holder", either=either, pair=pair, tags=tags)

    def _valid(self) -> preseria.Instance:
        return self._holder(
            either=_inst("B", y="hello"),
            pair=preseria.TupleOfValues([1, "a"]),
            tags=preseria.SetOfPrimitives(["z", "a"]),
        )

    def test_valid(self) -> None:
        self.assertIsNone(self._errors(self._valid()))

    def test_union_member_ok(self) -> None:
        instance = self._holder(
            _inst("A", x=3),
            preseria.TupleOfValues([1, "a"]),
            preseria.SetOfPrimitives([]),
        )
        self.assertIsNone(self._errors(instance))

    def test_union_wrong_class(self) -> None:
        instance = self._holder(
            _inst("Holder", either=_inst("A", x=1)),
            preseria.TupleOfValues([1, "a"]),
            preseria.SetOfPrimitives([]),
        )
        self.assertIsNotNone(self._errors(instance))

    def test_union_primitive(self) -> None:
        instance = self._holder(
            "text", preseria.TupleOfValues([1, "a"]), preseria.SetOfPrimitives([])
        )
        self.assertIsNotNone(self._errors(instance))

    def test_tuple_wrong_length(self) -> None:
        cases: List[List[preseria.ValueUnion]] = [[1], [1, "a", "b"]]
        for values_list in cases:
            instance = self._holder(
                _inst("A", x=1),
                preseria.TupleOfValues(values_list),
                preseria.SetOfPrimitives([]),
            )
            self.assertIsNotNone(self._errors(instance), values_list)

    def test_tuple_wrong_item_type(self) -> None:
        instance = self._holder(
            _inst("A", x=1),
            preseria.TupleOfValues(["a", 1]),
            preseria.SetOfPrimitives([]),
        )
        self.assertIsNotNone(self._errors(instance))

    def test_set_wrong_item_type(self) -> None:
        instance = self._holder(
            _inst("A", x=1),
            preseria.TupleOfValues([1, "a"]),
            preseria.SetOfPrimitives([1]),
        )
        self.assertIsNotNone(self._errors(instance))

    def test_set_duplicates(self) -> None:
        instance = self._holder(
            _inst("A", x=1),
            preseria.TupleOfValues([1, "a"]),
            preseria.SetOfPrimitives(["a", "a"]),
        )
        self.assertIsNotNone(self._errors(instance))

    def test_json(self) -> None:
        verified = self.verificator.must(self._valid())
        jsonable, error = jsoning.serialize(verified, self.symbol_table)
        self.assertIsNone(error)
        self.assertEqual(
            {"either": {"y": "hello"}, "pair": [1, "a"], "tags": ["a", "z"]},
            jsonable,
        )

    def test_xml(self) -> None:
        verified = self.verificator.must(self._valid())
        text = re.sub(r">\s+<", "><", xmling.serialize(verified, self.symbol_table))
        self.assertIn("<either><b><y>hello</y></b></either>", text)
        self.assertIn("<pair><v1>1</v1><v2>a</v2></pair>", text)
        self.assertIn("<tags><v>a</v><v>z</v></tags>", text)

    def test_generation_is_verified(self) -> None:
        generator = _ToyGenerator(self.verificator)
        cls = self.symbol_table.must_find_concrete_class(Identifier("Holder"))
        instance = generator.generate_minimal_concrete_instance(
            path_hash=common.hash_path(prefix_hash=None, segment_or_segments=[]),
            cls=cls,
        )
        self.assertIsNone(self._errors(instance))
        self.assertIsInstance(
            instance.properties[Identifier("pair")], preseria.TupleOfValues
        )
        self.assertIsInstance(
            instance.properties[Identifier("tags")], preseria.SetOfPrimitives
        )


if __name__ == "__main__":
    unittest.main()
