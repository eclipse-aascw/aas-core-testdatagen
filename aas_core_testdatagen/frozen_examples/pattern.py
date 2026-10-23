"""
Collect example texts which match / don't match regular expressions.

Some frozen_examples are manually curated, while others are fuzzed by Hypothesis.
Since we want to generate the test data in a deterministic manner, we do not
automatically fuzz the patterns on-the-fly.
"""

# pylint: disable=line-too-long

import collections
from typing import Mapping, MutableMapping, List

from aas_core_codegen import intermediate, infer_for_schema

from aas_core_testdatagen.common import Filenameable
from aas_core_testdatagen.frozen_examples._types import Examples

# noinspection SpellCheckingInspection,HttpUrlsUsage

BY_PATTERN: Mapping[str, Examples] = collections.OrderedDict(
    [
        # Version type, revision type
        (
            "^(0|[1-9][0-9]*)$",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("zero"), "0"),
                        (Filenameable("one"), "1"),
                        (Filenameable("two_digits"), "10"),
                        (Filenameable("three_digits"), "120"),
                        (Filenameable("four_digits"), "1230"),
                        (Filenameable("fuzzed_01"), "59"),
                        (Filenameable("fuzzed_02"), "116"),
                        (Filenameable("fuzzed_03"), "7"),
                        (Filenameable("fuzzed_04"), "32"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("negative"), "-1"),
                        (Filenameable("dot"), "1.0"),
                        (Filenameable("letter"), "1.0rc1"),
                    ]
                ),
            ),
        ),
        # Date-time UTC
        (
            "^-?(([1-9][0-9][0-9][0-9]+)|(0[0-9][0-9][0-9]))-((0[1-9])|(1[0-2]))-((0[1-9])|([12][0-9])|(3[01]))T(((([01][0-9])|(2[0-3])):[0-5][0-9]:([0-5][0-9])(\\.[0-9]+)?)|24:00:00(\\.0+)?)(Z|\\+00:00|-00:00)$",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("random_positive"), "2022-04-01T01:02:03Z"),
                        (Filenameable("midnight_with_zeros"), "2022-04-01T00:00:00Z"),
                        (
                            Filenameable("midnight_with_24_hours"),
                            "2022-04-01T24:00:00Z",
                        ),
                        (
                            Filenameable("very_large_year"),
                            "123456789012345678901234567-04-01T00:00:00Z",
                        ),
                        (
                            Filenameable("very_long_fractional_second"),
                            "2022-04-01T00:00:00.1234567890123456789012345678901234567890Z",
                        ),
                        (
                            Filenameable("year_1_bce_is_a_leap_year"),
                            "-0001-02-29T01:02:03Z",
                        ),
                        (
                            Filenameable("year_5_bce_is_a_leap_year"),
                            "-0005-02-29T01:02:03Z",
                        ),
                        (
                            Filenameable("plus_zero_offset"),
                            "2022-04-01T24:00:00+00:00",
                        ),
                        (
                            Filenameable("minus_zero_offset"),
                            "2022-04-01T24:00:00-00:00",
                        ),
                        (Filenameable("fuzzed_01"), "0013-10-11T24:00:00.000000Z"),
                        (Filenameable("fuzzed_02"), "0001-01-01T00:00:00Z"),
                        (Filenameable("fuzzed_03"), "-3020-08-21T24:00:00.0Z"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("only_date"), "2022-04-01"),
                        (Filenameable("only_date_with_time_zone"), "2022-04-01Z"),
                        (Filenameable("date_time_without_zone"), "2022-04-01T01:02:03"),
                        (
                            Filenameable("date_time_with_offset"),
                            "2022-04-01T01:02:03+02:00",
                        ),
                        (Filenameable("without_seconds"), "2022-04-01T01:02Z"),
                        (Filenameable("without_minutes"), "2022-04-01T01Z"),
                        (
                            Filenameable("date_time_with_UTC_and_suffix"),
                            "2022-04-01T01:02:03Z-unexpected-suffix",
                        ),
                        (
                            Filenameable("invalid_february_29th"),
                            "2026-02-29T01:02:03Z",
                        ),
                        (
                            Filenameable("negatively_fuzzed_01"),
                            "hh?aåx윳\x10[\x82\x15 K/",
                        ),
                        (
                            Filenameable("negatively_fuzzed_02"),
                            "<1\U0003ca06\U00088dd0Å\\H\U000c0a13",
                        ),
                        (
                            Filenameable("negatively_fuzzed_03"),
                            "𢬣\U0004287cÍ·ð\x98²+\x9a\U0004117f",
                        ),
                        (
                            Filenameable("negatively_fuzzed_04"),
                            "\U0004a4b3ð\x8d\x85\U0004742f",
                        ),
                        (
                            Filenameable("negatively_fuzzed_05"),
                            "\U000e2bbee\U0001354d\x97ñ>",
                        ),
                        (Filenameable("negatively_fuzzed_06"), "\U00103da6𮝸"),
                        (Filenameable("negatively_fuzzed_07"), "匟16È\x12\U000150e0"),
                        (Filenameable("negatively_fuzzed_08"), "hh"),
                        (Filenameable("negatively_fuzzed_09"), "E\x85𑄦𠧃Z"),
                        (
                            Filenameable("negatively_fuzzed_10"),
                            "\U000c9efd\U000c9efd\U0007bafe\U0001bfa8\U0010908c\U00013eb6",
                        ),
                    ]
                ),
            ),
        ),
        # duration
        (
            "^-?P((([0-9]+Y([0-9]+M)?([0-9]+D)?|([0-9]+M)([0-9]+D)?|([0-9]+D))(T(([0-9]+H)([0-9]+M)?([0-9]+(\\.[0-9]+)?S)?|([0-9]+M)([0-9]+(\\.[0-9]+)?S)?|([0-9]+(\\.[0-9]+)?S)))?)|(T(([0-9]+H)([0-9]+M)?([0-9]+(\\.[0-9]+)?S)?|([0-9]+M)([0-9]+(\\.[0-9]+)?S)?|([0-9]+(\\.[0-9]+)?S))))$",
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
        # is_BCP_47_for_english
        (
            "^(en|EN)(-.*)?$",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("just_english_lowercase"), "en"),
                        (Filenameable("just_english_uppercase"), "EN"),
                        (Filenameable("english_lowercase_great_britain"), "en-GB"),
                        (Filenameable("english_lowercase_south_africa"), "en-ZA"),
                        (Filenameable("english_uppercase_great_britain"), "en-GB"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("german_lowercase"), "de"),
                        (Filenameable("german_uppercase"), "DE"),
                        (Filenameable("german_swiss"), "de-CH"),
                    ]
                ),
            ),
        ),
        # XML serializable string
        (
            "^[\\x09\\x0A\\x0D\\x20-\\uD7FF\\uE000-\\uFFFD\\U00010000-\\U0010FFFF]*$",
            Examples(
                positives=collections.OrderedDict(
                    [
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
                        (
                            Filenameable("negatively_fuzzed_01"),
                            "\U00086b7aØõ\U00015e66,å½Ý\x92½\U000c5b6b\U000d0635\U0008817a©\x00\x92Ü",
                        ),
                        (Filenameable("negatively_fuzzed_02"), "餍\x17½é"),
                        (
                            Filenameable("negatively_fuzzed_03"),
                            "\U000fea28AD\x0f\U000ca696\x85\U000eff4fÕ",
                        ),
                        (Filenameable("negatively_fuzzed_04"), "ºò\x18\x7f"),
                        (
                            Filenameable("negatively_fuzzed_05"),
                            "A\x04\x1e»\U00069a46\U000bb36f\x17°P",
                        ),
                        (Filenameable("negatively_fuzzed_06"), "0\x00\x9a\U000b1206"),
                        (Filenameable("negatively_fuzzed_07"), "봇àc\x1dr\x0c"),
                        (
                            Filenameable("negatively_fuzzed_08"),
                            "Q\x1a\x90(^\\\x8a\U00052727\x8dü\U000104aa×\U000d6657\U00016006\x13",
                        ),
                        (Filenameable("negatively_fuzzed_09"), "Âû\x9f\x1c\x96m'ß"),
                        (Filenameable("negatively_fuzzed_10"), "êò\x0f\U00086254U"),
                    ]
                ),
            ),
        ),
        # ID short
        (
            "^[a-zA-Z][a-zA-Z0-9_-]*[a-zA-Z0-9_]+$",
            Examples(
                positives=collections.OrderedDict(
                    [
                        # Minimal valid values
                        (Filenameable("minimal_lower"), "aa"),
                        (Filenameable("minimal_upper"), "AZ"),
                        (Filenameable("minimal_digit"), "a0"),
                        (Filenameable("minimal_underscore"), "a_"),
                        # Hyphens are allowed only before the final character
                        (Filenameable("single_internal_hyphen"), "a-b"),
                        (Filenameable("many_internal_hyphens"), "a----------------b"),
                        (Filenameable("hyphen_then_underscore"), "a-_"),
                        (Filenameable("alternating_hyphen_underscore"), "a-_-_-_-_-_"),
                        # Underscores may appear anywhere except at the beginning
                        (Filenameable("many_underscores"), "a________________"),
                        (Filenameable("ends_with_underscore"), "strange-name_"),
                        (Filenameable("underscore_after_first"), "A_"),
                        # Fuzzed
                        (Filenameable("fuzzed_01"), "fULCVpULCVq"),
                        (Filenameable("fuzzed_02"), "AopQejF"),
                        (Filenameable("fuzzed_03"), "Jk0k1414Di"),
                        (Filenameable("fuzzed_04"), "pVz10Vz10vZZNO9hM"),
                        (Filenameable("fuzzed_05"), "t8x1pz9WS4TGV"),
                        (Filenameable("fuzzed_06"), "tWC"),
                        (Filenameable("fuzzed_07"), "xF2bO_Uje6"),
                        (Filenameable("fuzzed_08"), "EO5DYAe"),
                        (Filenameable("fuzzed_09"), "nRdRe"),
                        (Filenameable("fuzzed_10"), "P7gn"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("negatively_fuzzed_01"), "\U0009aabe\U000f0fab7"),
                        (Filenameable("negatively_fuzzed_02"), "\x7f15"),
                        (
                            Filenameable("negatively_fuzzed_03"),
                            "66a\x07 $\x05\x98V颵<8f\U000ce416\x88;ÉÐ2þ\U000c88e77y",
                        ),
                        (
                            Filenameable("negatively_fuzzed_04"),
                            "\x87Y\U0005017d\U000cd22a",
                        ),
                        (Filenameable("negatively_fuzzed_05"), "9䠄\U0005375d"),
                        (Filenameable("negatively_fuzzed_06"), "@"),
                        (
                            Filenameable("negatively_fuzzed_07"),
                            "[?Íô0Ù\U0007a0d4ê\x02¶𘏫s\U000c2e6e\x8dU\U0004587f°\U0001b5a6",
                        ),
                        (Filenameable("negatively_fuzzed_08"), "\x84\x05"),
                        (
                            Filenameable("negatively_fuzzed_09"),
                            "®\n|\x13h\x0fÈ\x81\x80\U000dd6ccQ\U000a98ec¥Õ",
                        ),
                        (
                            Filenameable("negatively_fuzzed_10"),
                            "\U0009fc85\x13\U0005375d",
                        ),
                    ]
                ),
            ),
        ),
        # Content type (a.k.a. MIME type)
        (
            "^([!#$%&'*+\\-.^_`|~0-9a-zA-Z])+/([!#$%&'*+\\-.^_`|~0-9a-zA-Z])+([ \t]*;[ \t]*([!#$%&'*+\\-.^_`|~0-9a-zA-Z])+=(([!#$%&'*+\\-.^_`|~0-9a-zA-Z])+|\"(([\t !#-\\[\\]-~]|[\\x80-\\xff])|\\\\([\t !-~]|[\\x80-\\xff]))*\"))*$",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (
                            Filenameable("random_common_MIME_type"),
                            "application/something-random",
                        ),
                        (Filenameable("only_letters"), "audio/aac"),
                        (Filenameable("dash"), "application/x-abiword"),
                        (Filenameable("dots"), "application/vnd.amazon.ebook"),
                        (Filenameable("plus"), "application/vnd.apple.installer+xml"),
                        (Filenameable("number prefix and suffix"), "audio/3gpp2"),
                        # Fuzzed
                        (Filenameable("fuzzed_01"), "7/6qwqh6g"),
                        (Filenameable("fuzzed_02"), "15j/5j"),
                        (
                            Filenameable("fuzzed_03"),
                            '\'VbrwFrYTU/fO7NnLxq   \t; \tMX.`10dB732`X5yRy=I56Ov9Us\t ;\t\t pRb~~hdw_C%2Zf=""\t\t\t    \t\t\t \t \t\t \t  ; h=1t',
                        ),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("number"), "1234"),
                        (
                            Filenameable("negatively_fuzzed_01"),
                            "\U000b1b2e\U000ea76e\U000c86fa7\x1eýÑ\x9d|\U001019cd",
                        ),
                        (
                            Filenameable("negatively_fuzzed_02"),
                            "\U000b1b2e\U000ea76e\U000c86fa7\x1eýÑ\x9d|\U001019cd",
                        ),
                        (
                            Filenameable("negatively_fuzzed_03"),
                            "𡔹",
                        ),
                        (
                            Filenameable("negatively_fuzzed_04"),
                            "ÐÐ",
                        ),
                        (
                            Filenameable("negatively_fuzzed_05"),
                            "\U000ddd7d§\x85°¢\U000c385a>3\U000f8d37",
                        ),
                        (
                            Filenameable("negatively_fuzzed_06"),
                            "q\x95d",
                        ),
                        (
                            Filenameable("negatively_fuzzed_07"),
                            "0",
                        ),
                        (
                            Filenameable("negatively_fuzzed_08"),
                            "",
                        ),
                        (
                            Filenameable("negatively_fuzzed_09"),
                            "\r|ä",
                        ),
                        (
                            Filenameable("negatively_fuzzed_10"),
                            "\U0001cbb0\U0001cbb0",
                        ),
                    ]
                ),
            ),
        ),
        # BCP 47
        (
            "^(([a-zA-Z]{2,3}(-[a-zA-Z]{3}(-[a-zA-Z]{3}){,2})?|[a-zA-Z]{4}|[a-zA-Z]{5,8})(-[a-zA-Z]{4})?(-([a-zA-Z]{2}|[0-9]{3}))?(-(([a-zA-Z0-9]){5,8}|[0-9]([a-zA-Z0-9]){3}))*(-[0-9A-WY-Za-wy-z](-([a-zA-Z0-9]){2,8})+)*(-[xX](-([a-zA-Z0-9]){1,8})+)?|[xX](-([a-zA-Z0-9]){1,8})+|((en-GB-oed|i-ami|i-bnn|i-default|i-enochian|i-hak|i-klingon|i-lux|i-mingo|i-navajo|i-pwn|i-tao|i-tay|i-tsu|sgn-BE-FR|sgn-BE-NL|sgn-CH-DE)|(art-lojban|cel-gaulish|no-bok|no-nyn|zh-guoyu|zh-hakka|zh-min|zh-min-nan|zh-xiang)))$",
            Examples(
                positives=collections.OrderedDict(
                    [
                        # NOTE (mristin):
                        # The positive examples are taken from:
                        # https://www.rfc-editor.org/rfc/bcp/bcp47.txt, Appendix A.
                        (Filenameable("simple_language_subtag_1"), "de"),
                        (Filenameable("simple_language_subtag_2"), "fr"),
                        (Filenameable("simple_language_subtag_3"), "ja"),
                        (
                            Filenameable(
                                "simple_language_subtag_example_of_a_grandfathered_tag"
                            ),
                            "i-enochian",
                        ),
                        (
                            Filenameable("language_subtag_plus_script_subtag_1"),
                            "zh-Hant",
                        ),
                        (
                            Filenameable("language_subtag_plus_script_subtag_2"),
                            "zh-Hans",
                        ),
                        (
                            Filenameable("language_subtag_plus_script_subtag_3"),
                            "sr-Cyrl",
                        ),
                        (
                            Filenameable("language_subtag_plus_script_subtag_4"),
                            "sr-Latn",
                        ),
                        (Filenameable("extended_language_subtags_1"), "zh-cmn-Hans-CN"),
                        (Filenameable("extended_language_subtags_2"), "cmn-Hans-CN"),
                        (Filenameable("extended_language_subtags_3"), "zh-yue-HK"),
                        (Filenameable("extended_language_subtags_4"), "yue-HK"),
                        (Filenameable("language_script_region_1"), "zh-Hans-CN"),
                        (Filenameable("language_script_region_2"), "sr-Latn-RS"),
                        (Filenameable("language_variant_1"), "sl-rozaj"),
                        (Filenameable("language_variant_2"), "sl-rozaj-biske"),
                        (Filenameable("language_variant_3"), "sl-nedis"),
                        (Filenameable("language_region_variant_1"), "de-CH-1901"),
                        (Filenameable("language_region_variant_2"), "sl-IT-nedis"),
                        (
                            Filenameable("language_script_region_variant"),
                            "hy-Latn-IT-arevela",
                        ),
                        (Filenameable("language_region_1"), "de-DE"),
                        (Filenameable("language_region_2"), "en-US"),
                        (Filenameable("language_region_3"), "es-419"),
                        (Filenameable("private_use_subtags_1"), "de-CH-x-phonebk"),
                        (
                            Filenameable("private_use_subtags_2"),
                            "az-Arab-x-AZE-derbend",
                        ),
                        (Filenameable("private_use_registry_values_1"), "x-whatever"),
                        (
                            Filenameable("private_use_registry_values_2"),
                            "qaa-Qaaa-QM-x-southern",
                        ),
                        (Filenameable("private_use_registry_values_3"), "de-Qaaa"),
                        (
                            Filenameable("private_use_registry_values_4"),
                            "sr-Latn-QM",
                        ),
                        (Filenameable("private_use_registry_values_5"), "sr-Qaaa-RS"),
                        (Filenameable("tag_with_extension_1"), "en-US-u-islamcal"),
                        (
                            Filenameable("tag_with_extension_2"),
                            "zh-CN-a-myext-x-private",
                        ),
                        (Filenameable("tag_with_extension_3"), "en-a-myext-b-another"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("free_form_text"), "some free-form text"),
                        (
                            Filenameable("negatively_fuzzed_01"),
                            "𝨀\U000f2076𫯶\U0005d155¼°\x07ê\x8b\x00\x04\U00015e5a",
                        ),
                        (
                            Filenameable("negatively_fuzzed_02"),
                            "Ûg\U00105156²\U00085634e´\U00097795",
                        ),
                        (Filenameable("negatively_fuzzed_03"), "\U000c9efd\U000c9efd"),
                        (Filenameable("negatively_fuzzed_04"), "0"),
                        (Filenameable("negatively_fuzzed_05"), "\U00100b017111"),
                        (Filenameable("negatively_fuzzed_06"), "\U000efe8f"),
                        (Filenameable("negatively_fuzzed_07"), "\U000c9efd"),
                        (Filenameable("negatively_fuzzed_08"), "øPí"),
                        (Filenameable("negatively_fuzzed_09"), "pÜ\U00083bcb®AÇ"),
                        (
                            Filenameable("negatively_fuzzed_10"),
                            "\U000f15c8\x0b~û\x95\U000d64c4",
                        ),
                    ]
                ),
            ),
        ),
        # RFC 2396
        (
            r"^([a-zA-Z][a-zA-Z0-9+\-.]*:((//((((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[;:&=+$,])*@)?((([a-zA-Z0-9]|[a-zA-Z0-9]([a-zA-Z0-9]|-)*[a-zA-Z0-9])\.)*([a-zA-Z]|[a-zA-Z]([a-zA-Z0-9]|-)*[a-zA-Z0-9])(\.)?|[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)(:[0-9]*)?)?|(([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[$,;:@&=+])+)(/((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*(;((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*)*(/((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*(;((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*)*)*)?|/((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*(;((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*)*(/((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*(;((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*)*)*)(\?(([;/?:@&=+$,]|([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])))*)?|(([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[;?:@&=+$,])(([;/?:@&=+$,]|([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])))*)|(//((((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[;:&=+$,])*@)?((([a-zA-Z0-9]|[a-zA-Z0-9]([a-zA-Z0-9]|-)*[a-zA-Z0-9])\.)*([a-zA-Z]|[a-zA-Z]([a-zA-Z0-9]|-)*[a-zA-Z0-9])(\.)?|[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)(:[0-9]*)?)?|(([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[$,;:@&=+])+)(/((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*(;((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*)*(/((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*(;((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*)*)*)?|/((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*(;((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*)*(/((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*(;((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*)*)*|(([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[;@&=+$,])+(/((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*(;((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*)*(/((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*(;((([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])|[:@&=+$,]))*)*)*)?)(\?(([;/?:@&=+$,]|([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])))*)?)?(\#(([;/?:@&=+$,]|([a-zA-Z0-9]|[\-_.!~*'()])|%([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])([0-9]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF]|[aA]|[bB]|[cC]|[dD]|[eE]|[fF])))*)?$",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("fuzzed_01"), "#%4b%6AT"),
                        (
                            Filenameable("fuzzed_02"),
                            "RqjJsrvAJ1Uk:%9d'%8C_%81k,%Fcd?yw,@B,M=.EE%8E",
                        ),
                        (Filenameable("fuzzed_03"), "#/%38%21&"),
                        (Filenameable("fuzzed_04"), "//QQ%BF(,xe;A.@%94($,=%38@"),
                        (
                            Filenameable("fuzzed_05"),
                            "/;=:&%30%1a;77@%321%A4%21;%FC:=/;=,=%13y:%2D;+J%c6%bcU%D3;j1G:sg=%EcA%f3/@z%29%B7&B;=#@H%8D=U%FE%5e%22%Db?,+",
                        ),
                        (Filenameable("fuzzed_06"), "#;"),
                        (Filenameable("fuzzed_07"), "#%6A%6AT"),
                        (
                            Filenameable("fuzzed_08"),
                            "//bVfwa.f./%DC%60O@=;;%63;6%9b;l%E8Ib@$e::9%c0;w%0F;P%bD!v,$;@$;,=$%454-:R%2C%5E%4b2B=%eB%Da%0E%C4p%5c&;%de@%82%fB;v%bbw5q=%57%EE%1c;%e0%2A%af%1c0%eDm%5c%D2&;k*%12%5B;%A0&,:&$;:&%33;+,;%6c5;l%1D%35+%4a&%Fe+lk,+;C,~W=+=%3bn;;-p%3f%66R+%53;o%Bd$BIW%0d%Be%0E+l=I(k%Ac:,R%e6%9E%21%7f%54;;N%F3X@%8f%03%AE(=%9b:/;%F20;0L%27%4F;;%b0:9;%D5%31%1C;21u@%CE%fAE@$=#T%7D",
                        ),
                        (
                            Filenameable("fuzzed_09"),
                            "q2t2uv://777646689268.160810318.01435447069935.47:/%Be/%04@%Cd@P%dc:C$&~x=;%3f9+;;sr-i=p,///;%D5@@x&;V@I%16/+;%e4,@%AA@Ih:%8Dg=%F8P,v%dE%3E%03%62%FB=$R,&%ac%71;u%11l8*;,;$%Faj:;;;%ee$%8b%EC@%4Alo;t,%0b%eB%D5%EA:%De;$$1:@/%8e%0D&9%C8M;@5%28%4E%BC@%34;;@%EC=tL)x(/M%D3%aF&%Ec;=%aa$$j;;%B3@hk=e:%DB%24Z;%F6%9E+%8e;=;%ba;;%b3;;p%f11=%34%c0;#lR:+k%BE4%EB",
                        ),
                        (Filenameable("fuzzed_10"), "#%59T=%e1&&%b4%53EYU?,/q%87%c6He"),
                        (Filenameable("made_up_01"), "http://www.example.org"),
                        (
                            Filenameable("made_up_02"),
                            "ftp://ftp.is.co.za/rfc/rfc1808.txt",
                        ),
                        (Filenameable("made_up_03"), "mailto:John.Doe@example.org"),
                        (
                            Filenameable("made_up_04"),
                            "news:comp.infosystems.www.servers.unix",
                        ),
                        (Filenameable("made_up_05"), "telnet://192.0.2.16:80/"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("negatively_fuzzed_01"), "\U0004afa4"),
                        (Filenameable("negatively_fuzzed_02"), "\U000ddeaeꨁ"),
                        (Filenameable("negatively_fuzzed_03"), "çö"),
                        (
                            Filenameable("negatively_fuzzed_04"),
                            "_\x18å¢\x84z|\x9d\U0010c28b\U0006255e\U000fe561i\U000d2b21-\x81",
                        ),
                        (Filenameable("negatively_fuzzed_05"), "\x86䀣\U000165c5"),
                        (Filenameable("negatively_fuzzed_06"), "\U000ddeaeꨁ\U0006990a"),
                        (Filenameable("negatively_fuzzed_07"), "ࠁࠁ\x7f𦊩"),
                        (Filenameable("negatively_fuzzed_08"), "\ue140P\x81Kâ"),
                        (Filenameable("negatively_fuzzed_09"), 'ð"u'),
                        (Filenameable("negatively_fuzzed_10"), "00𐀇"),
                        (
                            Filenameable("negatively_made_up_01"),
                            "http://exa mple.org",
                        ),  # Space in URI
                        (
                            Filenameable("negatively_made_up_02"),
                            "://example.org",
                        ),  # Missing scheme
                    ]
                ),
            ),
        ),
        # RFC 8089
        (
            "^file:(//((localhost|(\\[((([0-9A-Fa-f]{1,4}:){6}([0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|::([0-9A-Fa-f]{1,4}:){5}([0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|([0-9A-Fa-f]{1,4})?::([0-9A-Fa-f]{1,4}:){4}([0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(([0-9A-Fa-f]{1,4}:)?[0-9A-Fa-f]{1,4})?::([0-9A-Fa-f]{1,4}:){3}([0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(([0-9A-Fa-f]{1,4}:){,2}[0-9A-Fa-f]{1,4})?::([0-9A-Fa-f]{1,4}:){2}([0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(([0-9A-Fa-f]{1,4}:){,3}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}:([0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(([0-9A-Fa-f]{1,4}:){,4}[0-9A-Fa-f]{1,4})?::([0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(([0-9A-Fa-f]{1,4}:){,5}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}|(([0-9A-Fa-f]{1,4}:){,6}[0-9A-Fa-f]{1,4})?::)|[vV][0-9A-Fa-f]+\\.([a-zA-Z0-9\\-._~]|[!$&'()*+,;=]|:)+)\\]|([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])|([a-zA-Z0-9\\-._~]|%[0-9A-Fa-f][0-9A-Fa-f]|[!$&'()*+,;=])*)))?/((([a-zA-Z0-9\\-._~]|%[0-9A-Fa-f][0-9A-Fa-f]|[!$&'()*+,;=]|[:@]))+(/(([a-zA-Z0-9\\-._~]|%[0-9A-Fa-f][0-9A-Fa-f]|[!$&'()*+,;=]|[:@]))*)*)?|/((([a-zA-Z0-9\\-._~]|%[0-9A-Fa-f][0-9A-Fa-f]|[!$&'()*+,;=]|[:@]))+(/(([a-zA-Z0-9\\-._~]|%[0-9A-Fa-f][0-9A-Fa-f]|[!$&'()*+,;=]|[:@]))*)*)?)$",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (
                            Filenameable("local_absolute_path_with_scheme"),
                            "file:/path/to/somewhere",
                        ),
                        # See: https://datatracker.ietf.org/doc/html/rfc8089#appendix-B
                        (
                            Filenameable("local_file_with_an_explicit_authority"),
                            "file://host.example.com/path/to/file",
                        ),
                        # Fuzzed
                        (
                            Filenameable("fuzzed_01"),
                            "file:/M5/%bA:'%9c%6b%ed%00Y*/%4C=4h:d:",
                        ),
                        (
                            Filenameable("fuzzed_02"),
                            "file:///;/@@=%5a@@g@=S%D8:%f5;/@:/%A3&!%f8%6e;%a1!//~/%Ae%c2/%99O@,:",
                        ),
                        (Filenameable("fuzzed_03"), "file://localhost/C:"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty"), ""),
                        (Filenameable("number"), "1234"),
                        (
                            Filenameable("absolute_path_without_scheme"),
                            "/path/to/somewhere",
                        ),
                        (
                            Filenameable("relative_path_without_scheme"),
                            "path/to/somewhere",
                        ),
                        (
                            Filenameable("local_relative_path_with_scheme"),
                            "file:path/to/somewhere",
                        ),
                        (
                            Filenameable("negatively_fuzzed_01"),
                            "\U000a8eda\U00082f76ÃZ",
                        ),
                        (
                            Filenameable("negatively_fuzzed_02"),
                            "t#á\U0010318fXM~ùÌø\x9e\U0004c9d1",
                        ),
                        (Filenameable("negatively_fuzzed_03"), "\U000566ee&1𗃹þ𭀔9"),
                        (Filenameable("negatively_fuzzed_04"), "//"),
                        (
                            Filenameable("negatively_fuzzed_05"),
                            "\U000c7494\x1f\x9b\U000426da\xa0¸\U000be8e1*",
                        ),
                        (Filenameable("negatively_fuzzed_06"), "C"),
                        (Filenameable("negatively_fuzzed_07"), "\U000834ee"),
                        (Filenameable("negatively_fuzzed_08"), "â·\U00055392E"),
                        (
                            Filenameable("negatively_fuzzed_09"),
                            "s\U0001acc1\U00088dd0Å\\H\U000c0a13",
                        ),
                        (Filenameable("negatively_fuzzed_10"), "hxY"),
                    ]
                ),
            ),
        ),
        # matches_path_item
        (
            "^(([A-Za-z][A-Za-z0-9_]+)|(\\[[0-9]+\\]))((\\.[A-Za-z][A-Za-z0-9_]+)|(\\[[0-9]+\\])){0,}$",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("id_short"), "sme1"),
                        (Filenameable("nested"), "sme1.sme2[0].p1"),
                        (Filenameable("index_only"), "[0]"),
                        (Filenameable("index_then_id_short"), "[8].ABJ0MB8T"),
                        (Filenameable("fuzzed_01"), "[88607]"),
                        (Filenameable("fuzzed_02"), "A0"),
                        (Filenameable("fuzzed_03"), "[2004][688]"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("single_character_id_short"), "a"),
                        (Filenameable("trailing_dot"), "sme1."),
                        (Filenameable("leading_dot"), ".sme1"),
                        (Filenameable("unclosed_index"), "sme1[0"),
                        (Filenameable("empty_index"), "sme1[]"),
                        (Filenameable("leading_digit"), "1sme"),
                        (Filenameable("negatively_fuzzed_01"), "t!"),
                        (Filenameable("negatively_fuzzed_02"), "F2\x1b"),
                        (Filenameable("negatively_fuzzed_03"), "wºã"),
                    ]
                ),
            ),
        ),
        # matches_field_identifier
        (
            "^(\\$aas#(idShort|id|assetInformation\\.assetKind|assetInformation\\.assetType|assetInformation\\.globalAssetId|assetInformation\\.specificAssetIds\\[(0|[1-9][0-9]*)?\\]\\.(name|value|externalSubjectId(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?)|submodels\\[(0|[1-9][0-9]*)?\\](\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?)|\\$sm#(semanticId(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?|supplementalSemanticIds(\\[(0|[1-9][0-9]*)?\\])?(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?|idShort|id)|\\$sme(\\.[A-Za-z]([A-Za-z0-9_-]*[A-Za-z0-9_])?(\\[(0|[1-9][0-9]*)?\\])*(\\.[A-Za-z]([A-Za-z0-9_-]*[A-Za-z0-9_])?(\\[(0|[1-9][0-9]*)?\\])*)*)?#(semanticId(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?|supplementalSemanticIds(\\[(0|[1-9][0-9]*)?\\])?(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?|idShort|value|valueType|language)|\\$cd#(idShort|id)|\\$aasdesc#(idShort|id|assetKind|assetType|globalAssetId|specificAssetIds\\[(0|[1-9][0-9]*)?\\]\\.(name|value|externalSubjectId(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?)|endpoints\\[(0|[1-9][0-9]*)?\\]\\.(interface|protocolinformation\\.href)|submodelDescriptors\\[(0|[1-9][0-9]*)?\\]\\.(semanticId(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?|supplementalSemanticIds(\\[(0|[1-9][0-9]*)?\\])?(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?|idShort|id|endpoints\\[(0|[1-9][0-9]*)?\\]\\.(interface|protocolinformation\\.href)))|\\$smdesc#(semanticId(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?|supplementalSemanticIds(\\[(0|[1-9][0-9]*)?\\])?(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?|idShort|id|endpoints\\[(0|[1-9][0-9]*)?\\]\\.(interface|protocolinformation\\.href)))$",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("aas_id_short"), "$aas#idShort"),
                        (
                            Filenameable("aas_asset_kind"),
                            "$aas#assetInformation.assetKind",
                        ),
                        (
                            Filenameable("aas_specific_asset_id_name"),
                            "$aas#assetInformation.specificAssetIds[0].name",
                        ),
                        (
                            Filenameable("aas_submodel_key_value"),
                            "$aas#submodels[].keys[1].value",
                        ),
                        (
                            Filenameable("sm_semantic_id"),
                            "$sm#semanticId.keys[0].value",
                        ),
                        (
                            Filenameable("sme_with_path"),
                            "$sme.someCollection.someProperty#value",
                        ),
                        (
                            Filenameable("sme_with_index"),
                            "$sme.list[3].prop#valueType",
                        ),
                        (Filenameable("sme_root"), "$sme#idShort"),
                        (Filenameable("cd_id"), "$cd#id"),
                        (
                            Filenameable("aasdesc_endpoint"),
                            "$aasdesc#endpoints[0].protocolinformation.href",
                        ),
                        (Filenameable("smdesc_semantic_id"), "$smdesc#semanticId.type"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("unknown_root"), "$xyz#idShort"),
                        (Filenameable("missing_attribute"), "$aas"),
                        (Filenameable("wrong_attribute"), "$cd#value"),
                        (Filenameable("bare_index"), "$aas#submodels[a]"),
                        (Filenameable("leading_zero_index"), "$aas#submodels[01]"),
                        (Filenameable("id_short_path_trailing_dot"), "$sme.a.#value"),
                        (Filenameable("no_hash"), "$sm.idShort"),
                        (Filenameable("empty"), ""),
                    ]
                ),
            ),
        ),
        # matches_fragment_field_identifier
        (
            "^(\\$aas#(idShort|assetInformation\\.assetType|assetInformation\\.globalAssetId|assetInformation\\.specificAssetIds(\\[(0|[1-9][0-9]*)?\\](\\.externalSubjectId(\\.keys(\\[(0|[1-9][0-9]*)?\\])?)?)?)?|submodels(\\[(0|[1-9][0-9]*)?\\](\\.keys(\\[(0|[1-9][0-9]*)?\\])?)?)?)|\\$sm#(semanticId(\\.keys(\\[(0|[1-9][0-9]*)?\\])?)?|supplementalSemanticIds(\\[(0|[1-9][0-9]*)?\\](\\.keys(\\[(0|[1-9][0-9]*)?\\])?)?)?|idShort)|\\$sme(\\.[A-Za-z]([A-Za-z0-9_-]*[A-Za-z0-9_])?(\\[(0|[1-9][0-9]*)?\\])*(\\.[A-Za-z]([A-Za-z0-9_-]*[A-Za-z0-9_])?(\\[(0|[1-9][0-9]*)?\\])*)*)?(#(semanticId(\\.keys(\\[(0|[1-9][0-9]*)?\\])?)?|supplementalSemanticIds(\\[(0|[1-9][0-9]*)?\\](\\.keys(\\[(0|[1-9][0-9]*)?\\])?)?)?|idShort|value|valueType|language))?|\\$cd#idShort|\\$aasdesc#(idShort|description|displayName|extension|administration|assetKind|assetType|globalAssetId|specificAssetIds(\\[(0|[1-9][0-9]*)?\\](\\.externalSubjectId(\\.keys(\\[(0|[1-9][0-9]*)?\\])?)?)?)?|endpoints(\\[(0|[1-9][0-9]*)?\\])?|submodelDescriptors(\\[(0|[1-9][0-9]*)?\\](\\.(semanticId(\\.keys(\\[(0|[1-9][0-9]*)?\\])?)?|supplementalSemanticIds(\\[(0|[1-9][0-9]*)?\\](\\.keys(\\[(0|[1-9][0-9]*)?\\])?)?)?|idShort|endpoints(\\[(0|[1-9][0-9]*)?\\])?))?)?)|\\$smdesc#(semanticId(\\.keys(\\[(0|[1-9][0-9]*)?\\])?)?|supplementalSemanticIds(\\[(0|[1-9][0-9]*)?\\](\\.keys(\\[(0|[1-9][0-9]*)?\\])?)?)?|idShort|endpoints(\\[(0|[1-9][0-9]*)?\\])?))$",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (
                            Filenameable("aas_specific_asset_ids"),
                            "$aas#assetInformation.specificAssetIds[]",
                        ),
                        (Filenameable("aas_submodels"), "$aas#submodels"),
                        (
                            Filenameable("sm_semantic_id_keys"),
                            "$sm#semanticId.keys[0]",
                        ),
                        (Filenameable("sme_only_path"), "$sme.someCollection"),
                        (Filenameable("sme_root"), "$sme"),
                        (Filenameable("sme_value"), "$sme.prop#value"),
                        (Filenameable("cd_id_short"), "$cd#idShort"),
                        (Filenameable("aasdesc_description"), "$aasdesc#description"),
                        (
                            Filenameable("aasdesc_sm_descriptors"),
                            "$aasdesc#submodelDescriptors[1].idShort",
                        ),
                        (Filenameable("smdesc_endpoints"), "$smdesc#endpoints[]"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("unknown_root"), "$xyz#idShort"),
                        (Filenameable("cd_id"), "$cd#id"),
                        (Filenameable("sm_id"), "$sm#id"),
                        (Filenameable("bad_index"), "$aas#submodels[x]"),
                        (Filenameable("empty"), ""),
                        (Filenameable("trailing_dot"), "$sme.a."),
                        (Filenameable("missing_root"), "#idShort"),
                    ]
                ),
            ),
        ),
        # matches_hex_literal
        (
            "^16#[0-9A-F]+$",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("one_digit"), "16#1"),
                        (Filenameable("upper"), "16#1F"),
                        (Filenameable("long"), "16#DEADBEEF"),
                        (Filenameable("zeros"), "16#00"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("no_prefix"), "1F"),
                        (Filenameable("lower_case"), "16#1f"),
                        (Filenameable("empty_digits"), "16#"),
                        (Filenameable("other_base"), "8#17"),
                        (Filenameable("not_hex"), "16#G1"),
                    ]
                ),
            ),
        ),
        # matches_date_time_literal
        (
            "^(([0-9]{4}-((0[13578]|1[02])-(0[1-9]|[12][0-9]|3[01])|(0[469]|11)-(0[1-9]|[12][0-9]|30)|02-(0[1-9]|1[0-9]|2[0-8])))|(([0-9]{2}(0[48]|[2468][048]|[13579][26])|([02468][048]|[13579][26])00)-02-29))T?(([01][0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?(\\.[0-9]+)?|24:00(:00)?(\\.0+)?)(Z|[+-]((0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("utc"), "2024-02-29T12:00:00Z"),
                        (Filenameable("no_separator"), "2024-03-0112:00:00Z"),
                        (Filenameable("no_seconds"), "2023-12-31T23:59"),
                        (
                            Filenameable("with_fraction"),
                            "2023-01-01T00:00:00.123+01:00",
                        ),
                        (Filenameable("midnight_24"), "2023-01-01T24:00:00"),
                        (Filenameable("negative_offset"), "2023-06-15T08:30:00-05:00"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("no_leap_year"), "2023-02-29T12:00:00Z"),
                        (Filenameable("no_time"), "2024-01-01"),
                        (Filenameable("bad_month"), "2024-13-01T12:00:00Z"),
                        (Filenameable("bad_hour"), "2024-01-01T25:00:00Z"),
                        (Filenameable("bad_offset"), "2024-01-01T12:00:00+15:00"),
                        (Filenameable("empty"), ""),
                    ]
                ),
            ),
        ),
        # matches_time_literal
        (
            "^(([01][0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?(\\.[0-9]+)?|24:00(:00)?(\\.0+)?)(Z|[+-]((0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$",
            Examples(
                positives=collections.OrderedDict(
                    [
                        (Filenameable("hours_minutes"), "12:30"),
                        (Filenameable("with_seconds"), "12:00:00"),
                        (Filenameable("with_zone"), "12:00:00+01:00"),
                        (Filenameable("utc"), "23:59:59Z"),
                        (Filenameable("fraction"), "00:00:00.5"),
                        (Filenameable("end_of_day"), "24:00"),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("bad_hour"), "25:00"),
                        (Filenameable("bad_minute"), "12:60"),
                        (Filenameable("missing_minutes"), "12"),
                        (Filenameable("bad_offset"), "12:00+14:30"),
                        (Filenameable("date"), "2024-01-01"),
                        (Filenameable("empty"), ""),
                    ]
                ),
            ),
        ),
        # matches_reference_identifier
        (
            '^(\\$aas\\("([\\x09\\x0A\\x0D\\x20-\\x21\\x23-\\x5B\\x5D-\\uD7FF\\uE000-\\uFFFD\\U00010000-\\U0010FFFF]|\\\\["\\\\])+"\\)#(idShort|id|assetInformation\\.assetKind|assetInformation\\.assetType|assetInformation\\.globalAssetId|assetInformation\\.specificAssetIds\\[(0|[1-9][0-9]*)?\\]\\.(name|value|externalSubjectId(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?)|submodels\\[(0|[1-9][0-9]*)?\\](\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?)|\\$sm\\("([\\x09\\x0A\\x0D\\x20-\\x21\\x23-\\x5B\\x5D-\\uD7FF\\uE000-\\uFFFD\\U00010000-\\U0010FFFF]|\\\\["\\\\])+"\\)#(semanticId(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?|supplementalSemanticIds(\\[(0|[1-9][0-9]*)?\\])?(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?|idShort|id)|\\$cd\\("([\\x09\\x0A\\x0D\\x20-\\x21\\x23-\\x5B\\x5D-\\uD7FF\\uE000-\\uFFFD\\U00010000-\\U0010FFFF]|\\\\["\\\\])+"\\)#(idShort|id)|\\$sme\\("([\\x09\\x0A\\x0D\\x20-\\x21\\x23-\\x5B\\x5D-\\uD7FF\\uE000-\\uFFFD\\U00010000-\\U0010FFFF]|\\\\["\\\\])+"\\)\\.[A-Za-z]([A-Za-z0-9_-]*[A-Za-z0-9_])?(\\[(0|[1-9][0-9]*)?\\])*(\\.[A-Za-z]([A-Za-z0-9_-]*[A-Za-z0-9_])?(\\[(0|[1-9][0-9]*)?\\])*)*#(semanticId(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?|supplementalSemanticIds(\\[(0|[1-9][0-9]*)?\\])?(\\.(type|keys\\[(0|[1-9][0-9]*)?\\]\\.(type|value)))?|idShort|value|valueType|language))$',
            Examples(
                positives=collections.OrderedDict(
                    [
                        (
                            Filenameable("sm_id_short"),
                            '$sm("https://example.com/sm")#idShort',
                        ),
                        (Filenameable("aas_id"), '$aas("urn:aas:1")#id'),
                        (
                            Filenameable("sme_value"),
                            '$sme("https://example.com/sm").someProperty#value',
                        ),
                        (
                            Filenameable("sme_nested"),
                            '$sme("sm1").coll.list[0].prop#valueType',
                        ),
                        (Filenameable("cd_id_short"), '$cd("cd1")#idShort'),
                        (Filenameable("escaped_quote"), '$sm("a\\"b")#id'),
                        (Filenameable("escaped_backslash"), '$sm("a\\\\b")#id'),
                        (
                            Filenameable("aas_submodel_key"),
                            '$aas("urn:aas:1")#submodels[0].keys[0].value',
                        ),
                    ]
                ),
                negatives=collections.OrderedDict(
                    [
                        (Filenameable("empty_identifier"), '$sm("")#idShort'),
                        (Filenameable("unescaped_quote"), '$sm("a"b")#id'),
                        (Filenameable("missing_path"), '$sme("sm1")#value'),
                        (Filenameable("missing_parens"), "$sm#idShort"),
                        (Filenameable("unknown_root"), '$xyz("a")#idShort'),
                        (Filenameable("cd_value"), '$cd("a")#value'),
                        (Filenameable("empty"), ""),
                    ]
                ),
            ),
        ),
    ]
)


def assert_all_pattern_verification_functions_covered(
    symbol_table: intermediate.SymbolTable,
    constraints_by_class: Mapping[
        intermediate.ClassUnion, infer_for_schema.ConstraintsByValue
    ],
) -> None:
    """Assert that we have some pattern for each pattern verification function."""
    expected = {
        verification.pattern
        for verification in symbol_table.verification_functions
        if (
            isinstance(verification, intermediate.PatternVerification)
            # NOTE (mristin, 2023-03-01):
            # We test the ``matches_xs_*`` functions in xs_value.py.
            and not verification.name.startswith("matches_xs_")
        )
    }

    pattern_to_sources = dict()  # type: MutableMapping[str, List[str]]
    for verification in symbol_table.verification_functions:
        if not isinstance(verification, intermediate.PatternVerification):
            continue

        source = f"Verification function {verification.name}"
        if verification.pattern not in pattern_to_sources:
            pattern_to_sources[verification.pattern] = [source]
        else:
            pattern_to_sources[verification.pattern].append(source)

    for cls, class_constraints in constraints_by_class.items():
        for prop in cls.properties:
            type_anno = intermediate.beneath_optional(prop.type_annotation)

            constraints = class_constraints.get(type_anno, None)

            if constraints is None:
                continue

            if constraints.patterns is not None:
                for constraint in constraints.patterns:
                    expected.add(constraint.pattern)
                    source = f"Inferred constraint on {cls.name}.{prop.name}"

                    if constraint.pattern not in pattern_to_sources:
                        pattern_to_sources[constraint.pattern] = [source]
                    else:
                        pattern_to_sources[constraint.pattern].append(source)

    covered = set(BY_PATTERN.keys())

    not_covered = sorted(expected.difference(covered))

    if len(not_covered) > 0:
        pattern_analysis_joined = "\n".join(
            f"{pattern!r} -> {pattern_to_sources[pattern]}" for pattern in not_covered
        )
        raise AssertionError(
            f"The following patterns from the respective pattern verification "
            f"functions were not covered:\n{pattern_analysis_joined}"
        )
