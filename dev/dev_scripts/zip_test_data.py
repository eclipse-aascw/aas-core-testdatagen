# SPDX-FileCopyrightText: 2025 aas-core-testdatagen AUTHORS
#
# SPDX-License-Identifier: MIT

"""Zip the individual test data for each meta-model in a separate archive."""

import argparse
import os
import pathlib
import sys
import zipfile


def main() -> int:
    """Execute the main routine."""
    repo_root = pathlib.Path(os.path.realpath(__file__)).parent.parent.parent

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output_dir",
        help="Directory where to put the zip archives",
        default=str(repo_root / "build"),
    )
    args = parser.parse_args()

    output_dir = pathlib.Path(args.output_dir)

    if output_dir.exists() and not output_dir.is_dir():
        print(f"The --output_dir is not a directory: {output_dir}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    for meta_model_dir in sorted(
        path
        for path in (repo_root / "dev" / "test_data" / "test_generation").iterdir()
        if path.is_dir() and path.name.startswith("v")
    ):
        output_path = output_dir / f"test_data_for_{meta_model_dir.name}.zip"

        print(f"Creating {output_path}...")

        with zipfile.ZipFile(
            output_path, "w", zipfile.ZIP_LZMA, compresslevel=9
        ) as zip_file:
            for root, _, files in os.walk(meta_model_dir):
                for file in files:
                    file_path = pathlib.Path(root) / file
                    path_in_archive = file_path.relative_to(meta_model_dir)
                    zip_file.write(file_path, path_in_archive)

        print(f"Created {output_path}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
