# SPDX-FileCopyrightText: 2025 aas-core-testdatagen AUTHORS
#
# SPDX-License-Identifier: MIT

"""Provide common data types for the frozen_examples."""

from typing import OrderedDict

from aas_core_testdatagen.common import Filenameable


class Examples:
    """Represent frozen_examples and counter-frozen_examples of something textual."""

    def __init__(
        self,
        positives: OrderedDict[Filenameable, str],
        negatives: OrderedDict[Filenameable, str],
    ) -> None:
        """Initialize with the given values."""
        self.positives = positives
        self.negatives = negatives
