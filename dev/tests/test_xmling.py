# SPDX-FileCopyrightText: 2025 aas-core-testdatagen AUTHORS
#
# SPDX-License-Identifier: MIT

# pylint: disable=missing-docstring

import io
import unittest

from aas_core_codegen.common import Identifier

from aas_core_testdatagen import xmling


class TestXmlizer(unittest.TestCase):
    def test_empty(self) -> None:
        stream = io.StringIO()
        _ = xmling._Xmlizer(namespace="https://my-namespace.com", stream=stream)

        self.assertEqual("", stream.getvalue())

    def test_open_close(self) -> None:
        stream = io.StringIO()
        xmlizer = xmling._Xmlizer(namespace="https://my-namespace.com", stream=stream)

        xmlizer.enqueue_open(Identifier("hello"))
        xmlizer.write_close(Identifier("hello"))

        self.assertEqual(
            """\
<hello xmlns="https://my-namespace.com" />""",
            stream.getvalue(),
        )

    def test_double_open_close(self) -> None:
        stream = io.StringIO()
        with xmling._Xmlizer(
            namespace="https://my-namespace.com", stream=stream
        ) as xmlizer:
            # NOTE (mristin):
            # This is a bit of an uncommon XML -- sequence of elements instead of
            # a single root element, but we allow it for flexibility.

            xmlizer.enqueue_open(Identifier("hello"))
            xmlizer.write_close(Identifier("hello"))

            xmlizer.enqueue_open(Identifier("hello"))
            xmlizer.write_close(Identifier("hello"))

        self.assertEqual(
            """\
<hello xmlns="https://my-namespace.com" />
<hello xmlns="https://my-namespace.com" />""",
            stream.getvalue(),
        )

    def test_open_text_close(self) -> None:
        stream = io.StringIO()
        with xmling._Xmlizer(
            namespace="https://my-namespace.com", stream=stream
        ) as xmlizer:
            xmlizer.enqueue_open(Identifier("hello"))
            xmlizer.write_text("world!")
            xmlizer.write_close(Identifier("hello"))

        self.assertEqual(
            """\
<hello xmlns="https://my-namespace.com">world!</hello>""",
            stream.getvalue(),
        )

    def test_nested_self_close(self) -> None:
        stream = io.StringIO()
        with xmling._Xmlizer(
            namespace="https://my-namespace.com", stream=stream
        ) as xmlizer:
            xmlizer.enqueue_open(Identifier("hello"))

            xmlizer.enqueue_open(Identifier("world"))
            xmlizer.write_close(Identifier("world"))

            xmlizer.enqueue_open(Identifier("world"))
            xmlizer.write_close(Identifier("world"))

            xmlizer.write_close(Identifier("hello"))

        self.assertEqual(
            """\
<hello xmlns="https://my-namespace.com">
  <world />
  <world />
</hello>""",
            stream.getvalue(),
        )

    def test_nested_open_text_close(self) -> None:
        stream = io.StringIO()
        with xmling._Xmlizer(
            namespace="https://my-namespace.com", stream=stream
        ) as xmlizer:
            xmlizer.enqueue_open(Identifier("hello"))

            xmlizer.enqueue_open(Identifier("world"))
            xmlizer.write_text("!")
            xmlizer.write_close(Identifier("world"))

            xmlizer.enqueue_open(Identifier("world"))
            xmlizer.write_text("!")
            xmlizer.write_close(Identifier("world"))

            xmlizer.write_close(Identifier("hello"))

        self.assertEqual(
            """\
<hello xmlns="https://my-namespace.com">
  <world>!</world>
  <world>!</world>
</hello>""",
            stream.getvalue(),
        )

    def test_text_escaping(self) -> None:
        stream = io.StringIO()
        with xmling._Xmlizer(
            namespace="https://my-namespace.com", stream=stream
        ) as xmlizer:
            xmlizer.enqueue_open(Identifier("hello"))
            xmlizer.write_text("<&>")
            xmlizer.write_close(Identifier("hello"))

        self.assertEqual(
            """\
<hello xmlns="https://my-namespace.com">&lt;&amp;&gt;</hello>""",
            stream.getvalue(),
        )

    def test_text_and_elements_mixed(self) -> None:
        stream = io.StringIO()
        with xmling._Xmlizer(
            namespace="https://my-namespace.com", stream=stream
        ) as xmlizer:
            xmlizer.enqueue_open(Identifier("hello"))
            xmlizer.write_text("Hi ")
            xmlizer.enqueue_open(Identifier("world"))
            xmlizer.write_close(Identifier("world"))

            xmlizer.write_text("!")

            xmlizer.write_close(Identifier("hello"))

        self.assertEqual(
            """\
<hello xmlns="https://my-namespace.com">Hi <world />!</hello>""",
            stream.getvalue(),
        )

    def test_double_text(self) -> None:
        stream = io.StringIO()
        with xmling._Xmlizer(
            namespace="https://my-namespace.com", stream=stream
        ) as xmlizer:
            xmlizer.enqueue_open(Identifier("hello"))
            xmlizer.write_text("world")
            xmlizer.write_text("!")
            xmlizer.write_close(Identifier("hello"))

        self.assertEqual(
            """\
<hello xmlns="https://my-namespace.com">world!</hello>""",
            stream.getvalue(),
        )

    def test_unclosed_element_failure(self) -> None:
        stream = io.StringIO()
        xmlizer = xmling._Xmlizer(namespace="https://my-namespace.com", stream=stream)

        xmlizer.enqueue_open(Identifier("hello"))

        with self.assertRaises(ValueError):
            xmlizer.finalize()

    def test_intersecting_elements_failure(self) -> None:
        stream = io.StringIO()
        xmlizer = xmling._Xmlizer(namespace="https://my-namespace.com", stream=stream)

        xmlizer.enqueue_open(Identifier("a"))
        xmlizer.enqueue_open(Identifier("b"))

        with self.assertRaises(ValueError):
            xmlizer.write_close(Identifier("a"))

    def test_close_without_opening_failure(self) -> None:
        stream = io.StringIO()
        xmlizer = xmling._Xmlizer(namespace="https://my-namespace.com", stream=stream)

        with self.assertRaises(ValueError):
            xmlizer.write_close(Identifier("hello"))

    def test_text_without_opening_failure(self) -> None:
        stream = io.StringIO()
        xmlizer = xmling._Xmlizer(namespace="https://my-namespace.com", stream=stream)

        with self.assertRaises(ValueError):
            xmlizer.write_text("hello world")

    def test_double_close_failure(self) -> None:
        stream = io.StringIO()
        xmlizer = xmling._Xmlizer(namespace="https://my-namespace.com", stream=stream)

        xmlizer.enqueue_open(Identifier("hello"))
        xmlizer.write_close(Identifier("hello"))

        with self.assertRaises(ValueError):
            xmlizer.write_close(Identifier("hello"))


if __name__ == "__main__":
    unittest.main()
