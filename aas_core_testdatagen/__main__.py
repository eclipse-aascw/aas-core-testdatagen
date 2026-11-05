# SPDX-FileCopyrightText: 2025 aas-core-testdatagen AUTHORS
#
# SPDX-License-Identifier: MIT

"""Run aas-core3.1-testdatagen as Python module."""

import aas_core_testdatagen.main

if __name__ == "__main__":
    # The ``prog`` needs to be set in the argparse.
    # Otherwise, the program name in the help shown to the user will be ``__main__``.
    aas_core_testdatagen.main.main(prog="aas_core_testdatagen")
