# SPDX-FileCopyrightText: 2025 aas-core-testdatagen AUTHORS
#
# SPDX-License-Identifier: MIT

"""Collect frozen_examples and counter-frozen_examples of XSD values."""

import collections
from typing import Mapping

from aas_core_codegen import intermediate
from aas_core_codegen.common import Identifier

from aas_core_testdatagen.frozen_examples._types import Examples
from aas_core_testdatagen.common import Filenameable

# pylint: disable=line-too-long

# noinspection SpellCheckingInspection


BY_VALUE_TYPE: Mapping[str, Examples] = collections.OrderedDict(
    [
        (
            "xs:anyURI",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("integer"), "1234"),
                        (
                            Filenameable("absolute_path_without_scheme"),
                            "/path/to/somewhere",
                        ),
                        (
                            Filenameable("relative_path_without_scheme"),
                            "path/to/somewhere",
                        ),
                        (
                            Filenameable("URI"),
                            "https://github.com/aas-core-works/aas-core-codegen",
                        ),
                        (Filenameable("fuzzed_01"), "#"),
                        (
                            Filenameable("fuzzed_02"),
                            "//[d6FA:c:8b:4:7:be7:aD:C8C]:/~.49:f%Fee;%9D%58L/Q%ea'+Q%eb:&%7C,t:;a,@&%dB%2D%Ba&%bF%BF,;%06G%a0%bfk%7b&@&@1@=+%fE6%FF2j4;$;=,%Da$=R%17s+2%68;/v%Ca%a0&$d%Fd7%58@%a0%54D%0BA%00Bw%a59:6;;/%f1:;t%98$J0:Y;?%8Dx:%aC&$/S/L%A5u",
                        ),
                        (Filenameable("fuzzed_03"), "A://"),
                        (Filenameable("fuzzed_04"), ""),
                        (Filenameable("fuzzed_05"), "#;+;"),
                        (
                            Filenameable("fuzzed_06"),
                            "//@fr+%64@/%C5vw%A8N/%9f;%59%Ea%A9%Dd?#[=",
                        ),
                        (Filenameable("fuzzed_07"), "q%7E~@$=l#%f6,&;&"),
                        (
                            Filenameable("fuzzed_08"),
                            "j.:/%dd;=%78%Eaui;j/aTF&%Fd%9A9K;%f8-;;'4!C;,:C/=;k%b4;%09;;C%74%3a,2%C09;%127%5C;%81%d09/+;/%65%41%a0,@%34C_;%6E*;;%42%D9;%BA7%7EY%D4;%60Z=,/:+;$E&+$%Db4'%F2%7E;'+6-r$%64-;l%85%Eb%Ec+%ae/;=$-;;.%02L;,;%3Bj%a2:&@%3Ak$:;%CB;,(h(::=%b1;$+5&%810%04%3e,@$%60:G+%2d%c8%A4%01%5c,=&:O'CG%Eb@isa%2A+&$$%8D7X.+v)%Ed;3%6eo%DB&;7@%86n=9%aC%02;;k%bDH;%C0%BB;%c9,KF%De&%0A%6fP$:%9B%f5H%b8/T;%01$,%dD%8A%6B!/;,++;=;;%8dk$%0F%FB;;N%6B@;Om$%00#",
                        ),
                        (Filenameable("fuzzed_09"), "#b%39DX%f9a%76u%da%A1@%a9%D3n"),
                        (
                            Filenameable("fuzzed_10"),
                            "///%6B%0EX%9f-=++$:3%9az+,c&%3F:'Sx%3d%00:%7f%40:%08,;%5b%90%A1c;(;$:$y+%5b/=t%40+H+a@%E7$G%58;:+R$g$-yT%08&:,%fB;%F5b@;%Eb3%0C%A3n%4A%7dBf%75%2F%fc;vZ-%aFV$;%3a&;;=%fC;;~@+/=%A4#",
                        ),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (
                            Filenameable("too_many_fragments"),
                            "http://datypic.com#frag1#frag2",
                        ),
                        (
                            Filenameable(
                                "percentage_followed_by_non_two_hexadecimal_digits"
                            ),
                            "http://datypic.com#f% rag",
                        ),
                        (Filenameable("negatively_fuzzed_01"), "``"),
                        (
                            Filenameable("negatively_fuzzed_02"),
                            "yE;\x9a¶)Æ¬fQ\x13§A\U000975ed©\U00014675\x8a\U0003c040",
                        ),
                        (Filenameable("negatively_fuzzed_03"), "W:𠦳\x13\x8f¨9\x83"),
                        (Filenameable("negatively_fuzzed_04"), "''1\x83𐧂"),
                        (Filenameable("negatively_fuzzed_05"), "''ÿ\U00108c1a쎸Èº«Ù"),
                        (Filenameable("negatively_fuzzed_06"), "`0"),
                        (
                            Filenameable("negatively_fuzzed_07"),
                            "Ô·Ù\x9f\U000c8e74»\x06Ô#\x14FBÉÛÍ~O",
                        ),
                        (Filenameable("negatively_fuzzed_08"), "\U0004a254\x05¿."),
                        (
                            Filenameable("negatively_fuzzed_09"),
                            "Ꜭ倀\U000b4bf8½¼\x00ì\tº;Ï\U000847b7w\x97\U000b0dd9D𥙌º|",
                        ),
                        (Filenameable("negatively_fuzzed_10"), "\x97LùÙ"),
                    ]
                ),
            ),
        ),
        (
            "xs:base64Binary",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("without_space_uppercase"), "0FB8"),
                        (Filenameable("without_space_lowercase"), "0fb8"),
                        (
                            Filenameable("whitespace_is_allowed_anywhere_in_the_value"),
                            "0 FB8 0F+9",
                        ),
                        (Filenameable("equals_signs_are_used_for_padding"), "0F+40A=="),
                        (Filenameable("an_empty_value_is_valid"), ""),
                        (
                            Filenameable("fuzzed_01"),
                            "RJ I k 7 c /F / 1 J8F o 0ivZ v AE 3bj ASP y PI k+ 1 fku W 5M=",
                        ),
                        (
                            Filenameable("fuzzed_02"),
                            "Ie 9 20 Y F 5 Ve9 Y c 0W rH p 2 FQaS /xw /t RtE=",
                        ),
                        (Filenameable("fuzzed_03"), "n3wT"),
                        (Filenameable("fuzzed_04"), "wfw E"),
                        (Filenameable("fuzzed_05"), "jj5 n"),
                        (Filenameable("fuzzed_06"), "j j5 n"),
                        (Filenameable("fuzzed_07"), "S w SO 5 S5r"),
                        (Filenameable("fuzzed_08"), "UBU iUBU iQ n cy q 7wK"),
                        (Filenameable("fuzzed_09"), "HU UH"),
                        (Filenameable("fuzzed_10"), "00000000"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (
                            Filenameable("an_odd_number_of_characters_is_not_valid"),
                            "FB8",
                        ),
                        (
                            Filenameable("equals_signs_may_only_appear_at_the_end"),
                            "==0F",
                        ),
                        (
                            Filenameable("negatively_fuzzed_01"),
                            "©l·\x8eÌ𠸄T\x19Ø\x1agd¥6ZÄ",
                        ),
                        (
                            Filenameable("negatively_fuzzed_02"),
                            "1𑂘\x1a\xa0´`𦞙Ù\x9bÃ\x8a",
                        ),
                        (Filenameable("negatively_fuzzed_03"), "#/"),
                        (Filenameable("negatively_fuzzed_04"), "0"),
                        (
                            Filenameable("negatively_fuzzed_05"),
                            "\U000a4788\xa0\U00077a4e\U00060d14ú",
                        ),
                        (Filenameable("negatively_fuzzed_06"), "]]P"),
                        (Filenameable("negatively_fuzzed_07"), "ȏ®BFo^\x0e罳Ø"),
                        (Filenameable("negatively_fuzzed_08"), "í"),
                        (
                            Filenameable("negatively_fuzzed_09"),
                            "\U00055d62C\xad\x06\x02ÚH\x97Ô",
                        ),
                        (Filenameable("negatively_fuzzed_10"), "\x82"),
                    ]
                ),
            ),
        ),
        (
            "xs:boolean",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("true_in_letters"), "true"),
                        (Filenameable("true_as_number"), "1"),
                        (Filenameable("false_in_letters"), "false"),
                        (Filenameable("false_as_number"), "0"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("true_in_uppercase"), "TRUE"),
                        (Filenameable("true_in_camelcase"), "True"),
                        (Filenameable("false_in_uppercase"), "FALSE"),
                        (Filenameable("false_in_camelcase"), "False"),
                        (Filenameable("true_as_number_with_leading_zeros"), "0001"),
                        (Filenameable("false_as_number_with_leading_zeros"), "0000"),
                        (
                            Filenameable("negatively_fuzzed_01"),
                            "\U000bc161\U000da2326\U000da232",
                        ),
                        (
                            Filenameable("negatively_fuzzed_02"),
                            "/\U000787ef\x82»uÎÃ#öÚ¸\x1dÔ\U000cfd24\x1e",
                        ),
                        (Filenameable("negatively_fuzzed_03"), "\U00035bf4"),
                        (Filenameable("negatively_fuzzed_04"), "1Ñ¯ã¬]\x1aä"),
                        (Filenameable("negatively_fuzzed_05"), "\u2007º\U0004cbfdn"),
                        (
                            Filenameable("negatively_fuzzed_06"),
                            "¹½\x174x|톎¬§T\U00073818",
                        ),
                        (
                            Filenameable("negatively_fuzzed_07"),
                            "\U00011770\U0004a8afZ5\x1b \U001057b3ë{Â",
                        ),
                        (Filenameable("negatively_fuzzed_08"), "\U000a4ff6n\x11"),
                        (
                            Filenameable("negatively_fuzzed_09"),
                            "\xad\U0005e82b\U000338e2WX\x1b",
                        ),
                        (
                            Filenameable("negatively_fuzzed_10"),
                            "\U000aae0fza\U000368bb\x89",
                        ),
                    ]
                ),
            ),
        ),
        (
            "xs:date",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("date"), "2022-04-01"),
                        (Filenameable("date_with_utc"), "2022-04-01Z"),
                        (Filenameable("date_with_positive_offset"), "2022-04-01+02:34"),
                        (Filenameable("date_with_zero_offset"), "2022-04-01+00:00"),
                        (Filenameable("date_with_negative_offset"), "2022-04-01-02:00"),
                        (
                            Filenameable("date_with_large_positive_year"),
                            "12345678901234567890123456789012345678901234567890-04-01",
                        ),
                        (
                            Filenameable("date_with_large_negative_year"),
                            "-12345678901234567890123456789012345678901234567890-04-01",
                        ),
                        (
                            Filenameable("year_1_bce_is_a_leap_year"),
                            "-0001-02-29",
                        ),
                        (
                            Filenameable("year_5_bce_is_a_leap_year"),
                            "-0005-02-29",
                        ),
                        (Filenameable("fuzzed_01"), "0705-04-10+14:00"),
                        (Filenameable("fuzzed_02"), "-0236-12-31Z"),
                        (Filenameable("fuzzed_03"), "9088-11-06"),
                        (Filenameable("fuzzed_04"), "-7506-08-02"),
                        (Filenameable("fuzzed_05"), "-3637143-04-09"),
                        (Filenameable("fuzzed_06"), "-0311-11-30"),
                        (Filenameable("fuzzed_07"), "-0844-11-30"),
                        (Filenameable("fuzzed_08"), "0111-04-04"),
                        (Filenameable("fuzzed_09"), "0412-04-08-10:58"),
                        (Filenameable("fuzzed_10"), "0520-01-01"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("date_time_without_zone"), "2022-04-01T01:02:03"),
                        (
                            Filenameable("date_time_with_offset"),
                            "2022-04-01T01:02:03+02:00",
                        ),
                        (Filenameable("date_time_with_UTC"), "2022-04-01T01:02:03Z"),
                        (Filenameable("non_existing_february_29th"), "2011-02-29"),
                        (
                            Filenameable("date_with_invalid_positive_offset"),
                            "2022-04-01+15:00",
                        ),
                        (
                            Filenameable("date_with_invalid_negative_offset"),
                            "2022-04-01-15:00",
                        ),
                        (
                            Filenameable("date_with_seconds_in_offset"),
                            "2022-04-01+02:00:12",
                        ),
                        (Filenameable("year_zero_doesnt_exist"), "0000-01-02"),
                        # NOTE (mristin, 2022-10-30):
                        # Year 1 BCE is a leap year.
                        (Filenameable("year_4_bce_february_29th"), "-0004-02-29"),
                    ]
                ),
            ),
        ),
        (
            "xs:dateTime",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("date_time_without_zone"), "2022-04-01T01:02:03"),
                        (Filenameable("date_time_with_UTC"), "2022-04-01T01:02:03Z"),
                        (
                            Filenameable("date_time_with_positive_offset"),
                            "2022-04-01T01:02:03+02:00",
                        ),
                        (
                            Filenameable("date_time_with_zero_offset"),
                            "2022-04-01T01:02:03+00:00",
                        ),
                        (
                            Filenameable("date_time_with_negative_offset"),
                            "2022-04-01T01:02:03+00:00",
                        ),
                        (
                            Filenameable("date_time_with_long_fractional_seconds"),
                            "2022-04-01T01:02:03.0123456789Z",
                        ),
                        (
                            Filenameable("date_time_with_large_positive_year"),
                            "12345678901234567890123456789012345678901234567890-04-01T01:02:03",
                        ),
                        (
                            Filenameable("date_time_with_large_negative_year"),
                            "-12345678901234567890123456789012345678901234567890-04-01T01:02:03",
                        ),
                        (Filenameable("midnight_with_zeros"), "2022-04-01T00:00:00"),
                        (Filenameable("midnight_with_24_hours"), "2022-04-01T24:00:00"),
                        (
                            Filenameable("year_1_bce_is_a_leap_year"),
                            "-0001-02-29T01:02:03",
                        ),
                        (
                            Filenameable("year_5_bce_is_a_leap_year"),
                            "-0005-02-29T01:02:03",
                        ),
                        (Filenameable("fuzzed_01"), "-0811-10-21T24:00:00.000000Z"),
                        (Filenameable("fuzzed_02"), "-0819-11-21T24:00:00.00Z"),
                        (Filenameable("fuzzed_03"), "-665280014-06-30T21:15:16Z"),
                        (Filenameable("fuzzed_04"), "-0811-11-21T24:00:00.0000Z"),
                        (Filenameable("fuzzed_05"), "0532-09-07T18:47:52+14:00"),
                        (Filenameable("fuzzed_06"), "0707-11-02T24:00:00.00"),
                        (Filenameable("fuzzed_07"), "-0003-12-20T22:53:54.02567"),
                        (Filenameable("fuzzed_08"), "-1092-02-25T24:00:00.0000"),
                        (Filenameable("fuzzed_09"), "-6602-06-30T24:00:00"),
                        (Filenameable("fuzzed_10"), "-2111111-08-31T23:58:19.269348"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("date"), "2022-04-01"),
                        (Filenameable("date_with_time_zone"), "2022-04-01Z"),
                        (
                            Filenameable("non_existing_february_29th"),
                            "2011-02-29T01:02:03Z",
                        ),
                        (
                            Filenameable("date_time_with_invalid_positive_offset"),
                            "2022-04-01T01:02:03+15:00",
                        ),
                        (
                            Filenameable("date_time_with_invalid_negative_offset"),
                            "2022-04-01T01:02:03-15:00",
                        ),
                        (
                            Filenameable("date_time_with_seconds_in_offset"),
                            "2022-04-01T01:02:03+02:00:12",
                        ),
                        (Filenameable("without_seconds"), "2022-04-01T01:02Z"),
                        (Filenameable("without_minutes"), "2022-04-01T01Z"),
                        (
                            Filenameable("date_time_with_unexpected_suffix"),
                            "2022-04-01T01:02:03Z-unexpected-suffix",
                        ),
                        (
                            Filenameable("date_time_with_unexpected_prefix"),
                            "unexpected-prefix-2022-04-01T01:02:03Z",
                        ),
                        (Filenameable("year_zero_doesnt_exist"), "0000-01-02T01:02:03"),
                        # NOTE (mristin, 2022-10-30):
                        # Year 1 BCE is a leap year.
                        (
                            Filenameable("year_4_bce_february_29th"),
                            "-0004-02-29T01:02:03",
                        ),
                    ]
                ),
            ),
        ),
        (
            "xs:decimal",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("integer"), "1234"),
                        (Filenameable("decimal"), "1234.01234"),
                        (Filenameable("integer_with_preceding_zeros"), "0001234"),
                        (Filenameable("decimal_with_preceding_zeros"), "0001234.01234"),
                        (
                            Filenameable("decimal_with_long_fractional"),
                            "1234.1234567890123456789012345678901234567890123456789012345678901234567890",
                        ),
                        (
                            Filenameable("very_large_decimal"),
                            "123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890.12345678901234567890123456789012345678901234567890123456789012345678901234567890",
                        ),
                        (Filenameable("fuzzed_01"), ".33324"),
                        (Filenameable("fuzzed_02"), "01195"),
                        (Filenameable("fuzzed_03"), "+875"),
                        (Filenameable("fuzzed_04"), "-8"),
                        (Filenameable("fuzzed_05"), "-0.0"),
                        (Filenameable("fuzzed_06"), "-13522106"),
                        (Filenameable("fuzzed_07"), "+10"),
                        (Filenameable("fuzzed_08"), "-030725"),
                        (Filenameable("fuzzed_09"), ".3"),
                        (Filenameable("fuzzed_10"), "0061707"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                    ]
                ),
            ),
        ),
        (
            "xs:double",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("integer"), "1234"),
                        (Filenameable("double"), "1234.01234"),
                        (Filenameable("integer_with_preceding_zeros"), "0001234"),
                        (Filenameable("with_preceding_zeros"), "0001234.01234"),
                        (Filenameable("scientific_notation_negative"), "-12.34e56"),
                        (Filenameable("scientific_notation_positive"), "+12.34e56"),
                        (Filenameable("scientific_notation"), "12.34e56"),
                        (
                            Filenameable("scientific_notation_positive_exponent"),
                            "12.34e+56",
                        ),
                        (
                            Filenameable("scientific_notation_negative_exponent"),
                            "12.34e-56",
                        ),
                        (Filenameable("minus_inf"), "-INF"),
                        (Filenameable("inf"), "INF"),
                        (Filenameable("nan"), "NaN"),
                        (
                            Filenameable("loss_of_precision_is_not_detected_by_design"),
                            "1234.1234567890123456789012345678901234567890123456789012345678901234567890",
                        ),
                        # See https://stackoverflow.com/questions/48630106/what-are-the-actual-min-max-values-for-float-and-double-c
                        (
                            Filenameable("lowest"),
                            "-179769313486231570814527423731704356798070567525844996598917476803157260780028538760589558632766878171540458953514382464234321326889464182768467546703537516986049910576551282076245490090389328944075868508455133942304583236903222948165808559332123348274797826204144723168738177180919299881250404026184124858368",
                        ),
                        (
                            Filenameable("max"),
                            "179769313486231570814527423731704356798070567525844996598917476803157260780028538760589558632766878171540458953514382464234321326889464182768467546703537516986049910576551282076245490090389328944075868508455133942304583236903222948165808559332123348274797826204144723168738177180919299881250404026184124858368",
                        ),
                        # NOTE (mristin):
                        # See https://en.wikipedia.org/wiki/Double-precision_floating-point_format.
                        # The real edge cases for (sub)normals would be:
                        # * The smallest positive subnormal number:
                        #   ≈ 4.9406564584124654 × 10⁻³²⁴
                        # * The largest subnormal number:
                        #   ≈ 2.2250738585072009 × 10⁻³⁰⁸
                        # * The smallest positive normal number:
                        #   ≈ 2.2250738585072014 × 10⁻³⁰⁸
                        # * The largest finite (normal) number:
                        #   ≈ 1.7976931348623157 × 10³⁰⁸
                        #
                        # However, we had problems testing these numbers in C++ on
                        # Linux (Windows worked fine, though). Hence, we decide to
                        # limit the range a little bit, even though we miss the exact
                        # edge cases.
                        (
                            "very_precise_subnormal",
                            "2e-307",
                        ),
                        (
                            "very_large_normal",
                            "2e307",
                        ),
                        (Filenameable("fuzzed_01"), ".1118"),
                        (Filenameable("fuzzed_02"), "-.662"),
                        (Filenameable("fuzzed_03"), ".0E0"),
                        (Filenameable("fuzzed_04"), ".4"),
                        (Filenameable("fuzzed_05"), ".11"),
                        (Filenameable("fuzzed_06"), "+76E-86"),
                        (Filenameable("fuzzed_07"), "-.662"),
                        (Filenameable("fuzzed_08"), "1e+7"),
                        (Filenameable("fuzzed_09"), "-.66E-45"),
                        (Filenameable("fuzzed_10"), "140206134"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("inf_case_matters"), "inf"),
                        (Filenameable("nan_case_matters"), "nan"),
                        (Filenameable("plus_inf"), "+INF"),
                        (
                            Filenameable("no_fraction_in_scientific_notation"),
                            "12.34e5.6",
                        ),
                        (Filenameable("too_large"), "1.123456789e1234567890"),
                    ]
                ),
            ),
        ),
        (
            "xs:duration",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("full"), "P1Y2M3DT5H20M30.123S"),
                        (Filenameable("only_year"), "-P1Y"),
                        (Filenameable("day_seconds"), "P1DT2S"),
                        (Filenameable("month_seconds"), "PT2M10S"),
                        (Filenameable("only_seconds"), "PT130S"),
                        (
                            Filenameable("many_many_seconds"),
                            "PT1234567890"
                            "1234567890"
                            "1234567890"
                            "1234567890"
                            "1234567890"
                            "1234567890"
                            "1234567890"
                            "1234567890S",
                        ),
                        (
                            Filenameable("long_second_fractal"),
                            "PT1."
                            "1234567890"
                            "1234567890"
                            "1234567890"
                            "1234567890"
                            "1234567890"
                            "1234567890"
                            "1234567890"
                            "1234567890S",
                        ),
                        (Filenameable("fuzzed_01"), "-P009D"),
                        (Filenameable("fuzzed_02"), "P5Y36660767143M"),
                        (Filenameable("fuzzed_03"), "-PT01332.1S"),
                        (Filenameable("fuzzed_04"), "-P11DT142M"),
                        (
                            Filenameable("fuzzed_05"),
                            "PT88M48936316289.34291243605107045S",
                        ),
                        (Filenameable("fuzzed_06"), "-P1M923D"),
                        (Filenameable("fuzzed_07"), "-PT0.332S"),
                        (
                            Filenameable("fuzzed_08"),
                            "-PT313148178698146281H866062127724898M",
                        ),
                        (Filenameable("fuzzed_09"), "-PT1.5375209S"),
                        (Filenameable("fuzzed_10"), "PT18688M"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("integer"), "1234"),
                        (Filenameable("leading_P_missing"), "1Y"),
                        (Filenameable("separator_T_missing"), "P1S"),
                        (Filenameable("negative_years"), "P-1Y"),
                        (Filenameable("positive_year_negative_months"), "P1Y-1M"),
                        (Filenameable("the_order_matters"), "P1M2Y"),
                    ]
                ),
            ),
        ),
        (
            "xs:float",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("integer"), "1234"),
                        (Filenameable("float"), "1234.01234"),
                        (Filenameable("integer_with_preceding_zeros"), "0001234"),
                        (Filenameable("with_preceding_zeros"), "0001234.01234"),
                        (Filenameable("scientific_notation_negative"), "-12.34e16"),
                        (Filenameable("scientific_notation_positive"), "+12.34e16"),
                        (Filenameable("scientific_notation"), "12.34e16"),
                        (
                            Filenameable("scientific_notation_positive_exponent"),
                            "12.34e+16",
                        ),
                        (
                            Filenameable("scientific_notation_negative_exponent"),
                            "12.34e-16",
                        ),
                        (Filenameable("negative_inf"), "-INF"),
                        (Filenameable("inf"), "INF"),
                        (Filenameable("nan"), "NaN"),
                        (
                            Filenameable("loss_of_precision_is_not_detected_by_design"),
                            "1234.1234567890123456789012345678901234567890123456789012345678901234567890",
                        ),
                        # See https://en.wikipedia.org/wiki/Single-precision_floating-point_format
                        (
                            Filenameable("smallest_positive_subnormal"),
                            "0.00000000000000000000000000000000000000000000140129846432481707092372958328991613128026194187651577175706828388979108268586060148663818836212158203125",
                        ),
                        (
                            Filenameable("largest_subnormal"),
                            "0.00000000000000000000000000000000000001175494210692441075487029444849287348827052428745893333857174530571588870475618904265502351336181163787841796875",
                        ),
                        (
                            Filenameable("smallest_positive_normal"),
                            "0.000000000000000000000000000000000000011754943508222875079687365372222456778186655567720875215087517062784172594547271728515625",
                        ),
                        (
                            Filenameable("largest_normal"),
                            "340282346638528859811704183484516925440",
                        ),
                        (
                            Filenameable("largest_number_less_than_one"),
                            "0.999999940395355224609375",
                        ),
                        (
                            Filenameable("smallest_number_larger_than_one"),
                            "1.00000011920928955078125",
                        ),
                        (Filenameable("fuzzed_01"), "-.80E0"),
                        (Filenameable("fuzzed_02"), "-147E7"),
                        (Filenameable("fuzzed_03"), "18"),
                        (Filenameable("fuzzed_04"), ".1532E+16"),
                        (Filenameable("fuzzed_05"), "+44.6393"),
                        (Filenameable("fuzzed_06"), ".5885e-29"),
                        (Filenameable("fuzzed_07"), "1e-7"),
                        (Filenameable("fuzzed_08"), "+732.55619"),
                        (Filenameable("fuzzed_09"), ".1E05"),
                        (Filenameable("fuzzed_10"), "1102"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("inf_case_matters"), "inf"),
                        (Filenameable("nan_case_matters"), "nan"),
                        (Filenameable("plus_inf"), "+INF"),
                        (
                            Filenameable("no_fraction_in_scientific_notation"),
                            "12.34e5.6",
                        ),
                        (Filenameable("too_large"), "1.123456789e1234567890"),
                    ]
                ),
            ),
        ),
        (
            "xs:gDay",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("single_digit_day_without_zone"), "---01"),
                        (Filenameable("double_digit_day_without_zone"), "---15"),
                        (
                            Filenameable("day_not_existing_in_all_months_without_zone"),
                            "---31",
                        ),
                        (Filenameable("utc_zone"), "---01Z"),
                        (Filenameable("positive_offset"), "---01+02:00"),
                        (Filenameable("zero_offset"), "---01+00:00"),
                        (Filenameable("negative_offset"), "---01-04:00"),
                        (Filenameable("fuzzed_01"), "---23Z"),
                        (Filenameable("fuzzed_02"), "---24"),
                        (Filenameable("fuzzed_03"), "---10"),
                        (Filenameable("fuzzed_04"), "---30-14:00"),
                        (Filenameable("fuzzed_05"), "---31-09:25"),
                        (Filenameable("fuzzed_06"), "---17Z"),
                        (Filenameable("fuzzed_07"), "---30+00:00"),
                        (Filenameable("fuzzed_08"), "---30-10:11"),
                        (Filenameable("fuzzed_09"), "---22Z"),
                        (Filenameable("fuzzed_10"), "---30Z"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("unexpected_suffix"), "--30-"),
                        (Filenameable("day_outside_of_range"), "---35"),
                        (Filenameable("missing_leading_digit"), "---5"),
                        (Filenameable("missing_leading_dashes"), "15"),
                        (Filenameable("invalid_positive_offset"), "---01+15:00"),
                        (Filenameable("invalid_negative_offset"), "---01-15:00"),
                        (Filenameable("invalid_offset_with_seconds"), "---01+15:00:12"),
                    ]
                ),
            ),
        ),
        (
            "xs:gMonth",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("single_digit_month_without_zone"), "--05"),
                        (Filenameable("double_digit_month_without_zone"), "--11"),
                        (Filenameable("utc_zone"), "--11Z"),
                        (Filenameable("positive_offset"), "--11+02:00"),
                        (Filenameable("zero_offset"), "--11+00:00"),
                        (Filenameable("negative_offset"), "--11-04:00"),
                        (Filenameable("fuzzed_01"), "--11-13:34"),
                        (Filenameable("fuzzed_02"), "--10+14:00"),
                        (Filenameable("fuzzed_03"), "--10+07:39"),
                        (Filenameable("fuzzed_04"), "--11-05:22"),
                        (Filenameable("fuzzed_05"), "--01"),
                        (Filenameable("fuzzed_06"), "--12Z"),
                        (Filenameable("fuzzed_07"), "--10-13:30"),
                        (Filenameable("fuzzed_08"), "--07"),
                        (Filenameable("fuzzed_09"), "--11-10:05"),
                        (Filenameable("fuzzed_10"), "--11+12:33"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("unexpected_prefix_and_suffix"), "-01-"),
                        (Filenameable("month_outside_of_range"), "--13"),
                        (Filenameable("missing_leading_digit"), "--1"),
                        (Filenameable("missing_leading_dashes"), "01"),
                        (Filenameable("invalid_positive_offset"), "--11+15:00"),
                        (Filenameable("invalid_negative_offset"), "--11-15:00"),
                        (Filenameable("invalid_offset_with_seconds"), "--11+02:00:12"),
                    ]
                ),
            ),
        ),
        (
            "xs:gMonthDay",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (
                            Filenameable(
                                "single_digit_month_single_digit_day_without_zone"
                            ),
                            "--05-01",
                        ),
                        (
                            Filenameable(
                                "double_digit_month_single_digit_day_without_zone"
                            ),
                            "--11-01",
                        ),
                        (
                            Filenameable(
                                "double_digit_month_double_digit_day_without_zone"
                            ),
                            "--11-14",
                        ),
                        (
                            Filenameable(
                                "february_29th_which_does_not_exist_in_all_years"
                            ),
                            "--02-29",
                        ),
                        (Filenameable("utc_zone"), "--11-01Z"),
                        (Filenameable("positive_offset"), "--11-01+02:00"),
                        (Filenameable("zero_offset"), "--11-01+02:00"),
                        (Filenameable("negative_offset"), "--11-01-04:00"),
                        (Filenameable("fuzzed_01"), "--11-20"),
                        (Filenameable("fuzzed_02"), "--12-06"),
                        (Filenameable("fuzzed_03"), "--12-01"),
                        (Filenameable("fuzzed_04"), "--11-21+14:00"),
                        (Filenameable("fuzzed_05"), "--10-07"),
                        (Filenameable("fuzzed_06"), "--10-30"),
                        (Filenameable("fuzzed_07"), "--12-27"),
                        (Filenameable("fuzzed_08"), "--04-30"),
                        (Filenameable("fuzzed_09"), "--10-10-14:00"),
                        (Filenameable("fuzzed_10"), "--10-11Z"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("unexpected_prefix_and_suffix"), "-01-30-"),
                        (Filenameable("day_outside_of_range"), "--01-35"),
                        (Filenameable("non_existing_april_31st"), "--04-31"),
                        (Filenameable("missing_leading_digit"), "--1-5"),
                        (Filenameable("missing_leading_dashes"), "01-15"),
                        (Filenameable("invalid_positive_offset"), "--11-01+15:00"),
                        (Filenameable("invalid_negative_offset"), "--11-01-15:00"),
                        (
                            Filenameable("invalid_offset_with_seconds"),
                            "--11-01+02:00:12",
                        ),
                    ]
                ),
            ),
        ),
        (
            "xs:gYear",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("year_without_zone"), "2001"),
                        (Filenameable("five_digit_year"), "20000"),
                        (
                            Filenameable("very_large_positive_year"),
                            "123456789012345678901234567890123456789012345678901234567890",
                        ),
                        (
                            Filenameable("very_large_negative_year"),
                            "-123456789012345678901234567890123456789012345678901234567890",
                        ),
                        (Filenameable("utc_zone"), "2001Z"),
                        (Filenameable("positive_offset"), "2001+02:00"),
                        (Filenameable("zero_offset"), "2001+00:00"),
                        (Filenameable("negative_offset"), "2001-04:00"),
                        (Filenameable("negative_year"), "-2001"),
                        (Filenameable("five_digit_negative_year"), "-20000"),
                        (Filenameable("fuzzed_01"), "0740-07:36"),
                        (Filenameable("fuzzed_02"), "125774274"),
                        (Filenameable("fuzzed_03"), "-0444"),
                        (Filenameable("fuzzed_04"), "0000"),
                        (Filenameable("fuzzed_05"), "-0111+14:00"),
                        (Filenameable("fuzzed_06"), "11111"),
                        (Filenameable("fuzzed_07"), "973419862"),
                        (Filenameable("fuzzed_08"), "1717608219759Z"),
                        (Filenameable("fuzzed_09"), "-0863"),
                        (Filenameable("fuzzed_10"), "-0109+14:00"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("missing_century"), "01"),
                        (Filenameable("unexpected_month"), "2001-12"),
                        (Filenameable("invalid_positive_offset"), "2001+15:00"),
                        (Filenameable("invalid_negative_offset"), "2001-15:00"),
                        (Filenameable("invalid_offset_with_seconds"), "2001+02:00:12"),
                    ]
                ),
            ),
        ),
        (
            "xs:gYearMonth",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("common_year_month"), "2001-10"),
                        (
                            Filenameable("very_large_positive_year"),
                            "123456789012345678901234567890123456789012345678901234567890-04",
                        ),
                        (Filenameable("with_utc_zone"), "2001-10Z"),
                        (Filenameable("with_positive_offset"), "2001-10+02:00"),
                        (Filenameable("with_zero_offset"), "2001-10+00:00"),
                        (Filenameable("with_negative_offset"), "2001-10-02:00"),
                        (Filenameable("negative_year"), "-2001-10"),
                        (Filenameable("five_digit_negative_year"), "-20000-04"),
                        (
                            Filenameable("very_large_negative_year"),
                            "-123456789012345678901234567890123456789012345678901234567890-04",
                        ),
                        (Filenameable("fuzzed_01"), "-65822-10"),
                        (Filenameable("fuzzed_02"), "0730-10-14:00"),
                        (Filenameable("fuzzed_03"), "-4111-11Z"),
                        (Filenameable("fuzzed_04"), "1000-01"),
                        (Filenameable("fuzzed_05"), "0010-09-14:00"),
                        (Filenameable("fuzzed_06"), "0555-07"),
                        (Filenameable("fuzzed_07"), "0404-11-14:00"),
                        (Filenameable("fuzzed_08"), "-0882-11+14:00"),
                        (Filenameable("fuzzed_09"), "-0230-09Z"),
                        (Filenameable("fuzzed_10"), "0119-12-14:00"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("missing_month"), "2001"),
                        (Filenameable("month_out_of_range"), "2001-13"),
                        (Filenameable("missing_century"), "01-13"),
                        (Filenameable("invalid_positive_offset"), "2001-10+15:00"),
                        (Filenameable("invalid_negative_offset"), "2001-10-15:00"),
                        (
                            Filenameable("invalid_offset_with_seconds"),
                            "2001-10+02:00:12",
                        ),
                    ]
                ),
            ),
        ),
        (
            "xs:hexBinary",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("one_one"), "11"),
                        (Filenameable("one_two"), "12"),
                        (Filenameable("one_two_three_four"), "1234"),
                        (
                            Filenameable("long_random_hex"),
                            "3c3f786d6c2076657273696f6e3d22312e302220656e636f64696e67",
                        ),
                        (Filenameable("fuzzed_01"), "f22fF9004a6D9AD1"),
                        (Filenameable("fuzzed_02"), "00"),
                        (Filenameable("fuzzed_03"), "FFFFfef3CB"),
                        (Filenameable("fuzzed_04"), "A8"),
                        (Filenameable("fuzzed_05"), "3C3C82"),
                        (Filenameable("fuzzed_06"), "23ee"),
                        (Filenameable("fuzzed_07"), "00"),
                        (Filenameable("fuzzed_08"), "aBe5ccF85fbf32"),
                        (Filenameable("fuzzed_09"), "aBe5ccF85fbf32"),
                        (Filenameable("fuzzed_10"), "C4E02bbC"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("single_digit"), "1"),
                        (Filenameable("odd_number_of_digits"), "123"),
                    ]
                ),
            ),
        ),
        (
            "xs:time",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("common_example"), "21:32:52"),
                        (Filenameable("with_utc_timezone"), "19:32:52Z"),
                        (Filenameable("positive_offset"), "21:32:52+02:00"),
                        (Filenameable("zero_offset"), "21:32:52+00:00"),
                        (Filenameable("negative_offset"), "21:32:52-02:00"),
                        (Filenameable("with_second_fractional"), "21:32:52.12679"),
                        (
                            Filenameable("with_long_second_fractional"),
                            "21:32:52.12345678901234567890123456789012345678901234567890",
                        ),
                        (Filenameable("fuzzed_01"), "24:00:00.00Z"),
                        (Filenameable("fuzzed_02"), "01:19:39.4378+10:53"),
                        (Filenameable("fuzzed_03"), "01:00:12+14:00"),
                        (Filenameable("fuzzed_04"), "24:00:00.0Z"),
                        (Filenameable("fuzzed_05"), "01:10:12+14:00"),
                        (Filenameable("fuzzed_06"), "24:00:00-14:00"),
                        (Filenameable("fuzzed_07"), "20:55:25"),
                        (Filenameable("fuzzed_08"), "24:00:00-10:44"),
                        (Filenameable("fuzzed_09"), "24:00:00-13:00"),
                        (Filenameable("fuzzed_10"), "24:00:00.000000+14:00"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("missing_seconds"), "21:32"),
                        (Filenameable("hour_out_of_range"), "25:25:10"),
                        (Filenameable("minute_out_of_range"), "01:61:10"),
                        (Filenameable("second_out_of_range"), "01:02:61"),
                        (Filenameable("negative"), "-10:00:00"),
                        (Filenameable("missing_padded_zeros"), "1:20:10"),
                        (Filenameable("invalid_positive_offset"), "21:32:52+15:00"),
                        (Filenameable("invalid_negative_offset"), "21:32:52-15:00"),
                        (
                            Filenameable("invalid_offset_with_seconds"),
                            "21:32:52-02:00:12",
                        ),
                    ]
                ),
            ),
        ),
        (
            "xs:integer",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("common_example"), "1"),
                        (Filenameable("negative"), "-1"),
                        (Filenameable("zero"), "0"),
                        (Filenameable("explicitly_positive"), "+1"),
                        (Filenameable("prefixed_with_zeros"), "001"),
                        (Filenameable("zero_prefixed_with_zeros"), "000"),
                        (
                            Filenameable("very_large"),
                            "1234567890123456789012345678901234567890123456789012345678901234567890",
                        ),
                        (Filenameable("fuzzed_01"), "817778847926480"),
                        (Filenameable("fuzzed_02"), "+022"),
                        (Filenameable("fuzzed_03"), "-43045"),
                        (Filenameable("fuzzed_04"), "-3009"),
                        (Filenameable("fuzzed_05"), "0"),
                        (Filenameable("fuzzed_06"), "-3"),
                        (Filenameable("fuzzed_07"), "8"),
                        (Filenameable("fuzzed_08"), "221"),
                        (Filenameable("fuzzed_09"), "9191"),
                        (Filenameable("fuzzed_10"), "-3909"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("decimal"), "1.2"),
                        (Filenameable("scientific"), "1e2"),
                        (Filenameable("mathematical_formula"), "2**5"),
                    ]
                ),
            ),
        ),
        (
            "xs:long",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("common_example"), "1"),
                        (Filenameable("negative"), "-1"),
                        (Filenameable("zero"), "0"),
                        (Filenameable("explicitly_positive"), "+1"),
                        (Filenameable("prefixed_with_zeros"), "001"),
                        (Filenameable("zero_prefixed_with_zeros"), "000"),
                        (Filenameable("max"), "9223372036854775807"),
                        (Filenameable("min"), "-9223372036854775808"),
                        (Filenameable("fuzzed_01"), "-002728"),
                        (Filenameable("fuzzed_02"), "6257"),
                        (Filenameable("fuzzed_03"), "088"),
                        (Filenameable("fuzzed_04"), "29"),
                        (Filenameable("fuzzed_05"), "-288"),
                        (Filenameable("fuzzed_06"), "004775"),
                        (Filenameable("fuzzed_07"), "2912577609592844"),
                        (Filenameable("fuzzed_08"), "-0161"),
                        (Filenameable("fuzzed_09"), "00000000000048533"),
                        (Filenameable("fuzzed_10"), "3116670676"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("decimal"), "1.2"),
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("max_plus_one"), "9223372036854775808"),
                        (Filenameable("min_minus_one"), "-9223372036854775809"),
                        (Filenameable("scientific"), "1e2"),
                        (Filenameable("mathematical_formula"), "2**5"),
                    ]
                ),
            ),
        ),
        (
            "xs:int",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("common_example"), "1"),
                        (Filenameable("negative"), "-1"),
                        (Filenameable("zero"), "0"),
                        (Filenameable("explicitly_positive"), "+1"),
                        (Filenameable("prefixed_with_zeros"), "001"),
                        (Filenameable("zero_prefixed_with_zeros"), "000"),
                        (Filenameable("max"), "2147483647"),
                        (Filenameable("min"), "-2147483648"),
                        (Filenameable("fuzzed_01"), "00"),
                        (Filenameable("fuzzed_02"), "-0"),
                        (Filenameable("fuzzed_03"), "000000000000069268"),
                        (Filenameable("fuzzed_04"), "+478978"),
                        (Filenameable("fuzzed_05"), "7097"),
                        (Filenameable("fuzzed_06"), "68"),
                        (Filenameable("fuzzed_07"), "+0"),
                        (Filenameable("fuzzed_08"), "6612453"),
                        (Filenameable("fuzzed_09"), "-00"),
                        (Filenameable("fuzzed_10"), "+0000000946381"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("decimal"), "1.2"),
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("max_plus_one"), "2147483648"),
                        (Filenameable("min_minus_one"), "-2147483649"),
                        (Filenameable("scientific"), "1e2"),
                        (Filenameable("mathematical_formula"), "2**5"),
                    ]
                ),
            ),
        ),
        (
            "xs:short",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("common_example"), "1"),
                        (Filenameable("negative"), "-1"),
                        (Filenameable("zero"), "0"),
                        (Filenameable("explicitly_positive"), "+1"),
                        (Filenameable("prefixed_with_zeros"), "001"),
                        (Filenameable("zero_prefixed_with_zeros"), "000"),
                        (Filenameable("max"), "32767"),
                        (Filenameable("min"), "-32768"),
                        (Filenameable("fuzzed_01"), "9"),
                        (Filenameable("fuzzed_02"), "01"),
                        (Filenameable("fuzzed_03"), "+1"),
                        (Filenameable("fuzzed_04"), "8801"),
                        (Filenameable("fuzzed_05"), "125"),
                        (Filenameable("fuzzed_06"), "20518"),
                        (Filenameable("fuzzed_07"), "60"),
                        (Filenameable("fuzzed_08"), "-01"),
                        (Filenameable("fuzzed_09"), "+31923"),
                        (Filenameable("fuzzed_10"), "22"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("decimal"), "1.2"),
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("max_plus_one"), "32768"),
                        (Filenameable("min_minus_one"), "-32769"),
                        (Filenameable("scientific"), "1e2"),
                        (Filenameable("mathematical_formula"), "2**5"),
                    ]
                ),
            ),
        ),
        (
            "xs:byte",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("common_example"), "1"),
                        (Filenameable("negative"), "-1"),
                        (Filenameable("zero"), "0"),
                        (Filenameable("explicitly_positive"), "+1"),
                        (Filenameable("prefixed_with_zeros"), "001"),
                        (Filenameable("zero_prefixed_with_zeros"), "000"),
                        (Filenameable("max"), "127"),
                        (Filenameable("min"), "-128"),
                        (Filenameable("fuzzed_01"), "05"),
                        (Filenameable("fuzzed_02"), "000110"),
                        (Filenameable("fuzzed_03"), "+00"),
                        (Filenameable("fuzzed_04"), "-108"),
                        (Filenameable("fuzzed_05"), "0001"),
                        (Filenameable("fuzzed_06"), "103"),
                        (Filenameable("fuzzed_07"), "06"),
                        (Filenameable("fuzzed_08"), "+0000002"),
                        (Filenameable("fuzzed_09"), "000000006"),
                        (Filenameable("fuzzed_10"), "-00011"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("decimal"), "1.2"),
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("max_plus_one"), "128"),
                        (Filenameable("min_minus_one"), "-129"),
                        (Filenameable("scientific"), "1e2"),
                        (Filenameable("mathematical_formula"), "2**5"),
                    ]
                ),
            ),
        ),
        (
            "xs:nonNegativeInteger",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("common_example"), "1"),
                        (Filenameable("zero"), "0"),
                        (Filenameable("minus_zero"), "-0"),
                        (Filenameable("explicitly_positive"), "+1"),
                        (Filenameable("positive_zero"), "+0"),
                        (Filenameable("prefixed_with_zeros"), "001"),
                        (
                            Filenameable("explicitly_positive_prefixed_with_zeros"),
                            "+001",
                        ),
                        (Filenameable("zero_prefixed_with_zeros"), "000"),
                        (
                            Filenameable("very_large"),
                            "1234567890123456789012345678901234567890123456789012345678901234567890",
                        ),
                        (Filenameable("fuzzed_01"), "+4"),
                        (Filenameable("fuzzed_02"), "00018"),
                        (Filenameable("fuzzed_03"), "22777"),
                        (Filenameable("fuzzed_04"), "22077"),
                        (Filenameable("fuzzed_05"), "+06"),
                        (Filenameable("fuzzed_06"), "09"),
                        (Filenameable("fuzzed_07"), "+3"),
                        (Filenameable("fuzzed_08"), "+5739"),
                        (Filenameable("fuzzed_09"), "+70126"),
                        (Filenameable("fuzzed_10"), "05688"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("decimal"), "1.2"),
                        (Filenameable("negative"), "-1"),
                    ]
                ),
            ),
        ),
        (
            "xs:positiveInteger",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("common_example"), "1"),
                        (Filenameable("explicitly_positive"), "+1"),
                        (Filenameable("prefixed_with_zeros"), "001"),
                        (
                            Filenameable("very_large"),
                            "1234567890123456789012345678901234567890123456789012345678901234567890",
                        ),
                        (Filenameable("fuzzed_01"), "550788"),
                        (Filenameable("fuzzed_02"), "7775"),
                        (Filenameable("fuzzed_03"), "+87138"),
                        (Filenameable("fuzzed_04"), "8093888718"),
                        (Filenameable("fuzzed_05"), "01145"),
                        (Filenameable("fuzzed_06"), "01"),
                        (Filenameable("fuzzed_07"), "+57345"),
                        (Filenameable("fuzzed_08"), "54691"),
                        (Filenameable("fuzzed_09"), "+01"),
                        (Filenameable("fuzzed_10"), "3"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("decimal"), "1.2"),
                        (Filenameable("negative"), "-1"),
                        (Filenameable("zero_prefixed_with_zeros"), "000"),
                        (Filenameable("zero"), "0"),
                    ]
                ),
            ),
        ),
        (
            "xs:unsignedLong",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("common_example"), "1"),
                        (Filenameable("zero"), "0"),
                        (Filenameable("explicitly_positive"), "+1"),
                        (Filenameable("prefixed_with_zeros"), "001"),
                        (Filenameable("zero_prefixed_with_zeros"), "000"),
                        (Filenameable("max"), "18446744073709551615"),
                        (Filenameable("fuzzed_01"), "00"),
                        (Filenameable("fuzzed_02"), "+0013081"),
                        (Filenameable("fuzzed_03"), "+00008773"),
                        (Filenameable("fuzzed_04"), "+000000858"),
                        (Filenameable("fuzzed_05"), "+000000000002599"),
                        (Filenameable("fuzzed_06"), "+0257364527"),
                        (Filenameable("fuzzed_07"), "+000000038893"),
                        (Filenameable("fuzzed_08"), "+0000000000000111491"),
                        (Filenameable("fuzzed_09"), "+09"),
                        (Filenameable("fuzzed_10"), "0012208354443"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("decimal"), "1.2"),
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("max_plus_one"), "18446744073709551616"),
                        (Filenameable("negative"), "-1"),
                        (Filenameable("scientific"), "1e2"),
                        (Filenameable("mathematical_formula"), "2**5"),
                    ]
                ),
            ),
        ),
        (
            "xs:unsignedInt",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("common_example"), "1"),
                        (Filenameable("zero"), "0"),
                        (Filenameable("explicitly_positive"), "+1"),
                        (Filenameable("prefixed_with_zeros"), "001"),
                        (Filenameable("zero_prefixed_with_zeros"), "000"),
                        (Filenameable("max"), "4294967295"),
                        (Filenameable("fuzzed_01"), "+000832736002"),
                        (Filenameable("fuzzed_02"), "0454"),
                        (Filenameable("fuzzed_03"), "0000000000001161715506"),
                        (Filenameable("fuzzed_04"), "+0006096840"),
                        (Filenameable("fuzzed_05"), "8547"),
                        (Filenameable("fuzzed_06"), "+092843"),
                        (Filenameable("fuzzed_07"), "+44"),
                        (Filenameable("fuzzed_08"), "+0881299729"),
                        (Filenameable("fuzzed_09"), "+00604"),
                        (Filenameable("fuzzed_10"), "+000101"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("decimal"), "1.2"),
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("max_plus_one"), "4294967296"),
                        (Filenameable("negative"), "-1"),
                        (Filenameable("scientific"), "1e2"),
                        (Filenameable("mathematical_formula"), "2**5"),
                    ]
                ),
            ),
        ),
        (
            "xs:unsignedShort",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("common_example"), "1"),
                        (Filenameable("zero"), "0"),
                        (Filenameable("explicitly_positive"), "+1"),
                        (Filenameable("prefixed_with_zeros"), "001"),
                        (Filenameable("zero_prefixed_with_zeros"), "000"),
                        (Filenameable("max"), "65535"),
                        (Filenameable("fuzzed_01"), "+00"),
                        (Filenameable("fuzzed_02"), "06949"),
                        (Filenameable("fuzzed_03"), "0391"),
                        (Filenameable("fuzzed_04"), "+000004"),
                        (Filenameable("fuzzed_05"), "00000000391"),
                        (Filenameable("fuzzed_06"), "+085"),
                        (Filenameable("fuzzed_07"), "10233"),
                        (Filenameable("fuzzed_08"), "044598"),
                        (Filenameable("fuzzed_09"), "+00066"),
                        (Filenameable("fuzzed_10"), "+00000000000000000000003250"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("decimal"), "1.2"),
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("max_plus_one"), "65536"),
                        (Filenameable("negative"), "-1"),
                        (Filenameable("scientific"), "1e2"),
                        (Filenameable("mathematical_formula"), "2**5"),
                    ]
                ),
            ),
        ),
        (
            "xs:unsignedByte",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("common_example"), "1"),
                        (Filenameable("zero"), "0"),
                        (Filenameable("explicitly_positive"), "+1"),
                        (Filenameable("prefixed_with_zeros"), "001"),
                        (Filenameable("zero_prefixed_with_zeros"), "000"),
                        (Filenameable("max"), "255"),
                        (Filenameable("fuzzed_01"), "0000000000000000000000000000067"),
                        (Filenameable("fuzzed_02"), "+130"),
                        (Filenameable("fuzzed_03"), "232"),
                        (Filenameable("fuzzed_04"), "+110"),
                        (Filenameable("fuzzed_05"), "+000000000012"),
                        (Filenameable("fuzzed_06"), "055"),
                        (Filenameable("fuzzed_07"), "031"),
                        (Filenameable("fuzzed_08"), "0178"),
                        (Filenameable("fuzzed_09"), "+00"),
                        (Filenameable("fuzzed_10"), "+00000006"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("decimal"), "1.2"),
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("max_plus_one"), "256"),
                        (Filenameable("negative"), "-1"),
                        (Filenameable("scientific"), "1e2"),
                        (Filenameable("mathematical_formula"), "2**5"),
                    ]
                ),
            ),
        ),
        (
            "xs:nonPositiveInteger",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("negative"), "-1"),
                        (Filenameable("zero"), "0"),
                        (Filenameable("prefixed_with_zeros"), "-001"),
                        (Filenameable("explicitly_positive_zero"), "+0"),
                        (
                            Filenameable("very_large"),
                            "-1234567890123456789012345678901234567890123456789012345678901234567890",
                        ),
                        (Filenameable("fuzzed_01"), "-51"),
                        (Filenameable("fuzzed_02"), "-8908938"),
                        (Filenameable("fuzzed_03"), "-553"),
                        (Filenameable("fuzzed_04"), "+0"),
                        (Filenameable("fuzzed_05"), "-4006"),
                        (Filenameable("fuzzed_06"), "-83"),
                        (Filenameable("fuzzed_07"), "-004"),
                        (Filenameable("fuzzed_08"), "-551521749598676413553"),
                        (Filenameable("fuzzed_09"), "-12116166"),
                        (Filenameable("fuzzed_10"), "-553"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("decimal"), "1.2"),
                        (Filenameable("implicitly_positive"), "1"),
                        (Filenameable("explicitly_positive"), "+1"),
                        (Filenameable("scientific"), "-1e2"),
                        (Filenameable("mathematical_formula"), "-2**5"),
                    ]
                ),
            ),
        ),
        (
            "xs:negativeInteger",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("negative"), "-1"),
                        (Filenameable("prefixed_with_zeros"), "-001"),
                        (
                            Filenameable("very_large"),
                            "-1234567890123456789012345678901234567890123456789012345678901234567890",
                        ),
                        (Filenameable("fuzzed_01"), "-001"),
                        (Filenameable("fuzzed_02"), "-002"),
                        (Filenameable("fuzzed_03"), "-009"),
                        (Filenameable("fuzzed_04"), "-8"),
                        (Filenameable("fuzzed_05"), "-1"),
                        (Filenameable("fuzzed_06"), "-00000000000000000000000516481"),
                        (Filenameable("fuzzed_07"), "-003"),
                        (Filenameable("fuzzed_08"), "-00126"),
                        (Filenameable("fuzzed_09"), "-01"),
                        (Filenameable("fuzzed_10"), "-3"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free form text"),
                        (Filenameable("zero"), "0"),
                        (Filenameable("zero_prefixed_with_zeros"), "000"),
                        (Filenameable("explicitly_positive_zero"), "+0"),
                        (Filenameable("decimal"), "1.2"),
                        (Filenameable("implicitly_positive"), "1"),
                        (Filenameable("explicitly_positive"), "+1"),
                        (Filenameable("scientific"), "-1e2"),
                        (Filenameable("mathematical_formula"), "-2**5"),
                    ]
                ),
            ),
        ),
        (
            "xs:string",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (
                            Filenameable("free_form_text"),
                            "some free & <free> \u1984 form text",
                        ),
                        (
                            Filenameable("fuzzed_01"),
                            "11ÕÑ\U00010ee8´K\U00102b2de<\U000e15de¨ngA",
                        ),
                        (Filenameable("fuzzed_02"), "𠤢4𠤢"),
                        (Filenameable("fuzzed_03"), "[\\h$\U00052e9fìÖċ\x8a1¿"),
                        (Filenameable("fuzzed_04"), "öĖa\U0010d8e1\x99|"),
                        (Filenameable("fuzzed_05"), "J5"),
                        (Filenameable("fuzzed_06"), "Ûă<P\U000e8c7d²|dn\x9cÞ®"),
                        (Filenameable("fuzzed_07"), "6"),
                        (
                            Filenameable("fuzzed_08"),
                            "\U000a444cM𪠇\U0001b50a\U00082132",
                        ),
                        (Filenameable("fuzzed_09"), "<ă<P\U000e8c7d²|dn\x9cÞ®"),
                        (Filenameable("fuzzed_10"), "0"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("NUL_as_x"), "\x00"),
                        (Filenameable("NUL_as_utf16"), "\u0000"),
                        (Filenameable("NUL_as_utf32"), "\U00000000"),
                        (
                            Filenameable("negatively_fuzzed_01"),
                            "摲\x00À\x12Vêìê¸´ç;\U000da189Î\x8bOsJBô",
                        ),
                        (
                            Filenameable("negatively_fuzzed_02"),
                            "@ÝJ¦\x00\U0009afb6õ\U0004f775𐒐}",
                        ),
                        (Filenameable("negatively_fuzzed_03"), "\x91ÈÊ\x00\U00019bec"),
                        (Filenameable("negatively_fuzzed_04"), "\U00104e86\x00R\t-8^"),
                        (
                            Filenameable("negatively_fuzzed_05"),
                            "\x15>Ò\U000e5b00LË)T\x00Îç\U000ba5cf\U0010877d\x08Àº\U000a68cfÊ\xa08]\U000fca08\x181D\x0cY\U00060b23A\\¬ï\U000598e3\U0006622cc",
                        ),
                        (
                            Filenameable("negatively_fuzzed_06"),
                            "\U0003a78b\U000b955fÑ\x1c°\u1f58ªW\U00097442\x00\U000ca33b",
                        ),
                        (
                            Filenameable("negatively_fuzzed_07"),
                            "\U0005df63\x00'\x1f \U000562acxxÏÖ\nwf",
                        ),
                        (
                            Filenameable("negatively_fuzzed_08"),
                            "\U000cad55쮾\x17Ò\x918¤M\U000360d5ÔÅ\x00\r\U0007bfa9Zs6\x12À>\x19\U00105b43\x0e§\U000be9db",
                        ),
                        (
                            Filenameable("negatively_fuzzed_09"),
                            "\U000aa52b\x12U\x91ô\x81ô\x16\U0010bc24\U000cd094\x00",
                        ),
                        (
                            Filenameable("negatively_fuzzed_10"),
                            "´²\x82\x00\U000fc89dÀâ¨*û𭮩ò\x8f¤\x82¡ÂÝ_쇽\U000ac5e8EÖ\U000c9731ý⼪åùH\U0007d4cbP¶\x13Ä",
                        ),
                    ]
                ),
            ),
        ),
    ],
)


def assert_all_covered_and_not_more(symbol_table: intermediate.SymbolTable) -> None:
    """Assert that we covered all the XSD data types."""
    covered = set(BY_VALUE_TYPE.keys())

    data_type_def_xsd_id = Identifier("Data_type_def_XSD")

    data_type_def_xsd = symbol_table.must_find_enumeration(name=data_type_def_xsd_id)

    literal_values = {literal.value for literal in data_type_def_xsd.literals}

    not_covered = sorted(literal_values.difference(covered))
    surplus = sorted(covered.difference(literal_values))

    if len(not_covered) > 0:
        raise AssertionError(
            f"The following {data_type_def_xsd_id} literals of the meta-model "
            f"were not covered: {not_covered}"
        )

    if len(surplus) > 0:
        raise AssertionError(
            f"The following keys in BY_VALUE_TYPE were not present in "
            f"{data_type_def_xsd_id} literals of the meta-model: {surplus}"
        )
