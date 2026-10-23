"""Prepare the instances for further modification before the final serialization."""

import abc
import collections
import copy
import json
from typing import (
    Any,
    get_args,
    List,
    Mapping,
    MutableMapping,
    OrderedDict,
    Sequence,
    Union,
)

from aas_core_codegen.common import Identifier, assert_never, IDENTIFIER_RE
from typing_extensions import override

PrimitiveValueUnion = Union[bool, int, float, str, bytes]


PrimitiveValueTuple = (bool, int, float, str, bytes)
assert PrimitiveValueTuple == get_args(PrimitiveValueUnion)


ValueUnion = Union[
    PrimitiveValueUnion,
    "Instance",
    "ListOfInstances",
    "TupleOfValues",
    "SetOfPrimitives",
]


ImmutableValueUnion = Union[
    PrimitiveValueUnion,
    "ImmutableInstance",
    "SequenceOfImmutableInstances",
    "TupleOfImmutableValues",
    "SetOfImmutablePrimitives",
]


class ImmutableInstance(abc.ABC):
    """Represent an immutable instance of a class."""

    @property
    @abc.abstractmethod
    def properties(self) -> Mapping[Identifier, ImmutableValueUnion]:
        """
        Pre-serialized properties of the instance.

        Since the serialization needs to cover formats such as XML, where None is not
        defined, all the property values must be non-None.
        """
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def class_name(self) -> Identifier:
        """Class name according to the meta-model format, *not* as a Python class."""
        raise NotImplementedError()

    @abc.abstractmethod
    def mutable_copy(self) -> "Instance":
        """Make a mutable copy of this immutable instance."""
        raise NotImplementedError()


class SequenceOfImmutableInstances(abc.ABC):
    """Represent an immutable sequence of instances."""

    @property
    @abc.abstractmethod
    def values(self) -> Sequence["ImmutableInstance"]:
        """The items of the list."""
        raise NotImplementedError()


class TupleOfImmutableValues(abc.ABC):
    """Represent an immutable, fixed-length tuple of heterogeneous values."""

    @property
    @abc.abstractmethod
    def values(self) -> Sequence["ImmutableValueUnion"]:
        """The items of the tuple."""
        raise NotImplementedError()


class SetOfImmutablePrimitives(abc.ABC):
    """Represent an immutable set of primitive values."""

    @property
    @abc.abstractmethod
    def values(self) -> Sequence[PrimitiveValueUnion]:
        """
        The items of the set.

        We keep them in a sequence, so that test cases can contain duplicates and
        arbitrary order. The serialization sorts the items.
        """
        raise NotImplementedError()


class Instance(ImmutableInstance):
    """Represent an instance of a class."""

    def __init__(
        self, properties: OrderedDict[Identifier, ValueUnion], class_name: Identifier
    ) -> None:
        """
        Initialize with the given values.

        The ``class_name`` needs to be always indicated. It is written in meta-model
        format, *not* as the Python class name.
        """
        self._properties = properties
        self._class_name = class_name

    @property
    @override
    def properties(self) -> OrderedDict[Identifier, ValueUnion]:
        """
        Pre-serialized properties of the instance.

        Our default pre-serialization is to *omit* properties which are set to ``None``.
        However, there are test cases where we explicitly want to test handling of
        ``null`` JSON values. We leave it therefore open for the downstream client
        to define properties as ``null`` (by setting them to ``None``) even though
        our pre-serializer simply omits them.
        """
        return self._properties

    @properties.setter
    def properties(self, value: OrderedDict[Identifier, ValueUnion]) -> None:
        """Set the properties of the instance."""
        self._properties = value

    def must_str(self, property_name: str) -> str:
        """
        Get the property as string.

        Raise ``KeyError`` if it does not exist or a ``TypeError`` if it is not
        a string.
        """
        if not IDENTIFIER_RE.match(property_name):
            raise KeyError(property_name)

        property_value = self._properties.get(Identifier(property_name), None)
        if property_value is None:
            raise KeyError(property_name)

        if not isinstance(property_value, str):
            raise TypeError(
                f"Expected a str in the property {property_name!r}, "
                f"but got {type(property_value)}"
            )

        return property_value

    def must_instance(self, property_name: str) -> "Instance":
        """
        Get the property as a mutable instance.

        Raise ``KeyError`` if it does not exist or a ``TypeError`` if it is not
        an instance.
        """
        if not IDENTIFIER_RE.match(property_name):
            raise KeyError(property_name)

        property_value = self._properties.get(Identifier(property_name), None)
        if property_value is None:
            raise KeyError(property_name)

        if not isinstance(property_value, Instance):
            raise TypeError(
                f"Expected an instance in the property {property_name!r}, "
                f"but got {type(property_value)}"
            )

        return property_value

    def must_list_of_instances(self, property_name: str) -> "ListOfInstances":
        """
        Get the property as a list of instances.

        Raise ``KeyError`` if it does not exist or a ``TypeError`` if it is not
        a list of instances.
        """
        if not IDENTIFIER_RE.match(property_name):
            raise KeyError(property_name)

        property_value = self._properties.get(Identifier(property_name), None)
        if property_value is None:
            raise KeyError(property_name)

        if not isinstance(property_value, ListOfInstances):
            raise TypeError(
                f"Expected a list of instances in the property {property_name!r}, "
                f"but got {type(property_value)}"
            )

        return property_value

    @property
    @override
    def class_name(self) -> Identifier:
        """Class name according to the meta-model format, *not* as a Python class."""
        return self._class_name

    @class_name.setter
    def class_name(self, value: Identifier) -> None:
        """Set the class name of the instance."""
        self._class_name = value

    @override
    def mutable_copy(self) -> "Instance":
        return copy.deepcopy(self)


class ListOfInstances(SequenceOfImmutableInstances):
    """Represent a list of instances."""

    @property
    @override
    def values(self) -> List[Instance]:
        return self._values

    @values.setter
    def values(self, values: List[Instance]) -> None:
        self._values = values

    def __init__(self, values: List[Instance]) -> None:
        """Initialize with the given values."""
        self._values = values


class TupleOfValues(TupleOfImmutableValues):
    """Represent a tuple of values."""

    @property
    @override
    def values(self) -> List[ValueUnion]:
        return self._values

    @values.setter
    def values(self, values: List[ValueUnion]) -> None:
        self._values = values

    def __init__(self, values: List[ValueUnion]) -> None:
        """Initialize with the given values."""
        self._values = values


class SetOfPrimitives(SetOfImmutablePrimitives):
    """Represent a set of primitive values."""

    @property
    @override
    def values(self) -> List[PrimitiveValueUnion]:
        return self._values

    @values.setter
    def values(self, values: List[PrimitiveValueUnion]) -> None:
        self._values = values

    def __init__(self, values: List[PrimitiveValueUnion]) -> None:
        """Initialize with the given values."""
        self._values = values


def sorted_set_items(
    values: Sequence[PrimitiveValueUnion],
) -> List[PrimitiveValueUnion]:
    """
    Sort the set items as the meta-model mandates for the serialization.

    ``False`` goes before ``True``, integers are sorted numerically, and strings
    by their code points.
    """
    return sorted(values)


def _to_jsonable(value: ImmutableValueUnion) -> Any:
    """
    Represent the ``value`` as a JSON-able object.

    This is meant for debugging, not for the end-user serialization.
    """
    if isinstance(value, PrimitiveValueTuple):
        if isinstance(value, bytes):
            return repr(value)
        else:
            return value
    elif isinstance(value, ImmutableInstance):
        obj = collections.OrderedDict()  # type: MutableMapping[str, Any]
        obj["class_name"] = value.class_name

        properties_dict = collections.OrderedDict()  # type: MutableMapping[str, Any]
        for prop_name, prop_value in value.properties.items():
            properties_dict[prop_name] = _to_jsonable(prop_value)

        obj["properties"] = properties_dict

        return obj
    elif isinstance(value, SequenceOfImmutableInstances):
        return [_to_jsonable(item) for item in value.values]
    elif isinstance(value, TupleOfImmutableValues):
        return [_to_jsonable(item) for item in value.values]
    elif isinstance(value, SetOfImmutablePrimitives):
        return [_to_jsonable(item) for item in value.values]
    else:
        # noinspection PyTypeChecker
        assert_never(value)


def dump(value: ImmutableValueUnion) -> str:
    """
    Represent the ``value`` as a string.

    This is meant for debugging, not for the end-user serialization.
    """
    return json.dumps(_to_jsonable(value), indent=2)


# Automatically generated by dev_scripts/codegen/generate_preserialization.py.
# Do NOT edit or append!
