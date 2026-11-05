# SPDX-FileCopyrightText: 2025 aas-core-testdatagen AUTHORS
#
# SPDX-License-Identifier: MIT

"""Generate test data for AAS elements based on the meta-model."""

import argparse
import hashlib
import itertools
import os.path
import pathlib
import pickle
import sys
import tempfile
import uuid
from typing import TextIO, Tuple, Optional

import aas_core_codegen.infer_for_schema
import aas_core_codegen.intermediate
import aas_core_codegen.run
from icontract import ensure

import aas_core_testdatagen
from aas_core_testdatagen import generation, verification, jsoning, xmling
from aas_core_testdatagen.common import bullet_points
from aas_core_testdatagen.v3_1 import generation as v3_1_generation
from aas_core_testdatagen.v3_2 import generation as v3_2_generation

assert aas_core_testdatagen.__doc__ == __doc__


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _load_meta_model(
    meta_model_path: pathlib.Path,
) -> Tuple[Optional[aas_core_codegen.intermediate.SymbolTable], Optional[str]]:
    """
    Load and parse the symbol table from the disk.

    Return the symbol table, or an error, if any.
    """
    symbol_table_atok, error = aas_core_codegen.run.load_model(meta_model_path)
    if error is not None:
        return None, error

    assert symbol_table_atok is not None
    symbol_table, _ = symbol_table_atok

    return symbol_table, None


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _load_or_cache_meta_model(
    meta_model_path: pathlib.Path,
) -> Tuple[Optional[aas_core_codegen.intermediate.SymbolTable], Optional[str]]:
    """
    Use the system temp directory to manage the caching of the symbol table.

    Return the symbol table, or an error, if any.
    """
    symbol_table: Optional[aas_core_codegen.intermediate.SymbolTable] = None

    hasher = hashlib.sha256()
    hasher.update(meta_model_path.read_bytes())
    meta_model_hash_hexdigest = hasher.hexdigest()

    this_path = pathlib.Path(__file__).resolve()

    cached_symbol_table_path = (
        pathlib.Path(tempfile.gettempdir())
        / f"aas-core-testdatagen-{this_path.parent.name}-{this_path.stem}"
        / f"symbol_table-{meta_model_hash_hexdigest}.pickle"
    )

    if not cached_symbol_table_path.exists():
        # NOTE (mristin):
        # We include the hash of the content in the file name, so the parsed symbol
        # table will correspond to the source.

        symbol_table, error = _load_meta_model(meta_model_path=meta_model_path)
        if error is not None:
            return None, error

        assert symbol_table is not None

        try:
            cached_symbol_table_path.parent.mkdir(exist_ok=True, parents=True)
        except Exception as exception:
            return None, (
                f"Failed to create the cache directory {cached_symbol_table_path}: "
                f"{exception}"
            )

        # NOTE (mristin):
        # We assume here a non-distributed filesystem where the renames in the
        # same directory are atomic.

        tmp_path = (
            cached_symbol_table_path.parent
            / f"{cached_symbol_table_path.name}-{uuid.uuid4()}.tmp"
        )
        try:
            with tmp_path.open("wb") as fid:
                # noinspection PyTypeChecker
                pickle.dump(symbol_table, fid)

            tmp_path.rename(cached_symbol_table_path)
        except Exception as exception:
            return None, f"Failed to pickle the meta-model to {tmp_path}: {exception}"
        finally:
            tmp_path.unlink(missing_ok=True)

    else:
        try:
            with cached_symbol_table_path.open("rb") as fid:
                symbol_table = pickle.load(fid)
        except Exception as exception:
            return None, (
                f"Failed to load the cached symbol table "
                f"from {cached_symbol_table_path}: {exception}"
            )

        if not isinstance(symbol_table, aas_core_codegen.intermediate.SymbolTable):
            symbol_table_qualname = (
                aas_core_codegen.intermediate.SymbolTable.__qualname__
            )
            return None, (
                f"Expected a {symbol_table_qualname} "
                f"from {cached_symbol_table_path}, "
                f"but got {symbol_table}"
            )

    return symbol_table, None


def execute(
    meta_model_path: pathlib.Path,
    output_dir: pathlib.Path,
    cache_meta_model: bool,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """
    Execute the test case generation.

    Return the exit code.
    """
    if not meta_model_path.exists():
        print(f"The --model_path does not exist: {meta_model_path}", file=stderr)
        return 1

    if not meta_model_path.is_file():
        print(f"The --model_path is not a file: {meta_model_path}", file=stderr)
        return 1

    if cache_meta_model:
        print(
            f"Loading the meta-model from {meta_model_path} "
            f"or from the temporary directory if already cached..."
        )
        symbol_table, load_error = _load_or_cache_meta_model(
            meta_model_path=meta_model_path
        )
    else:
        print(f"Loading the meta-model from {meta_model_path} ...")
        symbol_table, load_error = _load_meta_model(meta_model_path=meta_model_path)

    if load_error is not None:
        print(
            f"Failed to load the meta-model from {meta_model_path}: {load_error}",
            file=sys.stderr,
        )
        return 1

    assert symbol_table is not None

    constraints_by_class, inference_errors = (
        aas_core_codegen.infer_for_schema.infer_constraints_by_class(
            symbol_table=symbol_table
        )
    )
    if inference_errors is not None:
        errors_str = bullet_points(map(repr, inference_errors))
        print(
            f"Failed to infer the schema constraints from --model_path:\n{errors_str}",
            file=stderr,
        )
        return 1

    assert constraints_by_class is not None
    reorganized_constraints_by_class = (
        verification.reorganize_schema_constraints_by_properties(
            constraints_by_class=constraints_by_class
        )
    )

    verificator = verification.Verificator(
        symbol_table=symbol_table, constraints_by_class=reorganized_constraints_by_class
    )

    case_generator: generation.CaseGenerator

    if symbol_table.meta_model.version == "V3.1":
        case_generator = v3_1_generation.CaseGenerator(
            instance_generator=v3_1_generation.InstanceGenerator(
                verificator=verificator
            )
        )
    elif symbol_table.meta_model.version == "V3.2":
        case_generator = v3_2_generation.CaseGenerator(
            instance_generator=v3_2_generation.InstanceGenerator(
                verificator=verificator
            )
        )
    else:
        print(
            f"Unhandled meta-model version in {symbol_table.meta_model.version} "
            f"from --model_path: {meta_model_path}. "
            f"The meta-model logic in {os.path.realpath(__file__)} needs to be "
            f"extended to handle this meta-model version.",
            file=stderr,
        )
        return 1

    print("Generating the cases...", file=stdout)

    file_count = 0
    for output in itertools.chain(
        jsoning.generate_test_data(case_generator),
        xmling.generate_test_data(case_generator),
    ):
        path = output_dir / output.relative_path

        path.parent.mkdir(exist_ok=True, parents=True)

        with path.open("wt", encoding="utf-8") as fid:
            fid.write(output.text)
            fid.write("\n")

        file_count += 1

    print(f"Written {file_count} file(s) to {output_dir}.", file=stdout)

    return 0


def main(prog: str) -> int:
    """
    Execute the main routine.

    :param prog: name of the program to be displayed in the help
    :return: exit code
    """
    parser = argparse.ArgumentParser(prog=prog, description=__doc__)
    parser.add_argument(
        "--meta_model_path", help="path to the AAS meta-model", required=True
    )
    parser.add_argument(
        "--output_dir",
        help="path to the directory where test data is stored",
        required=True,
    )
    parser.add_argument(
        "--cache_meta_model",
        action="store_true",
        help=(
            "Cache the parsed meta-model to temporary directory "
            "(dependent on your OS) for faster reuse"
        ),
    )
    parser.add_argument(
        "--version", help="show the current version and exit", action="store_true"
    )

    # NOTE (mristin):
    # The module ``argparse`` is not flexible enough to understand special options such
    # as ``--version`` so we manually hard-wire.
    if "--version" in sys.argv and "--help" not in sys.argv:
        print(aas_core_testdatagen.__version__)
        return 0

    args = parser.parse_args()

    meta_model_path = pathlib.Path(args.meta_model_path)
    output_dir = pathlib.Path(args.output_dir)
    cache_meta_model = bool(args.cache_meta_model)

    return execute(
        meta_model_path=meta_model_path,
        output_dir=output_dir,
        cache_meta_model=cache_meta_model,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


def entry_point() -> int:
    """Provide an entry point for a console script."""
    return main(prog="aas-core-testdatagen")


if __name__ == "__main__":
    sys.exit(main(prog="aas-core-testdatagen"))
