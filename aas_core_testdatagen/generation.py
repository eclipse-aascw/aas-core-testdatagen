"""Generate the pre-serialized representation of the test data."""

import abc
import ast
import collections
import inspect
from typing import (
    ClassVar,
    Final,
    Optional,
    Sequence,
    Mapping,
    MutableMapping,
    List,
    Iterator,
    Union,
    Callable,
    Set,
    cast,
    Type,
    OrderedDict,
)

from aas_core_codegen import intermediate
from aas_core_codegen.common import assert_never, Identifier
from icontract import require, ensure
from typing_extensions import override

from aas_core_testdatagen import preseria, common, primitiving, casing, verification
from aas_core_testdatagen.common import Filenameable
from aas_core_testdatagen.frozen_examples import (
    xs_value as frozen_examples_xs_value,
    pattern as frozen_examples_pattern,
)


_NO_CONSTRAINTS: Final = verification.PropertyConstraints(
    len_constraint=None, patterns=[], allowed_values=None
)


class InstanceGenerator(abc.ABC):
    """Define the generation of instances of classes for the given meta-model."""

    verificator: Final[verification.Verificator]

    # NOTE:
    # Since V3.2 (AASd-138), a submodel element list in an operation variable must
    # have exactly one element. This is the default; meta-models before V3.2
    # override the flag.
    single_element_lists_in_operation_variables: ClassVar[bool] = True

    # NOTE (mristin):
    # We introduce the shortcuts to the symbol table and schema constraints to stress
    # the independence of generation from the verificator.

    @property
    def symbol_table(self) -> intermediate.SymbolTable:
        """Symbol table of the meta-model"""
        return self.verificator.symbol_table

    @property
    def constraints_by_class(self) -> verification.ReorganizedConstraintsByClass:
        """Constraints of classes grouped by properties"""
        return self.verificator.constraints_by_class

    def __init__(self, verificator: verification.Verificator) -> None:
        self.verificator = verificator

    def generate_value(
        self,
        path_hash: common.CanHash,
        type_annotation: intermediate.TypeAnnotationExceptOptional,
        constraints: verification.PropertyConstraints,
    ) -> preseria.ValueUnion:
        """Sample the value following its schema constraints, if any."""
        primitive_type = intermediate.try_primitive_type(type_annotation)

        if primitive_type is not None:
            return primitiving.generate_primitive_value_with_constraints(
                path_hash=path_hash,
                primitive_type=primitive_type,
                len_constraint=constraints.len_constraint,
                patterns=constraints.patterns,
                allowed_values=constraints.allowed_values,
            )

        if isinstance(type_annotation, intermediate.PrimitiveTypeAnnotation):
            raise AssertionError("Expected this case to be handled before")

        elif isinstance(type_annotation, intermediate.OurTypeAnnotation):
            our_type = type_annotation.our_type

            if isinstance(our_type, intermediate.Enumeration):
                return primitiving.choose_value(
                    path_hash=path_hash, choice=our_type.literals
                ).value

            elif isinstance(our_type, intermediate.ConstrainedPrimitive):
                raise AssertionError("Expected this case to be handled before")

            elif isinstance(
                our_type, (intermediate.AbstractClass, intermediate.ConcreteClass)
            ):
                return self.generate_minimal_instance(path_hash=path_hash, cls=our_type)

            elif isinstance(our_type, intermediate.NamedUnion):
                return self.generate_minimal_concrete_instance(
                    path_hash=path_hash,
                    cls=primitiving.choose_value(
                        path_hash=path_hash, choice=our_type.implementers
                    ),
                )

            else:
                # noinspection PyTypeChecker
                assert_never(type_annotation.our_type)

        elif isinstance(type_annotation, intermediate.ListTypeAnnotation):
            assert isinstance(
                type_annotation.items, intermediate.OurTypeAnnotation
            ) and isinstance(
                type_annotation.items.our_type,
                (intermediate.AbstractClass, intermediate.ConcreteClass),
            ), (
                "We handle at the moment only lists of class instances, but you "
                f"want to sample from {type_annotation}. Please contact "
                "the developers if you need this feature."
            )

            # NOTE (mristin):
            # The AAS meta-model mandates at least one item in a list.
            minimum_len = 1

            # NOTE (mristin):
            # We do not generate arbitrarily long lists for efficiency reasons,
            # unless the min. length constraint mandates so.
            maximum_len = 3

            if constraints.len_constraint is not None:
                if (
                    constraints.len_constraint.min_value is not None
                    and constraints.len_constraint.min_value > 1
                ):
                    minimum_len = constraints.len_constraint.min_value

                maximum_len = max(maximum_len, minimum_len)

                if (
                    constraints.len_constraint.max_value is not None
                    and maximum_len > constraints.len_constraint.max_value
                ):
                    maximum_len = constraints.len_constraint.max_value

            length = primitiving.generate_int_in_range(
                path_hash=path_hash, minimum=minimum_len, maximum=maximum_len
            )

            values = []  # type: List[preseria.Instance]
            for i in range(length):
                values.append(
                    self.generate_minimal_instance(
                        path_hash=common.hash_path(
                            prefix_hash=path_hash, segment_or_segments=i
                        ),
                        cls=type_annotation.items.our_type,
                    )
                )

            return preseria.ListOfInstances(values)

        elif isinstance(type_annotation, intermediate.TupleTypeAnnotation):
            return preseria.TupleOfValues(
                [
                    self.generate_value(
                        path_hash=common.hash_path(
                            prefix_hash=path_hash, segment_or_segments=i
                        ),
                        type_annotation=intermediate.beneath_optional(item_annotation),
                        constraints=_NO_CONSTRAINTS,
                    )
                    for i, item_annotation in enumerate(type_annotation.items)
                ]
            )

        elif isinstance(type_annotation, intermediate.SetTypeAnnotation):
            item_annotation = intermediate.beneath_optional(type_annotation.items)

            minimum_len = 1
            maximum_len = 3

            if constraints.len_constraint is not None:
                if constraints.len_constraint.min_value is not None:
                    minimum_len = max(minimum_len, constraints.len_constraint.min_value)

                maximum_len = max(maximum_len, minimum_len)

                if constraints.len_constraint.max_value is not None:
                    maximum_len = min(maximum_len, constraints.len_constraint.max_value)

            length = primitiving.generate_int_in_range(
                path_hash=path_hash, minimum=minimum_len, maximum=maximum_len
            )

            # NOTE: The items must be unique, but the domain of an item may be small
            # (*e.g.*, booleans), so we sample with a bounded number of attempts.
            items = []  # type: List[preseria.PrimitiveValueUnion]
            for attempt in range(length * 20):
                if len(items) == length:
                    break

                item = self.generate_value(
                    path_hash=common.hash_path(
                        prefix_hash=path_hash, segment_or_segments=attempt
                    ),
                    type_annotation=item_annotation,
                    constraints=_NO_CONSTRAINTS,
                )
                assert isinstance(item, preseria.PrimitiveValueTuple)

                if item not in items:
                    items.append(item)

            if len(items) < minimum_len:
                raise AssertionError(
                    f"Failed to sample at least {minimum_len} unique item(s) "
                    f"for {type_annotation}, got only {items!r}."
                )

            return preseria.SetOfPrimitives(items)

        elif isinstance(
            type_annotation,
            (
                intermediate.JsonValueTypeAnnotation,
                intermediate.JsonArrayTypeAnnotation,
                intermediate.JsonObjectTypeAnnotation,
            ),
        ):
            # NOTE: Only raising for now; revisit once the extended meta-model
            # uses the JSON-able types in serializable properties.
            raise NotImplementedError(
                f"Sampling of the JSON-able type annotation {type_annotation} "
                f"is not supported yet."
            )

        else:
            # noinspection PyTypeChecker
            assert_never(type_annotation)

    @ensure(lambda result, cls: result.class_name == cls.name)
    def _generate_minimal_concrete_instance_by_schema(
        self, path_hash: common.CanHash, cls: intermediate.ConcreteClass
    ) -> preseria.Instance:
        """Generate the minimal instance simply following schema constraints."""
        constraints_by_property = self.constraints_by_class[cls]

        preseria_properties: OrderedDict[Identifier, preseria.ValueUnion] = (
            collections.OrderedDict()
        )

        for prop in cls.properties:
            if isinstance(prop.type_annotation, intermediate.OptionalTypeAnnotation):
                continue

            # NOTE (mristin):
            # We had to introduce separate variables to aid debugging; otherwise, they
            # can all be in-lined. We had a serious problem where the hash was not
            # properly updated and resulted in duplicates in a list.

            path_hash = common.hash_path(
                prefix_hash=path_hash, segment_or_segments=prop.name
            )

            value = self.generate_value(
                path_hash=path_hash,
                type_annotation=prop.type_annotation,
                constraints=constraints_by_property[prop],
            )

            preseria_properties[prop.name] = value

        return preseria.Instance(properties=preseria_properties, class_name=cls.name)

    @ensure(lambda cls, result: result.class_name == cls.name)
    def generate_minimal_concrete_instance(
        self, path_hash: common.CanHash, cls: intermediate.ConcreteClass
    ) -> preseria.Instance:
        """Generate the minimal instance of exactly ``cls`` class."""

        # NOTE (mristin):
        # The default behavior is to simply generate the instance using the schema
        # constraints and we pre-define generation for a couple of stable classes
        # across the meta-model versions. The descendants of this generator need to
        # refine the behavior if necessary.

        if cls.is_subclass_of(
            self.symbol_table.must_find_abstract_class(
                Identifier("Abstract_lang_string")
            )
        ):
            instance = preseria.Instance(
                class_name=cls.name,
                properties=collections.OrderedDict(
                    [
                        (
                            Identifier("language"),
                            primitiving.generate_bcp_47_en(
                                path_hash=common.hash_path(
                                    prefix_hash=path_hash,
                                    segment_or_segments="language",
                                )
                            ),
                        )
                    ]
                ),
            )

            self._make_instance_minimal_in_situ(path_hash=path_hash, instance=instance)

            return instance

        if cls is self.symbol_table.must_find_concrete_class(Identifier("Reference")):
            return self.generate_external_reference(path_hash=path_hash)

        elif cls is self.symbol_table.must_find_concrete_class(Identifier("Qualifier")):
            # NOTE (mristin):
            # We introduce a readable, but random qualifier type to avoid problems with
            # duplicates in qualifier types, debugging *etc.* A separate test must
            # verify for all the possible edge cases in qualifier types over patterns.
            instance = preseria.Instance(
                class_name=cls.name,
                properties=collections.OrderedDict(
                    [
                        (
                            Identifier("type"),
                            primitiving.generate_str(
                                path_hash=common.hash_path(
                                    prefix_hash=path_hash, segment_or_segments="type"
                                )
                            ),
                        )
                    ]
                ),
            )

            self._make_instance_minimal_in_situ(path_hash=path_hash, instance=instance)

            return instance

        elif cls is self.symbol_table.must_find_concrete_class(
            Identifier("Asset_information")
        ):
            # NOTE (mristin):
            # We fulfill here the constraints AASd-131 from V3.1. The wording is a bit
            # fuzzy:
            # "Either the global asset ID shall be defined or at least one specific
            # asset ID.:
            #
            # We simply set the global asset ID.
            instance = preseria.Instance(
                class_name=cls.name, properties=collections.OrderedDict()
            )

            global_asset_id_prop = cls.properties_by_name[Identifier("global_asset_ID")]

            instance.properties[Identifier("global_asset_ID")] = self.generate_value(
                path_hash=common.hash_path(path_hash, ["global_asset_ID"]),
                type_annotation=intermediate.beneath_optional(
                    global_asset_id_prop.type_annotation
                ),
                constraints=self.constraints_by_class[cls][global_asset_id_prop],
            )

            self._make_instance_minimal_in_situ(path_hash=path_hash, instance=instance)

            return instance

        elif cls is self.symbol_table.must_find_concrete_class(
            Identifier("Basic_event_element")
        ):
            # NOTE (mristin):
            # Observed must be a model reference to a referable.

            instance = preseria.Instance(
                class_name=cls.name, properties=collections.OrderedDict()
            )

            instance.properties[Identifier("observed")] = (
                self._generate_model_reference(
                    path_hash=common.hash_path(path_hash, ["observed"]),
                    # NOTE (mristin):
                    # The model reference to a property is just an arbitrary choice.
                    final_key_type_name=Identifier("Property"),
                )
            )

            self._make_instance_minimal_in_situ(path_hash=path_hash, instance=instance)

            return instance

        elif cls is self.symbol_table.must_find_concrete_class(
            Identifier("Event_payload")
        ):
            instance = preseria.Instance(
                properties=collections.OrderedDict(), class_name=cls.name
            )

            # Source must be a model reference to an Event element.
            instance.properties[Identifier("source")] = self._generate_model_reference(
                path_hash=common.hash_path(path_hash, "source"),
                final_key_type_name=Identifier("Event_element"),
            )

            # Observable reference must be a model reference to a referable.
            instance.properties[Identifier("observable_reference")] = (
                self._generate_model_reference(
                    path_hash=common.hash_path(path_hash, "observable_reference"),
                    # NOTE (mristin):
                    # The submodel as an observable is an arbitrary choice.
                    final_key_type_name=Identifier("Submodel"),
                )
            )

            self._make_instance_minimal_in_situ(path_hash=path_hash, instance=instance)

            return instance

        elif cls is self.symbol_table.must_find_concrete_class(
            Identifier("Operation_variable")
        ):
            instance = self._generate_minimal_concrete_instance_by_schema(
                path_hash=path_hash, cls=cls
            )

            # Value must have the ID-short specified [...].
            (instance.must_instance("value").properties[Identifier("ID_short")]) = (
                primitiving.generate_id_short(
                    path_hash=common.hash_path(path_hash, ["value", "ID_short"])
                )
            )

            return instance

        else:
            return self._generate_minimal_concrete_instance_by_schema(
                path_hash=path_hash, cls=cls
            )

        raise AssertionError("Expected to return from one of the branches before")

    # fmt: off
    @require(
        lambda cls:
        not (isinstance(cls, intermediate.AbstractClass))
        or (len(cls.concrete_descendants) > 0),
        "Only classes with concrete descendants can be sampled."
    )
    @ensure(
        lambda cls, result:
        (
                result.class_name == cls.name
                or result.class_name in [
                    concrete_cls.name
                    for concrete_cls in cls.concrete_descendants
                ]
        )
    )
    # fmt: on
    def generate_minimal_instance(
        self,
        path_hash: common.CanHash,
        cls: intermediate.ClassUnion,
    ) -> preseria.Instance:
        """
        Generate a minimal instance of the given class.

        If the class is abstract, one of the concrete descendants will be sampled.
        If the class is concrete and has concrete descendants, either the class itself
        or one from its concrete descendants will be sampled.
        """
        concrete_classes = []
        if isinstance(cls, intermediate.ConcreteClass):
            concrete_classes.append(cls)

        concrete_classes.extend(cls.concrete_descendants)

        return self.generate_minimal_concrete_instance(
            path_hash=path_hash,
            cls=primitiving.choose_value(
                path_hash=path_hash,
                choice=concrete_classes,
            ),
        )

    def _make_instance_minimal_in_situ(
        self, path_hash: common.CanHash, instance: preseria.Instance
    ) -> None:
        """Make the instance minimal by setting all the pending required properties."""
        cls = self.symbol_table.must_find_concrete_class(instance.class_name)

        constraints_by_property = self.constraints_by_class[cls]

        for prop in cls.properties:
            if prop.name in instance.properties:
                continue

            if isinstance(prop.type_annotation, intermediate.OptionalTypeAnnotation):
                continue

            instance.properties[prop.name] = self.generate_value(
                path_hash=common.hash_path(
                    prefix_hash=path_hash, segment_or_segments=prop.name
                ),
                type_annotation=intermediate.beneath_optional(prop.type_annotation),
                constraints=constraints_by_property[prop],
            )

    @ensure(lambda result, cls: result.class_name == cls.name)
    def _generate_maximal_concrete_instance_by_schema(
        self,
        path_hash: common.CanHash,
        cls: intermediate.ConcreteClass,
    ) -> preseria.Instance:
        """Generate the maximal instance simply following schema constraints."""
        constraints_by_property = self.constraints_by_class[cls]

        preseria_properties: OrderedDict[Identifier, preseria.ValueUnion] = (
            collections.OrderedDict()
        )

        for prop in cls.properties:
            preseria_properties[prop.name] = self.generate_value(
                path_hash=common.hash_path(
                    prefix_hash=path_hash, segment_or_segments=prop.name
                ),
                type_annotation=intermediate.beneath_optional(prop.type_annotation),
                constraints=constraints_by_property[prop],
            )

        return preseria.Instance(properties=preseria_properties, class_name=cls.name)

    def _make_instance_maximal_in_situ(
        self, path_hash: common.CanHash, instance: preseria.Instance
    ) -> None:
        """Make the instance maximal by setting all the properties not already set."""
        cls = self.symbol_table.must_find_concrete_class(instance.class_name)

        constraints_by_property = self.constraints_by_class[cls]

        for prop in cls.properties:
            if prop.name in instance.properties:
                continue

            instance.properties[prop.name] = self.generate_value(
                path_hash=common.hash_path(
                    prefix_hash=path_hash, segment_or_segments=prop.name
                ),
                type_annotation=intermediate.beneath_optional(prop.type_annotation),
                constraints=constraints_by_property[prop],
            )

    def _with_single_element_lists(self, element: preseria.Instance) -> None:
        """Make all the submodel element lists in the tree have exactly one element."""
        if element.class_name == "Submodel_element_list":
            template = mutable_list_with_two_boolean_properties(instance_generator=self)
            template_value = template.properties[Identifier("value")]
            assert isinstance(template_value, preseria.ListOfInstances)
            del template_value.values[1:]

            for name in (
                "type_value_list_element",
                "value_type_list_element",
                "semantic_ID_list_element",
                "value",
            ):
                element.properties[Identifier(name)] = template.properties[
                    Identifier(name)
                ]

            return

        children_name = {
            "Submodel_element_collection": "value",
            "Entity": "statements",
            "Annotated_relationship_element": "annotations",
        }.get(element.class_name, None)

        if children_name is not None:
            children = element.properties.get(Identifier(children_name), None)
            if isinstance(children, preseria.ListOfInstances):
                for child in children.values:
                    self._with_single_element_lists(child)

    @ensure(lambda cls, result: result.class_name == cls.name)
    def generate_maximal_concrete_instance(
        self,
        path_hash: common.CanHash,
        cls: intermediate.ConcreteClass,
    ) -> preseria.Instance:
        """Generate a maximal instance of the given concrete class."""
        # NOTE (mristin):
        # The default behavior is to simply generate the instance using the schema
        # constraints and we pre-define generation for a couple of stable classes
        # across the meta-model versions. The descendants of this generator need to
        # refine the behavior if necessary.

        if cls is self.symbol_table.must_find_concrete_class(Identifier("Reference")):
            instance = self.generate_external_reference(path_hash=path_hash)

            self._make_instance_maximal_in_situ(path_hash=path_hash, instance=instance)

            return instance

        elif cls is (
            self.symbol_table.must_find_concrete_class(
                Identifier("Submodel_element_list")
            )
        ):
            instance = cast(
                preseria.Instance,
                cast(
                    preseria.ImmutableInstance,
                    _list_with_two_boolean_properties(instance_generator=self),
                ),
            )

            self._make_instance_maximal_in_situ(path_hash=path_hash, instance=instance)

            return instance

        elif cls is (
            self.symbol_table.must_find_concrete_class(
                Identifier("Annotated_relationship_element")
            )
        ):
            instance = self._generate_maximal_concrete_instance_by_schema(
                path_hash=path_hash, cls=cls
            )

            annotations = instance.properties[Identifier("annotations")]
            assert isinstance(annotations, preseria.ListOfInstances)

            for i, annotation in enumerate(annotations.values):
                # ID-shorts need to be defined for all the items of annotations.
                if "ID_short" not in annotation.properties:
                    id_short_prop = cls.properties_by_name[Identifier("ID_short")]

                    annotation.properties[Identifier("ID_short")] = self.generate_value(
                        path_hash=common.hash_path(
                            path_hash, ["annotations", i, "ID_short"]
                        ),
                        type_annotation=intermediate.beneath_optional(
                            id_short_prop.type_annotation
                        ),
                        constraints=self.constraints_by_class[cls][id_short_prop],
                    )

            return instance

        elif cls is (
            self.symbol_table.must_find_concrete_class(
                Identifier("Asset_administration_shell")
            )
        ):
            instance = preseria.Instance(
                properties=collections.OrderedDict(), class_name=cls.name
            )

            # Derived-from must be a model reference to an asset administration shell.
            instance.properties[Identifier("derived_from")] = (
                self._generate_model_reference(
                    path_hash=common.hash_path(path_hash, ["derived_from"]),
                    final_key_type_name=Identifier("Asset_administration_shell"),
                )
            )

            # All submodels must be model references to a submodel.
            instance.properties[Identifier("submodels")] = preseria.ListOfInstances(
                values=[
                    self._generate_model_reference(
                        path_hash=common.hash_path(path_hash, ["submodels", i]),
                        final_key_type_name=Identifier("Submodel"),
                    )
                    for i in range(2)
                ]
            )

            self._make_instance_maximal_in_situ(path_hash=path_hash, instance=instance)

            return instance

        elif cls is (
            self.symbol_table.must_find_concrete_class(
                Identifier("Basic_event_element")
            )
        ):
            # Max. interval is not applicable for input direction.
            instance = preseria.Instance(
                properties=collections.OrderedDict(), class_name=cls.name
            )

            instance.properties[Identifier("direction")] = (
                self.symbol_table.must_find_enumeration(Identifier("Direction"))
                .literals_by_name[Identifier("Output")]
                .value
            )

            # Observed must be a model reference to a referable.
            instance.properties[Identifier("observed")] = (
                self._generate_model_reference(
                    path_hash=common.hash_path(path_hash, ["observed"]),
                    # NOTE (mristin):
                    # Property is an arbitrary choice for a target of a model reference.
                    final_key_type_name=Identifier("Property"),
                )
            )

            # Message broker must be a model reference to a referable.
            instance.properties[Identifier("message_broker")] = (
                self._generate_model_reference(
                    path_hash=common.hash_path(path_hash, ["message_broker"]),
                    # NOTE (mristin):
                    # Property is an arbitrary choice for a target of a model reference.
                    final_key_type_name=Identifier("Property"),
                )
            )

            self._make_instance_maximal_in_situ(path_hash=path_hash, instance=instance)

            return instance
        elif cls is (
            self.symbol_table.must_find_concrete_class(
                Identifier("Concept_description")
            )
        ):
            # For a concept description using data specification template IEC 61360,
            # the definition is mandatory and shall be defined at least in English.

            instance = self._generate_maximal_concrete_instance_by_schema(
                path_hash=path_hash, cls=cls
            )

            if "embedded_data_specifications" in instance.properties:
                embedded_data_specifications = instance.properties[
                    Identifier("embedded_data_specifications")
                ]

                assert isinstance(
                    embedded_data_specifications, preseria.ListOfInstances
                )

                for i, eds in enumerate(embedded_data_specifications.values):
                    dsc = eds.properties[Identifier("data_specification_content")]

                    assert isinstance(dsc, preseria.Instance)
                    if dsc.class_name == Identifier("Data_specification_IEC_61360"):
                        definition = preseria.ListOfInstances(
                            values=[
                                self.generate_minimal_instance(
                                    path_hash=common.hash_path(
                                        path_hash,
                                        [
                                            "embedded_data_specifications",
                                            i,
                                            "data_specification_content",
                                        ],
                                    ),
                                    cls=(
                                        self.symbol_table.must_find_concrete_class(
                                            Identifier(
                                                "Lang_string_definition_type_IEC_61360"
                                            )
                                        )
                                    ),
                                )
                            ]
                        )

                        dsc.properties[Identifier("definition")] = definition

            return instance

        elif cls is (
            self.symbol_table.must_find_concrete_class(
                Identifier("Data_specification_IEC_61360")
            )
        ):
            instance = self._generate_maximal_concrete_instance_by_schema(
                path_hash=path_hash, cls=cls
            )

            # If value is not empty then value list shall be empty and vice versa.
            if "value" in instance.properties:
                instance.properties.pop(Identifier("value_list"), None)

            return instance

        elif cls is (self.symbol_table.must_find_concrete_class(Identifier("Entity"))):
            instance = self._generate_maximal_concrete_instance_by_schema(
                path_hash=path_hash, cls=cls
            )

            # ID-shorts need to be defined for all the items of statements [...].
            statements = instance.properties[Identifier("statements")]
            assert isinstance(statements, preseria.ListOfInstances)

            for i, statement in enumerate(statements.values):
                statement.properties[Identifier("ID_short")] = (
                    primitiving.generate_id_short(
                        path_hash=common.hash_path(
                            path_hash, ["statements", i, "ID_short"]
                        )
                    )
                )

            return instance

        elif cls is (
            self.symbol_table.must_find_concrete_class(Identifier("Event_payload"))
        ):
            # NOTE (mristin):
            # The minimal instance needs to observe the constraints already, but
            # there are no constraints that the maximal constraints need
            # to observe in addition.

            instance = self.generate_minimal_concrete_instance(
                path_hash=path_hash, cls=cls
            )

            self._make_instance_maximal_in_situ(path_hash=path_hash, instance=instance)

            return instance

        elif (
            Identifier("value") in cls.properties_by_name
            and Identifier("value_type") in cls.properties_by_name
        ):
            instance = preseria.Instance(
                properties=collections.OrderedDict(), class_name=cls.name
            )

            value_type_literal = primitiving.choose_value(
                path_hash=common.hash_path(path_hash, ["value_type"]),
                choice=(
                    self.symbol_table.must_find_enumeration(
                        Identifier("Data_type_def_XSD")
                    ).literals
                ),
            )

            instance.properties[Identifier("value")] = self._generate_xs_value(
                path_hash=common.hash_path(path_hash, ["value"]),
                value_type=value_type_literal,
            )

            instance.properties[Identifier("value_type")] = value_type_literal.value

            self._make_instance_maximal_in_situ(path_hash=path_hash, instance=instance)

            return instance

        elif cls.is_subclass_of(
            self.symbol_table.must_find_abstract_class(
                Identifier("Abstract_lang_string")
            )
        ):
            # NOTE (mristin):
            # The minimal instance needs to observe the constraints already, but
            # there are no constraints that the maximal constraints need
            # to observe in addition.

            instance = self.generate_minimal_concrete_instance(
                path_hash=path_hash, cls=cls
            )

            self._make_instance_maximal_in_situ(path_hash=path_hash, instance=instance)

            return instance

        elif cls is self.symbol_table.must_find_concrete_class(Identifier("Operation")):
            instance = self._generate_maximal_concrete_instance_by_schema(
                path_hash=path_hash, cls=cls
            )

            # Value must have the ID-short specified [...].
            input_variables = instance.properties[Identifier("input_variables")]
            assert isinstance(input_variables, preseria.ListOfInstances)

            for i, input_variable in enumerate(input_variables.values):
                (
                    input_variable.must_instance("value").properties[
                        Identifier("ID_short")
                    ]
                ) = primitiving.generate_id_short(
                    path_hash=common.hash_path(
                        path_hash, ["input_variables", i, "value", "ID_short"]
                    )
                )

            output_variables = instance.properties[Identifier("output_variables")]
            assert isinstance(output_variables, preseria.ListOfInstances)

            for i, output_variable in enumerate(output_variables.values):
                (
                    output_variable.must_instance("value").properties[
                        Identifier("ID_short")
                    ]
                ) = primitiving.generate_id_short(
                    path_hash=common.hash_path(
                        path_hash, ["output_variables", i, "value", "ID_short"]
                    )
                )

            inoutput_variables = instance.properties[Identifier("inoutput_variables")]
            assert isinstance(inoutput_variables, preseria.ListOfInstances)

            for i, inoutput_variable in enumerate(inoutput_variables.values):
                (
                    inoutput_variable.must_instance("value").properties[
                        Identifier("ID_short")
                    ]
                ) = primitiving.generate_id_short(
                    path_hash=common.hash_path(
                        path_hash, ["inoutput_variables", i, "value", "ID_short"]
                    )
                )

            if self.single_element_lists_in_operation_variables:
                for variables in (
                    input_variables,
                    output_variables,
                    inoutput_variables,
                ):
                    for variable in variables.values:
                        self._with_single_element_lists(variable.must_instance("value"))

            return instance

        elif cls is self.symbol_table.must_find_concrete_class(
            Identifier("Operation_variable")
        ):
            # NOTE (mristin):
            # The minimal instance needs to observe the constraints already, but
            # there are no constraints that the maximal constraints need
            # to observe in addition.

            instance = self.generate_minimal_concrete_instance(
                path_hash=path_hash, cls=cls
            )

            self._make_instance_maximal_in_situ(path_hash=path_hash, instance=instance)

            return instance

        elif cls is self.symbol_table.must_find_concrete_class(Identifier("Range")):
            instance = preseria.Instance(
                properties=collections.OrderedDict(), class_name=cls.name
            )

            value_type_literal = primitiving.choose_value(
                path_hash=common.hash_path(path_hash, ["value_type"]),
                choice=(
                    self.symbol_table.must_find_enumeration(
                        Identifier("Data_type_def_XSD")
                    ).literals
                ),
            )

            instance.properties[Identifier("min")] = self._generate_xs_value(
                path_hash=common.hash_path(path_hash, ["min"]),
                value_type=value_type_literal,
            )

            instance.properties[Identifier("max")] = self._generate_xs_value(
                path_hash=common.hash_path(path_hash, ["max"]),
                value_type=value_type_literal,
            )

            instance.properties[Identifier("value_type")] = value_type_literal.value

            self._make_instance_maximal_in_situ(path_hash=path_hash, instance=instance)

            return instance

        elif cls is self.symbol_table.must_find_concrete_class(Identifier("Submodel")):
            instance = self._generate_maximal_concrete_instance_by_schema(
                path_hash=path_hash, cls=cls
            )

            # ID-shorts need to be defined for all the items of submodel elements [...]
            submodel_elements = instance.properties[Identifier("submodel_elements")]

            assert isinstance(submodel_elements, preseria.ListOfInstances)
            for i, submodel_element in enumerate(submodel_elements.values):
                submodel_element.properties[Identifier("ID_short")] = (
                    primitiving.generate_id_short(
                        path_hash=common.hash_path(
                            path_hash, ["submodel_elements", i, "ID_short"]
                        )
                    )
                )

            return instance

        elif cls is self.symbol_table.must_find_concrete_class(
            Identifier("Submodel_element_collection")
        ):
            instance = self._generate_maximal_concrete_instance_by_schema(
                path_hash=path_hash, cls=cls
            )

            # ID-shorts need to be defined for all the items of submodel elements [...]
            elements = instance.properties[Identifier("value")]

            assert isinstance(elements, preseria.ListOfInstances)
            for i, element in enumerate(elements.values):
                element.properties[Identifier("ID_short")] = (
                    primitiving.generate_id_short(
                        path_hash=common.hash_path(path_hash, ["value", i, "ID_short"])
                    )
                )

            return instance

        else:
            return self._generate_maximal_concrete_instance_by_schema(
                path_hash=path_hash, cls=cls
            )

        raise AssertionError("Expected to return before in one of the branches")

    # fmt: off
    @require(
        lambda cls:
        not (isinstance(cls, intermediate.AbstractClass))
        or (len(cls.concrete_descendants) > 0),
        "Only classes with concrete descendants can be sampled."
    )
    @ensure(
        lambda cls, result:
        (
                result.class_name == cls.name
                or result.class_name in [
                    concrete_cls.name
                    for concrete_cls in cls.concrete_descendants
                ]
        )
    )
    # fmt: on
    def generate_maximal_instance(
        self, path_hash: common.CanHash, cls: intermediate.ClassUnion
    ) -> preseria.Instance:
        """
        Generate a maximal instance of the given class.

        If the class is abstract, one of the concrete descendants will be sampled.
        If the class is concrete and has concrete descendants, either the class itself
        or one from its concrete descendants will be sampled.
        """
        concrete_classes = []
        if isinstance(cls, intermediate.ConcreteClass):
            concrete_classes.append(cls)

        concrete_classes.extend(cls.concrete_descendants)

        return self.generate_maximal_concrete_instance(
            path_hash=path_hash,
            cls=primitiving.choose_value(
                path_hash=path_hash,
                choice=concrete_classes,
            ),
        )

    # fmt: off
    @require(
        lambda self, value_type:
        self.symbol_table.is_enumeration_literal_of(
            value_type,
            Identifier("Data_type_def_XSD")
        )
    )
    # fmt: on
    def _generate_xs_value(
        self,
        path_hash: common.CanHash,
        value_type: intermediate.EnumerationLiteral,
    ) -> str:
        """Generate a semi-random value corresponding to the ``value_type``."""
        # NOTE (mristin):
        # At the moment (2026-01-08), we assume that the examples for XSD basic data
        # types are stable and pinned to XSD 1.0. If that assumption changes, we have
        # to refactor this function -- possibly make it abstract, and then specify
        # the frozen examples for each meta-model individually.

        return primitiving.choose_value(
            path_hash,
            list(
                frozen_examples_xs_value.BY_VALUE_TYPE[
                    value_type.value
                ].positives.values()
            ),
        )

    @require(
        lambda self, tajp: tajp
        in self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name,
        "The key type must be valid.",
    )
    @ensure(lambda self, result: self.verificator.must(result))
    @ensure(lambda result: result.class_name == Identifier("Key"))
    def create_key(self, tajp: Identifier, value: str) -> preseria.Instance:
        """Create a key with the given type literal name and value."""
        return preseria.Instance(
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(Identifier("Key_types"))
                        .literals_by_name[tajp]
                        .value,
                    ),
                    (Identifier("value"), value),
                ]
            ),
            class_name=Identifier("Key"),
        )

    # fmt: off
    @require(
        lambda self, final_key_type_name:
        final_key_type_name in self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name
    )
    @ensure(lambda result: result.class_name == Identifier("Reference"))
    # fmt: on
    def _generate_model_reference(
        self,
        path_hash: common.CanHash,
        final_key_type_name: Identifier,
    ) -> preseria.Instance:
        """Generate a model reference to something semi-random."""
        # NOTE (mristin):
        # We assume that the structure of the model references is stable, and thus will
        # not change between the meta-model versions. If that is not the case,
        # we need to either refactor the code, or the descendants of this generator
        # need to override this method.

        expected_key_type = self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name[final_key_type_name]

        keys: preseria.ListOfInstances

        if self.symbol_table.is_enumeration_literal_of(
            expected_key_type, Identifier("AAS_identifiables")
        ):
            keys = preseria.ListOfInstances(
                [
                    self.create_key(
                        tajp=final_key_type_name,
                        value=primitiving.generate_urn(
                            common.hash_path(path_hash, ["keys", 0, "value"])
                        ),
                    )
                ]
            )
        elif self.symbol_table.is_enumeration_literal_of(
            expected_key_type, Identifier("AAS_submodel_elements_as_keys")
        ) or expected_key_type.name == Identifier("Referable"):
            keys = preseria.ListOfInstances(
                [
                    self.create_key(
                        tajp=Identifier("Submodel"),
                        value=primitiving.generate_urn(
                            common.hash_path(path_hash, ["keys", 0, "value"])
                        ),
                    ),
                    self.create_key(
                        tajp=expected_key_type.name,
                        value=primitiving.generate_id_short(
                            common.hash_path(path_hash, ["keys", 1, "value"])
                        ),
                    ),
                ]
            )
        else:
            raise NotImplementedError(
                f"Unhandled {expected_key_type=}; when we developed this module "
                f"there were no other key types expected in the meta-model as "
                f"a reference, but this has obviously changed. Please contact "
                f"the developers."
            )

        return preseria.Instance(
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["Model_reference"]
                        .value,
                    ),
                    (Identifier("keys"), keys),
                ]
            ),
            class_name=Identifier("Reference"),
        )

    @ensure(lambda result: result.class_name == Identifier("Reference"))
    def generate_external_reference(
        self,
        path_hash: common.CanHash,
    ) -> preseria.Instance:
        """Generate a semi-random external reference."""
        # NOTE (mristin):
        # We assume that the structure of the external references is stable, and thus
        # will not change between the meta-model versions. If that is not the case,
        # we need to either refactor the code, or the descendants of this generator
        # need to override this method.

        keys = preseria.ListOfInstances(
            [
                self.create_key(
                    tajp=Identifier("Global_reference"),
                    value=primitiving.generate_urn(
                        common.hash_path(path_hash, ["keys", 0, "value"])
                    ),
                )
            ]
        )

        return preseria.Instance(
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["External_reference"]
                        .value,
                    ),
                    (Identifier("keys"), keys),
                ]
            ),
            class_name=Identifier("Reference"),
        )

    @ensure(lambda result: result.class_name == Identifier("Reference"))
    def external_reference_to(
        self,
        value: str,
    ) -> preseria.Instance:
        """Generate an external reference pointing to the given identifier ``value``."""
        # NOTE (mristin):
        # We assume that the structure of the external references is stable, and thus
        # will not change between the meta-model versions. If that is not the case,
        # we need to either refactor the code, or the descendants of this generator
        # need to override this method.

        keys = preseria.ListOfInstances(
            [self.create_key(tajp=Identifier("Global_reference"), value=value)]
        )

        return preseria.Instance(
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["External_reference"]
                        .value,
                    ),
                    (Identifier("keys"), keys),
                ]
            ),
            class_name=Identifier("Reference"),
        )


def generate_minimal_case(
    cls: intermediate.ConcreteClass, instance_generator: InstanceGenerator
) -> casing.CaseMinimal:
    """Generate the test case with an expected minimal instance."""
    try:
        return casing.CaseMinimal(
            instance=instance_generator.verificator.must(
                instance_generator.generate_minimal_concrete_instance(
                    path_hash=common.hash_path(
                        prefix_hash=None, segment_or_segments=[]
                    ),
                    cls=cls,
                )
            )
        )
    except Exception as exception:
        raise AssertionError(
            f"Failed to generate a minimal case for class {cls.name!r}"
        ) from exception


def generate_maximal_case(
    cls: intermediate.ConcreteClass, instance_generator: InstanceGenerator
) -> casing.CaseMaximal:
    """Generate the test case with an expected maximal instance."""
    try:
        return casing.CaseMaximal(
            instance_generator.verificator.must(
                instance_generator.generate_maximal_concrete_instance(
                    path_hash=common.hash_path(
                        prefix_hash=None, segment_or_segments=[]
                    ),
                    cls=cls,
                )
            )
        )
    except Exception as exception:
        raise AssertionError(
            f"Failed to generate a maximal case for class {cls.name!r}"
        ) from exception


class MinMaxCaseRegistry:
    """
    Keep track of generated minimal and maximal cases.

    These fundamental cases are used to build other test cases on top of them.
    """

    minimal_case_map: Final[Mapping[intermediate.ConcreteClass, casing.CaseMinimal]]
    maximal_case_map: Final[Mapping[intermediate.ConcreteClass, casing.CaseMaximal]]

    def __init__(
        self,
        minimal_case_map: Mapping[intermediate.ConcreteClass, casing.CaseMinimal],
        maximal_case_map: Mapping[intermediate.ConcreteClass, casing.CaseMaximal],
    ) -> None:
        self.minimal_case_map = minimal_case_map
        self.maximal_case_map = maximal_case_map


def build_min_max_case_registry(
    instance_generator: InstanceGenerator,
) -> MinMaxCaseRegistry:
    """Go over concrete classes and generate the minimal and maximal cases."""
    minimal_case_map: MutableMapping[intermediate.ConcreteClass, casing.CaseMinimal] = (
        dict()
    )

    maximal_case_map: MutableMapping[intermediate.ConcreteClass, casing.CaseMaximal] = (
        dict()
    )

    for cls in instance_generator.symbol_table.concrete_classes:
        try:
            minimal_case = casing.CaseMinimal(
                instance=instance_generator.verificator.must(
                    instance_generator.generate_minimal_concrete_instance(
                        path_hash=common.hash_path(
                            prefix_hash=None, segment_or_segments=[]
                        ),
                        cls=cls,
                    )
                )
            )
        except Exception as exception:
            raise AssertionError(
                f"Failed to generate a minimal case for class {cls.name!r}"
            ) from exception

        minimal_case_map[cls] = minimal_case

        try:
            maximal_case = casing.CaseMaximal(
                instance=instance_generator.verificator.must(
                    instance_generator.generate_maximal_concrete_instance(
                        path_hash=common.hash_path(
                            prefix_hash=None, segment_or_segments=[]
                        ),
                        cls=cls,
                    )
                )
            )
        except Exception as exception:
            raise AssertionError(
                f"Failed to generate a maximal case for class {cls.name!r}"
            ) from exception

        maximal_case_map[cls] = maximal_case

    return MinMaxCaseRegistry(
        minimal_case_map=minimal_case_map, maximal_case_map=maximal_case_map
    )


def _generate_outside_allowed_values(
    allowed_values: Sequence[Union[bool, int, float, str, bytes]],
) -> Union[bool, int, float, str, bytes]:
    """
    Generate the value outside the set of allowed values.

    >>> _generate_outside_allowed_values(['that', 'other'])
    'unexpected value'

    >>> _generate_outside_allowed_values(['something', 'unexpected value'])
    'really unexpected value'
    """
    if not all(isinstance(allowed_value, str) for allowed_value in allowed_values):
        raise NotImplementedError(
            "We haven't implemented the generation of non-strings "
            "outside a set of allowed values. Please contact the developers."
        )

    allowed_value_set = set(allowed_values)

    value = "unexpected value"
    while value in allowed_value_set:
        value = f"really {value}"

    return value


def human_readable_generate_phrase_from_function_name(function_name: str) -> str:
    """
    Generate a human-readable name from the test case generation function.

    >>> human_readable_generate_phrase_from_function_name(
    ...     '_generate_type_violations'
    ... )
    'generate type violations'
    """
    return function_name.replace("_", " ").strip()


class CaseGenerator(abc.ABC):
    """Generate test cases to be later fully serialized and output as test data."""

    @property
    @abc.abstractmethod
    def symbol_table(self) -> intermediate.SymbolTable:
        """Give the symbol table of the meta-model."""
        raise NotImplementedError()

    @abc.abstractmethod
    def generate(self) -> Iterator[casing.CaseUnion]:
        """Generate the test cases."""
        raise NotImplementedError()


class CaseGeneratorForSchemaConstraints(CaseGenerator):
    """Generate test cases for the given meta-model at the schema level."""

    instance_generator: Final[InstanceGenerator]

    @property
    def verificator(self) -> verification.Verificator:
        """Verificator of the meta-model"""
        return self.instance_generator.verificator

    @override
    @property
    def symbol_table(self) -> intermediate.SymbolTable:
        """Give the symbol table of the meta-model."""
        return self.instance_generator.symbol_table

    @property
    def constraints_by_class(self) -> verification.ReorganizedConstraintsByClass:
        """Give the schema constraints grouped by properties."""
        return self.instance_generator.constraints_by_class

    min_max_case_registry: Final[MinMaxCaseRegistry]

    def __init__(
        self,
        instance_generator: InstanceGenerator,
        min_max_case_registry: MinMaxCaseRegistry,
    ) -> None:
        self.instance_generator = instance_generator
        self.min_max_case_registry = min_max_case_registry

    def _generate_type_violations(
        self, cls: intermediate.ConcreteClass
    ) -> Iterator[casing.CaseTypeViolation]:
        """Generate a type violation for every property in the pre-serialization."""
        maximal_case = self.min_max_case_registry.maximal_case_map[cls]

        for prop in cls.properties:
            if prop.name not in maximal_case.instance.properties:
                continue

            instance = maximal_case.instance.mutable_copy()

            # region Mutate
            type_anno = intermediate.beneath_optional(prop.type_annotation)

            primitive_type = intermediate.try_primitive_type(type_anno)

            if primitive_type is not None or (
                isinstance(type_anno, intermediate.OurTypeAnnotation)
                and isinstance(type_anno.our_type, intermediate.Enumeration)
            ):
                unexpected_reference: preseria.Instance = (
                    self.instance_generator.external_reference_to(
                        value="unexpected reference"
                    )
                )

                instance.properties[prop.name] = unexpected_reference
            else:
                instance.properties[prop.name] = "Unexpected string value"

            yield casing.CaseTypeViolation(
                instance=instance,
                property_name=prop.name,
            )
            # endregion

    def _generate_positive_and_negative_pattern_examples(
        self, cls: intermediate.ConcreteClass
    ) -> Iterator[
        Union[casing.CasePositivePatternExample, casing.CasePatternViolation]
    ]:
        """Generate positive and negative pattern examples."""
        minimal_case = self.min_max_case_registry.minimal_case_map[cls]

        constraints_by_property = self.constraints_by_class[cls]

        for prop in cls.properties:
            property_constraints = constraints_by_property[prop]
            pattern_constraints = property_constraints.patterns

            if len(pattern_constraints) == 0:
                continue

            # NOTE (mristin):
            # We generate separate cases for value/value_type in
            # CaseGeneratorForStableSemantics.
            type_anno = intermediate.beneath_optional(prop.type_annotation)
            if isinstance(
                type_anno, intermediate.OurTypeAnnotation
            ) and type_anno.our_type is (
                self.symbol_table.must_find_constrained_primitive(
                    Identifier("Value_data_type")
                )
            ):
                continue

            # NOTE (mristin):
            # We try to satisfy only the last pattern, hoping that all the previous
            # patterns are satisfied implicitly.
            pattern = pattern_constraints[-1]

            pattern_examples = frozen_examples_pattern.BY_PATTERN[pattern]

            for example_name, example_text in pattern_examples.positives.items():
                # NOTE (mristin):
                # We assume that simply setting the value will not violate any
                # invariants. This might not be true for all meta-models! In that case,
                # you have to override this method, and add generation logic particular
                # for that meta-model.

                instance = minimal_case.instance.mutable_copy()

                instance.properties[prop.name] = example_text

                # NOTE (mristin):
                # We have to fix some classes manually to fulfill their constraints.
                if cls is self.symbol_table.must_find_concrete_class(
                    Identifier("Administrative_information")
                ):
                    # A revision requires a version.
                    if (
                        Identifier("version") not in instance.properties
                        and Identifier("revision") in instance.properties
                    ):
                        instance.properties[Identifier("version")] = (
                            self.instance_generator.generate_value(
                                # NOTE (mristin):
                                # We ignore hash here since version needs not be
                                # unique, so we are OK with any version as long as
                                # the constraints are satisfied.
                                path_hash=common.hash_path(None, []),
                                type_annotation=intermediate.beneath_optional(
                                    cls.properties_by_name[
                                        Identifier("version")
                                    ].type_annotation
                                ),
                                constraints=property_constraints,
                            )
                        )

                elif cls is self.symbol_table.must_find_concrete_class(
                    Identifier("Basic_event_element")
                ):
                    # Max. interval is not applicable for input direction.
                    if prop.name == "max_interval":
                        instance.properties[Identifier("direction")] = (
                            self.symbol_table.must_find_enumeration(
                                Identifier("Direction")
                            )
                            .literals_by_name[Identifier("Output")]
                            .value
                        )
                else:
                    # NOTE (mristin):
                    # No modifications are necessary for the pattern set.
                    pass

                yield casing.CasePositivePatternExample(
                    instance=self.verificator.must(instance),
                    property_name=prop.name,
                    example_name=example_name,
                )

            # NOTE (mristin):
            # We *certainly* violate the pattern constraint, but we might be also
            # violating some other constraint. This is OK, as we want to test
            # for *at least* the pattern violation.
            for example_name, example_text in pattern_examples.negatives.items():
                instance = minimal_case.instance.mutable_copy()

                instance.properties[prop.name] = example_text

                yield casing.CasePatternViolation(
                    instance=instance,
                    property_name=prop.name,
                    example_name=example_name,
                )

    def _generate_required_violations(
        self, cls: intermediate.ConcreteClass
    ) -> Iterator[casing.CaseRequiredViolation]:
        """Generate violations where required properties are removed."""
        minimal_case = self.min_max_case_registry.minimal_case_map[cls]

        for prop in cls.properties:
            if prop.name not in minimal_case.instance.properties:
                continue

            if isinstance(prop.type_annotation, intermediate.OptionalTypeAnnotation):
                continue

            instance = minimal_case.instance.mutable_copy()

            del instance.properties[prop.name]

            yield casing.CaseRequiredViolation(
                instance=instance,
                property_name=prop.name,
            )

    def _generate_length_violations(
        self, cls: intermediate.ConcreteClass
    ) -> Iterator[Union[casing.CaseMinLengthViolation, casing.CaseMaxLengthViolation]]:
        """Generate min. and max. length violations."""
        maximal_case = self.min_max_case_registry.maximal_case_map[cls]

        constraints_by_property = self.constraints_by_class[cls]

        for prop in cls.properties:
            if prop.name not in maximal_case.instance.properties:
                continue

            len_constraint = constraints_by_property[prop].len_constraint

            if len_constraint is None:
                continue

            if len_constraint.min_value is not None and len_constraint.min_value > 0:
                instance = maximal_case.instance.mutable_copy()

                prop_value = instance.properties[prop.name]
                assert isinstance(prop_value, (str, bytes, preseria.ListOfInstances)), (
                    f"Only strings, bytes and lists expected with length constraints, "
                    f"but got type {type(prop_value)} "
                    f"for instance: {preseria.dump(instance)}"
                )

                new_prop_value: Optional[
                    Union[str, bytes, preseria.ListOfInstances]
                ] = None

                if isinstance(prop_value, (str, bytes)):
                    new_prop_value = prop_value[: (len_constraint.min_value - 1)]

                    assert len(new_prop_value) < len_constraint.min_value, (
                        f"{len(new_prop_value)=}, {len(prop_value)=}, "
                        f"{len_constraint.min_value=}"
                    )

                elif isinstance(prop_value, preseria.ListOfInstances):
                    new_prop_value = preseria.ListOfInstances(
                        values=prop_value.values[: (len_constraint.min_value - 1)]
                    )
                else:
                    # noinspection PyTypeChecker
                    assert_never(prop_value)

                assert new_prop_value is not None

                instance.properties[prop.name] = new_prop_value

                yield casing.CaseMinLengthViolation(
                    instance=instance, property_name=prop.name
                )

            if len_constraint.max_value is not None:
                # NOTE (mristin):
                # Since we are dealing with a maximal example, we assume that the value
                # is non-empty, and simply extend it.
                #
                # This is quite brutish, and might violate other constraints as well,
                # but it will *certainly* violate the max value constraint.

                instance = maximal_case.instance.mutable_copy()

                prop_value = instance.properties[prop.name]
                assert isinstance(prop_value, (str, bytes, preseria.ListOfInstances)), (
                    f"Only strings, bytes and lists expected with "
                    f"length constraints, but got type {type(prop_value)} "
                    f"for instance: {preseria.dump(instance)}"
                )

                new_prop_value = None

                if isinstance(prop_value, str):
                    # NOTE (mristin):
                    # This might violate other constraints as well, but will *certainly*
                    # violate the length constraint.
                    new_prop_value = prop_value + primitiving.generate_str_padding(
                        len_constraint.max_value - len(prop_value) + 1
                    )

                    assert len(new_prop_value) > len_constraint.max_value, (
                        f"{len(prop_value)=}, {len(new_prop_value)=}, "
                        f"{len_constraint.max_value=}"
                    )

                elif isinstance(prop_value, bytes):
                    # NOTE (mristin):
                    # This might violate other constraints as well, but will *certainly*
                    # violate the length constraint.
                    new_prop_value = prop_value + primitiving.generate_bytes_padding(
                        len_constraint.max_value - len(prop_value) + 1
                    )

                elif isinstance(prop_value, preseria.ListOfInstances):
                    assert len(prop_value.values) >= 1, (
                        f"Maximal instance expected to have non-empty lists "
                        f"for property {prop.name!r}, "
                        f"but got: {preseria.dump(instance)}"
                    )

                    new_prop_value = preseria.ListOfInstances(
                        values=(
                            prop_value.values
                            # NOTE (mristin):
                            # We duplicate the last value many times to violate
                            # the constraint. While this will certainly violate
                            # the length constraint, it might violate other
                            # constraints as well.
                            + [prop_value.values[-1]]
                            * (len_constraint.max_value - len(prop_value.values) + 1)
                        )
                    )

                else:
                    # noinspection PyTypeChecker
                    assert_never(prop_value)

                assert new_prop_value is not None

                instance.properties[prop.name] = new_prop_value

                yield casing.CaseMaxLengthViolation(
                    instance=instance,
                    property_name=prop.name,
                )

    def _generate_unexpected_additional_properties(
        self, cls: intermediate.ConcreteClass
    ) -> Iterator[casing.CaseUnexpectedAdditionalProperty]:
        """Generate invalid cases with unexpected properties."""
        minimal_case = self.min_max_case_registry.minimal_case_map[cls]

        instance = minimal_case.instance.mutable_copy()

        additional_prop_name = Identifier("unexpected_additional_property")
        while additional_prop_name in cls.properties_by_name:
            additional_prop_name = Identifier(f"really_{additional_prop_name}")

        instance.properties[additional_prop_name] = "UNEXPECTED-ADDITIONAL-PROPERTY"

        yield casing.CaseUnexpectedAdditionalProperty(instance=instance)

    def _generate_enumeration_violations(
        self, cls: intermediate.ConcreteClass
    ) -> Iterator[casing.CaseEnumerationViolation]:
        minimal_case = self.min_max_case_registry.minimal_case_map[cls]

        for prop in cls.properties:
            type_anno = intermediate.beneath_optional(prop.type_annotation)

            if not (
                isinstance(type_anno, intermediate.OurTypeAnnotation)
                and isinstance(type_anno.our_type, intermediate.Enumeration)
            ):
                continue

            instance = minimal_case.instance.mutable_copy()

            invalid_value = "invalid"
            while invalid_value in type_anno.our_type.literal_value_set:
                invalid_value = f"really {invalid_value}"

            # NOTE (mristin):
            # We try the violation based on the best effort. Setting the property to
            # disallowed value might also violate other constraints, but it will
            # *certainly* violate the constraint on enumeration literals.

            instance.properties[prop.name] = invalid_value

            yield casing.CaseEnumerationViolation(
                instance=instance,
                property_name=prop.name,
            )

    def _generate_set_violations(
        self, cls: intermediate.ConcreteClass
    ) -> Iterator[casing.CaseSetViolation]:
        """Generate examples which violate the set of allowed values on a property."""
        minimal_case = self.min_max_case_registry.maximal_case_map[cls]

        constraints_by_properties = self.constraints_by_class[cls]

        for prop in cls.properties:
            type_anno = intermediate.beneath_optional(prop.type_annotation)

            # NOTE (mristin):
            # We handle enumeration violations in a separate generation method.
            if isinstance(type_anno, intermediate.OurTypeAnnotation) and isinstance(
                type_anno.our_type, intermediate.Enumeration
            ):
                continue

            property_constraints = constraints_by_properties[prop]

            if property_constraints.allowed_values is None:
                continue

            instance = minimal_case.instance.mutable_copy()

            # NOTE (mristin):
            # We try the violation based on the best effort. Setting the property to
            # disallowed value might also violate other constraints, but it will
            # *certainly* violate the allowed-value constraint.

            instance.properties[prop.name] = _generate_outside_allowed_values(
                property_constraints.allowed_values
            )

            yield casing.CaseSetViolation(
                instance=instance,
                property_name=prop.name,
            )

    def _generate_cases_for_class(
        self, cls: intermediate.ConcreteClass
    ) -> Iterator[casing.CaseUnion]:
        """Generate the test cases for the given class."""
        # NOTE (mristin):
        # This function generates the set of basic cases which are stable across
        # the meta-model versions. You might have to override and extend this method
        # for the individual meta-model versions.

        yield self.min_max_case_registry.minimal_case_map[cls]

        yield self.min_max_case_registry.maximal_case_map[cls]

        bound_generate_methods: Sequence[
            Callable[[intermediate.ConcreteClass], Iterator[casing.CaseUnion]]
        ] = [
            self._generate_type_violations,
            self._generate_positive_and_negative_pattern_examples,
            self._generate_required_violations,
            self._generate_length_violations,
            self._generate_unexpected_additional_properties,
            self._generate_set_violations,
        ]

        for bound_generate_method in bound_generate_methods:
            try:
                yield from bound_generate_method(cls)
            except Exception as exception:
                what = human_readable_generate_phrase_from_function_name(
                    bound_generate_method.__name__
                )
                raise AssertionError(
                    f"Failed to {what} for class {cls.name!r}"
                ) from exception

    def generate(self) -> Iterator[casing.CaseUnion]:
        """Generate all the cases according to the meta-model."""
        for cls in self.symbol_table.concrete_classes:
            yield from self._generate_cases_for_class(cls)


def test_name_from_function_name() -> Filenameable:
    """Analyze the call stack and produce the name for the test case."""
    current_frame = inspect.currentframe()
    assert current_frame is not None
    assert current_frame.f_back is not None
    function_name = current_frame.f_back.f_code.co_name
    assert function_name.startswith("_generate_"), f"{function_name=}"
    return Filenameable(function_name[10:])


@ensure(
    lambda result: result.class_name == "Submodel_element_list"
    and isinstance(result.properties["value"], preseria.ListOfInstances)
    and len(result.properties["value"].values) == 2
    and all(
        item.class_name == "Property"
        and item.properties[Identifier("value_type")] == "xs:boolean"
        for item in result.properties["value"].values
    )
)
def _list_with_two_boolean_properties(
    instance_generator: InstanceGenerator,
) -> verification.VerifiedInstance:
    """Generate a submodel element list with two boolean properties."""
    semantic_id = instance_generator.generate_external_reference(
        path_hash=common.hash_path(None, ["semantic_ID_list_element"])
    )

    item = preseria.Instance(
        class_name=Identifier("Property"),
        properties=collections.OrderedDict(
            [
                (Identifier("value_type"), "xs:boolean"),
                (Identifier("semantic_ID"), semantic_id.mutable_copy()),
            ]
        ),
    )

    return instance_generator.verificator.must(
        preseria.Instance(
            class_name=Identifier("Submodel_element_list"),
            properties=collections.OrderedDict(
                [
                    (Identifier("value_type_list_element"), "xs:boolean"),
                    (Identifier("type_value_list_element"), "Property"),
                    (Identifier("semantic_ID_list_element"), semantic_id),
                    (Identifier("ID_short"), "someList"),
                    (
                        Identifier("value"),
                        preseria.ListOfInstances(values=[item, item.mutable_copy()]),
                    ),
                ]
            ),
        )
    )


def mutable_list_with_two_boolean_properties(
    instance_generator: InstanceGenerator,
) -> preseria.Instance:
    """Generate a mutable submodel element list with two boolean properties."""
    return cast(
        preseria.Instance,
        cast(
            preseria.ImmutableInstance,
            _list_with_two_boolean_properties(instance_generator=instance_generator),
        ),
    )


class CaseGeneratorForStableSemantics(CaseGenerator):
    """
    Generate the test cases for a meta-model at the semantic level.

    We assume that different meta-models are all stable in regard to these particular
    semantics covered in this generator.
    """

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

    min_max_case_registry: Final[MinMaxCaseRegistry]

    def __init__(
        self,
        instance_generator: InstanceGenerator,
        min_max_case_registry: MinMaxCaseRegistry,
    ) -> None:
        self.instance_generator = instance_generator
        self.min_max_case_registry = min_max_case_registry

    def _generate_date_time_utc_violation_on_february_29th(
        self,
    ) -> Iterator[casing.CaseDateTimeUtcViolationOnFebruary29th]:
        date_time_utc_constrained_primitive = (
            self.symbol_table.must_find_constrained_primitive(
                Identifier("Date_time_UTC")
            )
        )

        for cls in self.symbol_table.concrete_classes:
            minimal_case = self.min_max_case_registry.minimal_case_map[cls]

            for prop in cls.properties:
                type_anno = intermediate.beneath_optional(prop.type_annotation)

                if (
                    isinstance(type_anno, intermediate.OurTypeAnnotation)
                    and type_anno.our_type is date_time_utc_constrained_primitive
                ):
                    instance = minimal_case.instance.mutable_copy()

                    # NOTE (mristin):
                    # This will *certainly* violate the date-time UTC constraint, but
                    # might also violate some other constraints as well.
                    instance.properties[prop.name] = "2022-02-29T12:13:14Z"

                    yield casing.CaseDateTimeUtcViolationOnFebruary29th(
                        instance=instance, property_name=prop.name
                    )

    def _generate_cases_for_value_and_value_types(
        self,
    ) -> Iterator[
        Union[casing.CasePositiveValueExample, casing.CaseInvalidValueExample]
    ]:
        data_type_def_xsd = self.symbol_table.must_find_enumeration(
            Identifier("Data_type_def_XSD")
        )

        classes_with_value_and_value_type = []  # type: List[intermediate.ConcreteClass]
        for cls in self.symbol_table.concrete_classes:
            value_prop = cls.properties_by_name.get(Identifier("value"), None)
            value_type_prop = cls.properties_by_name.get(Identifier("value_type"), None)

            if value_prop is None or value_type_prop is None:
                continue

            value_primitive_type = intermediate.try_primitive_type(
                intermediate.beneath_optional(value_prop.type_annotation)
            )

            if value_primitive_type is not intermediate.PrimitiveType.STR:
                continue

            value_type_prop_type_anno = intermediate.beneath_optional(
                value_type_prop.type_annotation
            )
            if (
                not isinstance(
                    value_type_prop_type_anno, intermediate.OurTypeAnnotation
                )
                or value_type_prop_type_anno.our_type is not data_type_def_xsd
            ):
                continue

            classes_with_value_and_value_type.append(cls)

        for cls in classes_with_value_and_value_type:
            minimal_case = self.min_max_case_registry.minimal_case_map[cls]

            for literal in data_type_def_xsd.literals:
                examples = frozen_examples_xs_value.BY_VALUE_TYPE.get(
                    literal.value, None
                )
                assert examples is not None, (
                    f"The entry is missing "
                    f"in the {frozen_examples_xs_value.__name__!r} "
                    f"for the value type {literal.value!r}"
                )

                for example_name, example_value in examples.positives.items():
                    # NOTE (mristin):
                    # We assume that setting value and value type will not violate
                    # anything in the class. You have to override this method or
                    # refactor the code at a deeper level if that is the case for your
                    # meta-model.
                    instance = minimal_case.instance.mutable_copy()

                    instance.properties[Identifier("value_type")] = literal.value
                    instance.properties[Identifier("value")] = example_value

                    yield casing.CasePositiveValueExample(
                        instance=self.verificator.must(instance),
                        property_name=Identifier("value"),
                        example_name=example_name,
                        value_type_name=literal.name,
                    )

                for example_name, example_value in examples.negatives.items():
                    # NOTE (mristin):
                    # This will *certainly* break value -- value_type constraint,
                    # but might also break some other constraint as well.
                    instance = minimal_case.instance.mutable_copy()

                    instance.properties[Identifier("value_type")] = literal.value
                    instance.properties[Identifier("value")] = example_value

                    yield casing.CaseInvalidValueExample(
                        instance=instance,
                        property_name=Identifier("value"),
                        example_name=example_name,
                        value_type_name=literal.name,
                    )

    def _generate_cases_for_range_value_type(
        self,
    ) -> Iterator[
        Union[casing.CasePositiveRangeExample, casing.CaseInvalidRangeExample]
    ]:
        data_type_def_xsd = self.symbol_table.must_find_enumeration(
            Identifier("Data_type_def_XSD")
        )

        range_cls = self.symbol_table.must_find_concrete_class(Identifier("Range"))

        minimal_case = self.min_max_case_registry.minimal_case_map[range_cls]

        for literal in data_type_def_xsd.literals:
            examples = frozen_examples_xs_value.BY_VALUE_TYPE.get(literal.value, None)
            assert examples is not None, (
                f"The entry is missing "
                f"in the {frozen_examples_xs_value.__name__!r} "
                f"for the value type {literal.value!r}"
            )

            for example_name, example_value in examples.positives.items():
                # NOTE (mristin):
                # We assume that setting min, max and value type will not violate
                # anything in the class. You have to override this method or
                # refactor the code at a deeper level if that is the case for your
                # meta-model.
                instance = minimal_case.instance.mutable_copy()

                instance.properties[Identifier("value_type")] = literal.value
                instance.properties[Identifier("min")] = example_value
                instance.properties[Identifier("max")] = example_value

                yield casing.CasePositiveRangeExample(
                    instance=self.verificator.must(instance),
                    example_name=example_name,
                    value_type_name=literal.name,
                )

            for example_name, example_value in examples.negatives.items():
                # NOTE (mristin):
                # This will *certainly* break min/max -- value_type constraints,
                # but might also break some other constraint as well.
                instance = minimal_case.instance.mutable_copy()

                instance.properties[Identifier("value_type")] = literal.value
                instance.properties[Identifier("min")] = example_value
                instance.properties[Identifier("max")] = example_value

                yield casing.CaseInvalidRangeExample(
                    instance=instance,
                    value_type_name=literal.name,
                    example_name=example_name,
                )

    def _generate_list_two_properties(self) -> Iterator[casing.CasePositiveManual]:
        yield casing.CasePositiveManual(
            instance=_list_with_two_boolean_properties(
                instance_generator=self.instance_generator
            ),
            name=test_name_from_function_name(),
        )

    def _generate_list_one_child_without_semantic_id(
        self,
    ) -> Iterator[casing.CasePositiveManual]:
        lst = mutable_list_with_two_boolean_properties(
            instance_generator=self.instance_generator
        )

        lst_value = lst.properties[Identifier("value")]
        assert isinstance(lst_value, preseria.ListOfInstances)

        first_element = lst_value.values[0]

        assert first_element.class_name == "Property"
        assert "semantic_ID" in first_element.properties

        assert "semantic_ID_list_element" in lst.properties

        # NOTE (mristin):
        # This is OK, since the semantic ID is None and thus mandated by the list.
        del first_element.properties[Identifier("semantic_ID")]

        yield casing.CasePositiveManual(
            instance=self.verificator.must(lst), name=test_name_from_function_name()
        )

    def _generate_list_no_semantic_id_list_element(
        self,
    ) -> Iterator[casing.CasePositiveManual]:
        lst = mutable_list_with_two_boolean_properties(
            instance_generator=self.instance_generator
        )

        assert "semantic_ID_list_element" in lst.properties
        del lst.properties[Identifier("semantic_ID_list_element")]

        yield casing.CasePositiveManual(
            instance=self.verificator.must(lst), name=test_name_from_function_name()
        )

    def _generate_list_violation_of_type_value_list_element(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        lst = mutable_list_with_two_boolean_properties(self.instance_generator)

        lst_value = lst.properties[Identifier("value")]

        assert isinstance(lst_value, preseria.ListOfInstances)
        assert len(lst_value.values) > 0

        range_element = preseria.Instance(
            class_name=Identifier("Range"),
            properties=collections.OrderedDict(
                [
                    (Identifier("value_type"), "xs:boolean"),
                    (
                        Identifier("semantic_ID"),
                        lst.properties[Identifier("semantic_ID_list_element")],
                    ),
                ]
            ),
        )
        _ = self.verificator.must(range_element)

        assert lst.properties[Identifier("type_value_list_element")] == "Property"

        # NOTE (mristin):
        # The range element is valid, but violates type_value_list_element which
        # mandates that all items are Properties.
        lst_value.values[0] = range_element

        yield casing.CaseConstraintViolation(
            instance=lst, name=test_name_from_function_name()
        )

    def _generate_list_violation_of_value_type_list_element(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        lst = mutable_list_with_two_boolean_properties(self.instance_generator)

        lst_value = lst.properties[Identifier("value")]

        assert isinstance(lst_value, preseria.ListOfInstances)
        assert len(lst_value.values) > 0

        first_element = lst_value.values[0]

        assert first_element.class_name == "Property"

        first_element.properties[Identifier("value_type")] = "xs:int"

        _ = self.verificator.must(first_element)

        assert lst.properties[Identifier("value_type_list_element")] == "xs:boolean"

        # NOTE (mristin):
        # The first element is valid, but its value type violates the list's
        # value_type_list_element.

        yield casing.CaseConstraintViolation(
            instance=lst, name=test_name_from_function_name()
        )

    def _generate_list_violation_of_semantic_id_list_element(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        lst = mutable_list_with_two_boolean_properties(
            instance_generator=self.instance_generator
        )

        lst_value = lst.properties[Identifier("value")]

        assert isinstance(lst_value, preseria.ListOfInstances)
        assert len(lst_value.values) > 0

        first_element = lst_value.values[0]

        first_element.properties[Identifier("semantic_ID")] = (
            self.instance_generator.external_reference_to(
                "something-very-different-from-the-expected"
            )
        )

        _ = self.verificator.must(first_element)

        assert "semantic_ID_list_element" in lst.properties

        # NOTE (mristin):
        # The first element is valid, but its semantic ID violates the list's
        # semantic_ID_list_element.

        yield casing.CaseConstraintViolation(
            instance=lst, name=test_name_from_function_name()
        )

    def _generate_list_violation_semantic_id_mismatch_between_elements(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        lst = mutable_list_with_two_boolean_properties(
            instance_generator=self.instance_generator
        )

        lst_value = lst.properties[Identifier("value")]

        assert isinstance(lst_value, preseria.ListOfInstances)
        assert len(lst_value.values) == 2

        first_element, second_element = lst_value.values

        # NOTE (mristin):
        # Without semantic ID list element in the list, the items must have the matching
        # semantic IDs.

        del lst.properties[Identifier("semantic_ID_list_element")]

        first_element.properties[Identifier("semantic_ID")] = (
            self.instance_generator.external_reference_to(
                "something-very-different-from-the-expected"
            )
        )

        second_element.properties[Identifier("semantic_ID")] = (
            self.instance_generator.external_reference_to(
                "yet-something-different-in-the-opposite-direction"
            )
        )

        _ = self.verificator.must(first_element)

        _ = self.verificator.must(second_element)

        assert "semantic_ID_list_element" not in lst.properties

        # NOTE (mristin):
        # The elements are valid, but they have conflicting semantic IDs, and the list
        # does not mandate any through semantic_ID_list_element.

        yield casing.CaseConstraintViolation(
            instance=lst, name=test_name_from_function_name()
        )

    def _generate_external_reference_first_key_in_generic_globally_identifiables(
        self,
    ) -> Iterator[casing.CasePositiveManual]:
        key_type_global_reference = self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name["Global_reference"]

        assert self.symbol_table.is_enumeration_literal_of(
            key_type_global_reference, Identifier("Globally_identifiables")
        )

        instance = preseria.Instance(
            class_name=Identifier("Reference"),
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["External_reference"]
                        .value,
                    ),
                    (
                        Identifier("keys"),
                        preseria.ListOfInstances(
                            [
                                self.instance_generator.create_key(
                                    tajp=key_type_global_reference.name,
                                    value="https://example.com/something",
                                )
                            ]
                        ),
                    ),
                ]
            ),
        )

        yield casing.CasePositiveManual(
            instance=self.verificator.must(instance),
            name=test_name_from_function_name(),
        )

    def _generate_external_reference_last_key_in_generic_globally_identifiable(
        self,
    ) -> Iterator[casing.CasePositiveManual]:
        key_type_global_reference = self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name["Global_reference"]

        assert self.symbol_table.is_enumeration_literal_of(
            key_type_global_reference, Identifier("Globally_identifiables")
        )

        instance = preseria.Instance(
            class_name=Identifier("Reference"),
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["External_reference"]
                        .value,
                    ),
                    (
                        Identifier("keys"),
                        preseria.ListOfInstances(
                            [
                                self.instance_generator.create_key(
                                    tajp=key_type_global_reference.name,
                                    value="https://example.com/something",
                                ),
                                self.instance_generator.create_key(
                                    tajp=key_type_global_reference.name,
                                    value="something-more",
                                ),
                            ]
                        ),
                    ),
                ]
            ),
        )

        yield casing.CasePositiveManual(
            instance=self.verificator.must(instance),
            name=test_name_from_function_name(),
        )

    def _generate_external_reference_last_key_in_generic_fragment_keys(
        self,
    ) -> Iterator[casing.CasePositiveManual]:
        key_type_global_reference = self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name["Global_reference"]

        assert self.symbol_table.is_enumeration_literal_of(
            key_type_global_reference, Identifier("Globally_identifiables")
        )

        key_type_fragment_reference = self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name["Fragment_reference"]

        assert self.symbol_table.is_enumeration_literal_of(
            key_type_fragment_reference, Identifier("Generic_fragment_keys")
        )

        instance = preseria.Instance(
            class_name=Identifier("Reference"),
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["External_reference"]
                        .value,
                    ),
                    (
                        Identifier("keys"),
                        preseria.ListOfInstances(
                            [
                                self.instance_generator.create_key(
                                    tajp=key_type_global_reference.name,
                                    value="https://example.com/something",
                                ),
                                self.instance_generator.create_key(
                                    tajp=key_type_fragment_reference.name,
                                    value="something-more",
                                ),
                            ]
                        ),
                    ),
                ]
            ),
        )

        yield casing.CasePositiveManual(
            instance=self.verificator.must(instance),
            name=test_name_from_function_name(),
        )

    def _generate_external_reference_violation_first_key_not_in_globally_identifiables(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        key_type_blob = self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name["Blob"]

        assert not self.symbol_table.is_enumeration_literal_of(
            key_type_blob, Identifier("Globally_identifiables")
        )

        instance = preseria.Instance(
            class_name=Identifier("Reference"),
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["External_reference"]
                        .value,
                    ),
                    (
                        Identifier("keys"),
                        preseria.ListOfInstances(
                            [
                                self.instance_generator.create_key(
                                    tajp=key_type_blob.name,
                                    value="https://example.com/something",
                                )
                            ]
                        ),
                    ),
                ]
            ),
        )

        yield casing.CaseConstraintViolation(
            instance=instance, name=test_name_from_function_name()
        )

    def _generate_external_reference_violation_invalid_last_key(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        key_type_blob = self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name["Blob"]

        assert not self.symbol_table.is_enumeration_literal_of(
            key_type_blob, Identifier("Generic_globally_identifiables")
        )

        assert not self.symbol_table.is_enumeration_literal_of(
            key_type_blob, Identifier("Generic_fragment_keys")
        )

        instance = preseria.Instance(
            class_name=Identifier("Reference"),
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["External_reference"]
                        .value,
                    ),
                    (
                        Identifier("keys"),
                        preseria.ListOfInstances(
                            [
                                self.instance_generator.create_key(
                                    tajp=Identifier("Global_reference"),
                                    value="https://example.com/something",
                                ),
                                self.instance_generator.create_key(
                                    tajp=key_type_blob.name, value="something_more"
                                ),
                            ]
                        ),
                    ),
                ]
            ),
        )

        yield casing.CaseConstraintViolation(
            instance=instance, name=test_name_from_function_name()
        )

    def _generate_model_reference_first_key_in_globally_and_aas_identifiables(
        self,
    ) -> Iterator[casing.CasePositiveManual]:
        key_type_submodel = self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name["Submodel"]

        assert self.symbol_table.is_enumeration_literal_of(
            key_type_submodel, Identifier("Globally_identifiables")
        )

        assert self.symbol_table.is_enumeration_literal_of(
            key_type_submodel, Identifier("AAS_identifiables")
        )

        instance = preseria.Instance(
            class_name=Identifier("Reference"),
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["Model_reference"]
                        .value,
                    ),
                    (
                        Identifier("keys"),
                        preseria.ListOfInstances(
                            [
                                self.instance_generator.create_key(
                                    tajp=key_type_submodel.name,
                                    value="https://example.com/something",
                                )
                            ]
                        ),
                    ),
                ]
            ),
        )

        yield casing.CasePositiveManual(
            instance=self.verificator.must(instance),
            name=test_name_from_function_name(),
        )

    def _generate_model_reference_fragment_after_blob(
        self,
    ) -> Iterator[casing.CasePositiveManual]:
        instance = preseria.Instance(
            class_name=Identifier("Reference"),
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["Model_reference"]
                        .value,
                    ),
                    (
                        Identifier("keys"),
                        preseria.ListOfInstances(
                            [
                                self.instance_generator.create_key(
                                    tajp=Identifier("Submodel"),
                                    value="https://example.com/something",
                                ),
                                self.instance_generator.create_key(
                                    tajp=Identifier("Blob"), value="something_more"
                                ),
                                self.instance_generator.create_key(
                                    tajp=Identifier("Fragment_reference"),
                                    value="yet_something_more",
                                ),
                            ]
                        ),
                    ),
                ]
            ),
        )

        yield casing.CasePositiveManual(
            instance=self.verificator.must(instance),
            name=test_name_from_function_name(),
        )

    def _generate_model_reference_valid_key_value_after_list(
        self,
    ) -> Iterator[casing.CasePositiveManual]:
        instance = preseria.Instance(
            class_name=Identifier("Reference"),
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["Model_reference"]
                        .value,
                    ),
                    (
                        Identifier("keys"),
                        preseria.ListOfInstances(
                            [
                                self.instance_generator.create_key(
                                    tajp=Identifier("Submodel"),
                                    value="https://example.com/something",
                                ),
                                self.instance_generator.create_key(
                                    tajp=Identifier("Submodel_element_list"),
                                    value="something_more",
                                ),
                                self.instance_generator.create_key(
                                    tajp=Identifier("Property"), value="123"
                                ),
                            ]
                        ),
                    ),
                ]
            ),
        )

        yield casing.CasePositiveManual(
            instance=self.verificator.must(instance),
            name=test_name_from_function_name(),
        )

    def _generate_model_reference_violation_first_key_not_in_globally_identifiables(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        key_type_blob = self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name["Blob"]

        assert not self.symbol_table.is_enumeration_literal_of(
            key_type_blob, Identifier("Globally_identifiables")
        )

        instance = preseria.Instance(
            class_name=Identifier("Reference"),
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["Model_reference"]
                        .value,
                    ),
                    (
                        Identifier("keys"),
                        preseria.ListOfInstances(
                            [
                                self.instance_generator.create_key(
                                    tajp=key_type_blob.name,
                                    value="https://example.com/something",
                                )
                            ]
                        ),
                    ),
                ]
            ),
        )

        yield casing.CaseConstraintViolation(
            instance=instance, name=test_name_from_function_name()
        )

    def _generate_model_reference_violation_first_key_not_in_aas_identifiables(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        key_type_global_reference = self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name["Global_reference"]

        assert not self.symbol_table.is_enumeration_literal_of(
            key_type_global_reference, Identifier("AAS_identifiables")
        )

        instance = preseria.Instance(
            class_name=Identifier("Reference"),
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["Model_reference"]
                        .value,
                    ),
                    (
                        Identifier("keys"),
                        preseria.ListOfInstances(
                            [
                                self.instance_generator.create_key(
                                    tajp=key_type_global_reference.name,
                                    value="https://example.com/something",
                                )
                            ]
                        ),
                    ),
                ]
            ),
        )

        yield casing.CaseConstraintViolation(
            instance=instance, name=test_name_from_function_name()
        )

    def _generate_model_reference_violation_second_key_not_in_fragment_keys(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        key_type_global_reference = self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name["Global_reference"]

        assert not self.symbol_table.is_enumeration_literal_of(
            key_type_global_reference, Identifier("Fragment_keys")
        )

        instance = preseria.Instance(
            class_name=Identifier("Reference"),
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["Model_reference"]
                        .value,
                    ),
                    (
                        Identifier("keys"),
                        preseria.ListOfInstances(
                            [
                                self.instance_generator.create_key(
                                    tajp=Identifier("Submodel"),
                                    value="https://example.com/something",
                                ),
                                self.instance_generator.create_key(
                                    tajp=key_type_global_reference.name,
                                    value="something_more",
                                ),
                            ]
                        ),
                    ),
                ]
            ),
        )

        yield casing.CaseConstraintViolation(
            instance=instance, name=test_name_from_function_name()
        )

    def _generate_model_reference_violation_fragment_reference_in_the_middle(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        key_type_fragment_reference = self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name["Fragment_reference"]

        assert self.symbol_table.is_enumeration_literal_of(
            key_type_fragment_reference, Identifier("Generic_fragment_keys")
        )

        instance = preseria.Instance(
            class_name=Identifier("Reference"),
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["Model_reference"]
                        .value,
                    ),
                    (
                        Identifier("keys"),
                        preseria.ListOfInstances(
                            [
                                self.instance_generator.create_key(
                                    tajp=Identifier("Submodel"),
                                    value="https://example.com/something",
                                ),
                                self.instance_generator.create_key(
                                    tajp=key_type_fragment_reference.name,
                                    value="something_more",
                                ),
                                self.instance_generator.create_key(
                                    tajp=Identifier("Property"),
                                    value="yet_something_more",
                                ),
                            ]
                        ),
                    ),
                ]
            ),
        )

        yield casing.CaseConstraintViolation(
            instance=instance, name=test_name_from_function_name()
        )

    def _generate_model_reference_violation_fragment_reference_not_after_file_or_blob(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        key_type_fragment_reference = self.symbol_table.must_find_enumeration(
            Identifier("Key_types")
        ).literals_by_name["Fragment_reference"]

        assert self.symbol_table.is_enumeration_literal_of(
            key_type_fragment_reference, Identifier("Generic_fragment_keys")
        )

        instance = preseria.Instance(
            class_name=Identifier("Reference"),
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["Model_reference"]
                        .value,
                    ),
                    (
                        Identifier("keys"),
                        preseria.ListOfInstances(
                            [
                                self.instance_generator.create_key(
                                    tajp=Identifier("Submodel"),
                                    value="https://example.com/something",
                                ),
                                self.instance_generator.create_key(
                                    tajp=Identifier("Property"), value="something_more"
                                ),
                                self.instance_generator.create_key(
                                    tajp=key_type_fragment_reference.name,
                                    value="yet_something_more",
                                ),
                            ]
                        ),
                    ),
                ]
            ),
        )

        yield casing.CaseConstraintViolation(
            instance=instance, name=test_name_from_function_name()
        )

    def _generate_model_reference_violation_invalid_key_value_after_list(
        self,
    ) -> Iterator[casing.CaseConstraintViolation]:
        instance = preseria.Instance(
            class_name=Identifier("Reference"),
            properties=collections.OrderedDict(
                [
                    (
                        Identifier("type"),
                        self.symbol_table.must_find_enumeration(
                            Identifier("Reference_types")
                        )
                        .literals_by_name["Model_reference"]
                        .value,
                    ),
                    (
                        Identifier("keys"),
                        preseria.ListOfInstances(
                            [
                                self.instance_generator.create_key(
                                    tajp=Identifier("Submodel"),
                                    value="https://example.com/something",
                                ),
                                self.instance_generator.create_key(
                                    tajp=Identifier("Submodel_element_list"),
                                    value="something_more",
                                ),
                                self.instance_generator.create_key(
                                    tajp=Identifier("Property"), value="-1"
                                ),
                            ]
                        ),
                    ),
                ]
            ),
        )

        yield casing.CaseConstraintViolation(
            instance=instance, name=test_name_from_function_name()
        )

    def generate(self) -> Iterator[casing.CaseUnion]:
        """Generate the test cases."""
        bound_generate_methods: Sequence[Callable[[], Iterator[casing.CaseUnion]]] = [
            self._generate_date_time_utc_violation_on_february_29th,
            self._generate_cases_for_value_and_value_types,
            self._generate_cases_for_range_value_type,
            self._generate_list_two_properties,
            self._generate_list_one_child_without_semantic_id,
            self._generate_list_no_semantic_id_list_element,
            self._generate_list_violation_of_type_value_list_element,
            self._generate_list_violation_of_value_type_list_element,
            self._generate_list_violation_of_semantic_id_list_element,
            self._generate_list_violation_semantic_id_mismatch_between_elements,
            self._generate_external_reference_first_key_in_generic_globally_identifiables,
            self._generate_external_reference_last_key_in_generic_globally_identifiable,
            self._generate_external_reference_last_key_in_generic_fragment_keys,
            self._generate_external_reference_violation_first_key_not_in_globally_identifiables,
            self._generate_external_reference_violation_invalid_last_key,
            self._generate_model_reference_first_key_in_globally_and_aas_identifiables,
            self._generate_model_reference_fragment_after_blob,
            self._generate_model_reference_valid_key_value_after_list,
            self._generate_model_reference_violation_first_key_not_in_globally_identifiables,
            self._generate_model_reference_violation_first_key_not_in_aas_identifiables,
            self._generate_model_reference_violation_second_key_not_in_fragment_keys,
            self._generate_model_reference_violation_fragment_reference_in_the_middle,
            self._generate_model_reference_violation_fragment_reference_not_after_file_or_blob,
            self._generate_model_reference_violation_invalid_key_value_after_list,
        ]

        for bound_generate_method in bound_generate_methods:
            try:
                yield from bound_generate_method()
            except Exception as exception:
                what = human_readable_generate_phrase_from_function_name(
                    bound_generate_method.__name__
                )
                raise AssertionError(f"Failed to {what}") from exception


def assert_all_generate_methods_listed_in_generate_bound_generate_methods(
    cls: Type[CaseGenerator],
) -> None:
    """
    Check that all ``_generate_*`` methods are listed in ``bound_generate_methods``.
    """
    source_code = inspect.getsource(cls)

    # Parse the AST
    tree = ast.parse(source_code)

    assert isinstance(tree, ast.Module)
    class_def = tree.body[0]

    assert isinstance(class_def, ast.ClassDef)
    assert class_def.name == cls.__name__

    generate_method_set = set()  # type: Set[str]
    for node in class_def.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("_generate_"):
            generate_method_set.add(node.name)

    generate_method = None
    for node in class_def.body:
        if isinstance(node, ast.FunctionDef) and node.name == "generate":
            generate_method = node
            break

    if generate_method is None:
        raise AssertionError(f"'generate' method not found in {class_def.name}")

    assignment = None  # type: Optional[Union[ast.AnnAssign, ast.Assign]]
    for statement in generate_method.body:
        # noinspection PyUnresolvedReferences
        if (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.target.id == "bound_generate_methods"
        ) or (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and statement.targets[0].id == "bound_generate_methods"
        ):
            assignment = statement
            break

    if assignment is None:
        raise AssertionError(
            f"Could not find the assignment to 'bound_generate_methods' "
            f"in 'generate' of {class_def.name}"
        )

    bound_generate_method_set = set()  # type: Set[str]

    assert isinstance(assignment.value, ast.List), (
        f"Expected a list literal to be assigned to 'bound_generate_methods', "
        f"but got: {ast.dump(assignment)}"
    )

    for elt in assignment.value.elts:
        assert (
            isinstance(elt, ast.Attribute)
            and isinstance(elt.value, ast.Name)
            and elt.value.id == "self"
        ), (
            f"Expected all items of 'bound_generate_methods' to be bounded methods, "
            f"but got {ast.dump(elt)}"
        )

        bound_generate_method_set.add(elt.attr)

    missing_methods = generate_method_set - bound_generate_method_set
    if missing_methods:
        raise AssertionError(
            f"The following _generate_* methods are not listed in "
            f"bound_generate_methods in {class_def.name}.generate: "
            f"{sorted(missing_methods)}"
        )

    extra_methods = bound_generate_method_set - generate_method_set
    if len(extra_methods) > 0:
        raise AssertionError(
            f"The following methods in bound_generate_methods do not exist as "
            f"_generate_* methods in {class_def.name}: "
            f"{sorted(extra_methods)}"
        )


assert_all_generate_methods_listed_in_generate_bound_generate_methods(
    cls=CaseGeneratorForStableSemantics
)
