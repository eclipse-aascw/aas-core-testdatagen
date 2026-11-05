# SPDX-FileCopyrightText: 2025 aas-core-testdatagen AUTHORS
#
# SPDX-License-Identifier: MIT

"""Re-generate the test data."""

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Final

import dev_scripts.common

_REPO_ROOT: Final[pathlib.Path] = pathlib.Path(
    os.path.realpath(__file__)
).parent.parent.parent


def construct_golden_dir(meta_model_version: str) -> pathlib.Path:
    """Construct the path to the directory with the golden test data."""
    meta_model_version_in_paths = dev_scripts.common.meta_model_version_in_paths(
        meta_model_version
    )

    return (
        _REPO_ROOT
        / "dev"
        / "test_data"
        / "test_generation"
        / f"v{meta_model_version_in_paths}"
    )


def construct_meta_model_path(meta_model_version: str) -> pathlib.Path:
    """Construct the path to the meta-model based on the meta-model version."""
    meta_model_version_in_paths = dev_scripts.common.meta_model_version_in_paths(
        meta_model_version
    )

    return (
        _REPO_ROOT
        / "dev"
        / "test_data"
        / "meta_model"
        / f"v{meta_model_version_in_paths}.py"
    )


def main() -> int:
    """Execute the main routine."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--meta_model_version",
        help="Version of the meta-model which we want to update",
        default=dev_scripts.common.DEFAULT_META_MODEL_VERSION,
    )
    args = parser.parse_args()

    meta_model_version = str(args.meta_model_version)

    golden_dir = construct_golden_dir(meta_model_version)

    if golden_dir.exists():
        print(f"Deleting {golden_dir} to re-create it...")
        shutil.rmtree(golden_dir)

    golden_dir.mkdir(parents=True)

    meta_model_path = construct_meta_model_path(meta_model_version=meta_model_version)

    print(
        f"Generating the new golden test data "
        f"based on {meta_model_path} to {golden_dir}..."
    )
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "aas_core_testdatagen",
            "--meta_model_path",
            str(meta_model_path),
            "--output_dir",
            str(golden_dir),
            "--cache_meta_model",
        ]
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
