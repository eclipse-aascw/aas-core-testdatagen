"""Determine the serialized names of the properties as defined in the meta-model."""

from typing import Optional

import aas_core_codegen.naming
from aas_core_codegen import intermediate
from aas_core_codegen.common import Identifier


def _find_property(
    symbol_table: intermediate.SymbolTable, class_name: str, property_name: str
) -> Optional[intermediate.Property]:
    """Find the property in the class, if both are defined in the symbol table."""
    cls = symbol_table.find_our_type(Identifier(class_name))
    if not isinstance(cls, intermediate.Class):
        return None

    return cls.properties_by_name.get(Identifier(property_name), None)


def json_property(
    symbol_table: intermediate.SymbolTable, class_name: str, property_name: str
) -> str:
    """
    Give the JSON name of the property.

    The explicit ``json_name`` of the meta-model takes precedence. If the property
    is not defined in the meta-model, the name is derived from the identifier.
    """
    prop = _find_property(symbol_table, class_name, property_name)
    if prop is not None:
        return str(prop.json_name)

    return aas_core_codegen.naming.json_property(Identifier(property_name))


def xml_property(
    symbol_table: intermediate.SymbolTable, class_name: str, property_name: str
) -> str:
    """
    Give the XML name of the property.

    The explicit ``xml_name`` of the meta-model takes precedence. If the property
    is not defined in the meta-model, the name is derived from the identifier.
    """
    prop = _find_property(symbol_table, class_name, property_name)
    if prop is not None:
        return str(prop.xml_name)

    return aas_core_codegen.naming.xml_property(Identifier(property_name))
