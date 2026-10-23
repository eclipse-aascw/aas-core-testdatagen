# pylint: disable=missing-docstring

import collections.abc
import contextlib
import difflib
import hashlib
import itertools
import json
import pathlib
import pickle
import tempfile
import unittest
import uuid
from typing import Set, ClassVar, Optional, Tuple

import aas_core_codegen.infer_for_schema
import aas_core_codegen.run
from aas_core_codegen import intermediate
from aas_core_codegen.common import Identifier

from aas_core_testdatagen import (
    verification,
    jsoning,
    common,
    generation,
    xmling,
    preseria,
)
from aas_core_testdatagen.common import bullet_points
from aas_core_testdatagen.v3_1 import generation as v3_1_generation
from aas_core_testdatagen.v3_2 import generation as v3_2_generation

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def _load_or_cache_meta_model(
    meta_model_path: pathlib.Path,
) -> Tuple[
    intermediate.SymbolTable,
    verification.ReorganizedConstraintsByClass,
    verification.Verificator,
]:
    """Use the system temp directory to manage the caching of the symbol table."""
    symbol_table: Optional[intermediate.SymbolTable] = None

    hasher = hashlib.sha256()
    hasher.update(meta_model_path.read_bytes())
    meta_model_hash_hexdigest = hasher.hexdigest()

    cached_symbol_table_path = (
        pathlib.Path(tempfile.gettempdir())
        / "aas-core-testdatagen-test-main"
        / f"symbol_table-{meta_model_hash_hexdigest}.pickle"
    )

    if not cached_symbol_table_path.exists():
        # NOTE (mristin):
        # We include the hash of the content in the file name, so the parsed symbol
        # table will correspond to the source.

        symbol_table_atok, error = aas_core_codegen.run.load_model(meta_model_path)
        if error is not None:
            raise AssertionError(
                f"The meta-model {meta_model_path} could not be parsed: {error}"
            )

        assert symbol_table_atok is not None
        symbol_table, _ = symbol_table_atok

        cached_symbol_table_path.parent.mkdir(exist_ok=True, parents=True)

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
        finally:
            tmp_path.unlink(missing_ok=True)

    else:
        with cached_symbol_table_path.open("rb") as fid:
            symbol_table = pickle.load(fid)

            if not isinstance(symbol_table, intermediate.SymbolTable):
                raise RuntimeError(
                    f"Expected a {intermediate.SymbolTable.__qualname__} "
                    f"from {cached_symbol_table_path}, "
                    f"but got {symbol_table}"
                )

    constraints_by_class, inference_errors = (
        aas_core_codegen.infer_for_schema.infer_constraints_by_class(
            symbol_table=symbol_table
        )
    )
    if inference_errors is not None:
        errors_str = bullet_points(map(repr, inference_errors))
        raise AssertionError(
            f"Failed to infer the schema constraints "
            f"from the meta-model {meta_model_path}:\n{errors_str}"
        )

    assert constraints_by_class is not None
    reorganized_constraints_by_class = (
        verification.reorganize_schema_constraints_by_properties(
            constraints_by_class=constraints_by_class
        )
    )

    verificator = verification.Verificator(
        symbol_table=symbol_table, constraints_by_class=reorganized_constraints_by_class
    )

    return symbol_table, reorganized_constraints_by_class, verificator


# noinspection PyPep8Naming
class TestIndividualCasesFor3_1(unittest.TestCase):
    _instance_generator: ClassVar[Optional[v3_1_generation.InstanceGenerator]]

    @property
    def instance_generator(self) -> v3_1_generation.InstanceGenerator:
        """Instance generator initialized for this version."""
        assert self.__class__._instance_generator is not None, (
            "Expected the instance generator to be created in setUpClass, "
            "but either the setUpClass was not called yet "
            "or setUpClass did not initialize the instance generator"
        )

        return self.__class__._instance_generator

    @classmethod
    def setUpClass(cls) -> None:
        _, _, verificator = _load_or_cache_meta_model(
            meta_model_path=(
                _REPO_ROOT / "dev" / "test_data" / "meta_model" / "v3_1.py"
            )
        )

        TestIndividualCasesFor3_1._instance_generator = (
            v3_1_generation.InstanceGenerator(verificator=verificator)
        )

    def test_list_maximal_no_duplicate_qualifiers(self) -> None:
        instance = self.instance_generator.generate_maximal_instance(
            path_hash=common.hash_path(prefix_hash=None, segment_or_segments=[]),
            cls=self.instance_generator.symbol_table.must_find_concrete_class(
                Identifier("Submodel_element_list")
            ),
        )

        jsonable = jsoning.must_serialize(
            value=instance,
            symbol_table=self.instance_generator.symbol_table,
        )

        assert isinstance(jsonable, collections.abc.Mapping)

        # NOTE (mristin):
        # We had a problem that a list of qualifiers results in qualifiers with
        # duplicate types.

        qualifier_types = [qualifier["type"] for qualifier in jsonable["qualifiers"]]

        assert len(set(qualifier_types)) == len(qualifier_types), (
            f"Expected unique qualifier types, but got duplicates "
            f"in:\n{json.dumps(jsonable['qualifiers'], indent=2)}"
        )

    def test_referable_display_name_valid(self) -> None:
        instance = self.instance_generator.generate_maximal_instance(
            path_hash=common.hash_path(prefix_hash=None, segment_or_segments=[]),
            cls=self.instance_generator.symbol_table.must_find_abstract_class(
                Identifier("Referable")
            ),
        )

        assert "display_name" in instance.properties

        display_name = instance.properties[Identifier("display_name")]

        assert isinstance(display_name, preseria.ListOfInstances)

        assert all(
            lang_string.must_str("language").startswith("en-")
            for lang_string in display_name.values
        ), (
            "All language strings in display name should be valid "
            "English language BCP 47 tags."
        )

    def test_no_pattern_cases_for_property_value(self) -> None:
        # NOTE (mristin):
        # The implementation of the case generator for patterns was buggy, so we wrote
        # this test to speed up the development. We leave the test here for future
        # regressions.

        instance_generator = self.instance_generator

        case_generator = generation.CaseGeneratorForSchemaConstraints(
            instance_generator=instance_generator,
            min_max_case_registry=generation.build_min_max_case_registry(
                instance_generator=instance_generator
            ),
        )

        pattern_cases = list(
            case_generator._generate_positive_and_negative_pattern_examples(
                cls=instance_generator.symbol_table.must_find_concrete_class(
                    Identifier("Property")
                )
            )
        )

        for pattern_case in pattern_cases:
            self.assertNotEqual(pattern_case.property_name, Identifier("value"))


# noinspection PyPep8Naming
class TestIndividualCasesFor3_2(unittest.TestCase):
    _instance_generator: ClassVar[Optional[v3_2_generation.InstanceGenerator]]

    @property
    def instance_generator(self) -> v3_2_generation.InstanceGenerator:
        """Instance generator initialized for this version."""
        assert self.__class__._instance_generator is not None, (
            "Expected the instance generator to be created in setUpClass, "
            "but either the setUpClass was not called yet "
            "or setUpClass did not initialize the instance generator"
        )

        return self.__class__._instance_generator

    @classmethod
    def setUpClass(cls) -> None:
        _, _, verificator = _load_or_cache_meta_model(
            meta_model_path=(
                _REPO_ROOT / "dev" / "test_data" / "meta_model" / "v3_2.py"
            )
        )

        TestIndividualCasesFor3_2._instance_generator = (
            v3_2_generation.InstanceGenerator(verificator=verificator)
        )

    def test_list_maximal_no_duplicate_qualifiers(self) -> None:
        instance = self.instance_generator.generate_maximal_instance(
            path_hash=common.hash_path(prefix_hash=None, segment_or_segments=[]),
            cls=self.instance_generator.symbol_table.must_find_concrete_class(
                Identifier("Submodel_element_list")
            ),
        )

        jsonable = jsoning.must_serialize(
            value=instance,
            symbol_table=self.instance_generator.symbol_table,
        )

        assert isinstance(jsonable, collections.abc.Mapping)

        # NOTE (mristin):
        # We had a problem that a list of qualifiers results in qualifiers with
        # duplicate types.

        qualifier_types = [qualifier["type"] for qualifier in jsonable["qualifiers"]]

        assert len(set(qualifier_types)) == len(qualifier_types), (
            f"Expected unique qualifier types, but got duplicates "
            f"in:\n{json.dumps(jsonable['qualifiers'], indent=2)}"
        )

    def test_referable_display_name_valid(self) -> None:
        instance = self.instance_generator.generate_maximal_instance(
            path_hash=common.hash_path(prefix_hash=None, segment_or_segments=[]),
            cls=self.instance_generator.symbol_table.must_find_abstract_class(
                Identifier("Referable")
            ),
        )

        assert "display_name" in instance.properties

        display_name = instance.properties[Identifier("display_name")]

        assert isinstance(display_name, preseria.ListOfInstances)

        assert all(
            lang_string.must_str("language").startswith("en-")
            for lang_string in display_name.values
        ), (
            "All language strings in display name should be valid "
            "English language BCP 47 tags."
        )

    def test_no_pattern_cases_for_property_value(self) -> None:
        # NOTE (mristin):
        # The implementation of the case generator for patterns was buggy, so we wrote
        # this test to speed up the development. We leave the test here for future
        # regressions.

        instance_generator = self.instance_generator

        case_generator = generation.CaseGeneratorForSchemaConstraints(
            instance_generator=instance_generator,
            min_max_case_registry=generation.build_min_max_case_registry(
                instance_generator=instance_generator
            ),
        )

        pattern_cases = list(
            case_generator._generate_positive_and_negative_pattern_examples(
                cls=instance_generator.symbol_table.must_find_concrete_class(
                    Identifier("Property")
                )
            )
        )

        for pattern_case in pattern_cases:
            self.assertNotEqual(pattern_case.property_name, Identifier("value"))


class TestAgainstRecorded(unittest.TestCase):
    def test_against_meta_models(self) -> None:
        test_data_dir = _REPO_ROOT / "dev" / "test_data"

        for meta_model_path in sorted((test_data_dir / "meta_model").glob("v*.py")):
            golden_dir = test_data_dir / "test_generation" / meta_model_path.stem

            if not golden_dir.exists():
                raise FileNotFoundError(
                    f"The directory with golden files does not exist: {golden_dir}"
                )

            if not golden_dir.is_dir():
                raise NotADirectoryError(
                    f"The path to golden files is not a directory: {golden_dir}"
                )

            symbol_table, _, verificator = _load_or_cache_meta_model(
                meta_model_path=meta_model_path
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
                raise NotImplementedError(
                    f"Unhandled meta-model version from {meta_model_path}: "
                    f"{symbol_table.meta_model.version}",
                )

            with contextlib.ExitStack() as exit_stack:
                # pylint: disable=consider-using-with
                temporary_directory = tempfile.TemporaryDirectory()
                exit_stack.push(temporary_directory)

                output_dir = pathlib.Path(temporary_directory.name)

                for output in itertools.chain(
                    jsoning.generate_test_data(case_generator),
                    xmling.generate_test_data(case_generator),
                ):
                    path = output_dir / output.relative_path

                    path.parent.mkdir(exist_ok=True, parents=True)

                    with path.open("wt", encoding="utf-8") as fid:
                        fid.write(output.text)
                        fid.write("\n")

                output_file_set = set()  # type: Set[pathlib.Path]
                golden_file_set = set()  # type: Set[pathlib.Path]

                for output_file in output_dir.rglob("*"):
                    if output_file.is_file():
                        output_file_set.add(output_file.relative_to(output_dir))

                for golden_file in golden_dir.rglob("*"):
                    if golden_file.is_file():
                        golden_file_set.add(golden_file.relative_to(golden_dir))

                missing_in_output = golden_file_set - output_file_set
                missing_in_golden = output_file_set - golden_file_set

                if len(missing_in_output) > 0:
                    missing_in_output_joined = "\n".join(
                        str(path) for path in sorted(missing_in_output)
                    )
                    raise AssertionError(
                        f"One or more files missing in the generated output "
                        f"related to the meta-model {meta_model_path}:\n"
                        f"{missing_in_output_joined}"
                    )

                if len(missing_in_golden) > 0:
                    missing_in_golden_joined = "\n".join(
                        str(path) for path in sorted(missing_in_golden)
                    )
                    raise AssertionError(
                        f"Unexpected one or more additional files in generated output:\n"
                        f"{missing_in_golden_joined}"
                    )

                for rel_path in sorted(output_file_set):
                    output_file = output_dir / rel_path
                    golden_file = golden_dir / rel_path

                    with open(output_file, "r", encoding="utf-8") as f:
                        output_content = f.readlines()

                    with open(golden_file, "r", encoding="utf-8") as f:
                        golden_content = f.readlines()

                    if output_content != golden_content:
                        diff = difflib.unified_diff(
                            golden_content,
                            output_content,
                            fromfile="golden",
                            tofile="generated",
                            lineterm="",
                        )
                        diff_text = "\n".join(diff)
                        raise AssertionError(
                            f"Unexpected content mismatch for file {rel_path}:\n"
                            f"{diff_text}"
                        )


if __name__ == "__main__":
    unittest.main()
