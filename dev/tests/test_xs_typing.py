# pylint: disable=missing-docstring

import base64
import datetime
import decimal
import unittest
from typing import Iterable, Tuple

from aas_core_testdatagen.xs_typing import (
    compare,
    Comparison,
    is_xs_double,
    is_xs_float,
    parse_date_time_to_seconds_since_epoch,
    value_consistent_with_xsd_type,
)


class TestCompare(unittest.TestCase):
    def test_xs_boolean(self) -> None:
        # Test true/false
        self.assertEqual(compare("true", "false", "xs:boolean"), Comparison.GREATER)
        self.assertEqual(compare("false", "true", "xs:boolean"), Comparison.LESS)
        self.assertEqual(compare("true", "true", "xs:boolean"), Comparison.EQUAL)
        self.assertEqual(compare("false", "false", "xs:boolean"), Comparison.EQUAL)

        # Test 1/0 format
        self.assertEqual(compare("1", "0", "xs:boolean"), Comparison.GREATER)
        self.assertEqual(compare("0", "1", "xs:boolean"), Comparison.LESS)
        self.assertEqual(compare("1", "1", "xs:boolean"), Comparison.EQUAL)
        self.assertEqual(compare("0", "0", "xs:boolean"), Comparison.EQUAL)

        # Test mixed formats
        self.assertEqual(compare("true", "0", "xs:boolean"), Comparison.GREATER)
        self.assertEqual(compare("1", "false", "xs:boolean"), Comparison.GREATER)
        self.assertEqual(compare("true", "1", "xs:boolean"), Comparison.EQUAL)
        self.assertEqual(compare("false", "0", "xs:boolean"), Comparison.EQUAL)

    def test_xs_byte(self) -> None:
        self.assertEqual(compare("5", "10", "xs:byte"), Comparison.LESS)
        self.assertEqual(compare("10", "5", "xs:byte"), Comparison.GREATER)
        self.assertEqual(compare("5", "5", "xs:byte"), Comparison.EQUAL)

        # Edge cases
        self.assertEqual(compare("-128", "127", "xs:byte"), Comparison.LESS)
        self.assertEqual(compare("0", "-1", "xs:byte"), Comparison.GREATER)
        self.assertEqual(compare("+5", "5", "xs:byte"), Comparison.EQUAL)

    def test_xs_short(self) -> None:
        self.assertEqual(compare("100", "200", "xs:short"), Comparison.LESS)
        self.assertEqual(compare("200", "100", "xs:short"), Comparison.GREATER)
        self.assertEqual(compare("100", "100", "xs:short"), Comparison.EQUAL)

        # Edge cases
        self.assertEqual(compare("-32768", "32767", "xs:short"), Comparison.LESS)
        self.assertEqual(compare("+100", "100", "xs:short"), Comparison.EQUAL)

    def test_xs_int(self) -> None:
        self.assertEqual(compare("5", "10", "xs:int"), Comparison.LESS)
        self.assertEqual(compare("10", "5", "xs:int"), Comparison.GREATER)
        self.assertEqual(compare("5", "5", "xs:int"), Comparison.EQUAL)

        # Test negative numbers
        self.assertEqual(compare("-5", "5", "xs:int"), Comparison.LESS)
        self.assertEqual(compare("5", "-5", "xs:int"), Comparison.GREATER)
        self.assertEqual(compare("-5", "-5", "xs:int"), Comparison.EQUAL)

        # Test zero variations
        self.assertEqual(compare("0", "1", "xs:int"), Comparison.LESS)
        self.assertEqual(compare("1", "0", "xs:int"), Comparison.GREATER)
        self.assertEqual(compare("0", "0", "xs:int"), Comparison.EQUAL)
        self.assertEqual(compare("+0", "0", "xs:int"), Comparison.EQUAL)
        self.assertEqual(compare("-0", "0", "xs:int"), Comparison.EQUAL)

        # Test leading zeros and signs
        self.assertEqual(compare("005", "5", "xs:int"), Comparison.EQUAL)
        self.assertEqual(compare("+5", "5", "xs:int"), Comparison.EQUAL)
        self.assertEqual(compare("00010", "10", "xs:int"), Comparison.EQUAL)

    def test_xs_long(self) -> None:
        self.assertEqual(compare("1000000", "2000000", "xs:long"), Comparison.LESS)
        self.assertEqual(compare("2000000", "1000000", "xs:long"), Comparison.GREATER)
        self.assertEqual(compare("1000000", "1000000", "xs:long"), Comparison.EQUAL)

        # Very large numbers
        self.assertEqual(
            compare("999999999999999999", "1000000000000000000", "xs:long"),
            Comparison.LESS,
        )

    def test_xs_integer(self) -> None:
        self.assertEqual(compare("5", "10", "xs:integer"), Comparison.LESS)
        self.assertEqual(compare("10", "5", "xs:integer"), Comparison.GREATER)
        self.assertEqual(compare("5", "5", "xs:integer"), Comparison.EQUAL)

        # Very large numbers
        self.assertEqual(
            compare("999999999999999999", "1000000000000000000", "xs:integer"),
            Comparison.LESS,
        )

    def test_xs_unsigned_byte(self) -> None:
        self.assertEqual(compare("5", "10", "xs:unsignedByte"), Comparison.LESS)
        self.assertEqual(compare("10", "5", "xs:unsignedByte"), Comparison.GREATER)
        self.assertEqual(compare("5", "5", "xs:unsignedByte"), Comparison.EQUAL)

        # Edge cases
        self.assertEqual(compare("0", "255", "xs:unsignedByte"), Comparison.LESS)

    def test_xs_unsigned_short(self) -> None:
        self.assertEqual(compare("100", "200", "xs:unsignedShort"), Comparison.LESS)
        self.assertEqual(compare("200", "100", "xs:unsignedShort"), Comparison.GREATER)
        self.assertEqual(compare("100", "100", "xs:unsignedShort"), Comparison.EQUAL)

    def test_xs_unsigned_int(self) -> None:
        self.assertEqual(compare("1000", "2000", "xs:unsignedInt"), Comparison.LESS)
        self.assertEqual(compare("2000", "1000", "xs:unsignedInt"), Comparison.GREATER)
        self.assertEqual(compare("1000", "1000", "xs:unsignedInt"), Comparison.EQUAL)

    def test_xs_unsigned_long(self) -> None:
        self.assertEqual(
            compare("1000000", "2000000", "xs:unsignedLong"), Comparison.LESS
        )
        self.assertEqual(
            compare("2000000", "1000000", "xs:unsignedLong"), Comparison.GREATER
        )
        self.assertEqual(
            compare("1000000", "1000000", "xs:unsignedLong"), Comparison.EQUAL
        )

    def test_xs_positive_integer(self) -> None:
        self.assertEqual(compare("1", "10", "xs:positiveInteger"), Comparison.LESS)
        self.assertEqual(compare("10", "1", "xs:positiveInteger"), Comparison.GREATER)
        self.assertEqual(compare("5", "5", "xs:positiveInteger"), Comparison.EQUAL)

    def test_xs_non_positive_integer(self) -> None:
        self.assertEqual(compare("-10", "-5", "xs:nonPositiveInteger"), Comparison.LESS)
        self.assertEqual(
            compare("-5", "-10", "xs:nonPositiveInteger"), Comparison.GREATER
        )
        self.assertEqual(compare("0", "0", "xs:nonPositiveInteger"), Comparison.EQUAL)
        self.assertEqual(compare("-5", "0", "xs:nonPositiveInteger"), Comparison.LESS)

    def test_xs_negative_integer(self) -> None:
        self.assertEqual(compare("-10", "-5", "xs:negativeInteger"), Comparison.LESS)
        self.assertEqual(compare("-5", "-10", "xs:negativeInteger"), Comparison.GREATER)
        self.assertEqual(compare("-5", "-5", "xs:negativeInteger"), Comparison.EQUAL)

    def test_xs_non_negative_integer(self) -> None:
        self.assertEqual(compare("0", "10", "xs:nonNegativeInteger"), Comparison.LESS)
        self.assertEqual(
            compare("10", "0", "xs:nonNegativeInteger"), Comparison.GREATER
        )
        self.assertEqual(compare("5", "5", "xs:nonNegativeInteger"), Comparison.EQUAL)

    def test_xs_decimal(self) -> None:
        self.assertEqual(compare("5.5", "10.1", "xs:decimal"), Comparison.LESS)
        self.assertEqual(compare("10.1", "5.5", "xs:decimal"), Comparison.GREATER)
        self.assertEqual(compare("5.5", "5.5", "xs:decimal"), Comparison.EQUAL)

        # Edge cases with decimal formatting
        self.assertEqual(compare("0.0", "0.00", "xs:decimal"), Comparison.EQUAL)
        self.assertEqual(compare("000.0", "0.0", "xs:decimal"), Comparison.EQUAL)
        self.assertEqual(compare("+001.00", "1", "xs:decimal"), Comparison.EQUAL)
        self.assertEqual(compare("5.000", "5", "xs:decimal"), Comparison.EQUAL)
        self.assertEqual(compare("-0.0", "0.0", "xs:decimal"), Comparison.EQUAL)

        # Very small decimals
        self.assertEqual(compare("0.000001", "0.000002", "xs:decimal"), Comparison.LESS)
        self.assertEqual(compare("0.999999", "1.0", "xs:decimal"), Comparison.LESS)

    def test_xs_float(self) -> None:
        self.assertEqual(compare("3.14", "3.15", "xs:float"), Comparison.LESS)
        self.assertEqual(compare("3.15", "3.14", "xs:float"), Comparison.GREATER)
        self.assertEqual(compare("3.14", "3.14", "xs:float"), Comparison.EQUAL)

        # Scientific notation
        self.assertEqual(compare("1e2", "200", "xs:float"), Comparison.LESS)
        self.assertEqual(compare("1e3", "500", "xs:float"), Comparison.GREATER)
        self.assertEqual(compare("12e-12", "1e-11", "xs:float"), Comparison.GREATER)
        self.assertEqual(compare("1.5e2", "150", "xs:float"), Comparison.EQUAL)

        # Edge cases
        self.assertEqual(compare("0.0", "-0.0", "xs:float"), Comparison.EQUAL)
        self.assertEqual(compare("+0.0", "0.0", "xs:float"), Comparison.EQUAL)

        # Special values
        self.assertEqual(compare("INF", "1000000", "xs:float"), Comparison.GREATER)
        self.assertEqual(compare("-INF", "-1000000", "xs:float"), Comparison.LESS)
        self.assertEqual(compare("INF", "-INF", "xs:float"), Comparison.GREATER)
        # Note: NaN handling depends on decimal module implementation
        # Skipping NaN tests as they may cause InvalidOperation

    def test_xs_double(self) -> None:
        self.assertEqual(
            compare("3.141592653589793", "3.141592653589794", "xs:double"),
            Comparison.LESS,
        )
        self.assertEqual(
            compare("3.141592653589794", "3.141592653589793", "xs:double"),
            Comparison.GREATER,
        )
        self.assertEqual(
            compare("3.141592653589793", "3.141592653589793", "xs:double"),
            Comparison.EQUAL,
        )

        # Scientific notation
        self.assertEqual(compare("1e2", "200", "xs:double"), Comparison.LESS)
        self.assertEqual(compare("1e3", "500", "xs:double"), Comparison.GREATER)
        self.assertEqual(compare("12e-12", "1.2e-11", "xs:double"), Comparison.EQUAL)

        # Special values
        self.assertEqual(compare("INF", "1000000", "xs:double"), Comparison.GREATER)
        self.assertEqual(compare("-INF", "-1000000", "xs:double"), Comparison.LESS)
        self.assertEqual(compare("INF", "-INF", "xs:double"), Comparison.GREATER)
        # Note: NaN handling depends on decimal module implementation
        # Skipping NaN tests as they may cause InvalidOperation

    def test_xs_string(self) -> None:
        self.assertEqual(compare("apple", "banana", "xs:string"), Comparison.LESS)
        self.assertEqual(compare("banana", "apple", "xs:string"), Comparison.GREATER)
        self.assertEqual(compare("apple", "apple", "xs:string"), Comparison.EQUAL)

        # Empty strings
        self.assertEqual(compare("", "a", "xs:string"), Comparison.LESS)
        self.assertEqual(compare("a", "", "xs:string"), Comparison.GREATER)
        self.assertEqual(compare("", "", "xs:string"), Comparison.EQUAL)

        # Special characters
        self.assertEqual(
            compare("Hello World", "Hello World!", "xs:string"), Comparison.LESS
        )
        self.assertEqual(
            compare("abc", "ABC", "xs:string"), Comparison.GREATER
        )  # lowercase > uppercase

    def test_xs_any_uri(self) -> None:
        self.assertEqual(
            compare("http://example.com", "http://test.com", "xs:anyURI"),
            Comparison.LESS,
        )
        self.assertEqual(
            compare("http://test.com", "http://example.com", "xs:anyURI"),
            Comparison.GREATER,
        )
        self.assertEqual(
            compare("http://example.com", "http://example.com", "xs:anyURI"),
            Comparison.EQUAL,
        )

        # Different protocols
        self.assertEqual(
            compare("ftp://example.com", "http://example.com", "xs:anyURI"),
            Comparison.LESS,
        )
        self.assertEqual(
            compare("https://example.com", "http://example.com", "xs:anyURI"),
            Comparison.GREATER,
        )

    def test_xs_base64_binary(self) -> None:
        val1 = base64.b64encode(b"hello").decode()  # aGVsbG8=
        val2 = base64.b64encode(b"world").decode()  # d29ybGQ=
        val3 = base64.b64encode(b"hello").decode()  # aGVsbG8=

        self.assertEqual(compare(val1, val2, "xs:base64Binary"), Comparison.LESS)
        self.assertEqual(compare(val2, val1, "xs:base64Binary"), Comparison.GREATER)
        self.assertEqual(compare(val1, val3, "xs:base64Binary"), Comparison.EQUAL)

        # Empty binary data
        empty = base64.b64encode(b"").decode()
        self.assertEqual(compare(empty, val1, "xs:base64Binary"), Comparison.LESS)

    def test_xs_hex_binary(self) -> None:
        self.assertEqual(
            compare("48656c6c6f", "576f726c64", "xs:hexBinary"), Comparison.LESS
        )  # hello vs world
        self.assertEqual(
            compare("576f726c64", "48656c6c6f", "xs:hexBinary"), Comparison.GREATER
        )
        self.assertEqual(
            compare("48656c6c6f", "48656c6c6f", "xs:hexBinary"), Comparison.EQUAL
        )

        # Case sensitivity test
        self.assertEqual(
            compare("48656c6c6f", "48656C6C6F", "xs:hexBinary"), Comparison.GREATER
        )  # lowercase vs uppercase

    def test_xs_date(self) -> None:
        self.assertEqual(
            compare("2023-01-01", "2023-12-31", "xs:date"), Comparison.LESS
        )
        self.assertEqual(
            compare("2023-12-31", "2023-01-01", "xs:date"), Comparison.GREATER
        )
        self.assertEqual(
            compare("2023-01-01", "2023-01-01", "xs:date"), Comparison.EQUAL
        )

        # Different years
        self.assertEqual(
            compare("2022-12-31", "2023-01-01", "xs:date"), Comparison.LESS
        )
        self.assertEqual(
            compare("2023-01-01", "2022-12-31", "xs:date"), Comparison.GREATER
        )

        # Leap year edge case
        self.assertEqual(
            compare("2020-02-29", "2020-03-01", "xs:date"), Comparison.LESS
        )

        # Negative years (BCE)
        self.assertEqual(
            compare("-0001-01-01", "0001-01-01", "xs:date"), Comparison.LESS
        )
        self.assertEqual(
            compare("0001-01-01", "-0001-01-01", "xs:date"), Comparison.GREATER
        )
        self.assertEqual(
            compare("-0001-01-01", "-0001-01-01", "xs:date"), Comparison.EQUAL
        )
        # Different BCE years
        self.assertEqual(
            compare("-0002-01-01", "-0001-01-01", "xs:date"), Comparison.LESS
        )
        # BCE leap year edge case (year -4 is 4 BCE, a leap year)
        self.assertEqual(
            compare("-0004-02-29", "-0004-03-01", "xs:date"), Comparison.LESS
        )

    def test_xs_date_time(self) -> None:
        self.assertEqual(
            compare("2023-01-01T10:00:00", "2023-01-01T11:00:00", "xs:dateTime"),
            Comparison.LESS,
        )
        self.assertEqual(
            compare("2023-01-01T11:00:00", "2023-01-01T10:00:00", "xs:dateTime"),
            Comparison.GREATER,
        )
        self.assertEqual(
            compare("2023-01-01T10:00:00", "2023-01-01T10:00:00", "xs:dateTime"),
            Comparison.EQUAL,
        )

        # With timezone
        self.assertEqual(
            compare("2023-01-01T10:00:00Z", "2023-01-01T11:00:00Z", "xs:dateTime"),
            Comparison.LESS,
        )
        self.assertEqual(
            compare("2023-01-01T11:00:00Z", "2023-01-01T10:00:00Z", "xs:dateTime"),
            Comparison.GREATER,
        )
        self.assertEqual(
            compare("2023-01-01T10:00:00Z", "2023-01-01T10:00:00Z", "xs:dateTime"),
            Comparison.EQUAL,
        )

        # Microseconds
        self.assertEqual(
            compare(
                "2023-01-01T10:00:00.123", "2023-01-01T10:00:00.124", "xs:dateTime"
            ),
            Comparison.LESS,
        )

        # Negative years (BCE)
        self.assertEqual(
            compare("-0001-01-01T00:00:00Z", "0001-01-01T00:00:00Z", "xs:dateTime"),
            Comparison.LESS,
        )
        self.assertEqual(
            compare("0001-01-01T00:00:00Z", "-0001-01-01T00:00:00Z", "xs:dateTime"),
            Comparison.GREATER,
        )
        self.assertEqual(
            compare("-0001-01-01T12:00:00Z", "-0001-01-01T12:00:00Z", "xs:dateTime"),
            Comparison.EQUAL,
        )
        # Different BCE years
        self.assertEqual(
            compare("-0002-01-01T00:00:00Z", "-0001-01-01T00:00:00Z", "xs:dateTime"),
            Comparison.LESS,
        )
        # BCE leap year with fractional seconds
        self.assertEqual(
            compare(
                "-0004-02-29T12:00:00.123Z", "-0004-02-29T12:00:00.124Z", "xs:dateTime"
            ),
            Comparison.LESS,
        )
        # BCE vs CE with same date different times
        self.assertEqual(
            compare("-0001-06-15T12:00:00Z", "0001-06-15T12:00:00Z", "xs:dateTime"),
            Comparison.LESS,
        )

    def test_xs_time(self) -> None:
        self.assertEqual(compare("10:00:00", "11:00:00", "xs:time"), Comparison.LESS)
        self.assertEqual(compare("11:00:00", "10:00:00", "xs:time"), Comparison.GREATER)
        self.assertEqual(compare("10:00:00", "10:00:00", "xs:time"), Comparison.EQUAL)

        # With seconds and microseconds
        self.assertEqual(compare("10:00:30", "10:00:45", "xs:time"), Comparison.LESS)
        self.assertEqual(compare("10:00:45", "10:00:30", "xs:time"), Comparison.GREATER)
        self.assertEqual(
            compare("10:00:00.123", "10:00:00.124", "xs:time"), Comparison.LESS
        )

    def test_xs_duration(self) -> None:
        self.assertEqual(compare("P1D", "P2D", "xs:duration"), Comparison.LESS)
        self.assertEqual(compare("P2D", "P1D", "xs:duration"), Comparison.GREATER)
        self.assertEqual(compare("P1D", "P1D", "xs:duration"), Comparison.EQUAL)

        # Hours
        self.assertEqual(compare("PT1H", "PT2H", "xs:duration"), Comparison.LESS)
        self.assertEqual(compare("PT2H", "PT1H", "xs:duration"), Comparison.GREATER)

        # Mixed units
        self.assertEqual(compare("P1DT1H", "P1DT2H", "xs:duration"), Comparison.LESS)
        self.assertEqual(compare("P1DT2H", "P1DT1H", "xs:duration"), Comparison.GREATER)

        # Years and months
        self.assertEqual(compare("P1Y", "P2Y", "xs:duration"), Comparison.LESS)
        self.assertEqual(compare("P1M", "P2M", "xs:duration"), Comparison.LESS)

        # Complex durations
        self.assertEqual(
            compare("P1Y2M3DT4H5M6S", "P1Y2M3DT4H5M7S", "xs:duration"), Comparison.LESS
        )

    def test_xs_g_year(self) -> None:
        self.assertEqual(compare("2023", "2024", "xs:gYear"), Comparison.LESS)
        self.assertEqual(compare("2024", "2023", "xs:gYear"), Comparison.GREATER)
        self.assertEqual(compare("2023", "2023", "xs:gYear"), Comparison.EQUAL)

        # With timezone
        self.assertEqual(compare("2023Z", "2024+05:00", "xs:gYear"), Comparison.LESS)
        self.assertEqual(
            compare("2023+01:00", "2023-01:00", "xs:gYear"), Comparison.LESS
        )

        # Negative years (BCE)
        self.assertEqual(compare("-0001", "0001", "xs:gYear"), Comparison.LESS)
        self.assertEqual(compare("0001", "-0001", "xs:gYear"), Comparison.GREATER)
        self.assertEqual(compare("-0001", "-0001", "xs:gYear"), Comparison.EQUAL)
        # Different BCE years
        self.assertEqual(compare("-0002", "-0001", "xs:gYear"), Comparison.LESS)
        self.assertEqual(compare("-0001", "-0002", "xs:gYear"), Comparison.GREATER)
        # BCE with timezone
        self.assertEqual(
            compare("-0001Z", "-0001+05:00", "xs:gYear"), Comparison.GREATER
        )
        self.assertEqual(
            compare("-0001+01:00", "-0001-01:00", "xs:gYear"), Comparison.LESS
        )
        # BCE vs CE with timezone
        self.assertEqual(compare("-0001Z", "0001+05:00", "xs:gYear"), Comparison.LESS)

    def test_xs_g_year_month(self) -> None:
        self.assertEqual(
            compare("2023-01", "2023-12", "xs:gYearMonth"), Comparison.LESS
        )
        self.assertEqual(
            compare("2023-12", "2023-01", "xs:gYearMonth"), Comparison.GREATER
        )
        self.assertEqual(
            compare("2023-01", "2023-01", "xs:gYearMonth"), Comparison.EQUAL
        )

        # Different years
        self.assertEqual(
            compare("2022-12", "2023-01", "xs:gYearMonth"), Comparison.LESS
        )

        # With timezone
        self.assertEqual(
            compare("2023-01Z", "2023-01+05:00", "xs:gYearMonth"), Comparison.GREATER
        )

        # Negative years (BCE)
        self.assertEqual(
            compare("-0001-01", "0001-01", "xs:gYearMonth"), Comparison.LESS
        )
        self.assertEqual(
            compare("0001-01", "-0001-01", "xs:gYearMonth"), Comparison.GREATER
        )
        self.assertEqual(
            compare("-0001-01", "-0001-01", "xs:gYearMonth"), Comparison.EQUAL
        )
        # Different BCE years
        self.assertEqual(
            compare("-0002-12", "-0001-01", "xs:gYearMonth"), Comparison.LESS
        )
        # Same BCE year, different months
        self.assertEqual(
            compare("-0001-01", "-0001-12", "xs:gYearMonth"), Comparison.LESS
        )
        # BCE with timezone
        self.assertEqual(
            compare("-0001-01Z", "-0001-01+05:00", "xs:gYearMonth"), Comparison.GREATER
        )
        # BCE vs CE with same month
        self.assertEqual(
            compare("-0001-06", "0001-06", "xs:gYearMonth"), Comparison.LESS
        )

    def test_xs_g_month(self) -> None:
        self.assertEqual(compare("--01", "--12", "xs:gMonth"), Comparison.LESS)
        self.assertEqual(compare("--12", "--01", "xs:gMonth"), Comparison.GREATER)
        self.assertEqual(compare("--01", "--01", "xs:gMonth"), Comparison.EQUAL)

        # With timezone
        self.assertEqual(
            compare("--01Z", "--01+05:00", "xs:gMonth"), Comparison.GREATER
        )

    def test_xs_g_month_day(self) -> None:
        self.assertEqual(compare("--01-01", "--12-31", "xs:gMonthDay"), Comparison.LESS)
        self.assertEqual(
            compare("--12-31", "--01-01", "xs:gMonthDay"), Comparison.GREATER
        )
        self.assertEqual(
            compare("--01-01", "--01-01", "xs:gMonthDay"), Comparison.EQUAL
        )

        # Same month, different day
        self.assertEqual(compare("--06-15", "--06-16", "xs:gMonthDay"), Comparison.LESS)

        # With timezone
        self.assertEqual(
            compare("--06-15Z", "--06-15+05:00", "xs:gMonthDay"), Comparison.GREATER
        )

    def test_xs_g_day(self) -> None:
        self.assertEqual(compare("---01", "---31", "xs:gDay"), Comparison.LESS)
        self.assertEqual(compare("---31", "---01", "xs:gDay"), Comparison.GREATER)
        self.assertEqual(compare("---01", "---01", "xs:gDay"), Comparison.EQUAL)

        # With timezone
        self.assertEqual(
            compare("---15Z", "---15+05:00", "xs:gDay"), Comparison.GREATER
        )

    def test_edge_cases_numeric_formatting(self) -> None:
        # Leading zeros
        numeric_types = ["xs:int", "xs:integer", "xs:long", "xs:short", "xs:byte"]
        for num_type in numeric_types:
            with self.subTest(num_type=num_type):
                self.assertEqual(compare("005", "5", num_type), Comparison.EQUAL)
                self.assertEqual(compare("000", "0", num_type), Comparison.EQUAL)
                self.assertEqual(compare("+5", "5", num_type), Comparison.EQUAL)

        # Decimal types with various formatting
        decimal_types = ["xs:decimal", "xs:float", "xs:double"]
        for dec_type in decimal_types:
            with self.subTest(dec_type=dec_type):
                self.assertEqual(compare("5.0", "5", dec_type), Comparison.EQUAL)
                self.assertEqual(compare("5.00", "5.0", dec_type), Comparison.EQUAL)
                self.assertEqual(compare("+5.0", "5.0", dec_type), Comparison.EQUAL)
                self.assertEqual(compare("-0.0", "0.0", dec_type), Comparison.EQUAL)

    def test_xs_float_nan_cases(self) -> None:
        # NaN vs NaN should return None.
        result = compare("NaN", "NaN", "xs:float")
        self.assertIsNone(result)

        # NaN vs normal number should return None.
        result = compare("NaN", "1.5", "xs:float")
        self.assertIsNone(result)

        # Normal number vs NaN should return None.
        result = compare("2.3", "NaN", "xs:float")
        self.assertIsNone(result)

    def test_xs_double_nan_cases(self) -> None:
        # NaN vs NaN should return None.
        result = compare("NaN", "NaN", "xs:double")
        self.assertIsNone(result)

        # NaN vs normal number should return None.
        result = compare("NaN", "1.5", "xs:double")
        self.assertIsNone(result)

        # Normal number vs NaN should return None.
        result = compare("2.3", "NaN", "xs:double")
        self.assertIsNone(result)

    def test_nan_case_insensitive(self) -> None:
        # Test different NaN representations
        nan_variations = ["NaN", "nan", "NAN"]

        for nan_str in nan_variations:
            with self.subTest(nan=nan_str):
                # xs:float
                result = compare(nan_str, "1.0", "xs:float")
                self.assertIsNone(result)

                result = compare("1.0", nan_str, "xs:float")
                self.assertIsNone(result)

                # xs:double
                result = compare(nan_str, "1.0", "xs:double")
                self.assertIsNone(result)

                result = compare("1.0", nan_str, "xs:double")
                self.assertIsNone(result)

    def test_infinity_handling(self) -> None:
        result = compare("INF", "1.0", "xs:float")
        self.assertEqual(result, Comparison.GREATER)

        result = compare("1.0", "INF", "xs:float")
        self.assertEqual(result, Comparison.LESS)

        result = compare("-INF", "1.0", "xs:float")
        self.assertEqual(result, Comparison.LESS)

        result = compare("1.0", "-INF", "xs:float")
        self.assertEqual(result, Comparison.GREATER)

        # Same for xs:double
        result = compare("INF", "1.0", "xs:double")
        self.assertEqual(result, Comparison.GREATER)

        result = compare("-INF", "1.0", "xs:double")
        self.assertEqual(result, Comparison.LESS)


class TestParseDateTimeToSecondsSinceEpoch(unittest.TestCase):
    def test_epoch_reference(self) -> None:
        result = parse_date_time_to_seconds_since_epoch("1970-01-01T00:00:00Z")
        self.assertEqual(result, decimal.Decimal("0"))

        # Test with explicit UTC
        result = parse_date_time_to_seconds_since_epoch("1970-01-01T00:00:00+00:00")
        self.assertEqual(result, decimal.Decimal("0"))

    def test_positive_leap_year(self) -> None:
        # 2000 is a leap year (divisible by 400)
        # Test February 29, 2000
        result = parse_date_time_to_seconds_since_epoch("2000-02-29T12:00:00Z")

        # Validate against datetime module
        dt = datetime.datetime(2000, 2, 29, 12, 0, 0, tzinfo=datetime.timezone.utc)
        expected = decimal.Decimal(dt.timestamp())
        self.assertEqual(result, expected)

    def test_positive_non_leap_year(self) -> None:
        # 1999 is not a leap year
        result = parse_date_time_to_seconds_since_epoch("1999-12-31T23:59:59Z")

        # Validate against datetime module
        dt = datetime.datetime(1999, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
        expected = decimal.Decimal(dt.timestamp())
        self.assertEqual(result, expected)

    def test_negative_leap_year(self) -> None:
        # Year 4 BCE (-4 in ISO format) is a leap year
        result = parse_date_time_to_seconds_since_epoch("-0004-02-29T12:00:00Z")

        # Since datetime module doesn't support negative years, we calculate manually.

        # We test that the result is negative (before epoch) and reasonable
        self.assertLess(result, decimal.Decimal("0"))

        # Basic validation: should be about 1974 years before epoch
        # Roughly -1974 * 365.25 * 24 * 3600 ≈ -62,265,600,000 seconds
        expected_approx = decimal.Decimal("-62000000000")  # Rough estimate
        self.assertLess(result, expected_approx * decimal.Decimal("0.8"))
        self.assertGreater(result, expected_approx * decimal.Decimal("1.2"))

    def test_negative_non_leap_year(self) -> None:
        # Year 1 BCE (-0 doesn't exist, so we use -1)
        result = parse_date_time_to_seconds_since_epoch("-0001-06-15T12:00:00Z")

        # Should be negative and about 1971 years before epoch
        self.assertLess(result, decimal.Decimal("0"))

        # Basic validation: should be about 1974 years before epoch
        # Roughly -1971 * 365.25 * 24 * 3600 ≈ -62,200,029,600
        expected_approx = decimal.Decimal("-62000000000")  # Rough estimate
        self.assertLess(result, expected_approx * decimal.Decimal("0.8"))
        self.assertGreater(result, expected_approx * decimal.Decimal("1.2"))

    def test_timezone_plus_02_00(self) -> None:
        # Test with +02:00 timezone
        result = parse_date_time_to_seconds_since_epoch("2023-06-15T12:00:00+02:00")

        # Same time in UTC should be 10:00:00
        result_utc = parse_date_time_to_seconds_since_epoch("2023-06-15T10:00:00Z")
        self.assertEqual(result, result_utc)

        # Validate against datetime module
        dt = datetime.datetime(
            2023, 6, 15, 12, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=2))
        )
        expected = decimal.Decimal(dt.timestamp())
        self.assertEqual(result, expected)

    def test_extreme_timezone_plus_14_00(self) -> None:
        # Test with extreme positive timezone +14:00
        result = parse_date_time_to_seconds_since_epoch("2023-06-15T12:00:00+14:00")

        # Same time in UTC should be 22:00:00 previous day
        result_utc = parse_date_time_to_seconds_since_epoch("2023-06-14T22:00:00Z")
        self.assertEqual(result, result_utc)

    def test_extreme_timezone_minus_12_00(self) -> None:
        # Test with extreme negative timezone -12:00
        result = parse_date_time_to_seconds_since_epoch("2023-06-15T12:00:00-12:00")

        # Same time in UTC should be 00:00:00 next day
        result_utc = parse_date_time_to_seconds_since_epoch("2023-06-16T00:00:00Z")
        self.assertEqual(result, result_utc)

    def test_z_timezone(self) -> None:
        # Test Z timezone (UTC)
        result = parse_date_time_to_seconds_since_epoch("2023-06-15T12:00:00Z")
        result_explicit = parse_date_time_to_seconds_since_epoch(
            "2023-06-15T12:00:00+00:00"
        )
        self.assertEqual(result, result_explicit)

        # Validate against datetime module
        dt = datetime.datetime(2023, 6, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        expected = decimal.Decimal(dt.timestamp())
        self.assertEqual(result, expected)

    def test_nanosecond_fractions(self) -> None:
        # Test with nanosecond precision (9 digits after decimal)
        result = parse_date_time_to_seconds_since_epoch(
            "2023-06-15T12:00:00.123456789Z"
        )

        # Compare with base time (no fractions)
        base_result = parse_date_time_to_seconds_since_epoch("2023-06-15T12:00:00Z")

        # Difference should be exactly 0.123456789 seconds
        expected_diff = decimal.Decimal("0.123456789")
        actual_diff = result - base_result
        self.assertEqual(actual_diff, expected_diff)

    def test_datetime_module_comparison(self) -> None:
        # Test several dates against datetime module
        test_cases = [
            "2023-01-01T00:00:00Z",
            "2023-12-31T23:59:59Z",
            "2000-02-29T12:00:00Z",  # Leap year
            "2001-02-28T12:00:00Z",  # Non-leap year
            "1980-06-15T18:30:45Z",
            "2050-12-25T06:15:30Z",
        ]

        for date_str in test_cases:
            with self.subTest(date_str=date_str):
                result = parse_date_time_to_seconds_since_epoch(date_str)

                # Parse with datetime module
                dt = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                expected = decimal.Decimal(dt.timestamp())

                self.assertEqual(
                    result,
                    expected,
                    f"Mismatch for {date_str}: got {result}, expected {expected}",
                )

    def test_datetime_module_comparison_with_timezones(self) -> None:
        # Test timezone handling against datetime module
        test_cases = [
            ("2023-06-15T12:00:00+02:00", "2023-06-15T10:00:00Z"),
            ("2023-06-15T12:00:00-05:00", "2023-06-15T17:00:00Z"),
            ("2023-06-15T12:00:00+05:30", "2023-06-15T06:30:00Z"),
        ]

        for local_str, utc_str in test_cases:
            with self.subTest(local=local_str, utc=utc_str):
                result_local = parse_date_time_to_seconds_since_epoch(local_str)
                result_utc = parse_date_time_to_seconds_since_epoch(utc_str)

                # Both should give same result
                self.assertEqual(result_local, result_utc)

                # Validate against datetime module
                dt = datetime.datetime.fromisoformat(local_str)
                expected = decimal.Decimal(dt.timestamp())
                self.assertEqual(result_local, expected)

    def test_error_cases(self) -> None:
        # Test various invalid formats
        invalid_cases = [
            "2023-13-01T00:00:00Z",  # Invalid month
            "2023-02-30T00:00:00Z",  # Invalid day for February
            "2023-06-15T25:00:00Z",  # Invalid hour
            "2023-06-15T12:60:00Z",  # Invalid minute
            "2023-06-15T12:00:60Z",  # Invalid second
            "2023-06-15 12:00:00Z",  # Missing T
            "not-a-date",  # Invalid format
            "",  # Empty string
        ]

        for invalid_date in invalid_cases:
            with self.subTest(invalid_date=invalid_date):
                with self.assertRaises(ValueError):
                    parse_date_time_to_seconds_since_epoch(invalid_date)


class TestValueConsistentWithXsdType(unittest.TestCase):
    def _assert_cases(
        self,
        value_type: str,
        values_expectations_descriptions: Iterable[Tuple[str, bool, str]],
    ) -> None:
        """
        Iterate over (value, expectation, description) and check individually.
        """
        for value, expectation, description in values_expectations_descriptions:
            with self.subTest(
                value_type=value_type,
                value=value,
                description=description,
            ):
                self.assertEqual(
                    expectation,
                    value_consistent_with_xsd_type(
                        value=value,
                        value_type=value_type,
                    ),
                )

    def test_xs_any_uri(self) -> None:
        self._assert_cases(
            "xs:anyURI",
            [
                ("", True, "empty string allowed"),
                ("http://example.com", True, "absolute HTTP URI"),
                (
                    "https://example.com/path?x=1#frag",
                    True,
                    "URI with query and fragment",
                ),
                ("/relative/path", True, "relative reference"),
                ("#only-fragment", True, "fragment-only reference"),
                ("http://[::1]/", True, "IPv6 literal host"),
                ("not a uri with spaces", False, "spaces not allowed"),
                ("http://exa mple.com", False, "space inside URI"),
                ("\n", False, "newline not allowed"),
            ],
        )

    def test_xs_base64_binary(self) -> None:
        self._assert_cases(
            "xs:base64Binary",
            [
                ("", True, "empty string allowed"),
                ("TQ==", True, "single byte"),
                ("TWE=", True, "two bytes"),
                ("TWFu", True, "three bytes"),
                ("TQ= =", True, "whitespace allowed"),
                ("!!!!", False, "invalid characters"),
                ("TQ==\n", False, "newline not allowed"),
            ],
        )

    def test_xs_boolean(self) -> None:
        self._assert_cases(
            "xs:boolean",
            [
                ("true", True, "canonical true"),
                ("false", True, "canonical false"),
                ("1", True, "numeric true"),
                ("0", True, "numeric false"),
                ("TRUE", False, "case-sensitive lexical space"),
                ("False", False, "case-sensitive lexical space"),
                ("", False, "empty string invalid"),
                ("yes", False, "non-lexical boolean"),
            ],
        )

    def test_xs_byte(self) -> None:
        self._assert_cases(
            "xs:byte",
            [
                ("-128", True, "minimum value"),
                ("127", True, "maximum value"),
                ("0", True, "zero"),
                ("+0", True, "explicit positive zero"),
                ("000", True, "zero with leading zeros"),
                ("-129", False, "below minimum"),
                ("128", False, "above maximum"),
                ("1.0", False, "decimal not allowed"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_date(self) -> None:
        self._assert_cases(
            "xs:date",
            [
                ("2024-02-29", True, "valid leap day"),
                ("2023-02-29", False, "invalid non-leap day"),
                ("0001-01-01", True, "minimum positive year"),
                ("0000-01-01", False, "year zero forbidden"),
                ("-0001-01-01", True, "negative year allowed"),
                ("-0004-02-29", True, "negative leap year"),
                ("2023-13-01", False, "month out of range"),
                ("2023-00-01", False, "month zero invalid"),
                ("2023-01-00", False, "day zero invalid"),
                ("2023-04-31", False, "day exceeds month length"),
                ("2023-12-25Z", True, "UTC timezone"),
                ("2023-12-25+14:00", True, "maximum timezone offset"),
                ("2023-12-25-14:00", True, "minimum timezone offset"),
                ("2023-12-25+14:01", False, "timezone offset too large"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_date_time(self) -> None:
        self._assert_cases(
            "xs:dateTime",
            [
                ("2023-12-25T00:00:00", True, "valid datetime without timezone"),
                ("2023-12-25T23:59:59Z", True, "UTC datetime"),
                ("2023-12-25T24:00:00", True, "end-of-day representation"),
                ("2023-12-25T24:00:01", False, "seconds past 24:00:00"),
                ("2023-02-29T00:00:00", False, "invalid leap day"),
                ("2024-02-29T00:00:00", True, "valid leap day"),
                ("0000-01-01T00:00:00", False, "year zero forbidden"),
                ("-0001-01-01T00:00:00", True, "negative year allowed"),
                ("2023-12-25T00:00:00+02:00", True, "positive timezone offset"),
                ("2023-12-25T00:00:00+14:01", False, "timezone offset too large"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_decimal(self) -> None:
        self._assert_cases(
            "xs:decimal",
            [
                ("0", True, "zero"),
                ("+0", True, "explicit positive zero"),
                ("-0", True, "explicit negative zero"),
                ("1", True, "integer"),
                ("-1", True, "negative integer"),
                ("01", True, "leading zero allowed"),
                ("1.0", True, "decimal fraction"),
                ("-1.25", True, "negative fraction"),
                (".5", True, "leading decimal point"),
                ("1.", False, "trailing decimal point"),
                ("1e3", False, "scientific notation not allowed"),
                ("NaN", False, "NaN not allowed"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_double(self) -> None:
        self._assert_cases(
            "xs:double",
            [
                ("0", True, "zero"),
                ("-0", True, "negative zero"),
                ("1.5", True, "decimal fraction"),
                ("1e3", True, "scientific notation"),
                ("-1E-3", True, "negative scientific notation"),
                ("INF", True, "positive infinity"),
                ("-INF", True, "negative infinity"),
                ("NaN", True, "NaN literal"),
                ("nan", False, "case-sensitive NaN"),
                ("1e400", False, "overflow to infinity rejected"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_duration(self) -> None:
        self._assert_cases(
            "xs:duration",
            [
                ("P1D", True, "one day"),
                ("PT1S", True, "one second"),
                ("P3Y", True, "three years"),
                ("P2M", True, "two months"),
                ("P1DT2H3M4S", True, "full duration"),
                ("-P1D", True, "negative duration"),
                ("P0D", True, "zero duration"),
                ("P", False, "no components"),
                ("PT", False, "time designator without components"),
                ("P1Y2D3H", False, "missing T before time fields"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_float(self) -> None:
        self._assert_cases(
            "xs:float",
            [
                ("0", True, "zero"),
                ("1.5", True, "decimal fraction"),
                ("1e3", True, "scientific notation"),
                ("INF", True, "positive infinity"),
                ("-INF", True, "negative infinity"),
                ("NaN", True, "NaN literal"),
                ("nan", False, "case-sensitive NaN"),
                ("1e400", False, "overflow rejected"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_g_day(self) -> None:
        self._assert_cases(
            "xs:gDay",
            [
                ("---01", True, "first day of month"),
                ("---31", True, "last possible day"),
                ("---00", False, "day zero invalid"),
                ("---32", False, "day out of range"),
                ("---15Z", True, "UTC timezone"),
                ("---15+02:30", True, "positive timezone offset"),
                ("---15-14:00", True, "minimum timezone offset"),
                ("---15+14:01", False, "timezone offset too large"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_g_month(self) -> None:
        self._assert_cases(
            "xs:gMonth",
            [
                ("--01", True, "January"),
                ("--12", True, "December"),
                ("--00", False, "month zero invalid"),
                ("--13", False, "month out of range"),
                ("--06Z", True, "UTC timezone"),
                ("--06+02:30", True, "positive timezone offset"),
                ("--06-14:00", True, "minimum timezone offset"),
                ("--06+14:01", False, "timezone offset too large"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_g_month_day(self) -> None:
        self._assert_cases(
            "xs:gMonthDay",
            [
                ("--01-01", True, "January first"),
                ("--12-31", True, "December thirty-first"),
                ("--02-29", True, "February 29 allowed lexically"),
                ("--02-30", False, "February 30 invalid"),
                ("--04-31", False, "April has only 30 days"),
                ("--00-01", False, "month zero invalid"),
                ("--13-01", False, "month out of range"),
                ("--01-00", False, "day zero invalid"),
                ("--01-32", False, "day out of range"),
                ("--06-01Z", True, "UTC timezone"),
                ("--06-01+02:30", True, "positive timezone offset"),
                ("--06-01+14:01", False, "timezone offset too large"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_g_year(self) -> None:
        self._assert_cases(
            "xs:gYear",
            [
                ("0001", True, "minimum positive year"),
                ("0000", True, "year zero lexically allowed"),
                ("-0001", True, "negative year"),
                ("2023", True, "common year"),
                ("2023Z", True, "UTC timezone"),
                ("2023+14:00", True, "maximum timezone offset"),
                ("2023+14:01", False, "timezone offset too large"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_g_year_month(self) -> None:
        self._assert_cases(
            "xs:gYearMonth",
            [
                ("2023-01", True, "January 2023"),
                ("2023-12", True, "December 2023"),
                ("-0001-12", True, "negative year December"),
                ("0000-01", True, "year zero lexically allowed"),
                ("2023-00", False, "month zero invalid"),
                ("2023-13", False, "month out of range"),
                ("2023-01Z", True, "UTC timezone"),
                ("2023-01+14:00", True, "maximum timezone offset"),
                ("2023-01+14:01", False, "timezone offset too large"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_hex_binary(self) -> None:
        self._assert_cases(
            "xs:hexBinary",
            [
                ("", True, "empty string allowed"),
                ("00", True, "single byte"),
                ("0F", True, "uppercase hex"),
                ("0f", True, "lowercase hex"),
                ("DEADBEEF", True, "multiple bytes"),
                ("A", False, "odd number of hex digits"),
                ("GG", False, "invalid hex characters"),
                ("00 ", False, "trailing whitespace"),
            ],
        )

    def test_xs_int(self) -> None:
        self._assert_cases(
            "xs:int",
            [
                ("-2147483648", True, "minimum value"),
                ("2147483647", True, "maximum value"),
                ("2147483648", False, "above maximum"),
                ("-2147483649", False, "below minimum"),
                ("0000000001", True, "leading zeros allowed"),
                ("1.0", False, "decimal not allowed"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_integer(self) -> None:
        self._assert_cases(
            "xs:integer",
            [
                ("0", True, "zero"),
                ("+0", True, "explicit positive zero"),
                ("-0", True, "explicit negative zero"),
                ("123456789012345678901234567890", True, "unbounded positive integer"),
                ("-999999999999999999999999999999", True, "unbounded negative integer"),
                ("1.0", False, "decimal not allowed"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_long(self) -> None:
        self._assert_cases(
            "xs:long",
            [
                ("-9223372036854775808", True, "minimum value"),
                ("9223372036854775807", True, "maximum value"),
                ("9223372036854775808", False, "above maximum"),
                ("-9223372036854775809", False, "below minimum"),
                ("0001", True, "leading zeros allowed"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_negative_integer(self) -> None:
        self._assert_cases(
            "xs:negativeInteger",
            [
                ("-1", True, "negative integer"),
                ("-0001", True, "negative with leading zeros"),
                ("0", False, "zero not allowed"),
                ("-0", False, "negative zero not allowed"),
                ("+0", False, "positive zero not allowed"),
                ("1", False, "positive integer not allowed"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_non_negative_integer(self) -> None:
        self._assert_cases(
            "xs:nonNegativeInteger",
            [
                ("0", True, "zero"),
                ("-0", True, "negative zero allowed lexically"),
                ("+0", True, "positive zero"),
                ("1", True, "positive integer"),
                ("000", True, "zero with leading zeros"),
                ("-1", False, "negative integer not allowed"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_non_positive_integer(self) -> None:
        self._assert_cases(
            "xs:nonPositiveInteger",
            [
                ("0", True, "zero"),
                ("+0", True, "explicit positive zero"),
                ("-0", True, "negative zero allowed"),
                ("-1", True, "negative integer"),
                ("-999", True, "large negative integer"),
                ("1", False, "positive integer not allowed"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_positive_integer(self) -> None:
        self._assert_cases(
            "xs:positiveInteger",
            [
                ("1", True, "minimum positive integer"),
                ("+1", True, "explicit positive integer"),
                ("0001", True, "leading zeros allowed"),
                ("0", False, "zero not allowed"),
                ("-1", False, "negative integer not allowed"),
                ("+0", False, "positive zero not allowed"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_short(self) -> None:
        self._assert_cases(
            "xs:short",
            [
                ("-32768", True, "minimum value"),
                ("32767", True, "maximum value"),
                ("-32769", False, "below minimum"),
                ("32768", False, "above maximum"),
                ("00001", True, "leading zeros allowed"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_string(self) -> None:
        self._assert_cases(
            "xs:string",
            [
                ("", True, "empty string allowed"),
                ("hello", True, "simple ASCII string"),
                ("with\nnewline", True, "newline allowed"),
                ("\u0000", False, "null character not allowed"),
            ],
        )

    def test_xs_time(self) -> None:
        self._assert_cases(
            "xs:time",
            [
                ("00:00:00", True, "start of day"),
                ("23:59:59", True, "last second of day"),
                ("23:59:59.123", True, "fractional seconds"),
                ("24:00:00", True, "end-of-day representation"),
                ("24:00:00.0", True, "fractional end-of-day"),
                ("24:00:00.000", True, "millisecond precision end-of-day"),
                ("24:00:01", False, "seconds past 24:00:00"),
                ("25:00:00", False, "hour out of range"),
                ("00:60:00", False, "minute out of range"),
                ("00:00:60", False, "second out of range"),
                ("12:34:56Z", True, "UTC timezone"),
                ("12:34:56+14:00", True, "maximum timezone offset"),
                ("12:34:56+14:01", False, "timezone offset too large"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_unsigned_byte(self) -> None:
        self._assert_cases(
            "xs:unsignedByte",
            [
                ("0", True, "zero"),
                ("255", True, "maximum value"),
                ("256", False, "above maximum"),
                ("-1", False, "negative integer not allowed"),
                ("-0", True, "negative zero allowed"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_unsigned_int(self) -> None:
        self._assert_cases(
            "xs:unsignedInt",
            [
                ("0", True, "zero"),
                ("4294967295", True, "maximum value"),
                ("4294967296", False, "above maximum"),
                ("-1", False, "negative integer not allowed"),
                ("-0", True, "negative zero allowed"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_unsigned_long(self) -> None:
        self._assert_cases(
            "xs:unsignedLong",
            [
                ("0", True, "zero"),
                ("18446744073709551615", True, "maximum value"),
                ("18446744073709551616", False, "above maximum"),
                ("-1", False, "negative integer not allowed"),
                ("-0", True, "negative zero allowed"),
                ("", False, "empty string invalid"),
            ],
        )

    def test_xs_unsigned_short(self) -> None:
        self._assert_cases(
            "xs:unsignedShort",
            [
                ("0", True, "zero"),
                ("65535", True, "maximum value"),
                ("65536", False, "above maximum"),
                ("-1", False, "negative integer not allowed"),
                ("-0", True, "negative zero allowed"),
                ("", False, "empty string invalid"),
            ],
        )


class TestOverflow(unittest.TestCase):
    def test_xs_float(self) -> None:
        for text in (
            "3.4028235e38",
            "3.4028235677973366e38",
            "-3.4028235e38",
            "1e-400",
        ):
            self.assertTrue(is_xs_float(text), text)

        for text in ("3.4028235677973367e38", "3.5e38", "1e400", "-1e400"):
            self.assertFalse(is_xs_float(text), text)

        for text in ("INF", "-INF", "NaN"):
            self.assertTrue(is_xs_float(text), text)

    def test_xs_double(self) -> None:
        for text in ("1.7976931348623157e308", "1.797693134862315807e308", "1e-400"):
            self.assertTrue(is_xs_double(text), text)

        for text in ("1.797693134862315808e308", "1.8e308", "1e400", "-1e400"):
            self.assertFalse(is_xs_double(text), text)

        for text in ("INF", "-INF", "NaN"):
            self.assertTrue(is_xs_double(text), text)


if __name__ == "__main__":
    unittest.main()
