"""Perform operations on XSD base data types."""

import base64
import datetime
import decimal
import enum
import re
from typing import Final, FrozenSet, Optional, Mapping, Callable, Pattern, Sequence

from icontract import require


class Comparison(enum.Enum):
    "List the outcomes of a comparison."

    LESS = -1
    EQUAL = 0
    GREATER = 1


XSD_TYPE_SET: Final[FrozenSet[str]] = frozenset(
    {
        "xs:anyURI",
        "xs:base64Binary",
        "xs:boolean",
        "xs:byte",
        "xs:date",
        "xs:dateTime",
        "xs:decimal",
        "xs:double",
        "xs:duration",
        "xs:float",
        "xs:gDay",
        "xs:gMonth",
        "xs:gMonthDay",
        "xs:gYear",
        "xs:gYearMonth",
        "xs:hexBinary",
        "xs:int",
        "xs:integer",
        "xs:long",
        "xs:negativeInteger",
        "xs:nonNegativeInteger",
        "xs:nonPositiveInteger",
        "xs:positiveInteger",
        "xs:short",
        "xs:string",
        "xs:time",
        "xs:unsignedByte",
        "xs:unsignedInt",
        "xs:unsignedLong",
        "xs:unsignedShort",
    }
)

_NUMERICAL_VALUE_TYPE_SET: Final[FrozenSet[str]] = frozenset(
    {
        "xs:byte",
        "xs:decimal",
        "xs:double",
        "xs:float",
        "xs:int",
        "xs:integer",
        "xs:long",
        "xs:negativeInteger",
        "xs:nonNegativeInteger",
        "xs:nonPositiveInteger",
        "xs:positiveInteger",
        "xs:short",
        "xs:unsignedByte",
        "xs:unsignedInt",
        "xs:unsignedLong",
        "xs:unsignedShort",
    }
)

_STRING_CMP_VALUE_TYPE_SET: Final[FrozenSet[str]] = frozenset(
    {"xs:anyURI", "xs:string", "xs:hexBinary"}
)


def _parse_timezone(tz_str: str) -> datetime.timedelta:
    """
    Parse timezone string like '+05:30' or 'Z' and return timedelta offset.

    UTC designator:
    >>> _parse_timezone("Z")
    datetime.timedelta(0)

    Positive offset with hours only:
    >>> _parse_timezone("+02:00")
    datetime.timedelta(seconds=7200)

    Positive offset with hours and minutes:
    >>> _parse_timezone("+05:30")
    datetime.timedelta(seconds=19800)

    Negative offset with hours only:
    >>> _parse_timezone("-04:00")
    datetime.timedelta(days=-1, seconds=72000)

    Negative offset with hours and minutes:
    >>> _parse_timezone("-05:45")
    datetime.timedelta(days=-1, seconds=65700)

    Zero offset expressed explicitly:
    >>> _parse_timezone("+00:00")
    datetime.timedelta(0)
    >>> _parse_timezone("-00:00")
    datetime.timedelta(0)
    """
    if tz_str == "Z":
        return datetime.timedelta(0)

    match = re.match(r"([+-])(\d{2}):(\d{2})$", tz_str)
    if not match:
        raise ValueError(f"Invalid timezone format: {tz_str}")

    sign, hours, minutes = match.groups()
    offset = datetime.timedelta(hours=int(hours), minutes=int(minutes))
    return offset if sign == "+" else -offset


def _normalize_g_day(value: str) -> tuple[int, datetime.timedelta]:
    """
    Parse xs:gDay value and return (day, timezone offset).

    Basic day with implicit Z timezone:
    >>> _normalize_g_day("---15")
    (15, datetime.timedelta(0))

    Explicit Z timezone:
    >>> _normalize_g_day("---31Z")
    (31, datetime.timedelta(0))

    Positive timezone offset:
    >>> _normalize_g_day("---01+02:30")
    (1, datetime.timedelta(seconds=9000))

    Negative timezone offset:
    >>> _normalize_g_day("---01-05:00")
    (1, datetime.timedelta(days=-1, seconds=68400))

    Boundary values:
    >>> _normalize_g_day("---01")
    (1, datetime.timedelta(0))
    >>> _normalize_g_day("---31")
    (31, datetime.timedelta(0))
    """
    # Format: ---DD[Z|(+|-)hh:mm]
    match = re.match(r"^---(\d{2})(Z|[+-]\d{2}:\d{2})?$", value)
    if not match:
        raise ValueError(f"Invalid xs:gDay format: {value}")

    day = int(match.group(1))
    tz_str = match.group(2) or "Z"
    tz_offset = _parse_timezone(tz_str)

    if not (1 <= day <= 31):  # pylint: disable=superfluous-parens
        raise ValueError(f"Invalid day value: {day}")

    return day, tz_offset


def _normalize_g_month(value: str) -> tuple[int, datetime.timedelta]:
    """
    Parse xs:gMonth value and return (month, timezone offset).

    Basic month with implicit Z timezone:
    >>> _normalize_g_month("--03")
    (3, datetime.timedelta(0))

    Explicit Z timezone:
    >>> _normalize_g_month("--12Z")
    (12, datetime.timedelta(0))

    Positive timezone offset:
    >>> _normalize_g_month("--06+02:30")
    (6, datetime.timedelta(seconds=9000))

    Negative timezone offset:
    >>> _normalize_g_month("--06-05:00")
    (6, datetime.timedelta(days=-1, seconds=68400))

    Boundary values:
    >>> _normalize_g_month("--01")
    (1, datetime.timedelta(0))
    >>> _normalize_g_month("--12")
    (12, datetime.timedelta(0))
    """
    # Format: --MM[Z|(+|-)hh:mm]
    match = re.match(r"^--(\d{2})(Z|[+-]\d{2}:\d{2})?$", value)
    if not match:
        raise ValueError(f"Invalid xs:gMonth format: {value}")

    month = int(match.group(1))
    tz_str = match.group(2) or "Z"
    tz_offset = _parse_timezone(tz_str)

    if not (1 <= month <= 12):  # pylint: disable=superfluous-parens
        raise ValueError(f"Invalid month value: {month}")

    return month, tz_offset


def _normalize_g_month_day(value: str) -> tuple[int, int, datetime.timedelta]:
    """
    Parse xs:gMonthDay value and return (month, day, timezone offset).

    Basic month-day with implicit Z timezone:
    >>> _normalize_g_month_day("--03-14")
    (3, 14, datetime.timedelta(0))

    Explicit Z timezone:
    >>> _normalize_g_month_day("--12-31Z")
    (12, 31, datetime.timedelta(0))

    Positive timezone offset:
    >>> _normalize_g_month_day("--06-01+02:30")
    (6, 1, datetime.timedelta(seconds=9000))

    Negative timezone offset:
    >>> _normalize_g_month_day("--06-01-05:00")
    (6, 1, datetime.timedelta(days=-1, seconds=68400))

    Boundary values:
    >>> _normalize_g_month_day("--01-01")
    (1, 1, datetime.timedelta(0))
    >>> _normalize_g_month_day("--12-31")
    (12, 31, datetime.timedelta(0))
    """
    # Format: --MM-DD[Z|(+|-)hh:mm]
    match = re.match(r"^--(\d{2})-(\d{2})(Z|[+-]\d{2}:\d{2})?$", value)
    if not match:
        raise ValueError(f"Invalid xs:gMonthDay format: {value}")

    month = int(match.group(1))
    day = int(match.group(2))
    tz_str = match.group(3) or "Z"
    tz_offset = _parse_timezone(tz_str)

    if not (1 <= month <= 12):  # pylint: disable=superfluous-parens
        raise ValueError(f"Invalid month value: {month}")

    if not (1 <= day <= 31):  # pylint: disable=superfluous-parens
        raise ValueError(f"Invalid day value: {day}")

    return month, day, tz_offset


def parse_duration_to_total_seconds(value: str) -> decimal.Decimal:
    """Parse ISO 8601 duration and convert to total seconds for comparison."""
    match = re.match(
        r"P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?"
        r"(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?",
        value,
    )
    if not match:
        raise ValueError(f"Invalid duration format: {value}")

    years, months, days, hours, minutes, seconds = match.groups()
    total_seconds = decimal.Decimal("0")

    if years:
        total_seconds += decimal.Decimal(years) * 365 * 24 * 3600
    if months:
        total_seconds += decimal.Decimal(months) * 30 * 24 * 3600
    if days:
        total_seconds += decimal.Decimal(days) * 24 * 3600
    if hours:
        total_seconds += decimal.Decimal(hours) * 3600
    if minutes:
        total_seconds += decimal.Decimal(minutes) * 60
    if seconds:
        total_seconds += decimal.Decimal(seconds)

    return total_seconds


@require(lambda year: year != 0, "No 0 year possible in XSD data types")
def _is_leap_year(year: int) -> bool:
    """
    Check if a year is a leap year according to Gregorian calendar rules.

    See: https://www.w3.org/TR/xmlschema-2/#dateTime

    The date and time datatypes described in XSD data types were inspired by ISO 8601.
    '0001' is the lexical representation of the year 1 of the Common Era (1 CE,
    sometimes written "AD 1" or "1 AD"). There is no year 0, and '0000' is not a valid
    lexical representation. '-0001' is the lexical representation of the year 1 Before
    Common Era (1 BCE, sometimes written "1 BC").

    >>> _is_leap_year(1)
    False

    >>> _is_leap_year(4)
    True

    >>> _is_leap_year(2000)
    True

    >>> _is_leap_year(1900)
    False

    >>> _is_leap_year(-4)
    True

    >>> _is_leap_year(-2000)
    True

    >>> _is_leap_year(-1900)
    False
    """
    # NOTE (mristin):
    # For negative years (BCE), we need to adjust the calculation. Year -1 corresponds
    # to 1 BCE, year -4 corresponds to 4 BCE, *etc.* The astronomical year 0 doesn't
    # exist in XSD data types.
    if year < 0:
        # NOTE (mristin):
        # Convert BCE year to positive equivalent for calculation:
        # -1 BCE becomes 1, -4 BCE becomes 4, *etc.*
        calc_year = -year
    else:
        calc_year = year

    if calc_year % 400 == 0:
        return True
    if calc_year % 100 == 0:
        return False
    if calc_year % 4 == 0:
        return True

    return False


#: YYYY-MM-DDTHH:MM:SS[.fraction][timezone]
_DATE_TIME_RE = re.compile(
    r"^(-?\d{4,})-(\d{2})-(\d{2})"
    r"T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})?$"
)


def _days_from_year_1_ce_to_year(target_year: int) -> decimal.Decimal:
    """
    Count days from year 1 CE January 1st 00:00 to the target year January 1st 00:00.

    See: https://www.w3.org/TR/xmlschema-2/#dateTime

    The date and time datatypes described in XSD data types were inspired by ISO 8601.
    '0001' is the lexical representation of the year 1 of the Common Era (1 CE,
    sometimes written "AD 1" or "1 AD"). There is no year 0, and '0000' is not a valid
    lexical representation. '-0001' is the lexical representation of the year 1 Before
    Common Era (1 BCE, sometimes written "1 BC").

    Year 1 CE is the origin (no days from year 1 to itself):
    >>> _days_from_year_1_ce_to_year(1)
    Decimal('0')

    Next year is one common year later (year 1 is not leap):
    >>> _days_from_year_1_ce_to_year(2)
    Decimal('365')

    Leap-year accumulation example: from year 1 to year 5 includes leap year 4.
    Years 2,3,4,5 => 365 + 365 + 366 + 365 = 1461
    >>> _days_from_year_1_ce_to_year(5)
    Decimal('1461')

    Century rule example (Gregorian-style): year 100 is not leap, year 4 is leap.
    From year 1 to year 101 includes leap years: 4..96 every 4 years = 24 leaps.
    Total = 100*365 + 24 = 36524
    >>> _days_from_year_1_ce_to_year(101)
    Decimal('36524')

    The year 1 BCE is one year before 1 CE (there is no year 0).
    >>> _days_from_year_1_ce_to_year(-1)
    Decimal('-365')

    Leap-year going backwards: year -4 is divisible by 4, so it is a leap year under
    typical proleptic Gregorian rules. From -4 up to 1 spans years -4,-3,-2,-1:
    366 + 365 + 365 + 365 = 1461 days backwards.
    >>> _days_from_year_1_ce_to_year(-4)
    Decimal('-1461')

    """
    if target_year >= 1:
        total_days = decimal.Decimal("0")
        for y in range(1, target_year):
            if _is_leap_year(y):
                total_days += 366
            else:
                total_days += 365

        return total_days
    else:
        total_days = decimal.Decimal("0")

        # NOTE (mristin):
        # The ``y`` goes from target_year to -1.
        for y in range(target_year, 0):
            if _is_leap_year(y):
                total_days -= 366
            else:
                total_days -= 365

        return total_days


_DAYS_IN_MONTH: Final[Sequence[int]] = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def days_in_month(month: int, year: int) -> int:
    """
    Determine the days in a given ``month`` in the ``year``.

    >>> days_in_month(1, 2023)   # January
    31
    >>> days_in_month(4, 2023)   # April
    30
    >>> days_in_month(12, 2023)  # December
    31

    >>> days_in_month(2, 2023)   # Common year
    28
    >>> days_in_month(2, 2024)   # Leap year
    29

    >>> days_in_month(2, 1900)   # Century, not leap
    28
    >>> days_in_month(2, 2000)   # Century, leap
    29

    >>> days_in_month(2, -1)     # 1 BCE, common year
    28
    >>> days_in_month(2, -4)     # 4 BCE, leap year
    29
    >>> days_in_month(2, -1900)  # Century BCE, not leap
    28
    >>> days_in_month(2, -2000)  # Century BCE, leap
    29
    """
    if month != 2:
        return _DAYS_IN_MONTH[month - 1]

    assert month == 2
    if _is_leap_year(year):
        return 29
    else:
        return 28


#: Pattern for time zone offset, excluding 'Z'
_TZ_OFFSET_RE = re.compile(r"([+-])(\d{2}):(\d{2})$")

#: Pattern for xs:date: YYYY-MM-DD[timezone]
_DATE_RE = re.compile(r"^(-?\d{4,})-(\d{2})-(\d{2})(Z|[+-]\d{2}:\d{2})?$")

#: Pattern for xs:gYear: YYYY[timezone]
_G_YEAR_RE = re.compile(r"^(-?\d{4,})(Z|[+-]\d{2}:\d{2})?$")

#: Pattern for xs:gYearMonth: YYYY-MM[timezone]
_G_YEAR_MONTH_RE = re.compile(r"^(-?\d{4,})-(\d{2})(Z|[+-]\d{2}:\d{2})?$")


def _date_to_datetime_str(date_str: str) -> str:
    """
    Convert xs:date string to xs:dateTime string by setting time to midnight.

    >>> _date_to_datetime_str("2023-12-25Z")
    '2023-12-25T00:00:00Z'

    >>> _date_to_datetime_str("2023-01-01+02:00")
    '2023-01-01T00:00:00+02:00'

    >>> _date_to_datetime_str("2023-06-15-05:00")
    '2023-06-15T00:00:00-05:00'

    We default to UTC if no time zone is specified:
    >>> _date_to_datetime_str("2023-02-28")
    '2023-02-28T00:00:00Z'

    >>> _date_to_datetime_str("-0001-01-01Z")
    '-0001-01-01T00:00:00Z'

    >>> _date_to_datetime_str("-0004-02-29+01:00")
    '-0004-02-29T00:00:00+01:00'
    """
    match = _DATE_RE.match(date_str)
    if match is None:
        raise ValueError(f"Invalid xs:date format: {date_str}")

    year_str, month_str, day_str, tz_str = match.groups()

    # NOTE (mristin):
    # We default to UTC if no timezone is specified.
    if tz_str is None:
        tz_str = "Z"

    return f"{year_str}-{month_str}-{day_str}T00:00:00{tz_str}"


def _g_year_to_datetime_str(g_year_str: str) -> str:
    """
    Convert xs:gYear string to xs:dateTime string by setting date to January 1st, midnight.

    >>> _g_year_to_datetime_str("2023Z")
    '2023-01-01T00:00:00Z'

    >>> _g_year_to_datetime_str("2023+02:00")
    '2023-01-01T00:00:00+02:00'

    >>> _g_year_to_datetime_str("2023-05:00")
    '2023-01-01T00:00:00-05:00'

    We default to UTC if no time zone is specified:
    >>> _g_year_to_datetime_str("2023")
    '2023-01-01T00:00:00Z'

    >>> _g_year_to_datetime_str("-0001Z")
    '-0001-01-01T00:00:00Z'

    >>> _g_year_to_datetime_str("-0004+01:00")
    '-0004-01-01T00:00:00+01:00'

    >>> _g_year_to_datetime_str("10000-12:00")
    '10000-01-01T00:00:00-12:00'
    """
    match = _G_YEAR_RE.match(g_year_str)
    if match is None:
        raise ValueError(f"Invalid xs:gYear format: {g_year_str}")

    year_str, tz_str = match.groups()

    # NOTE (mristin):
    # We default to UTC if no timezone is specified.
    if tz_str is None:
        tz_str = "Z"

    return f"{year_str}-01-01T00:00:00{tz_str}"


def _g_year_month_to_datetime_str(g_year_month_str: str) -> str:
    """
    Convert xs:gYearMonth string to xs:dateTime string by setting day to 1st, time to midnight.

    >>> _g_year_month_to_datetime_str("2023-12Z")
    '2023-12-01T00:00:00Z'

    >>> _g_year_month_to_datetime_str("2023-01+02:00")
    '2023-01-01T00:00:00+02:00'

    >>> _g_year_month_to_datetime_str("2023-06-05:00")
    '2023-06-01T00:00:00-05:00'

    We default to UTC if no time zone is specified:
    >>> _g_year_month_to_datetime_str("2023-02")
    '2023-02-01T00:00:00Z'

    >>> _g_year_month_to_datetime_str("-0001-12Z")
    '-0001-12-01T00:00:00Z'

    >>> _g_year_month_to_datetime_str("-0004-02+01:00")
    '-0004-02-01T00:00:00+01:00'

    >>> _g_year_month_to_datetime_str("10000-05-12:00")
    '10000-05-01T00:00:00-12:00'
    """
    match = _G_YEAR_MONTH_RE.match(g_year_month_str)
    if match is None:
        raise ValueError(f"Invalid xs:gYearMonth format: {g_year_month_str}")

    year_str, month_str, tz_str = match.groups()

    # NOTE (mristin):
    # We default to UTC if no timezone is specified.
    if tz_str is None:
        tz_str = "Z"

    return f"{year_str}-{month_str}-01T00:00:00{tz_str}"


def parse_date_time_to_seconds_since_epoch(text: str) -> decimal.Decimal:
    """
    Parse an ISO 8601 dateTime string and return seconds since Unix epoch
    (1970-01-01T00:00:00Z).

    See: https://www.w3.org/TR/xmlschema-2/#dateTime

    The date and time datatypes described in XSD data types were inspired by ISO 8601.
    '0001' is the lexical representation of the year 1 of the Common Era (1 CE,
    sometimes written "AD 1" or "1 AD"). There is no year 0, and '0000' is not a valid
    lexical representation. '-0001' is the lexical representation of the year 1 Before
    Common Era (1 BCE, sometimes written "1 BC").

    The time zone offset is not mandatory in XSD. We assume UTC (no time zone offset)
    if no time zone is specified.
    """
    match = _DATE_TIME_RE.match(text)
    if match is None:
        raise ValueError(f"Invalid dateTime format: {text}")

    (
        year_str,
        month_str,
        day_str,
        hour_str,
        minute_str,
        second_str,
        fraction_str,
        tz_str,
    ) = match.groups()

    year = int(year_str)
    month = int(month_str)
    day = int(day_str)
    hour = int(hour_str)
    minute = int(minute_str)
    second = int(second_str)

    if not (1 <= month <= 12):  # pylint: disable=superfluous-parens
        raise ValueError(f"Invalid month: {month}")

    if not (1 <= day <= 31):  # pylint: disable=superfluous-parens
        raise ValueError(f"Invalid day: {day}")

    if not (0 <= hour <= 23):  # pylint: disable=superfluous-parens
        raise ValueError(f"Invalid hour: {hour}")

    if not (0 <= minute <= 59):  # pylint: disable=superfluous-parens
        raise ValueError(f"Invalid minute: {minute}")

    if not (0 <= second <= 59):  # pylint: disable=superfluous-parens
        raise ValueError(f"Invalid second: {second}")

    if day > days_in_month(month, year):
        raise ValueError(f"Invalid day {day} for month {month} in year {year}")

    fraction_seconds = decimal.Decimal("0")
    if fraction_str:
        fraction_seconds = decimal.Decimal(f"0.{fraction_str}")

    tz_offset_seconds: decimal.Decimal

    # Compute time zone offset in seconds
    if tz_str is not None:
        if tz_str != "Z":
            tz_match = _TZ_OFFSET_RE.match(tz_str)

            assert tz_match is not None

            sign, tz_hours, tz_minutes = tz_match.groups()
            offset = decimal.Decimal(tz_hours) * 3600 + decimal.Decimal(tz_minutes) * 60
            tz_offset_seconds = offset if sign == "+" else -offset

        else:
            tz_offset_seconds = decimal.Decimal("0")
    else:
        # NOTE (mristin):
        # We assume UTC if there is no timezone.
        tz_offset_seconds = decimal.Decimal("0")

    # Calculate days since epoch (1970-01-01)
    # Note: There is no year 0, so -1 BCE is followed by 1 CE.
    epoch_year = 1970

    # Calculate days from epoch to target year
    target_days = _days_from_year_1_ce_to_year(year)
    epoch_days = _days_from_year_1_ce_to_year(epoch_year)
    days_since_epoch = target_days - epoch_days

    # Add days for months in the target year
    for m in range(1, month):
        days_since_epoch += days_in_month(month=m, year=year)

    # Add days in the current month (day - 1 because day 1 is the first day)
    days_since_epoch += day - 1

    # Convert to total seconds
    total_seconds = days_since_epoch * 86400  # 24 * 60 * 60
    total_seconds += hour * 3600
    total_seconds += minute * 60
    total_seconds += second
    total_seconds += fraction_seconds

    # Adjust for timezone (subtract timezone offset to get UTC)
    total_seconds -= tz_offset_seconds

    return total_seconds


@require(lambda value_type: value_type in XSD_TYPE_SET)
def compare(value: str, another: str, value_type: str) -> Optional[Comparison]:
    """
    Compare the two XSD data type values, both conforming to value type.

    Returns None if comparison is not possible (*e.g.*, NaN values for ``xs:float`` and
    ``xs:double``).
    """
    if value_type in _NUMERICAL_VALUE_TYPE_SET:
        # NOTE (mristin):
        # We handle special cases for float and double when they are NaN as comparison
        # is not possible.
        if value_type in ("xs:float", "xs:double"):
            if value.lower() == "nan" or another.lower() == "nan":
                return None

        dec_value = decimal.Decimal(value)
        dec_another = decimal.Decimal(another)
        if dec_value < dec_another:
            return Comparison.LESS
        elif dec_value > dec_another:
            return Comparison.GREATER
        else:
            return Comparison.EQUAL

    elif value_type == "xs:boolean":
        bool_value = value.lower() in ("true", "1")
        bool_another = another.lower() in ("true", "1")
        if bool_value < bool_another:
            return Comparison.LESS
        elif bool_value > bool_another:
            return Comparison.GREATER
        else:
            return Comparison.EQUAL

    elif value_type in _STRING_CMP_VALUE_TYPE_SET:
        if value < another:
            return Comparison.LESS
        elif value > another:
            return Comparison.GREATER
        else:
            return Comparison.EQUAL

    elif value_type == "xs:base64Binary":
        # NOTE (mristin):
        # We need to decode the bytes for the canonical representation.

        bytes_value = base64.b64decode(value)
        bytes_another = base64.b64decode(another)
        if bytes_value < bytes_another:
            return Comparison.LESS
        elif bytes_value > bytes_another:
            return Comparison.GREATER
        else:
            return Comparison.EQUAL

    elif value_type == "xs:date":
        # NOTE (mristin):
        # We need to use a separate function for comparison since the datetime module
        # in the standard library does not support arbitrary fractions of a second
        # and negative years.

        datetime_value = _date_to_datetime_str(value)
        datetime_another = _date_to_datetime_str(another)

        seconds_value = parse_date_time_to_seconds_since_epoch(datetime_value)
        seconds_another = parse_date_time_to_seconds_since_epoch(datetime_another)

        if seconds_value < seconds_another:
            return Comparison.LESS
        elif seconds_value > seconds_another:
            return Comparison.GREATER
        else:
            return Comparison.EQUAL

    elif value_type == "xs:dateTime":
        # NOTE (mristin):
        # We need to use a separate function for comparison since the datetime module
        # in the standard library does not support arbitrary fractions of a second
        # and negative years.

        seconds_value = parse_date_time_to_seconds_since_epoch(value)
        seconds_another = parse_date_time_to_seconds_since_epoch(another)

        if seconds_value < seconds_another:
            return Comparison.LESS
        elif seconds_value > seconds_another:
            return Comparison.GREATER
        else:
            return Comparison.EQUAL

    elif value_type == "xs:time":
        time_value = datetime.time.fromisoformat(value)
        time_another = datetime.time.fromisoformat(another)
        if time_value < time_another:
            return Comparison.LESS
        elif time_value > time_another:
            return Comparison.GREATER
        else:
            return Comparison.EQUAL

    elif value_type == "xs:duration":
        duration_value = parse_duration_to_total_seconds(value)
        duration_another = parse_duration_to_total_seconds(another)
        if duration_value < duration_another:
            return Comparison.LESS
        elif duration_value > duration_another:
            return Comparison.GREATER
        else:
            return Comparison.EQUAL

    elif value_type == "xs:gDay":
        day1, tz1 = _normalize_g_day(value)
        day2, tz2 = _normalize_g_day(another)

        # NOTE (mristin):
        # We use a reference datetime to apply timezone adjustments for a canonical form.
        ref_dt1 = datetime.datetime(2000, 1, day1, tzinfo=datetime.timezone(tz1))
        ref_dt2 = datetime.datetime(2000, 1, day2, tzinfo=datetime.timezone(tz2))
        utc_dt1 = ref_dt1.astimezone(datetime.timezone.utc)
        utc_dt2 = ref_dt2.astimezone(datetime.timezone.utc)

        if utc_dt1 < utc_dt2:
            return Comparison.LESS
        elif utc_dt1 > utc_dt2:
            return Comparison.GREATER
        else:
            return Comparison.EQUAL

    elif value_type == "xs:gMonth":
        month1, tz1 = _normalize_g_month(value)
        month2, tz2 = _normalize_g_month(another)

        # NOTE (mristin):
        # We use a reference datetime to apply timezone adjustments for a canonical form.
        ref_dt1 = datetime.datetime(2000, month1, 1, tzinfo=datetime.timezone(tz1))
        ref_dt2 = datetime.datetime(2000, month2, 1, tzinfo=datetime.timezone(tz2))
        utc_dt1 = ref_dt1.astimezone(datetime.timezone.utc)
        utc_dt2 = ref_dt2.astimezone(datetime.timezone.utc)

        if utc_dt1 < utc_dt2:
            return Comparison.LESS
        elif utc_dt1 > utc_dt2:
            return Comparison.GREATER
        else:
            return Comparison.EQUAL

    elif value_type == "xs:gMonthDay":
        month1, day1, tz1 = _normalize_g_month_day(value)
        month2, day2, tz2 = _normalize_g_month_day(another)

        # NOTE (mristin):
        # We use a reference datetime to apply timezone adjustments for a canonical form.
        ref_dt1 = datetime.datetime(2000, month1, day1, tzinfo=datetime.timezone(tz1))
        ref_dt2 = datetime.datetime(2000, month2, day2, tzinfo=datetime.timezone(tz2))
        utc_dt1 = ref_dt1.astimezone(datetime.timezone.utc)
        utc_dt2 = ref_dt2.astimezone(datetime.timezone.utc)

        if utc_dt1 < utc_dt2:
            return Comparison.LESS
        elif utc_dt1 > utc_dt2:
            return Comparison.GREATER
        else:
            return Comparison.EQUAL

    elif value_type == "xs:gYear":
        # NOTE (mristin):
        # We need to use a separate function for comparison since the datetime module
        # in the standard library does not support arbitrary fractions of a second
        # and negative years.

        datetime_value = _g_year_to_datetime_str(value)
        datetime_another = _g_year_to_datetime_str(another)

        seconds_value = parse_date_time_to_seconds_since_epoch(datetime_value)
        seconds_another = parse_date_time_to_seconds_since_epoch(datetime_another)

        if seconds_value < seconds_another:
            return Comparison.LESS
        elif seconds_value > seconds_another:
            return Comparison.GREATER
        else:
            return Comparison.EQUAL

    elif value_type == "xs:gYearMonth":
        # NOTE (mristin):
        # We need to use a separate function for comparison since the datetime module
        # in the standard library does not support arbitrary fractions of a second
        # and negative years.

        datetime_value = _g_year_month_to_datetime_str(value)
        datetime_another = _g_year_month_to_datetime_str(another)

        seconds_value = parse_date_time_to_seconds_since_epoch(datetime_value)
        seconds_another = parse_date_time_to_seconds_since_epoch(datetime_another)

        if seconds_value < seconds_another:
            return Comparison.LESS
        elif seconds_value > seconds_another:
            return Comparison.GREATER
        else:
            return Comparison.EQUAL

    else:
        # NOTE (mristin):
        # This should not happen due to the precondition, but we handle it here
        # gracefully.
        raise ValueError(f"Unexpected XSD type: {value_type}")


# region Verification


# noinspection SpellCheckingInspection
def _construct_matches_xs_any_uri() -> Pattern[str]:
    # pylint: disable=redefined-builtin
    alphanum = "[a-zA-Z0-9]"
    mark = "[-_.!~*'()]"
    unreserved = f"({alphanum}|{mark})"
    hex = "([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])"
    escaped = f"%{hex}{hex}"
    pchar = f"({unreserved}|{escaped}|[:@&=+$,])"
    param = f"({pchar})*"
    segment = f"({pchar})*(;{param})*"
    path_segments = f"{segment}(/{segment})*"
    abs_path = f"/{path_segments}"
    scheme = "[a-zA-Z][a-zA-Z0-9+\\-.]*"
    userinfo = f"({unreserved}|{escaped}|[;:&=+$,])*"
    domainlabel = f"({alphanum}|{alphanum}({alphanum}|-)*{alphanum})"
    toplabel = f"([a-zA-Z]|[a-zA-Z]({alphanum}|-)*{alphanum})"
    hostname = f"({domainlabel}\\.)*{toplabel}(\\.)?"
    ipv4address = "[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}"
    hex4 = "[0-9A-Fa-f]{1,4}"
    hexseq = f"{hex4}(:{hex4})*"
    hexpart = f"({hexseq}|{hexseq}::({hexseq})?|::({hexseq})?)"
    ipv6address = f"{hexpart}(:{ipv4address})?"
    ipv6reference = f"\\[{ipv6address}\\]"
    host = f"({hostname}|{ipv4address}|{ipv6reference})"
    port = "[0-9]*"
    hostport = f"{host}(:{port})?"
    server = f"(({userinfo}@)?{hostport})?"
    reg_name = f"({unreserved}|{escaped}|[$,;:@&=+])+"
    authority = f"({server}|{reg_name})"
    net_path = f"//{authority}({abs_path})?"
    reserved = "[;/?:@&=+$,\\[\\]]"
    uric = f"({reserved}|{unreserved}|{escaped})"
    query = f"({uric})*"
    hier_part = f"({net_path}|{abs_path})(\\?{query})?"
    uric_no_slash = f"({unreserved}|{escaped}|[;?:@&=+$,])"
    opaque_part = f"{uric_no_slash}({uric})*"
    absoluteuri = f"{scheme}:({hier_part}|{opaque_part})"
    fragment = f"({uric})*"
    rel_segment = f"({unreserved}|{escaped}|[;@&=+$,])+"
    rel_path = f"{rel_segment}({abs_path})?"
    relativeuri = f"({net_path}|{abs_path}|{rel_path})(\\?{query})?"
    uri_reference = f"^({absoluteuri}|{relativeuri})?(#{fragment})?$"

    return re.compile(uri_reference)


_REGEX_MATCHES_XS_ANY_URI = _construct_matches_xs_any_uri()


def matches_xs_any_uri(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:anyURI``.

    See: https://www.w3.org/TR/xmlschema-2/#anyURI and
    https://datatracker.ietf.org/doc/html/rfc2396 and
    https://datatracker.ietf.org/doc/html/rfc2732

    Note, that version 1.0 of the XSD specification defines ``xs:anyURI`` as
    "defined by RFC 2396, as amended by RFC 2732". Therefore, we use a
    pattern here that implements the amendments of RFC 2732. This should not
    be confused with ``matches_RFC_2396``, which does not include those
    amendments and is used in different parts of the specification.

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_ANY_URI.fullmatch(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_base_64_binary() -> Pattern[str]:
    b04_char = "[AQgw]"
    b04 = f"{b04_char}\\x20?"
    b16_char = "[AEIMQUYcgkosw048]"
    b16 = f"{b16_char}\\x20?"
    b64_char = "[A-Za-z0-9+/]"
    b64 = f"{b64_char}\\x20?"
    b64quad = f"({b64}{b64}{b64}{b64})"
    b64_final_quad = f"({b64}{b64}{b64}{b64_char})"
    padded_8 = f"{b64}{b04}= ?="
    padded_16 = f"{b64}{b64}{b16}="
    b64final = f"({b64_final_quad}|{padded_16}|{padded_8})"
    base64_binary = f"({b64quad}*{b64final})?"
    pattern = f"^{base64_binary}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_BASE_64_BINARY = _construct_matches_xs_base_64_binary()


def matches_xs_base_64_binary(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:base64Binary``.

    See: https://www.w3.org/TR/xmlschema-2/#base64Binary

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_BASE_64_BINARY.fullmatch(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_boolean() -> Pattern[str]:
    pattern = "^(true|false|1|0)$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_BOOLEAN = _construct_matches_xs_boolean()


def matches_xs_boolean(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:boolean``.

    See: https://www.w3.org/TR/xmlschema-2/#boolean

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_BOOLEAN.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_date() -> Pattern[str]:
    digit = "[0-9]"
    year_frag = f"-?(([1-9]{digit}{digit}{digit}+)|(0{digit}{digit}{digit}))"
    month_frag = "((0[1-9])|(1[0-2]))"
    day_frag = f"((0[1-9])|([12]{digit})|(3[01]))"
    minute_frag = f"[0-5]{digit}"
    timezone_frag = f"(Z|(\\+|-)((0{digit}|1[0-3]):{minute_frag}|14:00))"
    date_lexical_rep = f"{year_frag}-{month_frag}-{day_frag}{timezone_frag}?"
    pattern = f"^{date_lexical_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_DATE = _construct_matches_xs_date()


def matches_xs_date(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:date``.

    See: https://www.w3.org/TR/xmlschema-2/#date

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_DATE.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_date_time() -> Pattern[str]:
    # pylint: disable=line-too-long
    digit = "[0-9]"
    year_frag = f"-?(([1-9]{digit}{digit}{digit}+)|(0{digit}{digit}{digit}))"
    month_frag = "((0[1-9])|(1[0-2]))"
    day_frag = f"((0[1-9])|([12]{digit})|(3[01]))"
    hour_frag = f"(([01]{digit})|(2[0-3]))"
    minute_frag = f"[0-5]{digit}"
    second_frag = f"([0-5]{digit})(\\.{digit}+)?"
    end_of_day_frag = "24:00:00(\\.0+)?"
    timezone_frag = f"(Z|(\\+|-)((0{digit}|1[0-3]):{minute_frag}|14:00))"
    date_time_lexical_rep = f"{year_frag}-{month_frag}-{day_frag}T(({hour_frag}:{minute_frag}:{second_frag})|{end_of_day_frag}){timezone_frag}?"
    pattern = f"^{date_time_lexical_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_DATE_TIME = _construct_matches_xs_date_time()


def matches_xs_date_time(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:dateTime``.

    See: https://www.w3.org/TR/xmlschema-2/#dateTime

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_DATE_TIME.match(text) is not None


def is_xs_date_time(value: str) -> bool:
    """Check that ``value`` is a ``xs:dateTime``."""
    if not matches_xs_date_time(value):
        return False

    date, _ = value.split("T")
    return is_xs_date(date)


# noinspection SpellCheckingInspection
def _construct_matches_xs_decimal() -> Pattern[str]:
    digit = "[0-9]"
    unsigned_no_decimal_pt_numeral = f"{digit}+"
    no_decimal_pt_numeral = f"(\\+|-)?{unsigned_no_decimal_pt_numeral}"
    frac_frag = f"{digit}+"
    unsigned_decimal_pt_numeral = (
        f"({unsigned_no_decimal_pt_numeral}\\.{frac_frag}|\\.{frac_frag})"
    )
    decimal_pt_numeral = f"(\\+|-)?{unsigned_decimal_pt_numeral}"
    decimal_lexical_rep = f"({decimal_pt_numeral}|{no_decimal_pt_numeral})"
    pattern = f"^{decimal_lexical_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_DECIMAL = _construct_matches_xs_decimal()


def matches_xs_decimal(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:decimal``.

    See: https://www.w3.org/TR/xmlschema-2/#decimal

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_DECIMAL.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_double() -> Pattern[str]:
    double_rep = (
        "((\\+|-)?([0-9]+(\\.[0-9]*)?|\\.[0-9]+)([Ee](\\+|-)?[0-9]+)?|-?INF|NaN)"
    )
    pattern = f"^{double_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_DOUBLE = _construct_matches_xs_double()


def matches_xs_double(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:double``.

    See: https://www.w3.org/TR/xmlschema-2/#double

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_DOUBLE.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_duration() -> Pattern[str]:
    # pylint: disable=line-too-long
    duration_rep = "-?P((([0-9]+Y([0-9]+M)?([0-9]+D)?|([0-9]+M)([0-9]+D)?|([0-9]+D))(T(([0-9]+H)([0-9]+M)?([0-9]+(\\.[0-9]+)?S)?|([0-9]+M)([0-9]+(\\.[0-9]+)?S)?|([0-9]+(\\.[0-9]+)?S)))?)|(T(([0-9]+H)([0-9]+M)?([0-9]+(\\.[0-9]+)?S)?|([0-9]+M)([0-9]+(\\.[0-9]+)?S)?|([0-9]+(\\.[0-9]+)?S))))"
    pattern = f"^{duration_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_DURATION = _construct_matches_xs_duration()


def matches_xs_duration(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:duration``.

    See: https://www.w3.org/TR/xmlschema-2/#duration

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_DURATION.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_float() -> Pattern[str]:
    float_rep = (
        "((\\+|-)?([0-9]+(\\.[0-9]*)?|\\.[0-9]+)([Ee](\\+|-)?[0-9]+)?|-?INF|NaN)"
    )
    pattern = f"^{float_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_FLOAT = _construct_matches_xs_float()


def matches_xs_float(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:float``.

    See: https://www.w3.org/TR/xmlschema-2/#float

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_FLOAT.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_g_day() -> Pattern[str]:
    g_day_lexical_rep = (
        "---(0[1-9]|[12][0-9]|3[01])(Z|(\\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))?"
    )
    pattern = f"^{g_day_lexical_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_G_DAY = _construct_matches_xs_g_day()


def matches_xs_g_day(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:gDay``.

    See: https://www.w3.org/TR/xmlschema-2/#gDay

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_G_DAY.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_g_month() -> Pattern[str]:
    g_month_lexical_rep = (
        "--(0[1-9]|1[0-2])(Z|(\\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))?"
    )
    pattern = f"^{g_month_lexical_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_G_MONTH = _construct_matches_xs_g_month()


def matches_xs_g_month(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:gMonth``.

    See: https://www.w3.org/TR/xmlschema-2/#gMonth

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_G_MONTH.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_g_month_day() -> Pattern[str]:
    g_month_day_rep = "--(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])(Z|(\\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))?"
    pattern = f"^{g_month_day_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_G_MONTH_DAY = _construct_matches_xs_g_month_day()


def matches_xs_g_month_day(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:gMonthDay``.

    See: https://www.w3.org/TR/xmlschema-2/#gMonthDay

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_G_MONTH_DAY.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_g_year() -> Pattern[str]:
    g_year_rep = (
        "-?([1-9][0-9]{3,}|0[0-9]{3})(Z|(\\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))?"
    )
    pattern = f"^{g_year_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_G_YEAR = _construct_matches_xs_g_year()


def matches_xs_g_year(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:gYear``.

    See: https://www.w3.org/TR/xmlschema-2/#gYear

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_G_YEAR.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_g_year_month() -> Pattern[str]:
    g_year_month_rep = "-?([1-9][0-9]{3,}|0[0-9]{3})-(0[1-9]|1[0-2])(Z|(\\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))?"
    pattern = f"^{g_year_month_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_G_YEAR_MONTH = _construct_matches_xs_g_year_month()


def matches_xs_g_year_month(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:gYearMonth``.

    See: https://www.w3.org/TR/xmlschema-2/#gYearMonth

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_G_YEAR_MONTH.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_hex_binary() -> Pattern[str]:
    hex_binary = "([0-9a-fA-F]{2})*"
    pattern = f"^{hex_binary}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_HEX_BINARY = _construct_matches_xs_hex_binary()


def matches_xs_hex_binary(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:hexBinary``.

    See: https://www.w3.org/TR/xmlschema-2/#hexBinary

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_HEX_BINARY.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_time() -> Pattern[str]:
    # pylint: disable=line-too-long
    time_rep = "(([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\\.[0-9]+)?|(24:00:00(\\.0+)?))(Z|(\\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))?"
    pattern = f"^{time_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_TIME = _construct_matches_xs_time()


def matches_xs_time(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:time``.

    See: https://www.w3.org/TR/xmlschema-2/#time

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_TIME.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_integer() -> Pattern[str]:
    integer_rep = "[-+]?[0-9]+"
    pattern = f"^{integer_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_INTEGER = _construct_matches_xs_integer()


def matches_xs_integer(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:integer``.

    See: https://www.w3.org/TR/xmlschema-2/#integer

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_INTEGER.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_long() -> Pattern[str]:
    long_rep = "[-+]?0*[0-9]{1,20}"
    pattern = f"^{long_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_LONG = _construct_matches_xs_long()


def matches_xs_long(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:long``.

    See: https://www.w3.org/TR/xmlschema-2/#long

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_LONG.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_int() -> Pattern[str]:
    int_rep = "[-+]?0*[0-9]{1,10}"
    pattern = f"^{int_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_INT = _construct_matches_xs_int()


def matches_xs_int(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:int``.

    See: https://www.w3.org/TR/xmlschema-2/#int

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_INT.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_short() -> Pattern[str]:
    short_rep = "[-+]?0*[0-9]{1,5}"
    pattern = f"^{short_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_SHORT = _construct_matches_xs_short()


def matches_xs_short(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:short``.

    See: https://www.w3.org/TR/xmlschema-2/#short

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_SHORT.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_byte() -> Pattern[str]:
    byte_rep = "[-+]?0*[0-9]{1,3}"
    pattern = f"^{byte_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_BYTE = _construct_matches_xs_byte()


def matches_xs_byte(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:byte``.

    See: https://www.w3.org/TR/xmlschema-2/#byte

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_BYTE.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_non_negative_integer() -> Pattern[str]:
    non_negative_integer_rep = "(-0|\\+?[0-9]+)"
    pattern = f"^{non_negative_integer_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_NON_NEGATIVE_INTEGER = _construct_matches_xs_non_negative_integer()


def matches_xs_non_negative_integer(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:nonNegativeInteger``.

    See: https://www.w3.org/TR/xmlschema-2/#nonNegativeInteger

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_NON_NEGATIVE_INTEGER.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_positive_integer() -> Pattern[str]:
    positive_integer_rep = "\\+?0*[1-9][0-9]*"
    pattern = f"^{positive_integer_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_POSITIVE_INTEGER = _construct_matches_xs_positive_integer()


def matches_xs_positive_integer(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:positiveInteger``.

    See: https://www.w3.org/TR/xmlschema-2/#positiveInteger

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_POSITIVE_INTEGER.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_unsigned_long() -> Pattern[str]:
    unsigned_long_rep = "(-0|\\+?0*[0-9]{1,20})"
    pattern = f"^{unsigned_long_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_UNSIGNED_LONG = _construct_matches_xs_unsigned_long()


def matches_xs_unsigned_long(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:unsignedLong``.

    See: https://www.w3.org/TR/xmlschema-2/#unsignedLong

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_UNSIGNED_LONG.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_unsigned_int() -> Pattern[str]:
    unsigned_int_rep = "(-0|\\+?0*[0-9]{1,10})"
    pattern = f"^{unsigned_int_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_UNSIGNED_INT = _construct_matches_xs_unsigned_int()


def matches_xs_unsigned_int(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:unsignedInt``.

    See: https://www.w3.org/TR/xmlschema-2/#unsignedInt

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_UNSIGNED_INT.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_unsigned_short() -> Pattern[str]:
    unsigned_short_rep = "(-0|\\+?0*[0-9]{1,5})"
    pattern = f"^{unsigned_short_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_UNSIGNED_SHORT = _construct_matches_xs_unsigned_short()


def matches_xs_unsigned_short(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:unsignedShort``.

    See: https://www.w3.org/TR/xmlschema-2/#unsignedShort

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_UNSIGNED_SHORT.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_unsigned_byte() -> Pattern[str]:
    unsigned_byte_rep = "(-0|\\+?0*[0-9]{1,3})"
    pattern = f"^{unsigned_byte_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_UNSIGNED_BYTE = _construct_matches_xs_unsigned_byte()


def matches_xs_unsigned_byte(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:unsignedByte``.

    See: https://www.w3.org/TR/xmlschema-2/#unsignedByte

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_UNSIGNED_BYTE.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_non_positive_integer() -> Pattern[str]:
    non_positive_integer_rep = "(\\+0|0|-[0-9]+)"
    pattern = f"^{non_positive_integer_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_NON_POSITIVE_INTEGER = _construct_matches_xs_non_positive_integer()


def matches_xs_non_positive_integer(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:nonPositiveInteger``.

    See: https://www.w3.org/TR/xmlschema-2/#nonPositiveInteger

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_NON_POSITIVE_INTEGER.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_negative_integer() -> Pattern[str]:
    negative_integer_rep = "(-0*[1-9][0-9]*)"
    pattern = f"^{negative_integer_rep}$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_NEGATIVE_INTEGER = _construct_matches_xs_negative_integer()


def matches_xs_negative_integer(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:negativeInteger``.

    See: https://www.w3.org/TR/xmlschema-2/#negativeInteger

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_NEGATIVE_INTEGER.match(text) is not None


# noinspection SpellCheckingInspection
def _construct_matches_xs_string() -> Pattern[str]:
    pattern = "^[\\x09\\x0a\\x0d\\x20-\\ud7ff\\ue000-\\ufffd\\U00010000-\\U0010ffff]*$"

    return re.compile(pattern)


_REGEX_MATCHES_XS_STRING = _construct_matches_xs_string()


def matches_xs_string(text: str) -> bool:
    """
    Check that ``text`` conforms to the pattern of an ``xs:string``.

    See: https://www.w3.org/TR/xmlschema-2/#string

    :param text: Text to be checked
    :return:
        True if the ``text`` conforms to the pattern
    """
    return _REGEX_MATCHES_XS_STRING.match(text) is not None


_DATE_PREFIX_RE = re.compile(r"^(-?[0-9]+)-([0-9]{2})-([0-9]{2})")


def is_xs_date(value: str) -> bool:
    """Check that ``value`` is a valid ``xs:date``."""
    if not matches_xs_date(value):
        return False

    # NOTE (mristin, 2022-11-23):
    # We can not use :py:func:`datetime.datetime.strptime` as it does not
    # handle years below 1000 correctly on Windows (*e.g.*, ``-999-01-01``).

    # NOTE (mristin, 2022-10-30):
    # We need to match the prefix as zone offsets are allowed in the dates. Optimally,
    # we would re-use the pattern matching from :py:func`matches_xs_date`, but this
    # would make the code generation and constraint inference for schemas much more
    # difficult. Hence, we sacrifice the efficiency a bit for the clearer code & code
    # generation.
    match = _DATE_PREFIX_RE.match(value)
    assert match is not None

    year = int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))

    # We do not accept year zero,
    # see the note at: https://www.w3.org/TR/xmlschema-2/#dateTime
    if year == 0:
        return False

    if day <= 0:
        return False

    if month <= 0 or month >= 13:
        return False

    max_days = days_in_month(month=month, year=year)

    if day > max_days:
        return False

    return True


# The smallest magnitudes which round to infinity: the half-way between the largest
# finite value and the next power of two.
_XS_DOUBLE_OVERFLOW_THRESHOLD: Final[decimal.Decimal] = decimal.Decimal(
    2**1024 - 2**970
)
_XS_FLOAT_OVERFLOW_THRESHOLD: Final[decimal.Decimal] = decimal.Decimal(2**128 - 2**103)


def _is_finite_below(value: str, threshold: decimal.Decimal) -> bool:
    """Check the magnitude of the decimal ``value`` against ``threshold`` exactly."""
    # NOTE: ``float(.)`` would round the value, and the arithmetic of ``Decimal``
    # rounds to the context precision. We therefore compare the decimal exponents
    # first and build the unsigned ``Decimal`` from its tuple, which is exact.
    unsigned = value.lstrip("+-")
    mantissa_text, _, exponent_text = unsigned.lower().partition("e")

    mantissa = decimal.Decimal(mantissa_text)
    if mantissa == 0:
        return True

    exponent = int(exponent_text) if exponent_text else 0

    magnitude = mantissa.adjusted() + exponent
    threshold_magnitude = threshold.adjusted()
    if magnitude != threshold_magnitude:
        return magnitude < threshold_magnitude

    _, digits, mantissa_exponent = mantissa.as_tuple()
    assert isinstance(mantissa_exponent, int)
    return decimal.Decimal((0, digits, mantissa_exponent + exponent)) < threshold


def is_xs_double(value: str) -> bool:
    """Check that ``value`` is a valid ``xs:double``."""
    # We need to check explicitly for the regular expression since
    # ``float(.)`` is too permissive. For example,
    # it accepts "nan" although only "NaN" is valid.
    # See: https://www.w3.org/TR/xmlschema-2/#double
    if not matches_xs_double(value):
        return False

    if value in ("INF", "-INF", "NaN"):
        return True

    return _is_finite_below(value, _XS_DOUBLE_OVERFLOW_THRESHOLD)


def is_xs_float(value: str) -> bool:
    """Check that ``value`` is a valid ``xs:float``."""
    # See the note in :py:func:`is_xs_double`.
    # See: https://www.w3.org/TR/xmlschema-2/#float
    if not matches_xs_float(value):
        return False

    if value in ("INF", "-INF", "NaN"):
        return True

    return _is_finite_below(value, _XS_FLOAT_OVERFLOW_THRESHOLD)


def is_xs_g_month_day(value: str) -> bool:
    """Check that ``value`` is a valid ``xs:gMonthDay``."""
    if not matches_xs_g_month_day(value):
        return False

    month = int(value[2:4])
    day = int(value[5:7])

    max_days = _DAYS_IN_MONTH[month - 1]

    return day <= max_days


def is_xs_long(value: str) -> bool:
    """Check that ``value`` is a valid ``xs:long``."""
    if not matches_xs_long(value):
        return False

    converted = int(value)
    return -9223372036854775808 <= converted <= 9223372036854775807


def is_xs_int(value: str) -> bool:
    """Check that ``value`` is a valid ``xs:int``."""
    if not matches_xs_int(value):
        return False

    converted = int(value)
    return -2147483648 <= converted <= 2147483647


def is_xs_short(value: str) -> bool:
    """Check that ``value`` is a valid ``xs:short``."""
    if not matches_xs_short(value):
        return False

    converted = int(value)
    return -32768 <= converted <= 32767


def is_xs_byte(value: str) -> bool:
    """Check that ``value`` is a valid ``xs:byte``."""
    if not matches_xs_byte(value):
        return False

    converted = int(value)
    return -128 <= converted <= 127


def is_xs_unsigned_long(value: str) -> bool:
    """Check that ``value`` is a valid ``xs:unsignedLong``."""
    if not matches_xs_unsigned_long(value):
        return False

    converted = int(value)
    return 0 <= converted <= 18446744073709551615


def is_xs_unsigned_int(value: str) -> bool:
    """Check that ``value`` is a valid ``xs:unsignedInt``."""
    if not matches_xs_unsigned_int(value):
        return False

    converted = int(value)
    return 0 <= converted <= 4294967295


def is_xs_unsigned_short(value: str) -> bool:
    """Check that ``value`` is a valid ``xs:unsignedShort``."""
    if not matches_xs_unsigned_short(value):
        return False

    converted = int(value)
    return 0 <= converted <= 65535


def is_xs_unsigned_byte(value: str) -> bool:
    """Check that ``value`` is a valid ``xs:unsignedByte``."""
    if not matches_xs_unsigned_byte(value):
        return False

    converted = int(value)
    return 0 <= converted <= 255


_DATA_TYPE_DEF_XSD_TO_VALUE_CONSISTENCY: Final[Mapping[str, Callable[[str], bool]]] = {
    "xs:anyURI": matches_xs_any_uri,
    "xs:base64Binary": matches_xs_base_64_binary,
    "xs:boolean": matches_xs_boolean,
    "xs:byte": is_xs_byte,
    "xs:date": is_xs_date,
    "xs:dateTime": is_xs_date_time,
    "xs:decimal": matches_xs_decimal,
    "xs:double": is_xs_double,
    "xs:duration": matches_xs_duration,
    "xs:float": is_xs_float,
    "xs:gDay": matches_xs_g_day,
    "xs:gMonth": matches_xs_g_month,
    "xs:gMonthDay": is_xs_g_month_day,
    "xs:gYear": matches_xs_g_year,
    "xs:gYearMonth": matches_xs_g_year_month,
    "xs:hexBinary": matches_xs_hex_binary,
    "xs:int": is_xs_int,
    "xs:integer": matches_xs_integer,
    "xs:long": is_xs_long,
    "xs:negativeInteger": matches_xs_negative_integer,
    "xs:nonNegativeInteger": matches_xs_non_negative_integer,
    "xs:nonPositiveInteger": matches_xs_non_positive_integer,
    "xs:positiveInteger": matches_xs_positive_integer,
    "xs:short": is_xs_short,
    "xs:string": matches_xs_string,
    "xs:time": matches_xs_time,
    "xs:unsignedByte": is_xs_unsigned_byte,
    "xs:unsignedInt": is_xs_unsigned_int,
    "xs:unsignedLong": is_xs_unsigned_long,
    "xs:unsignedShort": is_xs_unsigned_short,
}
assert XSD_TYPE_SET == frozenset(_DATA_TYPE_DEF_XSD_TO_VALUE_CONSISTENCY.keys())


@require(lambda value_type: value_type in XSD_TYPE_SET)
def value_consistent_with_xsd_type(value: str, value_type: str) -> bool:
    """
    Check that ``value`` is consistent with the given
    ``value_type``.
    """
    return _DATA_TYPE_DEF_XSD_TO_VALUE_CONSISTENCY[value_type](value)


# endregion Verification
