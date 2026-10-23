"""Serialize the test cases to XML."""

import base64
import enum
import io
import itertools
import pathlib
import re
import xml.sax.saxutils
from types import TracebackType
from typing import Optional, List, Final, Iterator, TextIO, Type

import aas_core_codegen.common
import aas_core_codegen.naming
from aas_core_codegen import intermediate
from aas_core_codegen.common import assert_never, Identifier
from icontract import ensure, require, invariant

from aas_core_testdatagen import preseria, casing, generation, seria, common, names
from aas_core_testdatagen.casing import NegativeCase


class _LastWrite(enum.Enum):
    """Track the last writing action to the stream in :py:cls:`_Xmlizer`."""

    OPEN = "OPEN"
    CLOSE = "CLOSE"
    TEXT = "TEXT"


_XML_INDENT = "  "


class _Xmlizer:
    """Track XML tokens and convert them finally to a string."""

    _namespace: Final[str]
    _stream: Final[TextIO]

    def __init__(self, namespace: str, stream: TextIO) -> None:
        self._namespace = namespace
        self._stream = stream

        self._indent_level = 0
        self._pending_open = None  # type: Optional[str]
        self._pending_reset_namespace = False
        self._open_stack = []  # type: List[str]

        self._last_write = None  # type: Optional[_LastWrite]

    @ensure(lambda self: self._last_write is _LastWrite.OPEN)
    @ensure(lambda self: self._pending_open is None)
    def _handle_pending_open(self) -> None:
        assert (
            self._pending_open is not None
        ), "Pending open element expected before we can handle it."

        if self._last_write is None:
            assert self._indent_level == 0, (
                f"Expected 0 indent level when no previous writes, "
                f"but got: {self._indent_level}"
            )

            self._stream.write(
                f"<{self._pending_open} "
                f"xmlns={xml.sax.saxutils.quoteattr(self._namespace)}"
                f">"
            )

        elif self._last_write == _LastWrite.OPEN:
            self._indent_level += 1
            self._stream.write("\n")
            self._stream.write(_XML_INDENT * self._indent_level)
            self._stream.write(f"<{self._pending_open}{self._namespace_reset()}>")

        elif self._last_write == _LastWrite.CLOSE:
            self._stream.write("\n")
            self._stream.write(_XML_INDENT * self._indent_level)
            self._stream.write(f"<{self._pending_open}{self._namespace_reset()}>")

        elif self._last_write == _LastWrite.TEXT:
            self._stream.write(f"<{self._pending_open}{self._namespace_reset()}>")

        else:
            # noinspection PyTypeChecker
            assert_never(self._last_write)

        self._last_write = _LastWrite.OPEN
        self._pending_open = None
        self._pending_reset_namespace = False

    def _namespace_reset(self) -> str:
        """Give the attribute to put the pending element in no namespace, if any."""
        return ' xmlns=""' if self._pending_reset_namespace else ""

    @ensure(lambda self, name: self._pending_open == name)
    def enqueue_open(self, name: str, reset_namespace: bool = False) -> None:
        """
        Enqueue the open element for writing.

        If there is a pending open element, it is written to the stream first.

        If ``reset_namespace`` is set, the element is written with an empty default
        namespace, as required by the elements of XML-RPC.
        """
        if self._pending_open is not None:
            self._handle_pending_open()

        self._pending_open = name
        self._pending_reset_namespace = reset_namespace
        self._open_stack.append(self._pending_open)

    def write_close(self, name: str) -> None:
        """
        Write the close element to the stream, handling any pending open element first.

        Invalid close elements are detected, and a ``ValueError`` is raised.
        """
        if len(self._open_stack) == 0:
            raise ValueError(
                f"You are trying to close with {name!r}, "
                f"but no previous opening element was found."
            )

        last_open = self._open_stack.pop()
        if last_open != name:
            raise ValueError(
                f"You are trying to close with {name!r}, "
                f"but you previously opened with {last_open!r}."
            )

        if self._pending_open is not None:
            assert last_open == self._pending_open, (
                f"Expected the last name on open stack to coincide "
                f"with the pending open, but got {last_open!r} on stack "
                f"and {self._pending_open!r} as pending open."
            )

            self_closing_element = (
                f"<{name} xmlns={xml.sax.saxutils.quoteattr(self._namespace)} />"
                if len(self._open_stack) == 0
                else f"<{name}{self._namespace_reset()} />"
            )

            if self._last_write is None:
                self._stream.write(self_closing_element)
                self._pending_open = None

            elif self._last_write is _LastWrite.TEXT:
                self._stream.write(self_closing_element)

            elif self._last_write is _LastWrite.OPEN:
                self._stream.write("\n")
                self._indent_level += 1
                self._stream.write(_XML_INDENT * self._indent_level)
                self._stream.write(self_closing_element)

            elif self._last_write is _LastWrite.CLOSE:
                self._stream.write("\n")
                self._stream.write(_XML_INDENT * self._indent_level)
                self._stream.write(self_closing_element)

            else:
                # noinspection PyTypeChecker
                assert_never(self._last_write)

            self._pending_open = None
            self._pending_reset_namespace = False

        else:
            if self._last_write is None:
                raise AssertionError(
                    "Unexpected no last write when no pending open "
                    "and valid open stack."
                )

            elif self._last_write is _LastWrite.TEXT:
                self._stream.write(f"</{name}>")

            elif self._last_write is _LastWrite.OPEN:
                raise AssertionError(
                    "Unexpected last write open when no pending open "
                    "and valid open stack."
                )

            elif self._last_write is _LastWrite.CLOSE:
                self._stream.write("\n")
                self._indent_level -= 1

                self._stream.write(_XML_INDENT * self._indent_level)
                self._stream.write(f"</{name}>")

            else:
                # noinspection PyTypeChecker
                assert_never(self._last_write)

        self._last_write = _LastWrite.CLOSE

    @ensure(lambda self: self._last_write is _LastWrite.TEXT)
    def write_text(self, content: str) -> None:
        """
        Write the text to the stream, handling any pending open element first.

        Texts at invalid positions are detected, and a ``ValueError`` is raised.
        """
        if self._pending_open is not None:
            self._handle_pending_open()

        if self._last_write is None:
            raise ValueError("You are trying to write text without opening element.")

        self._stream.write(xml.sax.saxutils.escape(content))
        self._last_write = _LastWrite.TEXT

    def finalize(self) -> None:
        """Finalize the writing and check that all the elements were properly closed."""
        if len(self._open_stack) != 0:
            raise ValueError(
                f"The close elements are missing; the open stack is: {self._open_stack}"
            )

        assert self._pending_open is None, (
            "If there are no elements on the open stack then "
            "no pending open element is expected."
        )

    def __enter__(self) -> "_Xmlizer":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.finalize()


def _serialize_primitive_property(
    xmlizer: _Xmlizer, xml_prop_name: str, value: preseria.PrimitiveValueUnion
) -> None:

    xmlizer.enqueue_open(xml_prop_name)

    if isinstance(value, bool):
        xmlizer.write_text("true" if value else "false")

    elif isinstance(value, (int, float)):
        xmlizer.write_text(str(value))

    elif isinstance(value, str):
        xmlizer.write_text(value)

    elif isinstance(value, bytes):
        xmlizer.write_text(base64.b64encode(value).decode("utf-8"))

    else:
        # noinspection PyTypeChecker
        assert_never(value)

    xmlizer.write_close(xml_prop_name)


def _serialize_instance_property(
    xmlizer: _Xmlizer,
    xml_prop_name: str,
    instance: preseria.ImmutableInstance,
    symbol_table: intermediate.SymbolTable,
    force_class_element: bool = False,
) -> None:
    cls = symbol_table.must_find_concrete_class(instance.class_name)
    with_class_element = force_class_element or cls.serialization.with_model_type

    xmlizer.enqueue_open(xml_prop_name)

    xml_class_name = aas_core_codegen.naming.xml_class_name(instance.class_name)

    if with_class_element:
        xmlizer.enqueue_open(xml_class_name)

    _serialize_instance_as_sequence(
        xmlizer=xmlizer, instance=instance, symbol_table=symbol_table
    )

    if with_class_element:
        xmlizer.write_close(xml_class_name)

    xmlizer.write_close(xml_prop_name)


def _serialize_list_of_instances_property(
    xmlizer: _Xmlizer,
    xml_prop_name: str,
    list_of_instances: preseria.SequenceOfImmutableInstances,
    symbol_table: intermediate.SymbolTable,
) -> None:

    xmlizer.enqueue_open(xml_prop_name)

    for instance in list_of_instances.values:
        xml_cls_name = aas_core_codegen.naming.xml_class_name(instance.class_name)

        xmlizer.enqueue_open(xml_cls_name)

        _serialize_instance_as_sequence(
            xmlizer=xmlizer, instance=instance, symbol_table=symbol_table
        )

        xmlizer.write_close(xml_cls_name)

    xmlizer.write_close(xml_prop_name)


def _serialize_tuple_property(
    xmlizer: _Xmlizer,
    xml_prop_name: str,
    tuple_of_values: preseria.TupleOfImmutableValues,
    symbol_table: intermediate.SymbolTable,
) -> None:
    """
    Serialize the tuple as the property with one element per item.

    The primitive items are named ``v1``, ``v2``, *etc.* (counting only primitives),
    while the instances are named after their classes.
    """

    xmlizer.enqueue_open(xml_prop_name)

    primitive_count = 0

    for item in tuple_of_values.values:
        if isinstance(item, preseria.PrimitiveValueTuple):
            primitive_count += 1

            _serialize_primitive_property(
                xmlizer=xmlizer, xml_prop_name=f"v{primitive_count}", value=item
            )

        elif isinstance(item, preseria.ImmutableInstance):
            xml_cls_name = aas_core_codegen.naming.xml_class_name(item.class_name)

            xmlizer.enqueue_open(xml_cls_name)

            _serialize_instance_as_sequence(
                xmlizer=xmlizer, instance=item, symbol_table=symbol_table
            )

            xmlizer.write_close(xml_cls_name)

        elif isinstance(
            item,
            (
                preseria.SequenceOfImmutableInstances,
                preseria.TupleOfImmutableValues,
                preseria.SequenceOfImmutablePrimitives,
                preseria.SetOfImmutablePrimitives,
                preseria.ImmutableJsonArray,
                preseria.ImmutableJsonObject,
            ),
        ):
            raise NotImplementedError(
                f"XML serialization of nested lists, tuples and sets in the tuple "
                f"property {xml_prop_name!r} is not defined yet."
            )

        else:
            # noinspection PyTypeChecker
            assert_never(item)

    xmlizer.write_close(xml_prop_name)


def _serialize_set_property(
    xmlizer: _Xmlizer,
    xml_prop_name: str,
    set_of_primitives: preseria.SetOfImmutablePrimitives,
) -> None:
    """Serialize the sorted items of the set as ``<v>`` elements."""

    xmlizer.enqueue_open(xml_prop_name)

    for item in preseria.sorted_set_items(set_of_primitives.values):
        _serialize_primitive_property(xmlizer=xmlizer, xml_prop_name="v", value=item)

    xmlizer.write_close(xml_prop_name)


def _serialize_json_value_content(
    xmlizer: _Xmlizer, value: preseria.ImmutableJsonValueUnion, reset_namespace: bool
) -> None:
    """
    Serialize the JSON-able value with the subset of XML-RPC elements.

    The ``reset_namespace`` must be set for the first element beneath an element of
    the meta-model, as the XML-RPC elements reside in no namespace.
    """
    if isinstance(value, bool):
        xmlizer.enqueue_open("boolean", reset_namespace)
        # XML-RPC prescribes 0 and 1 for booleans.
        xmlizer.write_text("1" if value else "0")
        xmlizer.write_close("boolean")

    elif isinstance(value, float):
        xmlizer.enqueue_open("double", reset_namespace)
        xmlizer.write_text(str(value))
        xmlizer.write_close("double")

    elif isinstance(value, str):
        xmlizer.enqueue_open("string", reset_namespace)
        xmlizer.write_text(value)
        xmlizer.write_close("string")

    elif isinstance(value, preseria.ImmutableJsonArray):
        xmlizer.enqueue_open("array", reset_namespace)
        _serialize_json_array_data(xmlizer, value, reset_namespace=False)
        xmlizer.write_close("array")

    elif isinstance(value, preseria.ImmutableJsonObject):
        xmlizer.enqueue_open("struct", reset_namespace)
        _serialize_json_members(xmlizer, value, reset_namespace=False)
        xmlizer.write_close("struct")

    else:
        # noinspection PyTypeChecker
        assert_never(value)


def _serialize_json_array_data(
    xmlizer: _Xmlizer, array: preseria.ImmutableJsonArray, reset_namespace: bool
) -> None:
    """Serialize the items of the JSON array as the ``<data>`` element."""
    xmlizer.enqueue_open("data", reset_namespace)

    for item in array.values:
        xmlizer.enqueue_open("value")
        _serialize_json_value_content(xmlizer, item, reset_namespace=False)
        xmlizer.write_close("value")

    xmlizer.write_close("data")


def _serialize_json_members(
    xmlizer: _Xmlizer, json_object: preseria.ImmutableJsonObject, reset_namespace: bool
) -> None:
    """Serialize the members of the JSON object as the ``<member>`` elements."""
    for key, member_value in json_object.members:
        xmlizer.enqueue_open("member", reset_namespace)

        xmlizer.enqueue_open("name")
        xmlizer.write_text(key)
        xmlizer.write_close("name")

        xmlizer.enqueue_open("value")
        _serialize_json_value_content(xmlizer, member_value, reset_namespace=False)
        xmlizer.write_close("value")

        xmlizer.write_close("member")


def _serialize_json_value_property(
    xmlizer: _Xmlizer, xml_prop_name: str, value: preseria.ImmutableJsonValueUnion
) -> None:
    """Serialize the property whose value is an arbitrary JSON-able value."""
    xmlizer.enqueue_open(xml_prop_name)
    _serialize_json_value_content(xmlizer, value, reset_namespace=True)
    xmlizer.write_close(xml_prop_name)


def _serialize_json_array_property(
    xmlizer: _Xmlizer, xml_prop_name: str, array: preseria.ImmutableJsonArray
) -> None:
    """Serialize the property whose value is an open JSON array."""
    xmlizer.enqueue_open(xml_prop_name)
    _serialize_json_array_data(xmlizer, array, reset_namespace=True)
    xmlizer.write_close(xml_prop_name)


def _serialize_json_object_property(
    xmlizer: _Xmlizer, xml_prop_name: str, json_object: preseria.ImmutableJsonObject
) -> None:
    """Serialize the property whose value is an open JSON object."""
    xmlizer.enqueue_open(xml_prop_name)
    _serialize_json_members(xmlizer, json_object, reset_namespace=True)
    xmlizer.write_close(xml_prop_name)


def _serialize_instance_as_sequence(
    xmlizer: _Xmlizer,
    instance: preseria.ImmutableInstance,
    symbol_table: intermediate.SymbolTable,
) -> None:
    cls = symbol_table.must_find_concrete_class(instance.class_name)

    expected_property_order = itertools.chain(
        (prop.name for prop in cls.properties if prop.name in instance.properties),
        (
            prop_name
            for prop_name in instance.properties
            if prop_name not in cls.properties_by_name
        ),
    )

    for prop_name in expected_property_order:
        prop_value = instance.properties[prop_name]

        xml_prop_name = names.xml_property(symbol_table, cls.name, prop_name)

        if isinstance(prop_value, preseria.PrimitiveValueTuple):
            _serialize_primitive_property(
                xmlizer=xmlizer, xml_prop_name=xml_prop_name, value=prop_value
            )

        elif isinstance(prop_value, preseria.ImmutableInstance):
            prop_type_anno = intermediate.beneath_optional(
                cls.properties_by_name[prop_name].type_annotation
            )
            _serialize_instance_property(
                xmlizer=xmlizer,
                xml_prop_name=xml_prop_name,
                instance=prop_value,
                symbol_table=symbol_table,
                force_class_element=(
                    isinstance(prop_type_anno, intermediate.OurTypeAnnotation)
                    and isinstance(prop_type_anno.our_type, intermediate.NamedUnion)
                ),
            )

        elif isinstance(prop_value, preseria.SequenceOfImmutableInstances):
            prop = cls.properties_by_name[prop_name]

            type_anno = intermediate.beneath_optional(prop.type_annotation)

            assert isinstance(type_anno, intermediate.ListTypeAnnotation), (
                f"Expected the property {prop.name!r} of class {cls.name!r} "
                f"to have the list type annotation since the property of "
                f"the pre-serialized instances has the property value {prop_value!r}, "
                f"but the property is annotated with {prop.type_annotation} "
                f"in symbol table."
            )

            if not (
                isinstance(type_anno.items, intermediate.OurTypeAnnotation)
                and isinstance(
                    type_anno.items.our_type,
                    (intermediate.AbstractClass, intermediate.ConcreteClass),
                )
            ):
                raise NotImplementedError(
                    f"(mristin) We handle at the moment only lists of instances, "
                    f"but you supplied the property {prop.name!r} in class {cls.name!r} "
                    f"with type annotation {prop.type_annotation}. Please contact "
                    f"the developers if you need this feature."
                )

            _serialize_list_of_instances_property(
                xmlizer=xmlizer,
                xml_prop_name=xml_prop_name,
                list_of_instances=prop_value,
                symbol_table=symbol_table,
            )

        elif isinstance(prop_value, preseria.TupleOfImmutableValues):
            _serialize_tuple_property(
                xmlizer=xmlizer,
                xml_prop_name=xml_prop_name,
                tuple_of_values=prop_value,
                symbol_table=symbol_table,
            )

        elif isinstance(prop_value, preseria.SetOfImmutablePrimitives):
            _serialize_set_property(
                xmlizer=xmlizer,
                xml_prop_name=xml_prop_name,
                set_of_primitives=prop_value,
            )

        elif isinstance(prop_value, preseria.SequenceOfImmutablePrimitives):
            xmlizer.enqueue_open(xml_prop_name)
            for item in prop_value.values:
                if isinstance(item, preseria.ImmutableJsonObject):
                    xmlizer.enqueue_open("v")
                    _serialize_json_members(xmlizer, item, reset_namespace=True)
                    xmlizer.write_close("v")
                elif isinstance(item, preseria.ImmutableJsonArray):
                    xmlizer.enqueue_open("v")
                    _serialize_json_array_data(xmlizer, item, reset_namespace=True)
                    xmlizer.write_close("v")
                else:
                    _serialize_primitive_property(
                        xmlizer=xmlizer, xml_prop_name="v", value=item
                    )
            xmlizer.write_close(xml_prop_name)

        elif isinstance(prop_value, preseria.ImmutableJsonObject):
            _serialize_json_object_property(
                xmlizer=xmlizer, xml_prop_name=xml_prop_name, json_object=prop_value
            )

        elif isinstance(prop_value, preseria.ImmutableJsonArray):
            _serialize_json_array_property(
                xmlizer=xmlizer, xml_prop_name=xml_prop_name, array=prop_value
            )

        else:
            # noinspection PyTypeChecker
            assert_never(prop_value)


def serialize(
    instance: preseria.ImmutableInstance, symbol_table: intermediate.SymbolTable
) -> str:
    """Serialize the instance into an XML document."""
    stream = io.StringIO()

    with _Xmlizer(
        namespace=symbol_table.meta_model.xml_namespace, stream=stream
    ) as xmlizer:
        xml_cls_name = aas_core_codegen.naming.xml_class_name(instance.class_name)

        xmlizer.enqueue_open(xml_cls_name)

        _serialize_instance_as_sequence(
            xmlizer=xmlizer, instance=instance, symbol_table=symbol_table
        )

        xmlizer.write_close(xml_cls_name)

    return stream.getvalue()


@ensure(
    lambda result: len(result.parts) > 0
    and result.parts[0] == "Xml"
    and result.parts[-1].endswith(".xml")
)
@ensure(lambda result: not result.is_absolute())
def _determine_relative_path(
    case: casing.CaseUnion, symbol_table: intermediate.SymbolTable
) -> pathlib.Path:
    """Determine the relative path for a test case."""
    xml_class_name = aas_core_codegen.naming.xml_class_name(
        aas_core_codegen.common.Identifier(case.instance.class_name)
    )

    if isinstance(case, casing.PositiveCase):
        if isinstance(case, casing.CaseMinimal):
            case_path_component = pathlib.Path("minimal.xml")
        elif isinstance(case, casing.CaseMaximal):
            case_path_component = pathlib.Path("maximal.xml")
        elif isinstance(case, casing.CasePositivePatternExample):
            xml_prop_name = names.xml_property(
                symbol_table, case.instance.class_name, case.property_name
            )

            case_path_component = (
                pathlib.Path(f"{xml_prop_name}OverPatternExamples")
                / f"{case.example_name}.xml"
            )
        elif isinstance(case, casing.CasePositiveValueExample):
            xml_prop_name = names.xml_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            case_path_component = (
                pathlib.Path(f"{xml_prop_name}OverValueExamples")
                / f"{case.value_type_name}_{case.example_name}.xml"
            )
        elif isinstance(case, casing.CasePositiveRangeExample):
            case_path_component = (
                pathlib.Path("overMinMaxExamples")
                / f"{case.value_type_name}_{case.example_name}.xml"
            )
        elif isinstance(case, casing.CasePositiveManual):
            case_path_component = pathlib.Path(f"{case.name}.xml")
        else:
            # noinspection PyTypeChecker
            assert_never(case)

        return pathlib.Path("Xml") / "Expected" / xml_class_name / case_path_component

    elif isinstance(case, NegativeCase):
        if isinstance(case, casing.CaseTypeViolation):
            xml_prop_name = names.xml_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Xml")
                / "Unexpected"
                / "Unserializable"
                / "TypeViolation"
                / xml_class_name
                / f"{xml_prop_name}.xml"
            )

        elif isinstance(case, casing.CaseRequiredViolation):
            # NOTE (mristin):
            # If you change this part, make sure you also update
            # _make_null_violation_out_of_required_violation.

            xml_prop_name = names.xml_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Xml")
                / "Unexpected"
                / "Unserializable"
                / "RequiredViolation"
                / xml_class_name
                / f"{xml_prop_name}.xml"
            )

        elif isinstance(case, casing.CaseUnexpectedAdditionalProperty):
            return (
                pathlib.Path("Xml")
                / "Unexpected"
                / "Unserializable"
                / "UnexpectedAdditionalProperty"
                / xml_class_name
                / "instance.xml"
            )

        elif isinstance(case, casing.CaseEnumerationViolation):
            xml_prop_name = names.xml_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Xml")
                / "Unexpected"
                / "Unserializable"
                / "EnumerationViolation"
                / xml_class_name
                / f"{xml_prop_name}.xml"
            )

        elif isinstance(case, casing.CasePatternViolation):
            xml_prop_name = names.xml_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Xml")
                / "Unexpected"
                / "Invalid"
                / "PatternViolation"
                / xml_class_name
                / xml_prop_name
                / f"{case.example_name}.xml"
            )

        elif isinstance(case, casing.CaseJsonKeyViolation):
            xml_prop_name = names.xml_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Xml")
                / "Unexpected"
                / "Invalid"
                / "JsonKeyViolation"
                / xml_class_name
                / xml_prop_name
                / f"{case.example_name}.xml"
            )

        elif isinstance(case, casing.CaseMinLengthViolation):
            xml_prop_name = names.xml_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Xml")
                / "Unexpected"
                / "Invalid"
                / "MinLengthViolation"
                / xml_class_name
                / f"{xml_prop_name}.xml"
            )

        elif isinstance(case, casing.CaseMaxLengthViolation):
            xml_prop_name = names.xml_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Xml")
                / "Unexpected"
                / "Invalid"
                / "MaxLengthViolation"
                / xml_class_name
                / f"{xml_prop_name}.xml"
            )

        elif isinstance(case, casing.CaseEnumerationViolation):
            xml_prop_name = names.xml_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Xml")
                / "Unexpected"
                / "Invalid"
                / "EnumerationViolation"
                / xml_class_name
                / f"{xml_prop_name}.xml"
            )

        elif isinstance(case, casing.CaseSetViolation):
            xml_prop_name = names.xml_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Xml")
                / "Unexpected"
                / "Invalid"
                / "SetViolation"
                / xml_class_name
                / f"{xml_prop_name}.xml"
            )

        elif isinstance(case, casing.CaseDateTimeUtcViolationOnFebruary29th):
            xml_prop_name = names.xml_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Xml")
                / "Unexpected"
                / "Invalid"
                / "DateTimeUtcViolationOnFebruary29th"
                / xml_class_name
                / f"{xml_prop_name}.xml"
            )

        elif isinstance(case, casing.CaseInvalidValueExample):
            xml_prop_name = names.xml_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Xml")
                / "Unexpected"
                / "Invalid"
                / "InvalidValueExample"
                / xml_class_name
                / xml_prop_name
                / f"{case.value_type_name}_{case.example_name}.xml"
            )

        elif isinstance(case, casing.CaseInvalidRangeExample):
            return (
                pathlib.Path("Xml")
                / "Unexpected"
                / "Invalid"
                / "InvalidRangeExample"
                / xml_class_name
                / f"{case.value_type_name}_{case.example_name}.xml"
            )

        elif isinstance(case, casing.CaseConstraintViolation):
            return (
                pathlib.Path("Xml")
                / "Unexpected"
                / "Invalid"
                / "ConstraintViolation"
                / xml_class_name
                / f"{case.name}.xml"
            )

        else:
            # noinspection PyTypeChecker
            assert_never(case)
    else:
        # noinspection PyTypeChecker
        assert_never(case)


# fmt: off
@invariant(
    lambda self:
    len(self.relative_path.parts) > 0
    and self.relative_path.parts[0] == "Xml"
    and self.relative_path.parts[-1].endswith(".xml")
)
# fmt: on
class Output(common.Output):
    """Represent the test case serialized in XML."""

    # fmt: off
    @require(
        lambda relative_path:
        len(relative_path.parts) > 0
        and relative_path.parts[0] == "Xml"
        and relative_path.parts[-1].endswith(".xml")
    )
    @require(lambda relative_path: not relative_path.is_absolute())
    # fmt: on
    def __init__(self, relative_path: pathlib.Path, text: str) -> None:
        super().__init__(relative_path=relative_path, text=text)


def _make_invalid_xml_class_name_out_of_minimal(
    case: casing.CaseMinimal,
    symbol_table: intermediate.SymbolTable,
) -> Output:
    """Adapt the minimal case by invalidating the model type in the serialization."""
    invalid_class_name = Identifier("Utterly_invalid")

    while symbol_table.find_our_type(invalid_class_name) is not None:
        invalid_class_name = Identifier(f"So_{invalid_class_name.lower()}")

    invalid_xml_cls_name = aas_core_codegen.naming.xml_class_name(invalid_class_name)

    stream = io.StringIO()

    with _Xmlizer(
        namespace=symbol_table.meta_model.xml_namespace, stream=stream
    ) as xmlizer:
        xmlizer.enqueue_open(invalid_xml_cls_name)

        _serialize_instance_as_sequence(
            xmlizer=xmlizer, instance=case.instance, symbol_table=symbol_table
        )

        xmlizer.write_close(invalid_xml_cls_name)

    text = stream.getvalue()

    relative_path = (
        pathlib.Path("Xml")
        / "Unexpected"
        / "Unserializable"
        / "InvalidClassName"
        / aas_core_codegen.naming.xml_class_name(case.instance.class_name)
        / "wrong.xml"
    )

    return Output(relative_path=relative_path, text=text)


_INVALID_XML_RE = re.compile(
    r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]"
)


def generate_test_data(case_generator: generation.CaseGenerator) -> Iterator[Output]:
    """
    Generate the test cases.

    This will produce all the test cases produced by the test generator, but
    will also include some additional XML-specific test cases.
    """
    relative_path_asserter = seria.RelativePathAsserter()

    for case in case_generator.generate():
        relative_path = _determine_relative_path(case, case_generator.symbol_table)

        relative_path_asserter.assert_and_add(relative_path)

        text = serialize(
            instance=case.instance, symbol_table=case_generator.symbol_table
        )

        # NOTE (mristin):
        # We skip the cases which contain invalid XML symbols -- while some
        # XML de-serializers might be able to deal with them, most XML de-serializers
        # will complain, skewing the tests unnecessarily.

        if _INVALID_XML_RE.search(text) is not None:
            continue

        yield Output(relative_path=relative_path, text=text)

        # NOTE (mristin):
        # We delete the variables here to avoid bugs with the code below as we do not
        # want to introduce a separate methods to avoid unnecessary complexity.
        del relative_path
        del text

        if isinstance(case, casing.CaseMinimal):
            output = _make_invalid_xml_class_name_out_of_minimal(
                case=case, symbol_table=case_generator.symbol_table
            )

            relative_path_asserter.assert_and_add(output.relative_path)

            yield output
        else:
            # NOTE (mristin):
            # In general, we leave the cases as-are, no special treatment for XML.
            pass
