"""Generate the test data assuming the logic based on pillars of the meta-model V3.2."""

import collections
from typing import Final, Iterator, Optional, Sequence, Callable

from aas_core_codegen import intermediate
from aas_core_codegen.common import Identifier
from typing_extensions import override

from aas_core_testdatagen import (
    generation,
    verification,
    casing,
    preseria,
    common,
    primitiving,
)


class InstanceGenerator(generation.InstanceGenerator):
    """Generate instances specific for the meta-model V3.2."""

    # NOTE (mristin):
    # So far, we have not found any constraints which we had to
    # account for in V3.2.


class CaseGenerator(generation.CaseGenerator):
    """Generate the test cases specific for the meta-model V3.2."""

    instance_generator: Final[InstanceGenerator]

    @override
    @property
    def symbol_table(self) -> intermediate.SymbolTable:
        """Give the symbol table of the meta-model."""
        return self.instance_generator.symbol_table

    @property
    def verificator(self) -> verification.Verificator:
        """Verificator of the meta-model."""
        return self.instance_generator.verificator

    def __init__(self, instance_generator: InstanceGenerator) -> None:
        self.instance_generator = instance_generator

        min_max_case_registry = generation.build_min_max_case_registry(
            instance_generator
        )

        self._sub_generators = [
            generation.CaseGeneratorForSchemaConstraints(
                instance_generator=instance_generator,
                min_max_case_registry=min_max_case_registry,
            ),
            generation.CaseGeneratorForStableSemantics(
                instance_generator=instance_generator,
                min_max_case_registry=min_max_case_registry,
            ),
        ]

    def _generate_list_id_short_in_value(self) -> Iterator[casing.CasePositiveManual]:
        item = preseria.Instance(
            class_name=Identifier("Property"),
            properties=collections.OrderedDict(
                [
                    (Identifier("ID_short"), "something"),
                    (Identifier("value_type"), "xs:boolean"),
                ]
            ),
        )

        instance = preseria.Instance(
            class_name=Identifier("Submodel_element_list"),
            properties=collections.OrderedDict(
                [
                    (Identifier("value_type_list_element"), "xs:boolean"),
                    (Identifier("type_value_list_element"), "Property"),
                    (Identifier("ID_short"), "someList"),
                    (Identifier("value"), preseria.ListOfInstances(values=[item])),
                ]
            ),
        )

        yield casing.CasePositiveManual(
            instance=self.verificator.must(instance),
            name=generation.test_name_from_function_name(),
        )

    def _asset_information_with_specific_asset_id(
        self,
        specific_asset_id_name: str,
        specific_asset_id_value: str,
        global_asset_id: Optional[str],
    ) -> preseria.Instance:
        """Generate an asset information with a single specific asset ID."""
        path_hash = common.hash_path(
            None, ["asset_information", specific_asset_id_name]
        )

        instance = self.instance_generator.generate_minimal_concrete_instance(
            path_hash=path_hash,
            cls=self.symbol_table.must_find_concrete_class(
                Identifier("Asset_information")
            ),
        )

        if global_asset_id is not None:
            instance.properties[Identifier("global_asset_ID")] = global_asset_id

        specific_asset_id = self.instance_generator.generate_minimal_concrete_instance(
            path_hash=common.hash_path(path_hash, ["specific_asset_IDs", 0]),
            cls=self.symbol_table.must_find_concrete_class(
                Identifier("Specific_asset_ID")
            ),
        )
        specific_asset_id.properties[Identifier("name")] = specific_asset_id_name
        specific_asset_id.properties[Identifier("value")] = specific_asset_id_value

        instance.properties[Identifier("specific_asset_IDs")] = (
            preseria.ListOfInstances(values=[specific_asset_id])
        )

        return instance

    def _generate_global_asset_id_name_with_matching_value(
        self,
    ) -> Iterator[casing.CasePositiveManual]:
        yield casing.CasePositiveManual(
            instance=self.verificator.must(
                self._asset_information_with_specific_asset_id(
                    "globalAssetId", "urn:global:asset", "urn:global:asset"
                )
            ),
            name=generation.test_name_from_function_name(),
        )

    def _generate_global_asset_id_name_in_other_case_with_matching_value(
        self,
    ) -> Iterator[casing.CasePositiveManual]:
        yield casing.CasePositiveManual(
            instance=self.verificator.must(
                self._asset_information_with_specific_asset_id(
                    "GLOBALassetID", "urn:global:asset", "urn:global:asset"
                )
            ),
            name=generation.test_name_from_function_name(),
        )

    def _generate_similar_name_with_different_value(
        self,
    ) -> Iterator[casing.CasePositiveManual]:
        # The name only resembles the reserved key, so the value may differ.
        yield casing.CasePositiveManual(
            instance=self.verificator.must(
                self._asset_information_with_specific_asset_id(
                    "globalAssetIds", "urn:other", "urn:global:asset"
                )
            ),
            name=generation.test_name_from_function_name(),
        )

    def _generate_global_asset_id_name_with_different_value(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        yield casing.CaseConstraintViolation(
            instance=self._asset_information_with_specific_asset_id(
                "globalAssetId", "urn:other", "urn:global:asset"
            ),
            name=generation.test_name_from_function_name(),
        )

    def _generate_global_asset_id_name_in_other_case_with_different_value(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        yield casing.CaseConstraintViolation(
            instance=self._asset_information_with_specific_asset_id(
                "GlobalAssetId", "urn:other", "urn:global:asset"
            ),
            name=generation.test_name_from_function_name(),
        )

    def _generate_global_asset_id_name_without_global_asset_id(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        yield casing.CaseConstraintViolation(
            instance=self._asset_information_with_specific_asset_id(
                "globalAssetId", "urn:other", None
            ),
            name=generation.test_name_from_function_name(),
        )

    def _external_reference_with_middle_key(
        self, middle_key_type: str
    ) -> preseria.Instance:
        """Generate an external reference with three keys and the given middle key."""
        path_hash = common.hash_path(None, ["external_reference", middle_key_type])

        instance = self.instance_generator.generate_minimal_concrete_instance(
            path_hash=path_hash,
            cls=self.symbol_table.must_find_concrete_class(Identifier("Reference")),
        )

        instance.properties[Identifier("type")] = (
            self.symbol_table.must_find_enumeration(Identifier("Reference_types"))
            .literals_by_name[Identifier("External_reference")]
            .value
        )

        create_key = self.instance_generator.create_key
        instance.properties[Identifier("keys")] = preseria.ListOfInstances(
            [
                create_key(Identifier("Global_reference"), "urn:first"),
                create_key(Identifier(middle_key_type), "urn:middle"),
                create_key(Identifier("Global_reference"), "urn:last"),
            ]
        )

        return instance

    def _generate_external_reference_with_fragment_key(
        self,
    ) -> Iterator[casing.CasePositiveManual]:
        yield casing.CasePositiveManual(
            instance=self.verificator.must(
                self._external_reference_with_middle_key("Fragment_reference")
            ),
            name=generation.test_name_from_function_name(),
        )

    def _generate_external_reference_with_submodel_key(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        yield casing.CaseConstraintViolation(
            instance=self._external_reference_with_middle_key("Submodel"),
            name=generation.test_name_from_function_name(),
        )

    def _generate_external_reference_with_property_key(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        yield casing.CaseConstraintViolation(
            instance=self._external_reference_with_middle_key("Property"),
            name=generation.test_name_from_function_name(),
        )

    def _operation_with_list_in_input_variable(
        self, number_of_elements: int
    ) -> preseria.Instance:
        """Generate an operation with a list of the given length as input variable."""
        path_hash = common.hash_path(None, ["operation", number_of_elements])

        instance = self.instance_generator.generate_maximal_concrete_instance(
            path_hash=path_hash,
            cls=self.symbol_table.must_find_concrete_class(Identifier("Operation")),
        )

        input_variables = instance.properties[Identifier("input_variables")]
        assert isinstance(input_variables, preseria.ListOfInstances)
        assert len(input_variables.values) > 0

        element = generation.mutable_list_with_two_boolean_properties(
            instance_generator=self.instance_generator
        )
        element.properties[Identifier("ID_short")] = primitiving.generate_id_short(
            common.hash_path(path_hash, ["input_variables", 0, "value", "ID_short"])
        )

        if number_of_elements == 0:
            del element.properties[Identifier("value")]
        else:
            value = element.properties[Identifier("value")]
            assert isinstance(value, preseria.ListOfInstances)
            assert number_of_elements <= len(value.values)
            del value.values[number_of_elements:]

        input_variables.values[0].properties[Identifier("value")] = element

        return instance

    def _generate_operation_variable_list_with_two_elements(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        yield casing.CaseConstraintViolation(
            instance=self._operation_with_list_in_input_variable(2),
            name=generation.test_name_from_function_name(),
        )

    def _generate_operation_variable_list_without_elements(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        yield casing.CaseConstraintViolation(
            instance=self._operation_with_list_in_input_variable(0),
            name=generation.test_name_from_function_name(),
        )

    def generate(self) -> Iterator[casing.CaseUnion]:
        """Generate the cases."""
        for sub_generator in self._sub_generators:
            yield from sub_generator.generate()

        bound_generate_methods: Sequence[Callable[[], Iterator[casing.CaseUnion]]] = [
            self._generate_list_id_short_in_value,
            self._generate_global_asset_id_name_with_matching_value,
            self._generate_global_asset_id_name_in_other_case_with_matching_value,
            self._generate_similar_name_with_different_value,
            self._generate_global_asset_id_name_with_different_value,
            self._generate_global_asset_id_name_in_other_case_with_different_value,
            self._generate_global_asset_id_name_without_global_asset_id,
            self._generate_external_reference_with_fragment_key,
            self._generate_external_reference_with_submodel_key,
            self._generate_external_reference_with_property_key,
            self._generate_operation_variable_list_with_two_elements,
            self._generate_operation_variable_list_without_elements,
        ]

        for bound_generate_method in bound_generate_methods:
            try:
                yield from bound_generate_method()
            except Exception as exception:
                what = generation.human_readable_generate_phrase_from_function_name(
                    bound_generate_method.__name__
                )
                raise AssertionError(f"Failed to {what}") from exception


generation.assert_all_generate_methods_listed_in_generate_bound_generate_methods(
    cls=CaseGenerator
)
