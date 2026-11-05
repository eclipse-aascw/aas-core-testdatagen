# SPDX-FileCopyrightText: 2025 aas-core-testdatagen AUTHORS
#
# SPDX-License-Identifier: MIT

"""Update the meta-model, the golden test data and verify it for a given version."""

import argparse
import os
import pathlib
import subprocess
import sys

import dev_scripts.regenerate_test_data


def main() -> int:
    """Execute the main routine."""
    this_dir = pathlib.Path(os.path.realpath(__file__)).parent
    repo_root = this_dir.parent.parent

    default_sdk_path = (
        repo_root.parent
        / f"aas-core{dev_scripts.common.DEFAULT_META_MODEL_VERSION}-python"
    )

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--meta_model_version",
        help="Version of the meta-model which we want to update",
        default=dev_scripts.common.DEFAULT_META_MODEL_VERSION,
    )
    parser.add_argument(
        "--sdk_path",
        help="Path to the SDK used to verify the test data",
        default=os.path.relpath(str(default_sdk_path), os.getcwd()),
    )
    args = parser.parse_args()

    meta_model_version = str(args.meta_model_version)
    sdk_path = pathlib.Path(args.sdk_path)

    print("Downloading the latest meta-model...")
    subprocess.check_call(
        [
            sys.executable,
            str(this_dir / "download_latest_aas_core_meta.py"),
            "--meta_model_version",
            meta_model_version,
        ]
    )

    subprocess.check_call(
        [
            sys.executable,
            str(this_dir / "regenerate_test_data.py"),
            "--meta_model_version",
            meta_model_version,
        ]
    )

    golden_dir = dev_scripts.regenerate_test_data.construct_golden_dir(
        meta_model_version=meta_model_version
    )

    meta_model_path = dev_scripts.regenerate_test_data.construct_meta_model_path(
        meta_model_version=meta_model_version
    )

    print(f"Verifying the data in {golden_dir} with the SDK from {sdk_path} ...")

    subprocess.check_call(
        [
            sys.executable,
            str(this_dir / "verify_test_data_with_sdk.py"),
            "--sdk_path",
            str(sdk_path),
            "--test_data_dir",
            str(golden_dir),
            "--meta_model_path",
            str(meta_model_path),
            "--cache_meta_model",
        ]
    )

    print("Done.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
