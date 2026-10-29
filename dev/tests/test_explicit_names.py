# pylint: disable=missing-docstring

"""Test that the explicit JSON and XML names of the properties are respected."""

import collections
import pathlib
import tempfile
import textwrap
import unittest
from typing import ClassVar, Final

import aas_core_codegen.run
from aas_core_codegen import intermediate
from aas_core_codegen.common import Identifier

from aas_core_testdatagen import jsoning, names, preseria, xmling

_TOY_META_MODEL: Final[str] = textwrap.dedent(
    '''\
    """Toy meta-model with explicit names."""
    from typing import Annotated, Optional
    from aas_core_meta.marker import json_name, xml_name

    __xml_namespace__ = "https://example.com/toy/1/0"
    __version__ = "V1.0"

    class Inner:
        some_value: int

        def __init__(self, some_value: int) -> None:
            self.some_value = some_value

    class Outer:
        renamed: Annotated[str, json_name("jsonRenamed"), xml_name("xmlRenamed")]
        inner: Annotated[Inner, json_name("jsonInner"), xml_name("xmlInner")]
        plain: Optional[str]

        def __init__(
            self,
            renamed: str,
            inner: Inner,
            plain: Optional[str] = None,
        ) -> None:
            self.renamed = renamed
            self.inner = inner
            self.plain = plain
    '''
)


def _instance() -> preseria.Instance:
    return preseria.Instance(
        class_name=Identifier("Outer"),
        properties=collections.OrderedDict(
            [
                (Identifier("renamed"), "x"),
                (
                    Identifier("inner"),
                    preseria.Instance(
                        class_name=Identifier("Inner"),
                        properties=collections.OrderedDict(
                            [(Identifier("some_value"), 1)]
                        ),
                    ),
                ),
                (Identifier("plain"), "y"),
            ]
        ),
    )


class TestExplicitNames(unittest.TestCase):
    symbol_table: ClassVar[intermediate.SymbolTable]

    @classmethod
    def setUpClass(cls) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "toy.py"
            path.write_text(_TOY_META_MODEL, encoding="utf-8")
            loaded, error = aas_core_codegen.run.load_model(path)
            assert error is None, error
            assert loaded is not None
            cls.symbol_table, _ = loaded

    def test_names(self) -> None:
        self.assertEqual(
            "jsonRenamed", names.json_property(self.symbol_table, "Outer", "renamed")
        )
        self.assertEqual(
            "xmlRenamed", names.xml_property(self.symbol_table, "Outer", "renamed")
        )
        self.assertEqual(
            "someValue", names.json_property(self.symbol_table, "Inner", "some_value")
        )
        self.assertEqual(
            "someValue", names.xml_property(self.symbol_table, "Inner", "some_value")
        )

    def test_unknown_property_falls_back_to_derived_name(self) -> None:
        self.assertEqual(
            "someUnknown",
            names.json_property(self.symbol_table, "Outer", "some_unknown"),
        )
        self.assertEqual(
            "someUnknown",
            names.json_property(self.symbol_table, "Unknown", "some_unknown"),
        )

    def test_json(self) -> None:
        jsonable = jsoning.must_serialize(_instance(), self.symbol_table)
        self.assertEqual(
            {
                "jsonRenamed": "x",
                "jsonInner": {"someValue": 1},
                "plain": "y",
            },
            jsonable,
        )

    def test_xml(self) -> None:
        text = xmling.serialize(_instance(), self.symbol_table)
        self.assertIn("<xmlRenamed>x</xmlRenamed>", text)
        self.assertIn("<xmlInner>", text)
        self.assertIn("<someValue>1</someValue>", text)
        self.assertIn("<plain>y</plain>", text)


if __name__ == "__main__":
    unittest.main()
