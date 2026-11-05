# SPDX-FileCopyrightText: 2025 aas-core-testdatagen AUTHORS
#
# SPDX-License-Identifier: MIT

"""Provide common methods for generation of data in different formats."""

import collections.abc
import hashlib
import io
import pathlib
import re
from typing import (
    Tuple,
    Union,
    Protocol,
    TypeVar,
    Optional,
    Sequence,
    cast,
    Iterable,
    Generic,
    overload,
    Final,
    Mapping,
)

from aas_core_codegen.common import indent_but_first_line
import aas_core_codegen.parse
import aas_core_codegen.run
from aas_core_codegen import intermediate, infer_for_schema
from icontract import ensure, require, invariant, DBC
from typing_extensions import assert_never


def load_symbol_table_and_infer_constraints_for_schema(
    model_path: pathlib.Path,
) -> Tuple[
    intermediate.SymbolTable,
    Mapping[intermediate.ClassUnion, infer_for_schema.ConstraintsByValue],
]:
    """
    Load the symbol table from the meta-model and infer the schema constraints.

    These constraints might not be sufficient to generate *some* of the instances.
    Further constraints in form of invariants might apply which are not represented
    in the schema constraints. However, this will help us cover *many* classes of the
    meta-model and spare us the work of manually writing many generators.
    """
    assert model_path.exists() and model_path.is_file(), model_path

    text = model_path.read_text(encoding="utf-8")

    atok, parse_exception = aas_core_codegen.parse.source_to_atok(source=text)
    if parse_exception:
        if isinstance(parse_exception, SyntaxError):
            raise RuntimeError(
                f"Failed to parse the meta-model {model_path}: "
                f"invalid syntax at line {parse_exception.lineno}\n"
            )
        else:
            raise RuntimeError(
                f"Failed to parse the meta-model {model_path}: " f"{parse_exception}\n"
            )

    assert atok is not None

    import_errors = aas_core_codegen.parse.check_expected_imports(atok=atok)
    if import_errors:
        writer = io.StringIO()
        aas_core_codegen.run.write_error_report(
            message="One or more unexpected imports in the meta-model",
            errors=import_errors,
            stderr=writer,
        )

        raise RuntimeError(writer.getvalue())

    lineno_columner = aas_core_codegen.common.LinenoColumner(atok=atok)

    parsed_symbol_table, error = aas_core_codegen.parse.atok_to_symbol_table(atok=atok)
    if error is not None:
        writer = io.StringIO()
        aas_core_codegen.run.write_error_report(
            message=f"Failed to construct the symbol table from {model_path}",
            errors=[lineno_columner.error_message(error)],
            stderr=writer,
        )

        raise RuntimeError(writer.getvalue())

    assert parsed_symbol_table is not None

    ir_symbol_table, error = intermediate.translate(
        parsed_symbol_table=parsed_symbol_table,
        atok=atok,
    )
    if error is not None:
        writer = io.StringIO()
        aas_core_codegen.run.write_error_report(
            message=f"Failed to translate the parsed symbol table "
            f"to intermediate symbol table "
            f"based on {model_path}",
            errors=[lineno_columner.error_message(error)],
            stderr=writer,
        )

        raise RuntimeError(writer.getvalue())

    assert ir_symbol_table is not None

    (
        constraints_by_class,
        inference_errors,
    ) = aas_core_codegen.infer_for_schema.infer_constraints_by_class(
        symbol_table=ir_symbol_table
    )

    if inference_errors is not None:
        writer = io.StringIO()
        aas_core_codegen.run.write_error_report(
            message=f"Failed to infer the constraints for the schema "
            f"based on {model_path}",
            errors=[lineno_columner.error_message(error) for error in inference_errors],
            stderr=writer,
        )

        raise RuntimeError(writer.getvalue())

    assert constraints_by_class is not None

    return ir_symbol_table, constraints_by_class


CanHashT = TypeVar("CanHashT", bound="CanHash")


class CanHash(Protocol):
    """Represent an incremental hash."""

    def update(self, data: bytes) -> None:
        """Update the hasher with the given data."""
        raise NotImplementedError()

    def digest(self) -> bytes:
        """Return the hash digest as bytes."""
        raise NotImplementedError()

    def hexdigest(self) -> str:
        """Return the hexadecimal hash digest in hex."""
        raise NotImplementedError()

    def copy(self: CanHashT) -> CanHashT:
        """Copy the hasher state."""
        raise NotImplementedError()


@ensure(
    lambda prefix_hash, segment_or_segments, result: not (
        isinstance(segment_or_segments, collections.abc.Sized)
        and len(segment_or_segments) > 0
    )
    or (prefix_hash is not result),
    "Hash is always copied unless there were no segments to hash",
)
@ensure(
    lambda prefix_hash, segment_or_segments, result: not isinstance(
        segment_or_segments, (int, str)
    )
    or (prefix_hash is not result),
    "Hash is always copied when there is a segment given",
)
def hash_path(
    prefix_hash: Optional[CanHash],
    segment_or_segments: Union[int, str, Sequence[Union[int, str]]],
) -> CanHash:
    """
    Hash a path extended with a segment and pre-hashed prefix.

    Hashing a single segment in a list is equal to hashing that segment directly:

    >>> prefix = hash_path(None, 'something')
    >>> (
    ...     hash_path(prefix, ['something-more']).hexdigest()
    ...         == hash_path(prefix, 'something-more').hexdigest()
    ... )
    True
    """
    if isinstance(segment_or_segments, (int, str)):
        segment_bytes = f"/{repr(segment_or_segments)}".encode("utf-8")
        hsh = prefix_hash.copy() if prefix_hash is not None else hashlib.md5()
        hsh.update(segment_bytes)
        return hsh

    elif isinstance(segment_or_segments, collections.abc.Iterable) and isinstance(
        segment_or_segments, collections.abc.Sized
    ):
        if len(segment_or_segments) == 0:
            return prefix_hash if prefix_hash is not None else hashlib.md5()

        hsh = prefix_hash.copy() if prefix_hash is not None else hashlib.md5()
        # noinspection PyTypeChecker
        for segment in segment_or_segments:
            segment_bytes = f"/{repr(segment)}".encode("utf-8")
            hsh.update(segment_bytes)

        return hsh

    else:
        # noinspection PyTypeChecker
        assert_never(segment_or_segments)


def instance_path_as_posix(path: Sequence[Union[str, int]]) -> str:
    """Create a string representation as a POSIX-like path."""
    return "/" + "/".join(str(segment) for segment in path)


def is_valid_filename(name: str) -> bool:
    """Check whether the ``name`` is a valid file name."""
    name = name.strip()
    if len(name) == 0:
        return False

    # Disallow current/parent directory names
    if name in {".", ".."}:
        return False

    # Invalid characters (Windows + POSIX safe)
    if re.search(r'[<>:"/\\|?*\x00-\x1F]', name):
        return False

    # Cannot end with space or dot (Windows rule)
    if name.endswith(" ") or name.endswith("."):
        return False

    # Reserved Windows filenames (case-insensitive)
    reserved = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    if name.upper().split(".")[0] in reserved:
        return False

    return True


class Filenameable(str):
    """Represent a string which can be used across file systems for a file name."""

    @require(lambda value: is_valid_filename(value))
    def __new__(cls, value: str) -> "Filenameable":
        return cast(Filenameable, value)


T = TypeVar("T")


class NonEmptySequence(Sequence[T], Generic[T]):
    """Represent a sequence with at least one item."""

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[T]: ...

    def __getitem__(self, index: Union[int, slice]) -> Union[T, Sequence[T]]:
        raise NotImplementedError(
            "This method is added here only for mypy "
            "and is not expected to be called at all as we only perform a cast "
            "in __new__."
        )

    def __len__(self) -> int:
        raise NotImplementedError(
            "This method is added here only for mypy "
            "and is not expected to be called at all as we only perform a cast "
            "in __new__."
        )

    @require(lambda value: len(value) > 0)
    def __new__(cls, value: Sequence[T]) -> "NonEmptySequence[T]":
        return cast(NonEmptySequence[T], value)


def bullet_points(points: Iterable[str]) -> str:
    """Make a bullet point list out of the given points."""
    indent = "  "
    return "\n".join(f"* {indent_but_first_line(point, indent)}" for point in points)


@invariant(lambda self: not self.relative_path.is_absolute())
class Output(DBC):
    """Represent the test case serialized in text."""

    relative_path: Final[pathlib.Path]
    text: Final[str]

    @require(lambda relative_path: not relative_path.is_absolute())
    def __init__(self, relative_path: pathlib.Path, text: str) -> None:
        self.relative_path = relative_path
        self.text = text
