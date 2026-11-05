# SPDX-FileCopyrightText: 2025 aas-core-testdatagen AUTHORS
#
# SPDX-License-Identifier: MIT

"""Generate primitive values based on the path."""

import hashlib
from typing import Optional, TypeVar, Sequence, List

from aas_core_codegen import intermediate, infer_for_schema
from aas_core_codegen.common import assert_never
from icontract import ensure, require

from aas_core_testdatagen import common, preseria
from aas_core_testdatagen.frozen_examples import (
    pattern as frozen_examples_pattern,
)


def generate_bool(path_hash: common.CanHash) -> bool:
    """Return the hexadecimal digest transformed to a boolean."""
    number = int(path_hash.hexdigest()[:8], base=16)
    return number % 2 == 0


def generate_int(path_hash: common.CanHash) -> int:
    """Return the hexadecimal digest parsed as integer."""
    return int(path_hash.hexdigest()[:8], base=16)


# fmt: off
@require(
    lambda minimum, maximum:
    not (minimum is not None and maximum is not None)
    or minimum <= maximum
)
@ensure(
    lambda minimum, result:
    not (minimum is not None)
    or (minimum <= result)
)
@ensure(
    lambda maximum, result:
    not (maximum is not None)
    or (result <= maximum)
)
@ensure(
    lambda path_hash, minimum, maximum, result:
    not (minimum is None and maximum is None)
    or (result == generate_int(path_hash))
)
# fmt: on
def generate_int_in_range(
    path_hash: common.CanHash, minimum: Optional[int], maximum: Optional[int]
) -> int:
    """Return the integer sampled in the given range from the hash digest."""
    value = int(path_hash.hexdigest()[:8], base=16)

    if minimum is None and maximum is None:
        return value

    elif minimum is not None and maximum is None:
        return minimum + value

    elif minimum is None and maximum is not None:
        return maximum - value

    else:
        assert minimum is not None and maximum is not None

        if minimum == maximum:
            return minimum

        return minimum + value % (maximum - minimum + 1)


def generate_int64(path_hash: common.CanHash) -> int:
    """Return the hexadecimal digest parsed as integer."""
    return int(path_hash.hexdigest()[:8], base=16) % (2**63 - 1)


def generate_float(path_hash: common.CanHash) -> float:
    """Return the hexadecimal digest transformed to a float."""
    number = int(path_hash.hexdigest()[:8], base=16)
    return float(number) / 100


_RULER_STR = "1234567890"


@ensure(lambda length, result: len(result) == length)
def generate_str_padding(length: int) -> str:
    """
    Generate a dummy string padding.

    >>> generate_str_padding(0)
    ''

    >>> generate_str_padding(4)
    '1234'

    >>> generate_str_padding(11)
    '12345678901'
    """
    tens = length // 10
    remainder = length % 10
    return "".join([_RULER_STR * tens, _RULER_STR[:remainder]])


_RULER_BYTES = b"1234567890"


@ensure(lambda length, result: len(result) == length)
def generate_bytes_padding(length: int) -> bytes:
    """
    Generate a dummy bytes padding.

    >>> generate_bytes_padding(0)
    b''

    >>> generate_bytes_padding(4)
    b'1234'

    >>> generate_bytes_padding(11)
    b'12345678901'
    """
    tens = length // 10
    remainder = length % 10
    return b"".join([_RULER_BYTES * tens, _RULER_BYTES[:remainder]])


# fmt: off
@ensure(
    lambda length, result:
    len(result) == length
)
# fmt: on
def generate_str_of_exact_len(hexdigest: str, length: int) -> str:
    """Generate a semi-random string of the exact given ``length``."""
    if length < 12:
        # NOTE (mristin):
        # Short strings look just as hexadecimal.
        return hexdigest[:length]

    if length <= 10 + len(hexdigest):
        len_hexdigest_part = length - 10
        return f"something_{hexdigest[:len_hexdigest_part]}"

    prefix = f"something_{hexdigest}"
    return prefix + generate_str_padding(length - len(prefix))


# fmt: off
@ensure(
    lambda min_len, result:
    not (min_len is not None)
    or (min_len <= len(result))
)
@ensure(
    lambda max_len, result:
    not (max_len is not None)
    or (len(result) <= max_len)
)
# fmt: on
def generate_str(
    path_hash: common.CanHash,
    min_len: Optional[int] = None,
    max_len: Optional[int] = None,
) -> str:
    """Transform the digest to a semi-meaningful string value."""
    hexdigest = path_hash.hexdigest()

    default = f"something_{hexdigest[:8]}"

    if min_len is None and max_len is None:
        return default

    elif min_len is not None and max_len is None:
        if min_len <= len(default):
            return default

        return generate_str_of_exact_len(hexdigest, min_len)

    elif min_len is None and max_len is not None:
        if len(default) < max_len:
            return default

        return generate_str_of_exact_len(hexdigest, max_len)

    elif min_len is not None and max_len is not None:
        if min_len <= len(default) <= max_len:
            return default

        return generate_str_of_exact_len(hexdigest, min_len)

    else:
        raise AssertionError(f"Unexpected case: {min_len=}, {max_len=}")


def generate_str_satisfying_pattern(path_hash: common.CanHash, pattern: str) -> str:
    """Transform the digest to one of the pattern examples."""
    examples = frozen_examples_pattern.BY_PATTERN.get(pattern, None)
    if examples is None:
        raise AssertionError(
            f"Unexpected pattern not covered in the frozen examples: {pattern!r}"
        )

    return choose_value(path_hash, list(examples.positives.values()))


# fmt: off
@ensure(
    lambda min_len, result:
    not (min_len is not None)
    or (min_len <= len(result))
)
@ensure(
    lambda max_len, result:
    not (max_len is not None)
    or (len(result) <= max_len)
)
# fmt: on
def generate_bytes(
    path_hash: common.CanHash,
    min_len: Optional[int] = None,
    max_len: Optional[int] = None,
) -> bytes:
    """Transform the digest to a meaningless byte array."""
    digest = path_hash.digest()

    # NOTE (mristin, 2023-03-08):
    # We return here an arbitrary number of bytes to make it explicit
    # in the generated examples that there is no limit on 8 bytes or something
    # similar.
    default_len = 11

    count = None  # type: Optional[int]

    if min_len is None and max_len is None:
        count = default_len
    elif min_len is not None and max_len is None:
        count = min_len
    elif min_len is None and max_len is not None:
        count = min(max_len, default_len)
    elif min_len is not None and max_len is not None:
        count = min_len
    else:
        raise AssertionError("Unhandled case")

    assert count is not None

    if count <= len(digest):
        result = digest[:count]
    else:
        parts = []  # type: List[bytes]
        length = 0

        current_digest = digest

        while length < count:
            remaining = length - count
            if len(current_digest) < remaining:
                parts.append(current_digest)
                length += len(current_digest)

                # NOTE (mristin, 2023-03-08):
                # Re-hash for a "random" effect. This works OK for examples.
                hasher = hashlib.md5()
                hasher.update(current_digest)
                current_digest = hasher.digest()

            else:
                parts.append(current_digest[:remaining])
                length += remaining

        result = b"".join(parts)

    assert len(result) == count
    return result


T = TypeVar("T")


def choose_value(path_hash: common.CanHash, choice: Sequence[T]) -> T:
    """Choose the value among ``choice`` based on the ``path_hash``."""
    number = int(path_hash.hexdigest()[:8], base=16)

    return choice[number % len(choice)]


def generate_time_of_day(path_hash: common.CanHash) -> str:
    """Generate a semi-random time of the day based on the ``path_hash``."""
    number = int(path_hash.hexdigest()[:8], base=16)

    remainder = number
    hours = (remainder // 3600) % 24
    remainder = remainder % 3600
    minutes = (remainder // 60) % 60
    seconds = remainder % 60

    fraction = number % 1000000

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{fraction}"


def generate_url(path_hash: common.CanHash) -> str:
    """Sample a semi-random URL based on ``path_hash``."""
    domain = choose_value(
        path_hash,
        [
            "something.com",
            "example.com",
            "an-example.com",
            "another-example.com",
            "some-company.com",
            "another-company.com",
            "yet-another-company.com",
        ],
    )

    return f"https://{domain}/{path_hash.hexdigest()[:8]}"


def generate_urn(path_hash: common.CanHash) -> str:
    """Sample a semi-random URL based on ``path_hash``."""
    prefix = choose_value(
        path_hash,
        [
            "urn:something",
            "urn:example",
            "urn:an-example",
            "urn:another-example",
            "urn:some-company",
            "urn:another-company",
            "urn:yet-another-company",
        ],
    )
    number = int(path_hash.hexdigest()[:8], base=16)
    random_id = f"{number % 20:02d}"

    return f"{prefix}:{random_id}:{path_hash.hexdigest()[:8]}"


def generate_bcp_47_en(path_hash: common.CanHash) -> str:
    """Generate a random but valid BCP 47 tag with English as base."""
    hexdigest = path_hash.hexdigest()

    # NOTE (mristin):
    # We select Jamaica as region code since it is nice and sunny there.
    return f"en-JM-x-{hexdigest[:8]}"


def generate_id_short(path_hash: common.CanHash) -> str:
    """Sample a semi-random ID-short based on ``path_hash``."""
    return f"something{path_hash.hexdigest()[:8]}"


def generate_primitive_value_with_constraints(
    path_hash: common.CanHash,
    primitive_type: intermediate.PrimitiveType,
    len_constraint: Optional[infer_for_schema.LenConstraint],
    patterns: Sequence[str],
    allowed_values: Optional[Sequence[preseria.PrimitiveValueUnion]],
) -> preseria.PrimitiveValueUnion:
    """
    Generate a quasi-random primitive value fulfilling the constraints.

    The path hash is used as a seed. The calls with the same path hash should generate
    the same primitive value.
    """
    if allowed_values is not None:
        return choose_value(path_hash=path_hash, choice=allowed_values)

    if primitive_type is intermediate.PrimitiveType.BOOL:
        return generate_bool(path_hash=path_hash)

    elif primitive_type is intermediate.PrimitiveType.INT:
        return generate_int(path_hash=path_hash)

    elif primitive_type is intermediate.PrimitiveType.FLOAT:
        return generate_float(path_hash=path_hash)

    elif primitive_type is intermediate.PrimitiveType.STR:
        # NOTE (mristin):
        # We simply ignore length constraint on top of patterns. Please adapt
        # the frozen pattern samples to conform with the length constraints if this does
        # not work.

        if len(patterns) > 0:
            # NOTE (mristin):
            # We try the best effort sampling -- we generate by the last pattern, and
            # hope that the previous patterns are satisfied.
            #
            # If this is not good enough, you have to fix the sampling for
            # the individual properties or classes.
            return generate_str_satisfying_pattern(
                path_hash=path_hash, pattern=patterns[-1]
            )

        elif len_constraint is not None:
            return generate_str(
                path_hash=path_hash,
                min_len=len_constraint.min_value,
                max_len=len_constraint.max_value,
            )

        else:
            return generate_str(path_hash=path_hash)

    elif primitive_type is intermediate.PrimitiveType.BYTEARRAY:
        if len_constraint is not None:
            return generate_bytes(
                path_hash=path_hash,
                min_len=len_constraint.min_value,
                max_len=len_constraint.max_value,
            )

        else:
            return generate_bytes(path_hash=path_hash)

    else:
        # noinspection PyTypeChecker
        assert_never(primitive_type)
