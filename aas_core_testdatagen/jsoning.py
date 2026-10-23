"""Serialize the test cases to JSON."""

import base64
import collections
import itertools
import json
import pathlib
from typing import Any, Optional, Tuple, MutableMapping, List, Iterator, Union

import aas_core_codegen.common
import aas_core_codegen.naming
from aas_core_codegen import intermediate
from aas_core_codegen.common import assert_never, Identifier
from icontract import ensure, require, invariant

from aas_core_testdatagen import preseria, casing, generation, seria, common, names
from aas_core_testdatagen.casing import NegativeCase


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def serialize(
    value: preseria.ImmutableValueUnion, symbol_table: intermediate.SymbolTable
) -> Tuple[
    Optional[Union[bool, float, str, MutableMapping[str, Any], List[Any]]],
    Optional[str],
]:
    """
    Serialize the value to a JSON-able.

    Return the JSON-able, or an error, if any.
    """
    if isinstance(value, bool):
        return value, None

    elif isinstance(value, int):
        if not (-(2**53) <= value <= 2**53):  # pylint: disable=superfluous-parens
            return None, (
                f"The value {value} is an integer, but it can not be exactly mapped "
                f"to the JSON number, which is a 64-bit floating point number."
            )

        return float(value), None

    elif isinstance(value, float):
        return value, None

    elif isinstance(value, str):
        return value, None

    elif isinstance(value, bytes):
        return base64.b64encode(value).decode("utf-8"), None

    elif isinstance(value, preseria.ImmutableInstance):
        result: MutableMapping[str, Any] = collections.OrderedDict([])

        maybe_cls = symbol_table.find_our_type(name=value.class_name)

        expected_property_order: Iterator[Identifier]

        if maybe_cls is not None and isinstance(maybe_cls, intermediate.Class):
            expected_property_order = itertools.chain(
                (
                    prop.name
                    for prop in maybe_cls.properties
                    if prop.name in value.properties
                ),
                (
                    prop_name
                    for prop_name in value.properties
                    if prop_name not in maybe_cls.properties_by_name
                ),
            )
        else:
            expected_property_order = iter(value.properties.keys())

        for prop_name in expected_property_order:
            prop_value = value.properties[prop_name]

            if aas_core_codegen.common.IDENTIFIER_RE.fullmatch(prop_name) is not None:
                prop_name_json = names.json_property(
                    symbol_table, value.class_name, prop_name
                )
            else:
                prop_name_json = prop_name

            prop_value_json, serialization_error = serialize(
                value=prop_value, symbol_table=symbol_table
            )

            if serialization_error is not None:
                return None, (
                    f"Failed to serialize property {prop_name!r} "
                    f"of class {value.class_name!r}: {serialization_error}"
                )

            assert prop_value_json is not None

            result[prop_name_json] = prop_value_json

        if maybe_cls is None or not isinstance(maybe_cls, intermediate.ConcreteClass):
            result["modelType"] = value.class_name
        else:
            if maybe_cls.serialization.with_model_type:
                result["modelType"] = aas_core_codegen.naming.json_model_type(
                    value.class_name
                )

        return result, None

    elif isinstance(value, preseria.SequenceOfImmutableInstances):
        json_list = []  # type: List[Any]

        for i, item in enumerate(value.values):
            json_item, serialization_error = serialize(
                value=item, symbol_table=symbol_table
            )

            if serialization_error is not None:
                return None, (
                    f"Failed to serialize the item {i}: {serialization_error}"
                )

            assert json_item is not None

            json_list.append(json_item)

        return json_list, None

    elif isinstance(value, preseria.TupleOfImmutableValues):
        json_tuple = []  # type: List[Any]

        for i, tuple_item in enumerate(value.values):
            json_item, serialization_error = serialize(
                value=tuple_item, symbol_table=symbol_table
            )

            if serialization_error is not None:
                return None, (
                    f"Failed to serialize the tuple item {i}: {serialization_error}"
                )

            assert json_item is not None

            json_tuple.append(json_item)

        return json_tuple, None

    elif isinstance(value, preseria.SetOfImmutablePrimitives):
        json_set = []  # type: List[Any]

        for i, set_item in enumerate(preseria.sorted_set_items(value.values)):
            json_item, serialization_error = serialize(
                value=set_item, symbol_table=symbol_table
            )

            if serialization_error is not None:
                return None, (
                    f"Failed to serialize the set item {i}: {serialization_error}"
                )

            assert json_item is not None

            json_set.append(json_item)

        return json_set, None

    elif isinstance(value, preseria.SequenceOfImmutablePrimitives):
        json_primitives = []  # type: List[Any]

        for i, primitive_item in enumerate(value.values):
            json_item, serialization_error = serialize(
                value=primitive_item, symbol_table=symbol_table
            )

            if serialization_error is not None:
                return None, (
                    f"Failed to serialize the item {i}: {serialization_error}"
                )

            assert json_item is not None

            json_primitives.append(json_item)

        return json_primitives, None

    elif isinstance(value, preseria.ImmutableJsonArray):
        json_array = []  # type: List[Any]

        for i, array_item in enumerate(value.values):
            json_item, serialization_error = serialize(
                value=array_item, symbol_table=symbol_table
            )

            if serialization_error is not None:
                return None, (
                    f"Failed to serialize the item {i}: {serialization_error}"
                )

            assert json_item is not None

            json_array.append(json_item)

        return json_array, None

    elif isinstance(value, preseria.ImmutableJsonObject):
        json_object: MutableMapping[str, Any] = collections.OrderedDict([])

        for key, member_value in value.members:
            json_member, serialization_error = serialize(
                value=member_value, symbol_table=symbol_table
            )

            if serialization_error is not None:
                return None, (
                    f"Failed to serialize the member {key!r}: {serialization_error}"
                )

            assert json_member is not None

            json_object[key] = json_member

        return json_object, None

    else:
        # noinspection PyTypeChecker
        assert_never(value)


def must_serialize(
    value: preseria.ImmutableValueUnion, symbol_table: intermediate.SymbolTable
) -> Union[bool, float, str, MutableMapping[str, Any], List[Any]]:
    """
    Serialize the value to a JSON-able.

    Return the JSON-able, or raise an assertion error, if serialization failed.
    """
    result, error = serialize(value=value, symbol_table=symbol_table)
    if error is not None:
        raise AssertionError(
            f"Failed to serialize a value: {error}; "
            f"the value was {preseria.dump(value)}"
        )

    assert result is not None

    return result


@ensure(
    lambda result: len(result.parts) > 0
    and result.parts[0] == "Json"
    and result.parts[-1].endswith(".json")
)
@ensure(lambda result: not result.is_absolute())
def _determine_relative_path(
    case: casing.CaseUnion, symbol_table: intermediate.SymbolTable
) -> pathlib.Path:
    """Determine the relative path for a test case."""
    model_type = aas_core_codegen.naming.json_model_type(
        aas_core_codegen.common.Identifier(case.instance.class_name)
    )

    if isinstance(case, casing.PositiveCase):
        if isinstance(case, casing.CaseMinimal):
            case_path_component = pathlib.Path("minimal.json")
        elif isinstance(case, casing.CaseMaximal):
            case_path_component = pathlib.Path("maximal.json")
        elif isinstance(case, casing.CasePositivePatternExample):
            json_prop_name = names.json_property(
                symbol_table, case.instance.class_name, case.property_name
            )

            case_path_component = (
                pathlib.Path(f"{json_prop_name}OverPatternExamples")
                / f"{case.example_name}.json"
            )
        elif isinstance(case, casing.CasePositiveValueExample):
            json_prop_name = names.json_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            case_path_component = (
                pathlib.Path(f"{json_prop_name}OverValueExamples")
                / f"{case.value_type_name}_{case.example_name}.json"
            )
        elif isinstance(case, casing.CasePositiveRangeExample):
            case_path_component = (
                pathlib.Path("overMinMaxExamples")
                / f"{case.value_type_name}_{case.example_name}.json"
            )
        elif isinstance(case, casing.CasePositiveManual):
            case_path_component = pathlib.Path(f"{case.name}.json")
        else:
            # noinspection PyTypeChecker
            assert_never(case)

        return pathlib.Path("Json") / "Expected" / model_type / case_path_component

    elif isinstance(case, NegativeCase):
        if isinstance(case, casing.CaseTypeViolation):
            json_prop_name = names.json_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Json")
                / "Unexpected"
                / "Unserializable"
                / "TypeViolation"
                / model_type
                / f"{json_prop_name}.json"
            )

        elif isinstance(case, casing.CaseRequiredViolation):
            # NOTE (mristin):
            # If you change this part, make sure you also update
            # _make_null_violation_out_of_required_violation.

            json_prop_name = names.json_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Json")
                / "Unexpected"
                / "Unserializable"
                / "RequiredViolation"
                / model_type
                / f"{json_prop_name}.json"
            )

        elif isinstance(case, casing.CaseUnexpectedAdditionalProperty):
            return (
                pathlib.Path("Json")
                / "Unexpected"
                / "Unserializable"
                / "UnexpectedAdditionalProperty"
                / model_type
                / "instance.json"
            )

        elif isinstance(case, casing.CaseEnumerationViolation):
            json_prop_name = names.json_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Json")
                / "Unexpected"
                / "Unserializable"
                / "EnumerationViolation"
                / model_type
                / f"{json_prop_name}.json"
            )

        elif isinstance(case, casing.CasePatternViolation):
            json_prop_name = names.json_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Json")
                / "Unexpected"
                / "Invalid"
                / "PatternViolation"
                / model_type
                / json_prop_name
                / f"{case.example_name}.json"
            )

        elif isinstance(case, casing.CaseJsonKeyViolation):
            json_prop_name = names.json_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Json")
                / "Unexpected"
                / "Invalid"
                / "JsonKeyViolation"
                / model_type
                / json_prop_name
                / f"{case.example_name}.json"
            )

        elif isinstance(case, casing.CaseMinLengthViolation):
            json_prop_name = names.json_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Json")
                / "Unexpected"
                / "Invalid"
                / "MinLengthViolation"
                / model_type
                / f"{json_prop_name}.json"
            )

        elif isinstance(case, casing.CaseMaxLengthViolation):
            json_prop_name = names.json_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Json")
                / "Unexpected"
                / "Invalid"
                / "MaxLengthViolation"
                / model_type
                / f"{json_prop_name}.json"
            )

        elif isinstance(case, casing.CaseEnumerationViolation):
            json_prop_name = names.json_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Json")
                / "Unexpected"
                / "Invalid"
                / "EnumerationViolation"
                / model_type
                / f"{json_prop_name}.json"
            )

        elif isinstance(case, casing.CaseSetViolation):
            json_prop_name = names.json_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Json")
                / "Unexpected"
                / "Invalid"
                / "SetViolation"
                / model_type
                / f"{json_prop_name}.json"
            )

        elif isinstance(case, casing.CaseDateTimeUtcViolationOnFebruary29th):
            json_prop_name = names.json_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Json")
                / "Unexpected"
                / "Invalid"
                / "DateTimeUtcViolationOnFebruary29th"
                / model_type
                / f"{json_prop_name}.json"
            )

        elif isinstance(case, casing.CaseInvalidValueExample):
            json_prop_name = names.json_property(
                symbol_table, case.instance.class_name, case.property_name
            )
            return (
                pathlib.Path("Json")
                / "Unexpected"
                / "Invalid"
                / "InvalidValueExample"
                / model_type
                / json_prop_name
                / f"{case.value_type_name}_{case.example_name}.json"
            )

        elif isinstance(case, casing.CaseInvalidRangeExample):
            return (
                pathlib.Path("Json")
                / "Unexpected"
                / "Invalid"
                / "InvalidRangeExample"
                / model_type
                / f"{case.value_type_name}_{case.example_name}.json"
            )

        elif isinstance(case, casing.CaseConstraintViolation):
            return (
                pathlib.Path("Json")
                / "Unexpected"
                / "Invalid"
                / "ConstraintViolation"
                / model_type
                / f"{case.name}.json"
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
    and self.relative_path.parts[0] == "Json"
    and self.relative_path.parts[-1].endswith(".json")
)
# fmt: on
class Output(common.Output):
    """Represent the test case serialized in JSON."""

    # fmt: off
    @require(
        lambda relative_path:
        len(relative_path.parts) > 0
        and relative_path.parts[0] == "Json"
        and relative_path.parts[-1].endswith(".json")
    )
    @require(lambda relative_path: not relative_path.is_absolute())
    # fmt: on
    def __init__(self, relative_path: pathlib.Path, text: str) -> None:
        super().__init__(relative_path=relative_path, text=text)


def _make_null_violation_out_of_required_violation(
    case: casing.CaseRequiredViolation,
    symbol_table: intermediate.SymbolTable,
) -> Output:
    """Adapt the required violation by setting the property to None."""
    prop_name = case.property_name

    assert prop_name not in case.instance.properties, (
        "The original instance is expected to violated "
        f"the required property constraint of {case.instance.class_name!r} class, "
        f"but the property {prop_name!r} was set."
    )

    jsonable, serialization_error = serialize(
        value=case.instance, symbol_table=symbol_table
    )
    if serialization_error is not None:
        raise AssertionError(
            f"Failed to serialize instance to JSON: {serialization_error}; "
            f"the instance was:\n{preseria.dump(case.instance)}"
        )

    assert isinstance(jsonable, collections.abc.MutableMapping), (
        f"Expected the JSON representation of an instance to be a mutable mapping, "
        f"but got: {jsonable}"
    )

    json_prop_name = names.json_property(
        symbol_table, case.instance.class_name, prop_name
    )
    jsonable[json_prop_name] = None

    text = json.dumps(jsonable, indent=2)

    model_type = aas_core_codegen.naming.json_model_type(
        aas_core_codegen.common.Identifier(case.instance.class_name)
    )
    relative_path = (
        pathlib.Path("Json")
        / "Unexpected"
        / "Unserializable"
        / "NullViolation"
        / model_type
        / f"{json_prop_name}.json"
    )

    return Output(relative_path=relative_path, text=text)


# fmt: off
@require(
    lambda case, symbol_table:
    symbol_table
    .must_find_concrete_class(case.instance.class_name)
    .serialization
    .with_model_type
)
# fmt: on
def _make_missing_model_type_out_of_minimal(
    case: casing.CaseMinimal,
    symbol_table: intermediate.SymbolTable,
) -> Output:
    """Adapt the minimal case by removing the model type in the serialization."""
    jsonable, serialization_error = serialize(
        value=case.instance, symbol_table=symbol_table
    )
    if serialization_error is not None:
        raise AssertionError(
            f"Failed to serialize instance to JSON: {serialization_error}; "
            f"the instance was:\n{preseria.dump(case.instance)}"
        )

    assert isinstance(
        jsonable, collections.abc.MutableMapping
    ), f"Expected instance to be mapped to a mapping, but got: {jsonable}"

    assert "modelType" in jsonable
    del jsonable["modelType"]

    text = json.dumps(jsonable, indent=2)

    model_type = aas_core_codegen.naming.json_model_type(
        aas_core_codegen.common.Identifier(case.instance.class_name)
    )

    relative_path = (
        pathlib.Path("Json")
        / "Unexpected"
        / "Unserializable"
        / "MissingModelType"
        / model_type
        / "wrong.json"
    )

    return Output(relative_path=relative_path, text=text)


# fmt: off
@require(
    lambda case, symbol_table:
    symbol_table
    .must_find_concrete_class(case.instance.class_name)
    .serialization
    .with_model_type
)
# fmt: on
def _make_invalid_model_type_out_of_minimal(
    case: casing.CaseMinimal,
    symbol_table: intermediate.SymbolTable,
) -> Output:
    """Adapt the minimal case by invalidating the model type in the serialization."""
    jsonable, serialization_error = serialize(
        value=case.instance, symbol_table=symbol_table
    )
    if serialization_error is not None:
        raise AssertionError(
            f"Failed to serialize instance to JSON: {serialization_error}; "
            f"the instance was:\n{preseria.dump(case.instance)}"
        )

    assert isinstance(
        jsonable, collections.abc.MutableMapping
    ), f"Expected instance to be mapped to a mapping, but got: {jsonable}"

    assert "modelType" in jsonable
    jsonable["modelType"] = "soReallyUtterlyInvalid"

    text = json.dumps(jsonable, indent=2)

    model_type = aas_core_codegen.naming.json_model_type(
        aas_core_codegen.common.Identifier(case.instance.class_name)
    )

    relative_path = (
        pathlib.Path("Json")
        / "Unexpected"
        / "Unserializable"
        / "InvalidModelType"
        / model_type
        / "wrong.json"
    )

    return Output(relative_path=relative_path, text=text)


def generate_test_data(case_generator: generation.CaseGenerator) -> Iterator[Output]:
    """
    Generate the test cases.

    This will produce all the test cases produced by the test generator, but
    will also include some additional JSON-specific test cases.
    """
    relative_path_asserter = seria.RelativePathAsserter()

    for case in case_generator.generate():
        relative_path = _determine_relative_path(case, case_generator.symbol_table)

        relative_path_asserter.assert_and_add(relative_path)

        jsonable, serialization_error = serialize(
            value=case.instance, symbol_table=case_generator.symbol_table
        )
        if serialization_error is not None:
            raise AssertionError(
                f"Failed to serialize instance to JSON: {serialization_error}; "
                f"the instance was:\n{preseria.dump(case.instance)}"
            )

        text = json.dumps(jsonable, indent=2)

        yield Output(relative_path=relative_path, text=text)

        # NOTE (mristin):
        # We delete it here to avoid bugs with the code below as we do not want to
        # introduce a separate methods to avoid unnecessary complexity.
        del relative_path
        del jsonable
        del text

        if isinstance(case, casing.CaseRequiredViolation):
            output = _make_null_violation_out_of_required_violation(
                case=case, symbol_table=case_generator.symbol_table
            )

            relative_path_asserter.assert_and_add(output.relative_path)

            yield output

        elif isinstance(case, casing.CaseMinimal):
            if case_generator.symbol_table.must_find_concrete_class(
                case.instance.class_name
            ).serialization.with_model_type:
                output = _make_missing_model_type_out_of_minimal(
                    case=case, symbol_table=case_generator.symbol_table
                )

                relative_path_asserter.assert_and_add(output.relative_path)

                yield output

                output = _make_invalid_model_type_out_of_minimal(
                    case=case, symbol_table=case_generator.symbol_table
                )

                relative_path_asserter.assert_and_add(output.relative_path)

                yield output
        else:
            # NOTE (mristin):
            # In general, we leave the cases as-are, no special treatment for JSON.
            pass
