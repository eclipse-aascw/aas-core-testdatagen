# SPDX-FileCopyrightText: 2025 aas-core-testdatagen AUTHORS
#
# SPDX-License-Identifier: MIT

"""Provide shared functionality for serialization of test cases."""

import pathlib
from typing import Set


class RelativePathAsserter:
    """Make sure that no test files overlap."""

    def __init__(self) -> None:
        self._observed_relative_paths = set()  # type: Set[pathlib.Path]

    def assert_and_add(self, relative_path: pathlib.Path) -> None:
        """Assert that the relative path has not been observed, and register it."""
        assert (
            relative_path not in self._observed_relative_paths
        ), f"The test cases with duplicate output paths detected: {relative_path}"
        self._observed_relative_paths.add(relative_path)
