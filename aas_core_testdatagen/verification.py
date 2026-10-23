"""
Verify that pre-serialized instances conform to the meta-model.

The checks are not exhaustive, but they give us a certain confidence of our results,
even before we run a properly transpiled SDK. This is particularly useful during
the development of aas-core-testdatagen itself.
"""

import re
from typing import (
    Optional,
    List,
    Sequence,
    Union,
    cast,
    Final,
    TypeAlias,
    Mapping,
    MutableMapping,
    Set,
    Type,
)

from aas_core_codegen import intermediate, infer_for_schema
from aas_core_codegen.common import (
    assert_never,
    IDENTIFIER_RE,
    Identifier,
    indent_but_first_line,
)
from icontract import ensure, require

from aas_core_testdatagen import preseria
from aas_core_testdatagen.common import bullet_points
from aas_core_testdatagen.preseria import ImmutableInstance


class PropertyConstraints:
    """Group the constraints by a single property."""

    len_constraint: Final[Optional[infer_for_schema.LenConstraint]]
    patterns: Final[Sequence[str]]
    allowed_values: Final[Optional[Sequence[preseria.PrimitiveValueUnion]]]
    allowed_value_set: Final[Optional[Set[preseria.PrimitiveValueUnion]]]

    # Constraints on the items, if the property is a list of primitives
    item_constraints: Final[Optional["PropertyConstraints"]]

    # fmt: off
    @require(
        lambda allowed_values:
        not (allowed_values is not None)
        or (len(set(allowed_values)) == len(allowed_values))
    )
    # fmt: on
    def __init__(
        self,
        len_constraint: Optional[infer_for_schema.LenConstraint],
        patterns: Sequence[str],
        allowed_values: Optional[Sequence[preseria.PrimitiveValueUnion]],
        item_constraints: Optional["PropertyConstraints"] = None,
    ) -> None:
        self.item_constraints = item_constraints
        self.len_constraint = len_constraint
        self.patterns = patterns
        self.allowed_values = allowed_values
        self.allowed_value_set = (
            set(allowed_values) if allowed_values is not None else None
        )


ReorganizedConstraintsByClass: TypeAlias = Mapping[
    intermediate.ClassUnion, Mapping[intermediate.Property, PropertyConstraints]
]


def _is_class_annotation(type_anno: intermediate.TypeAnnotationUnion) -> bool:
    """Check that the annotation, ignoring optional, refers to a class."""
    type_anno = intermediate.beneath_optional(type_anno)
    return isinstance(type_anno, intermediate.OurTypeAnnotation) and isinstance(
        type_anno.our_type,
        (intermediate.AbstractClass, intermediate.ConcreteClass),
    )


def _constraints_of_annotation(
    type_anno: intermediate.TypeAnnotationExceptOptional,
    constraints_by_value: infer_for_schema.ConstraintsByValue,
    what: str,
) -> PropertyConstraints:
    """Translate the schema constraints of the annotation to property constraints."""
    constraints = constraints_by_value.get(type_anno, None)

    if constraints is None:
        return PropertyConstraints(
            len_constraint=None, patterns=[], allowed_values=None
        )

    allowed_values: Optional[Sequence[preseria.PrimitiveValueUnion]] = None

    is_primitive_type = intermediate.try_primitive_type(type_anno) is not None

    is_enum = isinstance(type_anno, intermediate.OurTypeAnnotation) and isinstance(
        type_anno.our_type, intermediate.Enumeration
    )

    assert not (is_primitive_type and is_enum), (
        f"Unexpected {what} with type annotation {type_anno} where "
        f"it was both matched as primitive type and enumeration."
    )

    if is_primitive_type:
        if constraints.set_of_primitives is not None:
            allowed_values = [
                (
                    bytes(literal.value)
                    if isinstance(literal.value, bytearray)
                    else literal.value
                )
                for literal in constraints.set_of_primitives.literals
            ]

    elif is_enum:
        if constraints.set_of_enumeration_literals is not None:
            allowed_values = [
                literal.value
                for literal in constraints.set_of_enumeration_literals.literals
            ]
        else:
            assert isinstance(type_anno, intermediate.OurTypeAnnotation) and isinstance(
                type_anno.our_type, intermediate.Enumeration
            )

            allowed_values = [literal.value for literal in type_anno.our_type.literals]
    else:
        # NOTE (empwilli):
        # There are no allowed value constraints for non-enums and
        # non-primitives.
        pass

    return PropertyConstraints(
        len_constraint=constraints.len_constraint,
        patterns=(
            [pattern_constraint.pattern for pattern_constraint in constraints.patterns]
            if constraints.patterns is not None
            else []
        ),
        allowed_values=allowed_values,
    )


def reorganize_schema_constraints_by_properties(
    constraints_by_class: Mapping[
        intermediate.ClassUnion, infer_for_schema.ConstraintsByValue
    ],
) -> ReorganizedConstraintsByClass:
    """
    Group the constraints by properties.

    The structure of the aas-core-codegen infer_for_schema module is quite impractical
    for this module since it is a sparse representation of different constraints.
    Instead, we re-organize the constraints by grouping them all by one property and
    transforming them to values that we can directly use in the generation (for example,
    translating enumeration literal objects to strings).
    """
    result: MutableMapping[
        intermediate.ClassUnion,
        MutableMapping[intermediate.Property, PropertyConstraints],
    ] = dict()

    for cls, constraints_by_value in constraints_by_class.items():
        result[cls] = {}

        for prop in cls.properties:
            type_anno = intermediate.beneath_optional(prop.type_annotation)

            item_constraints = None
            if isinstance(
                type_anno, intermediate.ListTypeAnnotation
            ) and not _is_class_annotation(type_anno.items):
                item_constraints = _constraints_of_annotation(
                    type_anno=intermediate.beneath_optional(type_anno.items),
                    constraints_by_value=constraints_by_value,
                    what=f"items of the property {prop.name!r} of class {cls.name!r}",
                )

            property_constraints = _constraints_of_annotation(
                type_anno=type_anno,
                constraints_by_value=constraints_by_value,
                what=f"property {prop.name!r} of class {cls.name!r}",
            )

            result[cls][prop] = PropertyConstraints(
                len_constraint=property_constraints.len_constraint,
                patterns=property_constraints.patterns,
                allowed_values=property_constraints.allowed_values,
                item_constraints=item_constraints,
            )

    return result


class Path:
    """Represent a path in the pre-serialized instance."""

    @property
    def segments(self) -> Sequence[Union[str, int]]:
        """Path segments as property names or list indices"""
        return self._segments

    def __init__(self, segments: Sequence[Union[str, int]]) -> None:
        # NOTE (mristin):
        # The internal users are expected to prepend the segments to the path to avoid
        # unnecessary list copies. The ``segments`` property is only immutable for
        # external users.
        self._segments = list(segments)

    def __str__(self) -> str:
        parts = []  # type: List[str]
        for i, segment in enumerate(self.segments):
            if isinstance(segment, str):
                if i > 0:
                    parts.append(f".{segment}")
                else:
                    parts.append(segment)

            elif isinstance(segment, int):
                parts.append(f"[{segment}]")

            else:
                # noinspection PyTypeChecker
                assert_never(segment)

        return "".join(parts)


class Error:
    """Represent a verification error performed on the pre-serialized instance."""

    def __init__(
        self,
        path: Path,
        message: str,
        underlying_errors: Optional[List["Error"]] = None,
    ) -> None:
        self.path = path
        self.message = message
        self.underlying_errors = (
            underlying_errors if underlying_errors is not None else []
        )

    def __str__(self) -> str:
        if len(self.underlying_errors) > 0:
            underlying_errors_str = bullet_points(
                [str(underlying_error) for underlying_error in self.underlying_errors]
            )
            indent = "  "
            return f"""\
.{self.path}: {self.message}
{indent}{indent_but_first_line(underlying_errors_str, indent)}"""

        return f".{self.path}: {self.message}"

    def __repr__(self) -> str:
        if len(self.underlying_errors) > 0:
            return (
                f"Error(path={self.path}, message={self.message!r}, "
                f"underlying_errors={map(str, self.underlying_errors)})"
            )

        return f"Error(path={self.path}, message={self.message!r})"


class VerifiedInstance(preseria.ImmutableInstance):
    """Mark that the instance has been verified."""


# fmt: off
_PRIMITIVE_TYPE_TO_PYTHON_TYPE: Final[
    Mapping[
        intermediate.PrimitiveType,
        Union[Type[bool], Type[int], Type[float], Type[str], Type[bytes]
        ]
    ]
] = {
    intermediate.PrimitiveType.BOOL: bool,
    intermediate.PrimitiveType.INT: int,
    intermediate.PrimitiveType.FLOAT: float,
    intermediate.PrimitiveType.STR: str,
    intermediate.PrimitiveType.BYTEARRAY: bytes,
}
assert all(
    primitive_type in _PRIMITIVE_TYPE_TO_PYTHON_TYPE
    for primitive_type in intermediate.PrimitiveType
)


# fmt: on


@ensure(lambda result: not (result is not None) or len(result) > 0)
def _check_list_of_primitives(
    value: preseria.ValueUnion,
    item_annotation: intermediate.TypeAnnotationExceptOptional,
    symbol_table: intermediate.SymbolTable,
    constraints_by_class: ReorganizedConstraintsByClass,
) -> Optional[List[Error]]:
    """Check that the value is a list whose items conform to the annotation."""
    if not isinstance(value, preseria.ListOfPrimitives):
        return [
            Error(
                path=Path(segments=[]),
                message=f"Expected a list of primitives, but got {value!r}.",
            )
        ]

    errors = []  # type: List[Error]

    for i, item_value in enumerate(value.values):
        item_errors = _check_value_against_type_annotation(
            value=item_value,
            type_annotation=item_annotation,
            symbol_table=symbol_table,
            constraints_by_class=constraints_by_class,
        )

        if item_errors is not None:
            for item_error in item_errors:
                # noinspection PyProtectedMember
                item_error.path._segments.insert(0, i)

            errors.extend(item_errors)

    return errors if len(errors) > 0 else None


@ensure(lambda result: not (result is not None) or len(result) > 0)
def _check_value_against_type_annotation(
    value: preseria.ValueUnion,
    type_annotation: intermediate.TypeAnnotationExceptOptional,
    symbol_table: intermediate.SymbolTable,
    constraints_by_class: ReorganizedConstraintsByClass,
) -> Optional[List[Error]]:
    """Check that the value conforms to the type annotation."""
    primitive_type = intermediate.try_primitive_type(type_annotation)

    if primitive_type is not None:
        expected_value_type = _PRIMITIVE_TYPE_TO_PYTHON_TYPE[primitive_type]

        if not isinstance(value, expected_value_type):
            return [
                Error(
                    path=Path(segments=[]),
                    message=(
                        f"Expected a primitive value as {expected_value_type}, "
                        f"but got {value!r}."
                    ),
                )
            ]

        return None

    else:
        if isinstance(type_annotation, intermediate.PrimitiveTypeAnnotation):
            raise AssertionError("Expected the primitive type to be handled before")

        elif isinstance(type_annotation, intermediate.OurTypeAnnotation):
            if isinstance(type_annotation.our_type, intermediate.Enumeration):
                if not isinstance(value, str):
                    return [
                        Error(
                            path=Path(segments=[]),
                            message=(
                                f"Expected "
                                f"the enumeration {type_annotation.our_type.name!r} "
                                f"represented as  a str, but got {value!r}."
                            ),
                        )
                    ]

                if value not in type_annotation.our_type.literal_value_set:
                    return [
                        Error(
                            path=Path(segments=[]),
                            message=(
                                f"Expected a valid literal of "
                                f"the enumeration {type_annotation.our_type.name!r}, "
                                f"but got {value!r}."
                            ),
                        )
                    ]

            elif isinstance(
                type_annotation.our_type, intermediate.ConstrainedPrimitive
            ):
                raise AssertionError("Expected the primitive type to be handled before")

            elif isinstance(
                type_annotation.our_type,
                (intermediate.AbstractClass, intermediate.ConcreteClass),
            ):
                if not isinstance(value, preseria.Instance):
                    return [
                        Error(
                            path=Path(segments=[]),
                            message=(
                                f"Expected a pre-serialized instance "
                                f"of class {type_annotation.our_type.name!r}, "
                                f"but got {value!r}."
                            ),
                        )
                    ]

                cls = symbol_table.find_our_type(value.class_name)
                if cls is None:
                    return [
                        Error(
                            path=Path(segments=[]),
                            message=(
                                f"Expected a pre-serialized instance "
                                f"of class {type_annotation.our_type.name!r}, "
                                f"but got an instance of {value.class_name!r} "
                                f"which could not be found in the symbol table."
                            ),
                        )
                    ]

                elif not isinstance(cls, intermediate.ConcreteClass):
                    return [
                        Error(
                            path=Path(segments=[]),
                            message=(
                                f"Expected a pre-serialized instance "
                                f"of class {type_annotation.our_type.name!r} "
                                f"but got an instance of {value.class_name!r} "
                                f"which is, according to the symbol table, not "
                                f"a concrete class, but: {cls}."
                            ),
                        )
                    ]
                else:
                    pass

                if not cls.is_subclass_of(type_annotation.our_type):
                    return [
                        Error(
                            path=Path(segments=[]),
                            message=(
                                f"Expected a pre-serialized instance "
                                f"of class {type_annotation.our_type.name!r}, "
                                f"but got an instance of {value.class_name!r} "
                                f"which is not the sub-class "
                                f"of {type_annotation.our_type.name!r}."
                            ),
                        )
                    ]

                structural_errors = check_structural_constraints(
                    instance=value,
                    symbol_table=symbol_table,
                    constraints_by_class=constraints_by_class,
                )

                if structural_errors is not None:
                    return structural_errors

            elif isinstance(type_annotation.our_type, intermediate.NamedUnion):
                union = type_annotation.our_type

                if not isinstance(value, preseria.Instance):
                    return [
                        Error(
                            path=Path(segments=[]),
                            message=(
                                f"Expected a pre-serialized instance "
                                f"of the union {union.name!r}, but got {value!r}."
                            ),
                        )
                    ]

                # NOTE: The implementers are the flattened concrete members.
                if value.class_name not in {
                    implementer.name for implementer in union.implementers
                }:
                    return [
                        Error(
                            path=Path(segments=[]),
                            message=(
                                f"Expected a pre-serialized instance of a member "
                                f"of the union {union.name!r}, "
                                f"but got an instance of {value.class_name!r}."
                            ),
                        )
                    ]

                structural_errors = check_structural_constraints(
                    instance=value,
                    symbol_table=symbol_table,
                    constraints_by_class=constraints_by_class,
                )

                if structural_errors is not None:
                    return structural_errors

            else:
                # noinspection PyTypeChecker
                assert_never(type_annotation.our_type)

        elif isinstance(type_annotation, intermediate.ListTypeAnnotation):
            item_annotation = intermediate.beneath_optional(type_annotation.items)
            if not (
                isinstance(item_annotation, intermediate.OurTypeAnnotation)
                and isinstance(
                    item_annotation.our_type,
                    (intermediate.AbstractClass, intermediate.ConcreteClass),
                )
            ):
                return _check_list_of_primitives(
                    value=value,
                    item_annotation=item_annotation,
                    symbol_table=symbol_table,
                    constraints_by_class=constraints_by_class,
                )

            assert isinstance(
                type_annotation.items, intermediate.OurTypeAnnotation
            ) and isinstance(
                type_annotation.items.our_type,
                (intermediate.AbstractClass, intermediate.ConcreteClass),
            ), (
                f"NOTE (mristin): We expect only lists of classes "
                f"at the moment, but got {type_annotation}. "
                f"Please contact the developers if you need this feature."
            )

            if not isinstance(value, preseria.ListOfInstances):
                return [
                    Error(
                        path=Path(segments=[]),
                        message=f"Expected a list of instances, but got {value!r}.",
                    )
                ]

            errors = []  # type: List[Error]

            for i, item in enumerate(value.values):
                item_errors = check_structural_constraints(
                    instance=item,
                    symbol_table=symbol_table,
                    constraints_by_class=constraints_by_class,
                )

                if item_errors is not None:
                    for item_error in item_errors:
                        # noinspection PyProtectedMember
                        item_error.path._segments.insert(0, i)

                    errors.extend(item_errors)

            if len(errors) > 0:
                return errors

        elif isinstance(type_annotation, intermediate.TupleTypeAnnotation):
            if not isinstance(value, preseria.TupleOfValues):
                return [
                    Error(
                        path=Path(segments=[]),
                        message=f"Expected a tuple of values, but got {value!r}.",
                    )
                ]

            if len(value.values) != len(type_annotation.items):
                return [
                    Error(
                        path=Path(segments=[]),
                        message=(
                            f"Expected a tuple of {len(type_annotation.items)} "
                            f"item(s), but got {len(value.values)}: {value!r}."
                        ),
                    )
                ]

            errors = []

            for i, (item_value, item_annotation) in enumerate(
                zip(value.values, type_annotation.items)
            ):
                item_errors = _check_value_against_type_annotation(
                    value=item_value,
                    type_annotation=intermediate.beneath_optional(item_annotation),
                    symbol_table=symbol_table,
                    constraints_by_class=constraints_by_class,
                )

                if item_errors is not None:
                    for item_error in item_errors:
                        # noinspection PyProtectedMember
                        item_error.path._segments.insert(0, i)

                    errors.extend(item_errors)

            if len(errors) > 0:
                return errors

        elif isinstance(type_annotation, intermediate.SetTypeAnnotation):
            if not isinstance(value, preseria.SetOfPrimitives):
                return [
                    Error(
                        path=Path(segments=[]),
                        message=f"Expected a set of primitives, but got {value!r}.",
                    )
                ]

            errors = []

            item_annotation = intermediate.beneath_optional(type_annotation.items)

            for i, item_value in enumerate(value.values):
                item_errors = _check_value_against_type_annotation(
                    value=item_value,
                    type_annotation=item_annotation,
                    symbol_table=symbol_table,
                    constraints_by_class=constraints_by_class,
                )

                if item_errors is not None:
                    for item_error in item_errors:
                        # noinspection PyProtectedMember
                        item_error.path._segments.insert(0, i)

                    errors.extend(item_errors)

            if len(errors) == 0 and len(set(value.values)) != len(value.values):
                errors.append(
                    Error(
                        path=Path(segments=[]),
                        message=f"Expected unique set items, but got {value!r}.",
                    )
                )

            if len(errors) > 0:
                return errors

        elif isinstance(
            type_annotation,
            (
                intermediate.JsonValueTypeAnnotation,
                intermediate.JsonArrayTypeAnnotation,
                intermediate.JsonObjectTypeAnnotation,
            ),
        ):
            # NOTE: Only raising for now; revisit once the extended meta-model
            # uses the JSON-able types in serializable properties.
            raise NotImplementedError(
                f"Verification against the JSON-able type annotation "
                f"{type_annotation} is not supported yet."
            )

        else:
            # noinspection PyTypeChecker
            assert_never(type_annotation)

    return None


def _check_items_against_constraints(
    property_name: str,
    class_name: str,
    items: Sequence[preseria.PrimitiveValueUnion],
    constraints: PropertyConstraints,
) -> List[Error]:
    """Check the items of a list of primitives against the item constraints."""
    errors = []  # type: List[Error]

    for i, item in enumerate(items):
        problems = []  # type: List[str]

        if constraints.len_constraint is not None and isinstance(item, (str, bytes)):
            if (
                constraints.len_constraint.min_value is not None
                and len(item) < constraints.len_constraint.min_value
            ):
                problems.append(
                    f"its length {len(item)} is shorter than "
                    f"{constraints.len_constraint.min_value}"
                )

            if (
                constraints.len_constraint.max_value is not None
                and len(item) > constraints.len_constraint.max_value
            ):
                problems.append(
                    f"its length {len(item)} is longer than "
                    f"{constraints.len_constraint.max_value}"
                )

        if isinstance(item, str):
            for pattern in constraints.patterns:
                if re.fullmatch(pattern, item) is None:
                    problems.append(f"it does not match the pattern {pattern!r}")

        if (
            constraints.allowed_value_set is not None
            and item not in constraints.allowed_value_set
        ):
            problems.append("it is not in the set of allowed values")

        for problem in problems:
            errors.append(
                Error(
                    path=Path(segments=[property_name, i]),
                    message=(
                        f"Item {i} of the property {property_name!r} "
                        f"of class {class_name}, {item!r}, is invalid: {problem}."
                    ),
                )
            )

    return errors


@ensure(lambda result: not (result is not None) or len(result) > 0)
def check_structural_constraints(
    instance: preseria.Instance,
    symbol_table: intermediate.SymbolTable,
    constraints_by_class: ReorganizedConstraintsByClass,
) -> Optional[List[Error]]:
    """
    Check that the structure of the instance conforms to the symbol table.

    Return verified instance or errors, if any.
    """

    errors = []  # type: List[Error]

    cls = symbol_table.find_our_type(instance.class_name)
    if cls is None:
        return [
            Error(
                path=Path(segments=[]),
                message=(
                    f"The class of the pre-serialized instance could not be "
                    f"found in the symbol table: {instance.class_name!r}."
                ),
            )
        ]

    elif not isinstance(cls, intermediate.ConcreteClass):
        return [
            Error(
                path=Path(segments=[]),
                message=(
                    f"Expected a pre-serialized instance to be of a concrete class, "
                    f"but got an instance of {instance.class_name!r} "
                    f"which is, according to the symbol table, not "
                    f"a concrete class, but: {cls}."
                ),
            )
        ]
    else:
        pass

    # NOTE (mristin):
    # We check first for missing mandatory properties.
    for prop in cls.properties:
        if isinstance(prop.type_annotation, intermediate.OptionalTypeAnnotation):
            continue

        if prop.name not in instance.properties:
            errors.append(
                Error(
                    Path(segments=[]),
                    f"Property {prop.name!r} is mandatory "
                    f"for class {cls.name!r}, but it is missing.",
                )
            )
            continue

    # NOTE (mristin):
    # We then check the structural constraints.

    constraints_by_prop = constraints_by_class[cls]

    for prop_name, prop_value in instance.properties.items():
        if IDENTIFIER_RE.match(prop_name) is None:
            errors.append(
                Error(
                    Path(segments=[]),
                    f"Property {prop_name!r} is not a valid identifier "
                    f"for class {cls.name!r}.",
                )
            )
            continue

        maybe_prop = cls.properties_by_name.get(Identifier(prop_name), None)

        if maybe_prop is None:
            errors.append(
                Error(
                    Path(segments=[]),
                    f"Property {prop_name!r} is not defined "
                    f"for class {cls.name!r}.",
                )
            )
            continue

        prop = maybe_prop

        # NOTE (mristin):
        # We accept here None as value for optional properties. The serialization
        # is not stable across different meta-model versions on this question, so we
        # simply accept None, leaving this as the responsibility for the client code
        # to deal with the edge cases properly.
        if prop_value is None:
            if not isinstance(
                prop.type_annotation, intermediate.OptionalTypeAnnotation
            ):
                errors.append(
                    Error(
                        Path(segments=[]),
                        f"Property {prop_name!r} is required, but it is None "
                        f"for class {cls.name!r}.",
                    )
                )

            continue

        type_anno = intermediate.beneath_optional(prop.type_annotation)

        type_errors = _check_value_against_type_annotation(
            value=prop_value,
            type_annotation=type_anno,
            symbol_table=symbol_table,
            constraints_by_class=constraints_by_class,
        )
        if type_errors is not None:
            for type_error in type_errors:
                # noinspection PyProtectedMember
                type_error.path._segments = [prop.name] + type_error.path._segments

            errors.append(
                Error(
                    path=Path(segments=[prop.name]),
                    message=(
                        f"Value of the property {prop.name!r} of class {cls.name!r} "
                        f"does not conform to type annotation {prop.type_annotation}."
                    ),
                    underlying_errors=type_errors,
                )
            )
            continue

        prop_constraints = constraints_by_prop[prop]

        if prop_constraints.item_constraints is not None and isinstance(
            prop_value, preseria.ListOfPrimitives
        ):
            errors.extend(
                _check_items_against_constraints(
                    property_name=prop.name,
                    class_name=cls.name,
                    items=prop_value.values,
                    constraints=prop_constraints.item_constraints,
                )
            )

        if prop_constraints.len_constraint is not None:
            if isinstance(
                prop_value,
                (
                    str,
                    bytes,
                    preseria.ListOfInstances,
                    preseria.SetOfPrimitives,
                    preseria.ListOfPrimitives,
                ),
            ):
                length: int
                if isinstance(prop_value, (str, bytes)):
                    length = len(prop_value)
                elif isinstance(
                    prop_value,
                    (
                        preseria.ListOfInstances,
                        preseria.SetOfPrimitives,
                        preseria.ListOfPrimitives,
                    ),
                ):
                    length = len(prop_value.values)
                else:
                    # noinspection PyTypeChecker
                    assert_never(prop_value)

                if (
                    prop_constraints.len_constraint.min_value is not None
                    and length < prop_constraints.len_constraint.min_value
                ):
                    errors.append(
                        Error(
                            path=Path(segments=[prop.name]),
                            message=(
                                f"Value of the property {prop.name!r} "
                                f"of class {cls.name!r} is too short -- min. length "
                                f"is {prop_constraints.len_constraint.min_value}, "
                                f"but got {length}: {prop_value!r}"
                            ),
                        )
                    )

                if (
                    prop_constraints.len_constraint.max_value is not None
                    and length > prop_constraints.len_constraint.max_value
                ):
                    errors.append(
                        Error(
                            path=Path(segments=[prop.name]),
                            message=(
                                f"Value of the property {prop.name!r} "
                                f"of class {cls.name!r} is too long -- max. length "
                                f"is {prop_constraints.len_constraint.max_value}, "
                                f"but got {length}: {prop_value!r}"
                            ),
                        )
                    )

            else:
                raise AssertionError(
                    f"Unapplicable length constraints on property {prop.name!r} "
                    f"of class {cls.name!r} with value {prop_value!r}"
                )

            if isinstance(prop_value, str):
                for pattern in prop_constraints.patterns:
                    if re.fullmatch(pattern, prop_value) is None:
                        errors.append(
                            Error(
                                path=Path(segments=[prop.name]),
                                message=(
                                    f"Value of the property {prop.name!r} "
                                    f"of class {cls.name}, {prop_value!r}, "
                                    f"does not match the expected pattern {pattern!r}."
                                ),
                            )
                        )

            if prop_constraints.allowed_values is not None:
                assert prop_constraints.allowed_value_set is not None

                if isinstance(prop_value, (bool, int, float, str, bytes)):
                    if prop_value not in prop_constraints.allowed_value_set:
                        errors.append(
                            Error(
                                path=Path(segments=[prop.name]),
                                message=(
                                    f"Value of the property {prop.name!r} "
                                    f"of class {cls.name}, {prop_value!r}, "
                                    f"is not in the set of allowed values "
                                    f"{prop_constraints.allowed_values!r}."
                                ),
                            )
                        )
                elif isinstance(
                    prop_value,
                    (
                        preseria.ListOfInstances,
                        preseria.TupleOfValues,
                        preseria.SetOfPrimitives,
                        preseria.ListOfPrimitives,
                    ),
                ):
                    continue

                else:
                    # noinspection PyTypeChecker
                    assert_never(prop_value)

    if len(errors) > 0:
        return errors

    return None


class Verificator:
    """Verify that instances comply with the meta-model."""

    symbol_table: Final[intermediate.SymbolTable]
    constraints_by_class: Final[ReorganizedConstraintsByClass]

    def __init__(
        self,
        symbol_table: intermediate.SymbolTable,
        constraints_by_class: ReorganizedConstraintsByClass,
    ) -> None:
        self.symbol_table = symbol_table
        self.constraints_by_class = constraints_by_class

    def must(self, instance: preseria.Instance) -> VerifiedInstance:
        """
        Establish that the instance is valid according to the symbol table.

        If there are verification errors, an ``AssertionError`` is raised.
        """
        errors = check_structural_constraints(
            instance=instance,
            symbol_table=self.symbol_table,
            constraints_by_class=self.constraints_by_class,
        )

        if errors is not None:
            errors_str = bullet_points(map(str, errors))
            raise AssertionError(
                f"""\
Invalid instance:
{errors_str}"""
            )

        return cast(VerifiedInstance, cast(ImmutableInstance, instance))
