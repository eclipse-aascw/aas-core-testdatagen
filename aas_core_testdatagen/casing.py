"""Structure the test cases."""

import inspect
import sys
from typing import Union, Final, TypeAlias, get_args

from aas_core_codegen.common import Identifier
from icontract import DBC

from aas_core_testdatagen import preseria, verification
from aas_core_testdatagen.common import Filenameable


class Case(DBC):
    """Represent an abstract test case."""

    instance: Final[preseria.ImmutableInstance]
    expected: Final[bool]

    def __init__(self, instance: preseria.ImmutableInstance, expected: bool) -> None:
        """Initialize with the given values."""
        self.instance = instance
        self.expected = expected


class PositiveCase(Case):
    """Represent an expected case."""

    def __init__(self, instance: preseria.ImmutableInstance) -> None:
        super().__init__(instance=instance, expected=True)


class NegativeCase(Case):
    """Represent an unexpected case."""

    def __init__(self, instance: preseria.ImmutableInstance) -> None:
        super().__init__(instance=instance, expected=False)


class CaseMinimal(PositiveCase):
    """Represent a minimal test case."""

    def __init__(
        self,
        instance: verification.VerifiedInstance,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)


class CaseMaximal(PositiveCase):
    """Represent a maximal test case."""

    def __init__(
        self,
        instance: verification.VerifiedInstance,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)


class CaseTypeViolation(NegativeCase):
    """Represent a test case where a property has invalid type."""

    property_name: Final[Identifier]

    def __init__(
        self,
        instance: preseria.ImmutableInstance,
        property_name: Identifier,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.property_name = property_name


class CasePositivePatternExample(PositiveCase):
    """Represent a test case with a property set to a pattern example."""

    property_name: Final[Identifier]
    example_name: Final[Filenameable]

    def __init__(
        self,
        instance: verification.VerifiedInstance,
        property_name: Identifier,
        example_name: Filenameable,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.property_name = property_name
        self.example_name = example_name


class CasePatternViolation(NegativeCase):
    """Represent a test case with a property set to a pattern example."""

    property_name: Final[Identifier]
    example_name: Final[Filenameable]

    def __init__(
        self,
        instance: preseria.ImmutableInstance,
        property_name: Identifier,
        example_name: Filenameable,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.property_name = property_name
        self.example_name = example_name


class CaseJsonKeyViolation(NegativeCase):
    """Represent a test case where a key of a JSON object violates its constraints."""

    property_name: Final[Identifier]
    example_name: Final[Filenameable]

    def __init__(
        self,
        instance: preseria.ImmutableInstance,
        property_name: Identifier,
        example_name: Filenameable,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.property_name = property_name
        self.example_name = example_name


class CaseRequiredViolation(NegativeCase):
    """Represent a test case where a required property is missing."""

    property_name: Final[Identifier]

    def __init__(
        self,
        instance: preseria.ImmutableInstance,
        property_name: Identifier,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.property_name = property_name


class CaseMinLengthViolation(NegativeCase):
    """Represent a test case where a min. len constraint is violated."""

    property_name: Final[Identifier]

    def __init__(
        self,
        instance: preseria.ImmutableInstance,
        property_name: Identifier,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.property_name = property_name


class CaseMaxLengthViolation(NegativeCase):
    """Represent a test case where a max. len constraint is violated."""

    property_name: Final[Identifier]

    def __init__(
        self,
        instance: preseria.ImmutableInstance,
        property_name: Identifier,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.property_name = property_name


class CaseUnexpectedAdditionalProperty(NegativeCase):
    """Represent a test case where there is an unexpected property in the instance."""

    def __init__(
        self,
        instance: preseria.ImmutableInstance,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)


class CaseEnumerationViolation(NegativeCase):
    """Represent a case where a property is outside a set of enumeration literals."""

    property_name: Final[Identifier]

    def __init__(
        self,
        instance: preseria.ImmutableInstance,
        property_name: Identifier,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.property_name = property_name


class CaseSetViolation(NegativeCase):
    """Represent a case where a property is outside a set of allowed values."""

    property_name: Final[Identifier]

    def __init__(
        self,
        instance: preseria.ImmutableInstance,
        property_name: Identifier,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.property_name = property_name


class CaseDateTimeUtcViolationOnFebruary29th(NegativeCase):
    """Represent a test case where we supply an invalid UTC date time stamp."""

    property_name: Final[Identifier]

    def __init__(
        self,
        instance: preseria.ImmutableInstance,
        property_name: Identifier,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.property_name = property_name


class CasePositiveValueExample(PositiveCase):
    """Represent a test case with a XSD value set to a positive example."""

    property_name: Final[Identifier]
    example_name: Final[Filenameable]

    def __init__(
        self,
        instance: verification.VerifiedInstance,
        property_name: Identifier,
        example_name: Filenameable,
        value_type_name: Identifier,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.property_name = property_name
        self.example_name = example_name
        self.value_type_name = value_type_name


class CaseInvalidValueExample(NegativeCase):
    """Represent a test case with a XSD value set to a negative example."""

    property_name: Final[Identifier]
    example_name: Final[Filenameable]

    def __init__(
        self,
        instance: preseria.ImmutableInstance,
        property_name: Identifier,
        example_name: Filenameable,
        value_type_name: Identifier,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.property_name = property_name
        self.example_name = example_name
        self.value_type_name = value_type_name


class CasePositiveRangeExample(PositiveCase):
    """Represent a test case with a min/max XSD values set to a positive example."""

    example_name: Final[Filenameable]

    def __init__(
        self,
        instance: verification.VerifiedInstance,
        example_name: Filenameable,
        value_type_name: Identifier,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.example_name = example_name
        self.value_type_name = value_type_name


class CaseInvalidRangeExample(NegativeCase):
    """Represent a test case with a min/max XSD values set to a negative example."""

    example_name: Final[Filenameable]

    def __init__(
        self,
        instance: preseria.ImmutableInstance,
        value_type_name: Identifier,
        example_name: Filenameable,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.value_type_name = value_type_name
        self.example_name = example_name


class CasePositiveManual(PositiveCase):
    """Represent a custom-tailored positive case."""

    name: Final[Filenameable]

    def __init__(
        self,
        instance: verification.VerifiedInstance,
        name: Filenameable,
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.name = name


class CaseConstraintViolation(NegativeCase):
    """Represent a custom-tailored negative case that violates a constraint."""

    name: Final[Filenameable]

    def __init__(
        self, instance: preseria.ImmutableInstance, name: Filenameable
    ) -> None:
        """Initialize with the given values."""
        super().__init__(instance=instance)
        self.name = name


CaseUnion: TypeAlias = Union[
    CaseMinimal,
    CaseMaximal,
    CaseTypeViolation,
    CasePositivePatternExample,
    CasePatternViolation,
    CaseJsonKeyViolation,
    CaseRequiredViolation,
    CaseMinLengthViolation,
    CaseMaxLengthViolation,
    CaseUnexpectedAdditionalProperty,
    CaseEnumerationViolation,
    CaseSetViolation,
    CaseDateTimeUtcViolationOnFebruary29th,
    CasePositiveValueExample,
    CaseInvalidValueExample,
    CasePositiveRangeExample,
    CaseInvalidRangeExample,
    CasePositiveManual,
    CaseConstraintViolation,
]


def _assert_all_case_classes_listed_in_case_union() -> None:
    """Assert that all Case classes are included in CaseUnion."""
    current_module = sys.modules[__name__]

    case_classes = set()
    for _, obj in inspect.getmembers(current_module, inspect.isclass):
        if (
            obj is not Case
            and obj is not PositiveCase
            and obj is not NegativeCase
            and issubclass(obj, Case)
            and obj.__module__ == __name__
        ):
            case_classes.add(obj)

    union_classes = set(get_args(CaseUnion))

    missing_classes = case_classes - union_classes
    extra_classes = union_classes - case_classes

    if missing_classes:
        missing_names = [cls.__name__ for cls in missing_classes]
        raise AssertionError(f"Case classes not listed in CaseUnion: {missing_names}")

    if extra_classes:
        extra_names = [cls.__name__ for cls in extra_classes]
        raise AssertionError(
            f"Classes in CaseUnion that are not Case classes: {extra_names}"
        )


_assert_all_case_classes_listed_in_case_union()
