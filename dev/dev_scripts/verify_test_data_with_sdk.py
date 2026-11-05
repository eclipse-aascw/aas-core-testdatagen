# SPDX-FileCopyrightText: 2025 aas-core-testdatagen AUTHORS
#
# SPDX-License-Identifier: MIT

"""
Run a basic verification of the test data using an SDK.

We have a general problem that it is difficult to develop a test data generator due
to a chicken-and-egg problem: your test data generation might be buggy, or your SDK
can be buggy. Usually, you have to develop both the SDK and your test data generation
in parallel. To that end, we provide this script to verify the test data using
an existing SDK.
"""

import argparse
import difflib
import enum
import hashlib
import importlib.util
import inspect
import json
import pathlib
import pickle
import sys
import tempfile
import uuid
from types import ModuleType
from typing import Any, Dict, Optional, Callable, Tuple, List

import aas_core_codegen.naming
import aas_core_codegen.python.naming
import aas_core_codegen.run
from aas_core_codegen import intermediate
from icontract import ensure

from aas_core_testdatagen.common import bullet_points

if sys.version_info >= (3, 11):
    # noinspection PyUnreachableCode
    import tomllib
else:
    # noinspection SpellCheckingInspection
    import tomli as tomllib


class Target(enum.Enum):
    """Enumerate different verification targets."""

    JSON = "json"
    XML = "xml"


class SDK:
    """Represent the modules imported from the sdk."""

    init: ModuleType
    jsonization: ModuleType
    types: ModuleType
    verification: ModuleType
    xmlization: ModuleType

    def __init__(
        self,
        init: ModuleType,
        jsonization: ModuleType,
        types: ModuleType,
        verification: ModuleType,
        xmlization: ModuleType,
    ) -> None:
        self.init = init
        self.jsonization = jsonization
        self.types = types
        self.verification = verification
        self.xmlization = xmlization


@ensure(lambda result: (result[0] is not None) ^ (result[1] is not None))
def _load_meta_model(
    meta_model_path: pathlib.Path,
) -> Tuple[Optional[intermediate.SymbolTable], Optional[str]]:
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
) -> Tuple[Optional[intermediate.SymbolTable], Optional[str]]:
    """
    Use the system temp directory to manage the caching of the symbol table.

    Return the symbol table, or an error, if any.
    """
    symbol_table: Optional[intermediate.SymbolTable] = None

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
            return None, (f"Failed to pickle the meta-model to {tmp_path}: {exception}")
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

        if not isinstance(symbol_table, intermediate.SymbolTable):
            return None, (
                f"Expected a {intermediate.SymbolTable.__qualname__} "
                f"from {cached_symbol_table_path}, "
                f"but got {symbol_table}"
            )

    return symbol_table, None


def _verify_json(
    json_dir: pathlib.Path, sdk: SDK, symbol_table: intermediate.SymbolTable
) -> Optional[str]:
    """Verify that all the JSON test data is correct."""
    model_type_to_from_jsonable: Dict[str, Callable[..., Any]] = dict()

    for concrete_cls in symbol_table.concrete_classes:
        model_type = aas_core_codegen.naming.json_model_type(concrete_cls.name)

        from_jsonable_name = (
            f"{aas_core_codegen.naming.lower_snake_case(concrete_cls.name)}"
            f"_from_jsonable"
        )

        from_jsonable_func = getattr(sdk.jsonization, from_jsonable_name)
        assert inspect.isfunction(from_jsonable_func), (
            f"Expected {from_jsonable_name} to be a function "
            f"in {sdk.jsonization.__file__}, but got {type(from_jsonable_func)}"
        )

        model_type_to_from_jsonable[model_type] = from_jsonable_func

    expected_dir = json_dir / "Expected"

    errors = []  # type: List[str]

    for cls_dir in sorted(path for path in expected_dir.iterdir() if path.is_dir()):
        from_jsonable = model_type_to_from_jsonable.get(cls_dir.name, None)
        if from_jsonable is None:
            errors.append(
                f"{cls_dir}: The from_jsonable function could not be resolved "
                f"for model type {cls_dir.name!r} derived from the path {cls_dir}."
            )
            continue

        for instance_path in sorted(cls_dir.glob("**/*.json")):
            # noinspection PyBroadException
            try:
                jsonable = json.loads(instance_path.read_text(encoding="utf-8"))
            except Exception as exception:
                errors.append(f"{instance_path}: Failed to read JSON: {exception}")
                continue

            try:
                instance = from_jsonable(jsonable)
            except Exception as exception:
                errors.append(
                    f"{instance_path}: Failed to de-serialize instance: {exception}"
                )
                continue

            verification_errors = list(sdk.verification.verify(instance))

            if len(verification_errors) > 0:
                verification_errors_joined = bullet_points(
                    [
                        f"{verification_error.path}: {verification_error.cause}"
                        for verification_error in verification_errors
                    ]
                )

                # NOTE (mristin):
                # We add the first line (':1') to make the output clickable in terminals
                # which match for <file>:<line> pattern.
                errors.append(f"{instance_path}:1:\n{verification_errors_joined}")
                continue

            another_jsonable = sdk.jsonization.to_jsonable(instance)

            jsonable_normalized_str = json.dumps(jsonable, indent=2)
            another_jsonable_normalized_str = json.dumps(another_jsonable, indent=2)

            if jsonable_normalized_str != another_jsonable_normalized_str:
                diff_lines = list(
                    difflib.unified_diff(
                        jsonable_normalized_str.splitlines(keepends=True),
                        another_jsonable_normalized_str.splitlines(keepends=True),
                        fromfile=str(instance_path),
                        tofile=f"round-trip from {instance_path}",
                        lineterm="",
                    )
                )

                diff_str = "".join(diff_lines)
                errors.append(
                    f"{instance_path}:1: diff in JSON round-trip:\n{diff_str}"
                )
                continue

    unserializable_dir = json_dir / "Unexpected" / "Unserializable"
    assert unserializable_dir.is_dir()

    for case_dir in sorted(
        path for path in unserializable_dir.iterdir() if path.is_dir()
    ):
        for cls_dir in sorted(path for path in case_dir.iterdir() if path.is_dir()):
            from_jsonable = model_type_to_from_jsonable.get(cls_dir.name, None)

            if from_jsonable is None:
                errors.append(
                    f"{cls_dir}: The from_jsonable function could not be resolved "
                    f"for model type {cls_dir.name!r} derived from the path {cls_dir}."
                )
                continue

            for instance_path in sorted(cls_dir.glob("**/*.json")):
                # noinspection PyBroadException
                try:
                    jsonable = json.loads(instance_path.read_text(encoding="utf-8"))
                except Exception as exception:
                    errors.append(f"{instance_path}: Failed to read JSON: {exception}")
                    continue

                deserialization_exception: Optional[Exception] = None

                try:
                    _ = from_jsonable(jsonable)
                except Exception as exception:
                    deserialization_exception = exception

                if deserialization_exception is None:
                    errors.append(
                        f"{instance_path}: Expected the JSON de-serialization to fail, "
                        f"but it did not."
                    )
                    continue

    invalid_dir = json_dir / "Unexpected" / "Invalid"
    assert invalid_dir.is_dir()

    for case_dir in sorted(path for path in invalid_dir.iterdir() if path.is_dir()):
        for cls_dir in sorted(path for path in case_dir.iterdir() if path.is_dir()):
            from_jsonable = model_type_to_from_jsonable.get(cls_dir.name, None)

            if from_jsonable is None:
                errors.append(
                    f"{cls_dir}: The from_jsonable function could not be resolved "
                    f"for model type {cls_dir.name!r} derived from the path {cls_dir}."
                )
                continue

            for instance_path in sorted(cls_dir.glob("**/*.json")):
                # noinspection PyBroadException
                try:
                    jsonable = json.loads(instance_path.read_text(encoding="utf-8"))
                except Exception as exception:
                    errors.append(f"{instance_path}: Failed to read JSON: {exception}")
                    continue

                try:
                    instance = from_jsonable(jsonable)
                except Exception as exception:
                    errors.append(
                        f"{instance_path}: Failed to de-serialize instance: {exception}"
                    )
                    continue

                verification_errors = list(sdk.verification.verify(instance))

                if len(verification_errors) == 0:
                    errors.append(
                        f"{instance_path}: Expected the verification to fail, "
                        f"but it did not."
                    )
                    continue

    if len(errors) > 0:
        return "\n".join(errors)

    return None


def _verify_xml(
    xml_dir: pathlib.Path, sdk: SDK, symbol_table: intermediate.SymbolTable
) -> Optional[str]:
    """Verify that all the XML test data is correct."""
    xml_class_name_to_from_file: Dict[str, Callable[..., Any]] = dict()

    for concrete_cls in symbol_table.concrete_classes:
        xml_class_name = aas_core_codegen.naming.xml_class_name(concrete_cls.name)

        from_file_name = (
            f"{aas_core_codegen.naming.lower_snake_case(concrete_cls.name)}"
            f"_from_file"
        )

        from_file_func = getattr(sdk.xmlization, from_file_name)

        assert inspect.isfunction(from_file_func), (
            f"Expected {from_file_func} to be a function "
            f"in {sdk.xmlization.__file__}, but got {type(from_file_func)}"
        )

        xml_class_name_to_from_file[xml_class_name] = from_file_func

    expected_dir = xml_dir / "Expected"

    errors = []  # type: List[str]

    for cls_dir in sorted(path for path in expected_dir.iterdir() if path.is_dir()):
        from_file = xml_class_name_to_from_file.get(cls_dir.name, None)
        if from_file is None:
            errors.append(
                f"{cls_dir}: The from_file function could not be resolved "
                f"for XML class name {cls_dir.name!r} derived from the path {cls_dir}."
            )
            continue

        for instance_path in sorted(cls_dir.glob("**/*.xml")):
            # noinspection PyBroadException
            try:
                instance = from_file(instance_path)
            except Exception as exception:
                errors.append(
                    f"{instance_path}: Failed to de-serialize XML: {exception}"
                )
                continue

            verification_errors = list(sdk.verification.verify(instance))

            if len(verification_errors) > 0:
                verification_errors_joined = bullet_points(
                    [
                        f"{verification_error.path}: {verification_error.cause}"
                        for verification_error in verification_errors
                    ]
                )

                # NOTE (mristin):
                # We add the first line (':1') to make the output clickable in terminals
                # which match for <file>:<line> pattern.
                errors.append(f"{instance_path}:1:\n{verification_errors_joined}")
                continue

    unserializable_dir = xml_dir / "Unexpected" / "Unserializable"
    assert unserializable_dir.is_dir()

    for case_dir in sorted(
        path for path in unserializable_dir.iterdir() if path.is_dir()
    ):
        for cls_dir in sorted(path for path in case_dir.iterdir() if path.is_dir()):
            from_file = xml_class_name_to_from_file.get(cls_dir.name, None)

            if from_file is None:
                errors.append(
                    f"{cls_dir}: The from_file function could not be resolved "
                    f"for model type {cls_dir.name!r} derived from the path {cls_dir}."
                )
                continue

            for instance_path in sorted(cls_dir.glob("**/*.xml")):
                # noinspection PyBroadException
                deserialization_exception: Optional[Exception] = None

                try:
                    _ = from_file(instance_path)
                except Exception as exception:
                    deserialization_exception = exception

                if deserialization_exception is None:
                    errors.append(
                        f"{instance_path}: Expected the XML de-serialization to fail, "
                        f"but it did not."
                    )
                    continue

    invalid_dir = xml_dir / "Unexpected" / "Invalid"
    assert invalid_dir.is_dir()

    for case_dir in sorted(path for path in invalid_dir.iterdir() if path.is_dir()):
        for cls_dir in sorted(path for path in case_dir.iterdir() if path.is_dir()):
            from_file = xml_class_name_to_from_file.get(cls_dir.name, None)

            if from_file is None:
                errors.append(
                    f"{cls_dir}: The from_file function could not be resolved "
                    f"for model type {cls_dir.name!r} derived from the path {cls_dir}."
                )
                continue

            for instance_path in sorted(cls_dir.glob("**/*.xml")):
                # noinspection PyBroadException
                try:
                    instance = from_file(instance_path)
                except Exception as exception:
                    errors.append(
                        f"{instance_path}: Failed to de-serialize instance: {exception}"
                    )
                    continue

                verification_errors = list(sdk.verification.verify(instance))

                if len(verification_errors) == 0:
                    errors.append(
                        f"{instance_path}: Expected the verification to fail, "
                        f"but it did not."
                    )
                    continue

    if len(errors) > 0:
        return "\n".join(errors)

    return None


def main() -> int:
    """Execute the main routine."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sdk_path",
        help="Path to aas-core Python SDK that you want to use",
        required=True,
    )
    parser.add_argument(
        "--test_data_dir",
        help="Path to the test data directory containing JSON and XML cases",
        required=True,
    )
    parser.add_argument(
        "--meta_model_path",
        help=(
            "Path to the meta-model. If omitted, "
            "<sdk_path>/dev/dev_scripts/codegen/meta_model.py will be read."
        ),
    )
    parser.add_argument(
        "--select",
        help=(
            "If set, only the selected targets are verified. "
            "This is practical if you want to test only specific formats. "
            "The targets are given as a space-separated list of: "
            + " ".join(value.value for value in Target)
        ),
        metavar="",
        nargs="+",
        choices=[value.value for value in Target],
    )
    parser.add_argument(
        "--skip",
        help=(
            "If set, skips the specified targets. "
            "This is practical if you want to exclude specific formats. "
            "The targets are given as a space-separated list of: "
            + " ".join(value.value for value in Target)
        ),
        metavar="",
        nargs="+",
        choices=[value.value for value in Target],
    )
    parser.add_argument(
        "--cache_meta_model",
        action="store_true",
        help=(
            "Cache the parsed meta-model to temporary directory "
            "(dependent on your OS) for faster reuse"
        ),
    )
    args = parser.parse_args()

    selects = (
        [Target(value) for value in args.select]
        if args.select is not None
        else [value for value in Target]  # pylint: disable=unnecessary-comprehension
    )
    skips = [Target(value) for value in args.skip] if args.skip is not None else []

    sdk_path = pathlib.Path(args.sdk_path)
    meta_model_path = (
        pathlib.Path(args.meta_model_path)
        if args.meta_model_path is not None
        else sdk_path / "dev" / "dev_scripts" / "codegen" / "meta_model.py"
    )
    test_data_dir = pathlib.Path(args.test_data_dir)
    cache_meta_model = bool(args.cache_meta_model)

    if not sdk_path.exists():
        print(f"--sdk_path does not exist: {sdk_path}", file=sys.stderr)
        return 1

    if not sdk_path.is_dir():
        print(f"--sdk_path is not a directory: {sdk_path}", file=sys.stderr)
        return 1

    pyproject_path = sdk_path / "pyproject.toml"
    if not pyproject_path.exists():
        print(
            f"pyproject.toml not found in --sdk_path: {pyproject_path}", file=sys.stderr
        )
        return 1

    try:
        with open(pyproject_path, "rb") as fid:
            pyproject_data = tomllib.load(fid)
    except Exception as exception:
        print(f"Failed to read {pyproject_path}: {exception}", file=sys.stderr)
        return 1

    try:
        packages = pyproject_data["tool"]["setuptools"]["packages"]["find"]["include"]
        main_package = packages[0].rstrip("*")
    except KeyError as exception:
        print(
            f"Could not find main package in {pyproject_path}: {exception}",
            file=sys.stderr,
        )
        return 1

    print(f"Importing the SDK from {sdk_path} ...")
    sys.path.insert(0, str(sdk_path))

    try:
        sdk_init = importlib.import_module(f"{main_package}")
        sdk_jsonization = importlib.import_module(f"{main_package}.jsonization")
        sdk_types = importlib.import_module(f"{main_package}.types")
        sdk_verification = importlib.import_module(f"{main_package}.verification")
        sdk_xmlization = importlib.import_module(f"{main_package}.xmlization")
    except ImportError as exception:
        print(f"Failed to import SDK modules: {exception}", file=sys.stderr)
        return 1

    sdk = SDK(
        init=sdk_init,
        jsonization=sdk_jsonization,
        types=sdk_types,
        verification=sdk_verification,
        xmlization=sdk_xmlization,
    )

    print(
        f"Imported SDK: {sdk_init.__name__} {sdk_init.__version__} "
        f"from {sdk_path}, main package {main_package}"
    )

    if not meta_model_path.exists():
        print(f"Meta-model path does not exist: {meta_model_path}", file=sys.stderr)
        return 1

    if not meta_model_path.is_file():
        print(f"Meta-model path is not to a file: {meta_model_path}", file=sys.stderr)
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

    if not test_data_dir.exists():
        print(f"--test_data_dir does not exist: {test_data_dir}", file=sys.stderr)
        return 1

    if not test_data_dir.is_dir():
        print(f"--test_data_dir is not a directory: {test_data_dir}", file=sys.stderr)
        return 1

    one_or_more_tests_failed = False

    if Target.JSON in selects and Target.JSON not in skips:
        json_dir = test_data_dir / "Json"
        if not json_dir.exists():
            print(
                f"JSON subdirectory in --test_data_dir does not exist: {json_dir}",
                file=sys.stderr,
            )
            return 1

        print(f"Verifying JSON test data in {json_dir} ...")
        maybe_error = _verify_json(
            json_dir=json_dir,
            sdk=sdk,
            symbol_table=symbol_table,
        )

        # NOTE (mristin):
        # We explicitly output to STDOUT so that the user can use head/tail commands
        # on it.
        if maybe_error is not None:
            print(f"Failed to verify JSON test data:\n{maybe_error}", file=sys.stdout)
            one_or_more_tests_failed = True

    if Target.XML in selects and Target.XML not in skips:
        xml_dir = test_data_dir / "Xml"
        if not xml_dir.exists():
            print(
                f"XML subdirectory in --test_data_dir does not exist: {xml_dir}",
                file=sys.stdout,
            )
            return 1

        print(f"Verifying XML test data in {xml_dir} ...")
        maybe_error = _verify_xml(
            xml_dir=xml_dir,
            sdk=sdk,
            symbol_table=symbol_table,
        )

        # NOTE (mristin):
        # We explicitly output to STDOUT so that the user can use head/tail commands
        # on it.
        if maybe_error is not None:
            print(f"Failed to verify XML test data:\n{maybe_error}", file=sys.stdout)
            one_or_more_tests_failed = True

    if one_or_more_tests_failed:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
